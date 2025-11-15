-- Enable FK enforcement and speed up bulk load
PRAGMA foreign_keys = ON;

-- Note: Run this script from the repository root (so data/ path resolves), e.g.:
--   sqlite3 RecordCollection_V2.db ".read sql/schemas.sql" ".read sql/seed.sql"

-- Start a transaction for faster, atomic seeding
BEGIN TRANSACTION;

-- Drop temp table if it exists from previous run
DROP TABLE IF EXISTS temp_records;

-- Create a temporary staging table matching records.csv header order
-- Header columns: record_id,artist_id,title,release_date,total_tracks,artist_genre,artist_name
CREATE TEMP TABLE temp_records (
    record_id    TEXT,
    artist_id    TEXT,
    title        TEXT,
    release_date TEXT,
    total_tracks INTEGER,
    artist_genre TEXT,
    artist_name  TEXT
);

-- Import CSV data into temporary table
.mode csv
.headers on
.import data/records.csv temp_records

-- Populate Artists table from CSV
INSERT OR IGNORE INTO artists (artist_name, genre) 
SELECT DISTINCT artist_name, artist_genre 
FROM temp_records 
WHERE artist_name IS NOT NULL AND TRIM(artist_name) <> '';

-- Populate Records table from CSV with proper artist_id foreign keys (idempotent via unique index)
INSERT OR IGNORE INTO records (artist_id, title, genre, release_date, total_tracks)
SELECT 
    a.artist_id,
    t.title,
    t.artist_genre,
    t.release_date,
    t.total_tracks
FROM temp_records t
JOIN artists a ON t.artist_name = a.artist_name;

-- Clean up temporary table
DROP TABLE temp_records;

-- ============================================================
-- Seed Copies: create K physical copies per active record
-- Idempotent: only inserts missing barcodes per record
-- Change K below to adjust copies per record (default: 3)
WITH RECURSIVE params(K) AS (VALUES(3)),
nums(n) AS (
    SELECT 1
    UNION ALL
    SELECT n+1 FROM nums, params WHERE n < (SELECT K FROM params)
)
INSERT INTO Copies (record_id, barcode, condition, status)
SELECT r.record_id,
             'R' || r.record_id || '-C' || n AS barcode,
             'GOOD' AS condition,
             'AVAILABLE' AS status
FROM Records r
CROSS JOIN nums
LEFT JOIN Copies c
    ON c.record_id = r.record_id
 AND c.barcode   = 'R' || r.record_id || '-C' || n
WHERE r.is_active = 1
    AND c.copy_id IS NULL;

-- ============================================================
-- Seed Users (basic educational, plaintext passwords)
-- Only inserts if Users table is currently empty to stay idempotent.
INSERT INTO Users (username, email, is_admin, password)
SELECT username, email, is_admin, password
FROM (
    SELECT 'admin'   AS username, 'admin@example.com'   AS email, 1 AS is_admin, 'admin123'    AS password UNION ALL
    SELECT 'ricardo' AS username, 'ricardo@example.com' AS email, 0 AS is_admin, 'password123' AS password UNION ALL
    SELECT 'testuser' AS username,'testuser@example.com' AS email,0 AS is_admin,'testpass'     AS password UNION ALL
    SELECT 'alice'   AS username, 'alice@example.com'   AS email, 0 AS is_admin, 'alicepass'   AS password UNION ALL
    SELECT 'bob'     AS username, 'bob@example.com'     AS email, 0 AS is_admin, 'bobpass'     AS password
) seed
WHERE (SELECT COUNT(*) FROM Users) = 0;

-- Commit seeding
COMMIT;