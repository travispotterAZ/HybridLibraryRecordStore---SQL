#!/usr/bin/env python3

import sqlite3
from getpass import getpass

DB_PATH = "main.db"  # make sure this matches your DB file name


def connect_db():
    return sqlite3.connect("data/main.db")
    


def username_or_email_taken(cur, username, email):
    cur.execute(
        """
        SELECT username, email
        FROM Users
        WHERE username = ? OR email = ?
        """,
        (username, email),
    )
    return cur.fetchone()


def register_user():
    print("================================================")
    print("=== Vinyl Record Library - User Registration ===")
    print("================================================")
    print("Press Ctrl+C at any time to quit.\n")

    # 1) Collect input
    username = input("Choose a username: ").strip()
    email = input("Email address: ").strip()

    # 2) Get password (hidden) + confirm
    while True:
        password1 = getpass("Choose a password: ")
        password2 = getpass("Confirm password: ")

        if password1 != password2:
            print("Passwords do not match. Please try again.\n")
            continue

        if not password1:
            print("Password cannot be empty. Please try again.\n")
            continue

        break

    # 3) Connect to DB
    conn = connect_db()
    cur = conn.cursor()

    # 4) Check for duplicates
    existing = username_or_email_taken(cur, username, email)
    if existing:
        print("\n❌ Registration failed:")
        print("   That username or email is already in use.")
        print("   Please choose a different username/email.\n")
        conn.close()
        return

    # 5) Insert new user
    cur.execute(
        """
        INSERT INTO Users (username, email, password, is_admin)
        VALUES (?, ?, ?, 0);
        """,
        (username, email, password1),
    )
    conn.commit()

    new_user_id = cur.lastrowid
    conn.close()

    print("\n✅ Registration successful!")
    print(f"   Your assigned user_id is: {new_user_id}")
    print("   You can now use this user_id in your checkout/return workflows.\n")


if __name__ == "__main__":
    try:
        register_user()
    except KeyboardInterrupt:
        print("\nRegistration cancelled by user.")
