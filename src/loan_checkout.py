#!/usr/bin/env python3
"""
Checkout Loan Workflow
Converts the checkout_workflow.sql into an interactive Python script.
This handles LOANS (temporary checkouts), not purchases.
"""
import argparse
import sqlite3
import sys

DB_PATH = "data/main_V2.db"
LOAN_DURATION_DAYS = 7
DEFAULT_PRICE = 39.99


def get_connection():
    """Establish database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_user(conn, user_id: int):
    """Fetch user details by user_id."""
    return conn.execute(
        "SELECT user_id, username, email FROM Users WHERE user_id = ?",
        (user_id,),
    ).fetchone()


def get_copy_details(conn, copy_id: int):
    """Fetch copy details including record and artist information."""
    return conn.execute(
        """
        SELECT
          c.copy_id,
          c.status,
          c.condition,
          c.barcode,
          c.purchase_price,
          r.record_id,
          r.title,
          a.artist_name
        FROM Copies c
        JOIN Records r ON c.record_id = r.record_id
        JOIN Artists a ON r.artist_id = a.artist_id
        WHERE c.copy_id = ?
        """,
        (copy_id,),
    ).fetchone()


def is_copy_in_cart(conn, copy_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM CartItems WHERE copy_id = ? LIMIT 1",
        (copy_id,),
    ).fetchone()
    return row is not None


def validate_checkout(conn, user, copy):
    """
    Validate that the checkout can proceed.
    Raises ValueError if validation fails.
    """
    if user is None:
        raise ValueError("User not found.")
    
    if copy is None:
        raise ValueError("Copy not found.")
    
    if copy["status"] != "AVAILABLE":
        raise ValueError(
            f"Copy {copy['copy_id']} is not available for checkout. "
            f"Current status: {copy['status']}"
        )

    # Block if the copy is currently in any cart
    if is_copy_in_cart(conn, copy["copy_id"]):
        raise ValueError(
            f"Copy {copy['copy_id']} is currently reserved in a cart and cannot be loaned."
        )


def create_loan(conn, user_id: int, copy_id: int, copy):
    """
    Create a loan record for the checkout.
    Returns the loan_id of the newly created loan.
    """
    cursor = conn.execute(
        """
        INSERT INTO Loans (
          user_id,
          copy_id,
          record_id,
          due_at,
          price_at_checkout,
          notes
        )
        VALUES (?, ?, ?, datetime('now', ?), ?, ?)
        """,
        (
            user_id,
            copy_id,
            copy["record_id"],
            f"+{LOAN_DURATION_DAYS} days",
            DEFAULT_PRICE,
            f"Standard {LOAN_DURATION_DAYS}-day checkout",
        ),
    )
    return cursor.lastrowid


def mark_copy_checked_out(conn, copy_id: int):
    """Update the copy status to CHECKED_OUT."""
    conn.execute(
        """
        UPDATE Copies
        SET status = 'CHECKED_OUT'
        WHERE copy_id = ?
          AND status = 'AVAILABLE'
        """,
        (copy_id,),
    )


def create_pending_charge(conn, loan_id: int):
    """Create a pending purchase charge for the loan."""
    conn.execute(
        """
        INSERT INTO Charges (loan_id, type, amount, status)
        VALUES (?, 'purchase', ?, 'pending')
        """,
        (loan_id, DEFAULT_PRICE),
    )


def print_checkout_summary(user, copy, loan_id, due_date):
    """Print a summary of the successful checkout."""
    print()
    print("=" * 60)
    print("LOAN CHECKOUT SUCCESSFUL")
    print("=" * 60)
    print()
    print(f"User:        {user['username']} (ID: {user['user_id']})")
    print(f"Email:       {user['email']}")
    print()
    print(f"Record:      {copy['title']}")
    print(f"Artist:      {copy['artist_name']}")
    print(f"Copy ID:     {copy['copy_id']}")
    print(f"Barcode:     {copy['barcode']}")
    print(f"Condition:   {copy['condition']}")
    print()
    print(f"Loan ID:     {loan_id}")
    print(f"Checkout:    Now")
    print(f"Due Date:    {due_date}")
    print(f"Duration:    {LOAN_DURATION_DAYS} days")
    print()
    print(f"Price:       ${DEFAULT_PRICE:.2f} (if purchased)")
    print()
    print("=" * 60)
    print()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Checkout a record copy as a loan for a user."
    )
    parser.add_argument("--user-id", type=int, help="User ID")
    parser.add_argument("--copy-id", type=int, help="Copy ID to checkout")
    return parser.parse_args()


def main():
    args = parse_args()

    # Prompt for user_id if not provided
    if args.user_id is None:
        try:
            args.user_id = int(input("Enter user_id: ").strip())
        except ValueError:
            print("Invalid user_id. Must be an integer.")
            sys.exit(1)

    # Prompt for copy_id if not provided
    if args.copy_id is None:
        try:
            args.copy_id = int(input("Enter copy_id to checkout: ").strip())
        except ValueError:
            print("Invalid copy_id. Must be an integer.")
            sys.exit(1)

    # Connect to database
    try:
        conn = get_connection()
    except sqlite3.Error as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        # Fetch user and copy details
        user = get_user(conn, args.user_id)
        copy = get_copy_details(conn, args.copy_id)

        # Validate checkout
        validate_checkout(conn, user, copy)

        # Begin transaction
        conn.execute("BEGIN TRANSACTION;")

        # Create loan
        loan_id = create_loan(conn, args.user_id, args.copy_id, copy)

        # Mark copy as checked out
        mark_copy_checked_out(conn, args.copy_id)

        # Create pending charge
        create_pending_charge(conn, loan_id)

        # Get the due date for display
        due_date_row = conn.execute(
            "SELECT due_at FROM Loans WHERE loan_id = ?",
            (loan_id,),
        ).fetchone()
        due_date = due_date_row["due_at"] if due_date_row else "Unknown"

        # Commit transaction
        conn.commit()

        # Print success summary
        print_checkout_summary(user, copy, loan_id, due_date)

    except ValueError as ve:
        conn.rollback()
        print(f"\n[VALIDATION ERROR] {ve}\n")
        sys.exit(1)
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[DATABASE ERROR] {e}\n")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
