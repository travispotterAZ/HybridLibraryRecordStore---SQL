#!/usr/bin/env python3
import argparse
import sqlite3
import sys

DB_PATH = "data/main_V2.db"
TAX_RATE = 0.0  # Set to something like 0.08 if you want tax


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_user(conn, user_id: int):
    return conn.execute(
        "SELECT user_id, username, email FROM Users WHERE user_id = ?",
        (user_id,),
    ).fetchone()


def get_cart_items_for_checkout(conn, user_id: int):
    """
    Fetch cart items joined with copies/records/artists for this user.
    """
    rows = conn.execute(
        """
        SELECT
          ci.cart_item_id,
          ci.quantity,
          c.copy_id,
          c.purchase_price,
          c.status AS copy_status,
          r.record_id,
          r.title,
          a.artist_name
        FROM CartItems ci
        JOIN Copies c   ON ci.copy_id = c.copy_id
        JOIN Records r  ON c.record_id = r.record_id
        JOIN Artists a  ON r.artist_id = a.artist_id
        WHERE ci.user_id = ?
        ORDER BY a.artist_name, r.title, c.copy_id;
        """,
        (user_id,),
    ).fetchall()
    return rows


def validate_cart_items(items):
    """
    Ensure all items are still available for sale and have valid prices.
    Raises ValueError if anything is wrong.
    """
    if not items:
        raise ValueError("Cart is empty; nothing to checkout.")

    for row in items:
        status = row["copy_status"]
        price = row["purchase_price"]

        if status != "AVAILABLE":
            raise ValueError(
                f"Copy {row['copy_id']} is not available (status={status}). "
                "You may need to remove it from the cart."
            )

        if price is None or price <= 0:
            raise ValueError(
                f"Copy {row['copy_id']} has no valid sale price (purchase_price={price})."
            )


def create_order(conn, user_id: int, items):
    """
    Compute totals, create an Orders row and corresponding OrderItems rows.
    Returns (order_id, subtotal, tax_amount, total_amount).
    """
    subtotal = 0.0
    for row in items:
        price = row["purchase_price"] or 0.0
        qty = row["quantity"]
        subtotal += price * qty

    tax_amount = round(subtotal * TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)

    # For now, we won't capture shipping info; leave it NULL
    cur = conn.execute(
        """
        INSERT INTO Orders (
          user_id,
          status,
          subtotal,
          tax_amount,
          total_amount,
          shipping_name,
          shipping_address,
          notes,
          created_at
        )
        VALUES (?, 'paid', ?, ?, ?, NULL, NULL, NULL, datetime('now'));
        """,
        (user_id, subtotal, tax_amount, total_amount),
    )
    order_id = cur.lastrowid

    # Insert order items (snapshot of what was purchased)
    for row in items:
        price = row["purchase_price"] or 0.0
        qty = row["quantity"]
        line_total = price * qty

        description = f"{row['title']} — {row['artist_name']}"

        conn.execute(
            """
            INSERT INTO OrderItems (
              order_id,
              copy_id,
              record_id,
              description,
              unit_price,
              quantity,
              line_total
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                order_id,
                row["copy_id"],
                row["record_id"],
                description,
                price,
                qty,
                line_total,
            ),
        )

    return order_id, subtotal, tax_amount, total_amount


def create_payment(conn, order_id: int, total_amount: float):
    """
    Simulate a successful payment for this order.
    """
    conn.execute(
        """
        INSERT INTO Payments (
          order_id,
          amount,
          method,
          status,
          transaction_ref,
          processed_at
        )
        VALUES (?, ?, 'test', 'captured', 'TEST-TXN', datetime('now'));
        """,
        (order_id, total_amount),
    )


def mark_copies_sold(conn, items):
    """
    Update Copies.status to 'SOLD' for all purchased copies.
    """
    copy_ids = [row["copy_id"] for row in items]
    if not copy_ids:
        return

    placeholders = ",".join(["?"] * len(copy_ids))
    conn.execute(
        f"""
        UPDATE Copies
        SET status = 'SOLD'
        WHERE copy_id IN ({placeholders});
        """,
        copy_ids,
    )


def clear_cart(conn, user_id: int):
    conn.execute(
        "DELETE FROM CartItems WHERE user_id = ?;",
        (user_id,),
    )


def print_order_summary(user, order_id, items, subtotal, tax_amount, total_amount):
    print()
    print(f"Checkout complete for user {user['user_id']} "
          f"({user['username']} / {user['email']})")
    print(f"Order ID: {order_id}")
    print("-" * 60)

    for row in items:
        price = row["purchase_price"] or 0.0
        qty = row["quantity"]
        line_total = price * qty

        print(
            f"{row['title']} — {row['artist_name']} "
            f"(copy_id={row['copy_id']})"
        )
        print(
            f"    qty: {qty}, "
            f"unit price: ${price:.2f}, "
            f"line total: ${line_total:.2f}"
        )
        print()

    print("-" * 60)
    print(f"Subtotal:  ${subtotal:.2f}")
    print(f"Tax:       ${tax_amount:.2f}")
    print(f"Total:     ${total_amount:.2f}")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Checkout all items in a user's shopping cart."
    )
    parser.add_argument("--user-id", type=int, help="User ID")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.user_id is None:
        try:
            print("=========================================")
            print("=== Vinyl Record Library - Checkout Cart ===")   
            print("=========================================")
            args.user_id = int(input("Enter user_id to checkout: ").strip())
        except ValueError:
            print("Invalid user_id.")
            sys.exit(1)

    try:
        conn = get_connection()
    except sqlite3.Error as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        user = get_user(conn, args.user_id)
        if user is None:
            print(f"\nUser {args.user_id} does not exist.\n")
            sys.exit(1)

        items = get_cart_items_for_checkout(conn, args.user_id)
        validate_cart_items(items)

        # Use an explicit transaction for all-or-nothing behavior
        conn.execute("BEGIN;")

        order_id, subtotal, tax_amount, total_amount = create_order(
            conn, args.user_id, items
        )
        create_payment(conn, order_id, total_amount)
        mark_copies_sold(conn, items)
        clear_cart(conn, args.user_id)

        conn.commit()

        print_order_summary(user, order_id, items, subtotal, tax_amount, total_amount)

    except ValueError as ve:
        conn.rollback()
        print(f"\n[CHECKOUT ERROR] {ve}\n")
        sys.exit(1)
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[DATABASE ERROR] {e}\n")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
