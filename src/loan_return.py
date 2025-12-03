#!/usr/bin/env python3
"""
Return Loan Workflow
Converts sql/return_workflow.sql into an interactive Python script.
Allows returning a checked-out record (loan) and voids pending charges.

Usage examples:
  python src/return_loan.py --loan-id 2
  python src/return_loan.py --user-id 1 --copy-id 4
  python src/return_loan.py  # prompts for identifiers
"""
import argparse
import sqlite3
import sys
from typing import Optional, Tuple

DB_PATH = "data/main_V2.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def find_active_loan_by_id(conn, loan_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT l.*, u.username, r.title, a.artist_name
        FROM Loans l
        JOIN Users u   ON l.user_id = u.user_id
        JOIN Records r ON l.record_id = r.record_id
        JOIN Artists a ON r.artist_id = a.artist_id
        WHERE l.loan_id = ? AND l.returned_at IS NULL
        """,
        (loan_id,),
    ).fetchone()


def find_active_loan_by_user_copy(conn, user_id: int, copy_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT l.*, u.username, r.title, a.artist_name
        FROM Loans l
        JOIN Users u   ON l.user_id = u.user_id
        JOIN Records r ON l.record_id = r.record_id
        JOIN Artists a ON r.artist_id = a.artist_id
        WHERE l.user_id = ? AND l.copy_id = ? AND l.returned_at IS NULL
        ORDER BY l.loan_id DESC
        LIMIT 1
        """,
        (user_id, copy_id),
    ).fetchone()


def return_loan(conn, loan_id: int, copy_id: int) -> Tuple[int, int, int]:
    """
    Perform the return workflow:
      1) Mark the loan as returned (returned_at = now)
      2) Set the copy back to AVAILABLE (if currently CHECKED_OUT)
      3) Void any pending purchase charge for this loan

    Returns a tuple of (loans_updated, copies_updated, charges_voided).
    """
    # 1) Mark the loan as returned
    cur1 = conn.execute(
        """
        UPDATE Loans
        SET returned_at = datetime('now')
        WHERE loan_id = ? AND returned_at IS NULL
        """,
        (loan_id,),
    )

    # 2) Set the copy back to AVAILABLE
    cur2 = conn.execute(
        """
        UPDATE Copies
        SET status = 'AVAILABLE'
        WHERE copy_id = ? AND status = 'CHECKED_OUT'
        """,
        (copy_id,),
    )

    # 3) Void any pending purchase charge
    cur3 = conn.execute(
        """
        UPDATE Charges
        SET status = 'void'
        WHERE loan_id = ? AND status = 'pending'
        """,
        (loan_id,),
    )

    return cur1.rowcount or 0, cur2.rowcount or 0, cur3.rowcount or 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Return a checked out record (loan)."
    )
    parser.add_argument("--loan-id", type=int, help="Loan ID to return")
    parser.add_argument("--user-id", type=int, help="User ID (alternative to --loan-id)")
    parser.add_argument("--copy-id", type=int, help="Copy ID (required with --user-id)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Interactive prompts if identifiers missing
    loan_id = args.loan_id
    user_id = args.user_id
    copy_id = args.copy_id

    if loan_id is None:
        if user_id is None:
            try:
                print("=========================================")
                print("=== Vinyl Record Library - Return Loan ===")
                print("=========================================")
                user_id = int(input("Enter user_id: ").strip())
            except ValueError:
                print("Invalid user_id.")
                sys.exit(1)
        if copy_id is None:
            try:
                copy_id = int(input("Enter copy_id being returned: ").strip())
            except ValueError:
                print("Invalid copy_id.")
                sys.exit(1)

    try:
        conn = get_connection()
    except sqlite3.Error as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        # Resolve loan row
        if loan_id is not None:
            loan = find_active_loan_by_id(conn, loan_id)
            if loan is None:
                print(f"No active loan found with loan_id={loan_id}.")
                sys.exit(1)
            copy_id = loan["copy_id"]
        else:
            loan = find_active_loan_by_user_copy(conn, user_id, copy_id)
            if loan is None:
                print(
                    f"No active loan found for user_id={user_id}, copy_id={copy_id}."
                )
                sys.exit(1)
            loan_id = loan["loan_id"]

        # Begin transaction
        conn.execute("BEGIN TRANSACTION;")
        loans_updated, copies_updated, charges_voided = return_loan(conn, loan_id, copy_id)
        conn.commit()

        print()
        print("Return processed successfully.")
        print("-" * 60)
        print(f"Loan ID:     {loan_id}")
        print(f"User:        {loan['username']} (ID: {loan['user_id']})")
        print(f"Record:      {loan['title']} — {loan['artist_name']}")
        print(f"Copy ID:     {copy_id}")
        print()
        print(f"Loans updated:    {loans_updated}")
        print(f"Copies updated:   {copies_updated}")
        print(f"Charges voided:   {charges_voided}")
        print()

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[DATABASE ERROR] {e}\n")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
