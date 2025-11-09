-- Drop temp table if it exists from previous run
DROP TABLE IF EXISTS temp_records;

-- Import CSV data into temporary table
.mode csv
.headers on
.import data/records.csv temp_records

-- Populate Artists table from CSV
INSERT OR IGNORE INTO artists (artist_name, genre) 
SELECT DISTINCT artist_name, artist_genre 
FROM temp_records 
WHERE artist_name IS NOT NULL AND TRIM(artist_name) <> '';

-- Populate Records table from CSV with proper artist_id foreign keys
INSERT INTO records (artist_id, title, genre, release_date, total_tracks)
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