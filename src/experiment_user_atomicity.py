import sqlite3
import os

# ==========================
# Database Path
# ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "main.db")  # Correct DB file

# ==========================
# Connect to database
# ==========================
def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# ==========================
# Count rows in Users and CartItems
# ==========================
def count_rows(cur):
    cur.execute("SELECT COUNT(*) FROM Users;")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM CartItems;")
    cart_items = cur.fetchone()[0]

    return users, cart_items

# ==========================
# Clean up test users (for resetting database)
# ==========================
def cleanup_test_users(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM CartItems WHERE user_id IN (SELECT user_id FROM Users WHERE username LIKE 'atomic_%');")
    cur.execute("DELETE FROM Users WHERE username LIKE 'atomic_%';")
    conn.commit()

# ==========================
# Case A: No Transaction Protection
# ==========================
def register_user_no_transaction():
    print("\n--- Case A: No Transaction Protection ---")

    conn = connect_db()
    cur = conn.cursor()

    before = count_rows(cur)
    print("Before:", before)

    try:
        # Step 1: Insert user
        cur.execute("""
            INSERT INTO Users (username, email, password)
            VALUES ('atomic_test_user', 'atomic_test@fail.com', 'testpw');
        """)
        user_id = cur.lastrowid

        # Step 2: Insert a valid cart item
        cur.execute("""
            INSERT INTO CartItems (user_id, record_id, quantity)
            VALUES (?, 1, 1);
        """, (user_id,))

        # Step 3: Simulated failure
        raise Exception("Simulated crash after inserting user and cart items")

    except Exception as e:
        print("❌ Failure occurred:", e)

    # No rollback in Case A
    conn.commit()

    after = count_rows(cur)
    print("After:", after)

    conn.close()


# ==========================
# Case B: Atomic Transaction with Rollback
# ==========================
def register_user_atomic():
    print("\n--- Case B: Atomic Transaction with Rollback ---")

    conn = connect_db()

    # Reset database to same starting state as Case A
    cleanup_test_users(conn)

    cur = conn.cursor()
    before = count_rows(cur)
    print("Before:", before)

    try:
        conn.execute("BEGIN")  # Start explicit transaction

        # Step 1: Insert user
        cur.execute("""
            INSERT INTO Users (username, email, password)
            VALUES ('atomic_safe_user', 'atomic_safe@fail.com', 'testpw');
        """)
        user_id = cur.lastrowid

        # Step 2: Insert a valid cart item
        cur.execute("""
            INSERT INTO CartItems (user_id, record_id, quantity)
            VALUES (?, 1, 1);
        """, (user_id,))

        # Step 3: Simulated failure after inserts
        raise Exception("Simulated crash during atomic registration")

        conn.commit()  # Won't reach here due to exception

    except Exception as e:
        print("⚠️ Failure occurred:", e)
        conn.rollback()  # Undo both inserts

    after = count_rows(cur)
    print("After:", after)

    conn.close()


# ==========================
# Initial Cleanup Before Any Experiment
# ==========================
def initial_cleanup():
    print("\n--- Initial Database Cleanup ---")
    conn = connect_db()
    cleanup_test_users(conn)
    print("Removed any leftover test users and cart items from previous runs.")
    conn.close()


# ==========================
# Run Experiment
# ==========================
if __name__ == "__main__":
    initial_cleanup()
    register_user_no_transaction()
    register_user_atomic()

# To run:
# python experiments/experiment_user_atomicity.py
