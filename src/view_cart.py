#!/usr/bin/env python3
import argparse
import sqlite3
import sys

DB_PATH = "data/main.db"


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


def get_cart_items(conn, user_id: int):
    """
    Return all cart items for this user, joined with copy/record/artist info.
    """
    rows = conn.execute(
        """
        SELECT
          ci.cart_item_id,
          ci.quantity,
          c.copy_id,
          c.purchase_price,
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


def print_cart(user, items):
    print()
    print(f"Cart for user {user['user_id']} ({user['username']} / {user['email']}):")
    print("-" * 60)

    if not items:
        print("Your cart is currently empty.\n")
        return

    subtotal = 0.0
    for row in items:
        price = row["purchase_price"] or 0.0
        qty = row["quantity"]
        line_total = price * qty
        subtotal += line_total

        print(
            f"[cart_item_id: {row['cart_item_id']}] "
            f"{row['title']} — {row['artist_name']}"
        )
        print(
            f"    copy_id: {row['copy_id']}, "
            f"qty: {qty}, "
            f"unit price: ${price:.2f}, "
            f"line total: ${line_total:.2f}"
        )
        print()

    print("-" * 60)
    print(f"Cart subtotal (no tax): ${subtotal:.2f}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="View all items in a user's shopping cart."
    )
    parser.add_argument("--user-id", type=int, help="User ID")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.user_id is None:
        try:
            print("===========================================")
            print("=== Vinyl Record Library - View Cart ===")
            print("===========================================")
            args.user_id = int(input("Enter user_id: ").strip())
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

        items = get_cart_items(conn, args.user_id)
        print_cart(user, items)

    except sqlite3.Error as e:
        print(f"\n[DATABASE ERROR] {e}\n")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
