#!/usr/bin/env python3
import sqlite3

DB_PATH = "data/main.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows accessing columns by name
    return conn


def get_available_copies(conn, record_id):
    """
    Return a list of copy_ids that are not currently on loan
    (i.e., no loan with returned_at IS NULL).
    """
    rows = conn.execute(
        """
        SELECT c.copy_id
        FROM Copies c
                WHERE c.record_id = ?
                    AND c.status = 'AVAILABLE'
          AND NOT EXISTS (
              SELECT 1
              FROM Loans l
              WHERE l.copy_id = c.copy_id
                AND l.returned_at IS NULL
          )
                    AND NOT EXISTS (
                            SELECT 1
                            FROM CartItems ci
                            WHERE ci.copy_id = c.copy_id
                    )
        ORDER BY c.copy_id;
        """,
        (record_id,),
    ).fetchall()

    return [row["copy_id"] for row in rows]

def get_sellable_copies(conn, record_id):
    """
    Return a list of rows for copies that are available to BUY.
    Assumes:
      - Copies.purchase_price is NOT NULL for sellable copies
      - Copies.status = 'AVAILABLE' means not sold / not retired
    Adjust status values if your schema uses different ones.
    """
    rows = conn.execute(
        """
        SELECT c.copy_id, c.purchase_price
        FROM Copies c
        WHERE c.record_id = ?
          AND c.purchase_price IS NOT NULL
          AND c.status = 'AVAILABLE'
        ORDER BY c.purchase_price ASC, c.copy_id ASC;
        """,
        (record_id,),
    ).fetchall()

    return rows


def search_records(conn, mode, term):
    """
    mode: 'artist' or 'title'
    term: search string
    Returns a list of dicts with record info and availability.
    """
    if mode == "artist":
        where_clause = "a.artist_name LIKE ?"
    elif mode == "title":
        where_clause = "r.title LIKE ?"
    else:
        raise ValueError("Invalid search mode")

    like_param = f"%{term}%"

    query = f"""
        SELECT
            r.record_id,
            r.title,
            a.artist_name
        FROM Records r
        JOIN Artists a ON r.artist_id = a.artist_id
        WHERE {where_clause}
        ORDER BY a.artist_name, r.title;
        """

    rows = conn.execute(query, (like_param,)).fetchall()

    results = []
    for row in rows:
        record_id = row["record_id"]

        # total copies for this record (only those currently AVAILABLE)
        total_copies = conn.execute(
            "SELECT COUNT(*) AS cnt FROM Copies WHERE record_id = ? AND status = 'AVAILABLE';",
            (record_id,),
        ).fetchone()["cnt"]

        # available copies
        available_copy_ids = get_available_copies(conn, record_id)
        sellable_rows = get_sellable_copies(conn, record_id)
        for_sale_copy_ids = [row["copy_id"] for row in sellable_rows]
        for_sale_prices = [row["purchase_price"] for row in sellable_rows]
        for_sale_count = len(for_sale_copy_ids)
        min_price = sellable_rows[0]["purchase_price"] if sellable_rows else None
        available_count = len(available_copy_ids)

        results.append(
            {
                "record_id": record_id,
                "title": row["title"],
                "artist_name": row["artist_name"],
                "total_copies": total_copies,
                "available_copies": available_count,
                "available_copy_ids": available_copy_ids,
                "for_sale_count": for_sale_count,
                "for_sale_copy_ids": for_sale_copy_ids,
                "for_sale_prices": for_sale_prices,
                "min_price": min_price,
            }
        )

    return results


def print_results(results):
    if not results:
        print("\nNo matching records found.\n")
        return

    print("\nSearch results:\n")
    for idx, r in enumerate(results, start=1):
        print(
            f"{idx}) [record_id: {r['record_id']}] "
            f"{r['title']} — {r['artist_name']}"
        )
       
        print(
            f"    total copies: {r['total_copies']}, "
            f"available: {r['available_copies']}"
        )
        if r["available_copy_ids"]:
            print(
                f"    available copy_ids: "
                f"{', '.join(map(str, r['available_copy_ids']))}"
            )
        else:
            print("    all copies currently on loan")

          # Sale availability
        if r.get("for_sale_count", 0) > 0:
            print(
                f"    for sale: {r['for_sale_count']} "
                f"copy/copies (cheapest: ${r['min_price']:.2f})"
            )
            # Show all prices for transparency
            prices_str = ", ".join(f"${p:.2f}" for p in r["for_sale_prices"])
            print(f"    prices: {prices_str}")
            print(
                f"    sellable copy_ids: "
                f"{', '.join(map(str, r['for_sale_copy_ids']))}"
            )
        else:
            print("    no copies currently for sale")
        print()
    print()


def main():
    conn = get_connection()
    try:
        while True:
            print("====================================")
            print("  Hybrid Vinyl: Search Records      ")
            print("====================================")
            print("1) Search by artist name")
            print("2) Search by record title")
            print("3) Exit")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                mode = "artist"
                term = input("Enter (partial) artist name: ").strip()
            elif choice == "2":
                mode = "title"
                term = input("Enter (partial) record title: ").strip()
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice.\n")
                continue

            if not term:
                print("Search term cannot be empty.\n")
                continue

            results = search_records(conn, mode, term)
            print_results(results)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
