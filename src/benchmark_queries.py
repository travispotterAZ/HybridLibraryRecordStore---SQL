#!/usr/bin/env python3
import sqlite3
import time

ARTIST_TERM = "%Miles%"   # adjust to something that exists in your data
RECORD_ID = 3             # adjust to a real record_id in your DB
REPEATS = 200             # how many times to run each query


def time_query(db_path, sql, params=(), repeats=REPEATS):
    conn = sqlite3.connect(db_path)
    try:
        start = time.perf_counter()
        for _ in range(repeats):
            conn.execute(sql, params).fetchall()
        end = time.perf_counter()
    finally:
        conn.close()
    return (end - start) * 1000.0  # ms


def main():
    dbs = [
        ("No indexes", "data/main_no_idx.db"),
        ("With indexes", "data/main.db"),
    ]

    q_artist = """
    SELECT
        r.record_id,
        r.title,
        a.artist_name AS artist_name
    FROM Records r
    JOIN Artists a ON r.artist_id = a.artist_id
    WHERE a.artist_name LIKE ?
    ORDER BY artist_name, r.title;
    """

    q_avail = """
    SELECT c.copy_id
    FROM Copies c
    WHERE c.record_id = ?
      AND NOT EXISTS (
          SELECT 1
          FROM Loans l
          WHERE l.copy_id = c.copy_id
            AND l.returned_at IS NULL
      );
    """

    for label, db_path in dbs:
        t1 = time_query(db_path, q_artist, (ARTIST_TERM,))
        t2 = time_query(db_path, q_avail, (RECORD_ID,))
        print(f"=== {label} ({db_path}) ===")
        print(f"Artist search: {t1:.2f} ms for {REPEATS} runs")
        print(f"Availability:  {t2:.2f} ms for {REPEATS} runs")
        print()


if __name__ == "__main__":
    main()
