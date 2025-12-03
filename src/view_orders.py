#!/usr/bin/env python3
import argparse
import sqlite3
import sys
import json
from typing import Optional, List

DB_PATH = "data/main_V2.db"


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


def get_orders_for_user(
    conn,
    user_id: int,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
):
    """
    Return a summary of all orders for this user, including:
      - basic order info
      - count of items
      - latest payment status (if any)
    """
    params: List = [user_id]

    where_status = ""
    if status:
        where_status = " AND o.status = ?"
        params.append(status)

    limit_clause = ""
    if isinstance(limit, int) and limit > 0:
        limit_clause = " LIMIT ?"
        params.append(limit)

    offset_clause = ""
    if isinstance(offset, int) and offset >= 0:
        if not limit_clause:
            limit_clause = " LIMIT -1"  # no upper bound
        offset_clause = " OFFSET ?"
        params.append(offset)

    rows = conn.execute(
        f"""
        SELECT
          o.order_id,
          o.status AS order_status,
          o.subtotal,
          o.tax_amount,
          o.total_amount,
          o.created_at,
          COUNT(DISTINCT oi.order_item_id) AS item_count,
          COALESCE(
            (
              SELECT p.status
              FROM Payments p
              WHERE p.order_id = o.order_id
              ORDER BY p.processed_at DESC, p.payment_id DESC
              LIMIT 1
            ),
            'none'
          ) AS payment_status
        FROM Orders o
        LEFT JOIN OrderItems oi ON o.order_id = oi.order_id
        WHERE o.user_id = ?{where_status}
        GROUP BY o.order_id
        ORDER BY o.created_at DESC, o.order_id DESC{limit_clause}{offset_clause};
        """,
        tuple(params),
    ).fetchall()
    return rows


def get_order_with_payment(conn, user_id: int, order_id: int):
    """
    Get a single order for this user, plus the latest payment info (if any).
    """
    row = conn.execute(
        """
        SELECT
          o.order_id,
          o.user_id,
          o.status AS order_status,
          o.subtotal,
          o.tax_amount,
          o.total_amount,
          o.created_at,
          o.updated_at,
          o.shipping_name,
          o.shipping_address,
          o.notes,
          p.payment_id,
          p.status AS payment_status,
          p.method AS payment_method,
          p.amount AS payment_amount,
          p.transaction_ref,
          p.processed_at AS payment_processed_at
        FROM Orders o
        LEFT JOIN Payments p
          ON p.order_id = o.order_id
         AND p.payment_id = (
              SELECT p2.payment_id
              FROM Payments p2
              WHERE p2.order_id = o.order_id
              ORDER BY p2.processed_at DESC, p2.payment_id DESC
              LIMIT 1
            )
        WHERE o.order_id = ?
          AND o.user_id = ?
        LIMIT 1;
        """,
        (order_id, user_id),
    ).fetchone()
    return row


def get_order_items(conn, order_id: int):
    """
    Get all line items for this order.
    We rely on the snapshot fields stored in OrderItems (description, prices).
    """
    rows = conn.execute(
        """
        SELECT
          order_item_id,
          copy_id,
          record_id,
          description,
          unit_price,
          quantity,
          line_total
        FROM OrderItems
        WHERE order_id = ?
        ORDER BY order_item_id;
        """,
        (order_id,),
    ).fetchall()
    return rows


def print_orders_summary(user, orders):
    print()
    print(
        f"Orders for user {user['user_id']} "
        f"({user['username']} / {user['email']}):"
    )
    print("-" * 70)

    if not orders:
        print("No orders found.\n")
        return

    for row in orders:
        print(
            f"Order {row['order_id']}: "
            f"status={row['order_status']}, "
            f"items={row['item_count']}, "
            f"total=${row['total_amount']:.2f}"
        )
        print(
            f"    created_at: {row['created_at']}, "
            f"payment_status: {row['payment_status']}"
        )
        print()

    print("-" * 70)
    print(
        "To view details for a specific order, run:\n"
        "  python view_orders.py --user-id <id> --order-id <order_id>\n"
    )


def print_orders_summary_json(user, orders):
    payload = {
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
        },
        "orders": [
            {
                "order_id": row["order_id"],
                "status": row["order_status"],
                "item_count": row["item_count"],
                "subtotal": float(row["subtotal"]) if row["subtotal"] is not None else None,
                "tax_amount": float(row["tax_amount"]) if row["tax_amount"] is not None else None,
                "total_amount": float(row["total_amount"]) if row["total_amount"] is not None else None,
                "created_at": row["created_at"],
                "payment_status": row["payment_status"],
            }
            for row in orders
        ],
    }
    print(json.dumps(payload, indent=2))


