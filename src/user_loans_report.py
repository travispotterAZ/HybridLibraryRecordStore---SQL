#!/usr/bin/env python3
"""
user_loans_report.py

Show all CURRENT (not yet returned) loans for a given user
from a SQLite database.

Usage examples:

    python user_loans_report.py --user-id 5
    python user_loans_report.py --username alice
    python user_loans_report.py --db ./path/to/example.db --username alice
"""

import argparse
import sqlite3
import sys
import json
from typing import Optional, Tuple, List
from datetime import datetime


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show all current loans for a given user."
    )
    parser.add_argument(
        "--db",
        default="data/main_V2.db",
        help="Path to SQLite database (default: data/main_V2.db)",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID to look up loans for",
    )
    parser.add_argument(
        "--username",
        help="Username to look up loans for (alternative to --user-id)",
    )
    parser.add_argument(
        "--overdue-only",
        action="store_true",
        help="Show only overdue loans",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    return parser.parse_args()


def connect_db(db_path: str) -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Error: could not connect to database '{db_path}': {e}")
        sys.exit(1)


def resolve_user(
    conn: sqlite3.Connection, user_id: Optional[int], username: Optional[str]
) -> Tuple[int, str]:
    """
    Resolve the user either by user_id or username.
    Returns (user_id, username).
    Exits with an error message if not found or ambiguous input.
    """
    cur = conn.cursor()

    if user_id is not None:
        cur.execute(
            "SELECT user_id, username FROM Users WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if row is None:
            print(f"No user found with user_id = {user_id}")
            sys.exit(1)
        return row[0], row[1]

    if username is not None:
        cur.execute(
            "SELECT user_id, username FROM Users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
        if row is None:
            print(f"No user found with username = '{username}'")
            sys.exit(1)
        return row[0], row[1]

    # If neither provided, ask interactively
    username = input("Enter username: ").strip()
    if not username:
        print("No username provided.")
        sys.exit(1)

    cur.execute(
        "SELECT user_id, username FROM Users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if row is None:
        print(f"No user found with username = '{username}'")
        sys.exit(1)
    return row[0], row[1]


def fetch_current_loans_for_user(
    conn: sqlite3.Connection, user_id: int, overdue_only: bool = False
) -> List[sqlite3.Row]:
    """
    Fetch all current (not returned) loans for the given user_id.
    If overdue_only=True, only return loans past their due date.
    """
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    overdue_clause = ""
    if overdue_only:
        overdue_clause = " AND datetime(l.due_at) < datetime('now')"

    query = f"""
    SELECT
      l.loan_id,
      r.title,
      a.artist_name,
      l.copy_id,
      l.checked_out_at,
      l.due_at
    FROM Loans l
    JOIN Copies  c ON l.copy_id  = c.copy_id
    JOIN Records r ON c.record_id = r.record_id
    JOIN Artists a ON r.artist_id = a.artist_id
    WHERE l.user_id = ?
      AND l.returned_at IS NULL{overdue_clause}
    ORDER BY l.due_at;
    """

    cur.execute(query, (user_id,))
    return cur.fetchall()


def is_overdue(due_at_str: str) -> bool:
    """Check if a loan is overdue based on due_at timestamp."""
    try:
        due_at = datetime.fromisoformat(due_at_str)
        return due_at < datetime.now()
    except (ValueError, TypeError):
        return False


def format_table(rows: List[sqlite3.Row]) -> str:
    """
    Format the rows into a simple plain-text table with overdue indicators.
    """
    if not rows:
        return "No active loans for this user."

    headers = ["Loan ID", "Title", "Artist", "Copy ID", "Checked Out At", "Due At", "Status"]

    # Convert rows to list of lists of strings
    data = []
    overdue_count = 0
    for row in rows:
        overdue = is_overdue(row["due_at"])
        if overdue:
            overdue_count += 1
        status = "⚠ OVERDUE" if overdue else "Active"
        data.append(
            [
                str(row["loan_id"]),
                str(row["title"]),
                str(row["artist_name"]),
                str(row["copy_id"]),
                str(row["checked_out_at"]),
                str(row["due_at"]),
                status,
            ]
        )

    # Compute column widths
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    # Helper to format a row
    def fmt_row(cols):
        return " | ".join(val.ljust(col_widths[i]) for i, val in enumerate(cols))

    # Build table string
    lines = []
    lines.append(fmt_row(headers))
    lines.append("-+-".join("-" * w for w in col_widths))
    for row in data:
        lines.append(fmt_row(row))
    
    # Add summary footer
    lines.append("")
    lines.append(f"Total: {len(rows)} active loan(s)")
    if overdue_count > 0:
        lines.append(f"⚠ {overdue_count} overdue loan(s)")

    return "\n".join(lines)


def format_json(user_id: int, username: str, rows: List[sqlite3.Row]) -> str:
    """
    Format the loans data as JSON.
    """
    loans = []
    overdue_count = 0
    for row in rows:
        overdue = is_overdue(row["due_at"])
        if overdue:
            overdue_count += 1
        loans.append({
            "loan_id": row["loan_id"],
            "title": row["title"],
            "artist_name": row["artist_name"],
            "copy_id": row["copy_id"],
            "checked_out_at": row["checked_out_at"],
            "due_at": row["due_at"],
            "is_overdue": overdue,
        })
    
    payload = {
        "user": {
            "user_id": user_id,
            "username": username,
        },
        "summary": {
            "total_active_loans": len(rows),
            "overdue_count": overdue_count,
        },
        "loans": loans,
    }
    return json.dumps(payload, indent=2)


def main() -> None:
    args = get_args()
    conn = connect_db(args.db)

    try:
        user_id, username = resolve_user(conn, args.user_id, args.username)
        rows = fetch_current_loans_for_user(conn, user_id, args.overdue_only)

        if args.json:
            print(format_json(user_id, username, rows))
        else:
            loan_type = "overdue" if args.overdue_only else "current"
            print(f"\n{loan_type.capitalize()} loans for user '{username}' (user_id = {user_id}):\n")
            print(format_table(rows))
            print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
