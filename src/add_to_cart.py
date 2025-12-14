#!/usr/bin/env python3
import argparse
import sqlite3
import sys

DB_PATH = "data/main.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Make sure foreign key constraints are enforced
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_user(conn, user_id: int):
    row = conn.execute(
        "SELECT user_id, username, email FROM Users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return row


def get_copy_for_sale(conn, copy_id: int):
    """
    Return details for a copy that *might* be sellable.
    We'll validate status and price here.
    """
    row = conn.execute(
        """
        SELECT
          c.copy_id,
          c.record_id,
          c.purchase_price,
          c.status,
          r.title,
          a.artist_name
        FROM Copies c
        JOIN Records r ON c.record_id = r.record_id
        JOIN Artists a ON r.artist_id = a.artist_id
        WHERE c.copy_id = ?
        """,
        (copy_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Copy {copy_id} does not exist.")

    # Business rules for "sellable"
    if row["status"] != "AVAILABLE":
        raise ValueError(
            f"Copy {copy_id} is not available for sale (status={row['status']})."
        )

    price = row["purchase_price"]
    # With your schema's DEFAULT 0, treat 0 as "not for sale"
    if price is None or price <= 0:
        raise ValueError(
            f"Copy {copy_id} does not have a valid sale price (purchase_price={price})."
        )

    return row


def add_to_cart(conn, user_id: int, copy_id: int, quantity: int = 1):
    """
    Insert a row into CartItems. For now we only support copy-level items.
    """
    if quantity <= 0:
        raise ValueError("Quantity must be a positive integer.")

    # Ensure user exists
    user = get_user(conn, user_id)
    if user is None:
        raise ValueError(f"User {user_id} does not exist.")

    # Ensure copy is sellable
    copy_row = get_copy_for_sale(conn, copy_id)

    try:
        conn.execute(
            """
            INSERT INTO CartItems (user_id, copy_id, quantity)
            VALUES (?, ?, ?);
            """,
            (user_id, copy_id, quantity),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        # Likely UNIQUE(user_id, copy_id) violation
        msg = str(e).lower()
        if "unique" in msg:
            raise ValueError(
                f"Copy {copy_id} is already in the cart for user {user_id}."
            ) from e
        raise

    return user, copy_row


def print_cart_confirmation(user, copy_row, quantity):
    print("\nItem added to cart:\n")
    print(f"  User:    {user['user_id']} ({user['username']} / {user['email']})")
    print(
        f"  Record:  {copy_row['title']} — {copy_row['artist_name']} "
        f"(copy_id={copy_row['copy_id']})"
    )
    print(f"  Price:   ${copy_row['purchase_price']:.2f}")
    print(f"  Qty:     {quantity}")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Add a vinyl copy to a user's shopping cart."
    )
    parser.add_argument("--user-id", type=int, help="User ID")
    parser.add_argument("--copy-id", type=int, help="Copy ID to add to the cart")
    parser.add_argument(
        "--quantity",
        type=int,
        default=1,
        help="Quantity to add (default: 1)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Interactive fallback if args were omitted
    if args.user_id is None:
        try:
            print("=========================================")
            print("=== Vinyl Record Library - Add to Cart ===")
            print("=========================================")
            args.user_id = int(input("Enter user_id: ").strip())
        except ValueError:
            print("Invalid user_id.")
            sys.exit(1)

    if args.copy_id is None:
        try:
            args.copy_id = int(input("Enter copy_id to add to cart: ").strip())
        except ValueError:
            print("Invalid copy_id.")
            sys.exit(1)

    try:
        conn = get_connection()
    except sqlite3.Error as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        user, copy_row = add_to_cart(conn, args.user_id, args.copy_id, args.quantity)
        print_cart_confirmation(user, copy_row, args.quantity)
    except ValueError as ve:
        print(f"\n[ERROR] {ve}\n")
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"\n[DATABASE ERROR] {e}\n")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