def print_order_detail(user, order, items):
    print()
    print(
        f"Order detail for user {user['user_id']} "
        f"({user['username']} / {user['email']}):"
    )
    print("-" * 70)
    print(f"Order ID:      {order['order_id']}")
    print(f"Status:        {order['order_status']}")
    print(f"Created at:    {order['created_at']}")
    print(f"Updated at:    {order['updated_at']}")
    print(f"Subtotal:      ${order['subtotal']:.2f}")
    print(f"Tax amount:    ${order['tax_amount']:.2f}")
    print(f"Total amount:  ${order['total_amount']:.2f}")
    if order["shipping_name"] or order["shipping_address"]:
        print(f"Ship to:       {order['shipping_name']}")
        print(f"Shipping addr: {order['shipping_address']}")
    if order["notes"]:
        print(f"Notes:         {order['notes']}")

    print()
    print("Payment info:")
    if order["payment_id"] is None:
        print("    No payment record found.")
    else:
        print(
            f"    payment_id:     {order['payment_id']}, "
            f"status: {order['payment_status']}"
        )
        print(
            f"    method:         {order['payment_method']}, "
            f"amount: ${order['payment_amount']:.2f}"
        )
        print(
            f"    transaction_ref: {order['transaction_ref']}, "
            f"processed_at: {order['payment_processed_at']}"
        )

    print()
    print("Line items:")
    if not items:
        print("    (No items found for this order.)")
    else:
        for row in items:
            print(
                f"  [order_item_id: {row['order_item_id']}] "
                f"{row['description']}"
            )
            print(
                f"      copy_id: {row['copy_id']}, "
                f"record_id: {row['record_id']}, "
                f"qty: {row['quantity']}, "
                f"unit: ${row['unit_price']:.2f}, "
                f"line total: ${row['line_total']:.2f}"
            )
            print()

    print("-" * 70)
    print()


def print_order_detail_json(user, order, items):
    payload = {
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
        },
        "order": {
            "order_id": order["order_id"],
            "status": order["order_status"],
            "subtotal": float(order["subtotal"]) if order["subtotal"] is not None else None,
            "tax_amount": float(order["tax_amount"]) if order["tax_amount"] is not None else None,
            "total_amount": float(order["total_amount"]) if order["total_amount"] is not None else None,
            "created_at": order["created_at"],
            "updated_at": order["updated_at"],
            "shipping_name": order["shipping_name"],
            "shipping_address": order["shipping_address"],
            "notes": order["notes"],
            "payment": None
            if order["payment_id"] is None
            else {
                "payment_id": order["payment_id"],
                "status": order["payment_status"],
                "method": order["payment_method"],
                "amount": float(order["payment_amount"]) if order["payment_amount"] is not None else None,
                "transaction_ref": order["transaction_ref"],
                "processed_at": order["payment_processed_at"],
            },
        },
        "items": [
            {
                "order_item_id": row["order_item_id"],
                "copy_id": row["copy_id"],
                "record_id": row["record_id"],
                "description": row["description"],
                "unit_price": float(row["unit_price"]) if row["unit_price"] is not None else None,
                "quantity": row["quantity"],
                "line_total": float(row["line_total"]) if row["line_total"] is not None else None,
            }
            for row in items
        ],
    }
    print(json.dumps(payload, indent=2))


def parse_args():
    parser = argparse.ArgumentParser(
        description="View a user's orders (summary or detail)."
    )
    parser.add_argument("--user-id", type=int, help="User ID", required=False)
    parser.add_argument(
        "--order-id",
        type=int,
        help="Specific order ID to view in detail",
        required=False,
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Filter summary by order status (e.g., 'pending','paid','shipped')",
        required=False,
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of orders returned in summary",
        required=False,
    )
    parser.add_argument(
        "--offset",
        type=int,
        help="Offset for orders summary pagination",
        required=False,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
        required=False,
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Interactive prompt if user_id omitted
    if args.user_id is None:
        try:
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

        if args.order_id is None:
            # Show summary of all orders for this user
            # Validate pagination inputs
            if args.limit is not None and args.limit <= 0:
                print("--limit must be a positive integer")
                sys.exit(1)
            if args.offset is not None and args.offset < 0:
                print("--offset must be a non-negative integer")
                sys.exit(1)

            orders = get_orders_for_user(
                conn,
                args.user_id,
                status=args.status,
                limit=args.limit,
                offset=args.offset,
            )
            if args.json:
                print_orders_summary_json(user, orders)
            else:
                print_orders_summary(user, orders)
        else:
            # Show details for a specific order
            order = get_order_with_payment(conn, args.user_id, args.order_id)
            if order is None:
                print(
                    f"\nOrder {args.order_id} not found for user {args.user_id}.\n"
                )
                sys.exit(1)

            items = get_order_items(conn, args.order_id)
            if args.json:
                print_order_detail_json(user, order, items)
            else:
                print_order_detail(user, order, items)

    except sqlite3.Error as e:
        print(f"\n[DATABASE ERROR] {e}\n")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
