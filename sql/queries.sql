
SELECT * FROM records;

SELECT * FROM records WHERE genre = 'classic rock';

--List all records with artist names (alphabetical by artist/title)
SELECT r.record_id, a.artist_name, r.title, r.genre, r.release_date, r.total_tracks, r.is_active
FROM Records r
JOIN Artists a ON a.artist_id = r.artist_id
ORDER BY a.artist_name, r.title;

--Find all records by artist (name lookup)
SELECT r.*
FROM Records r
JOIN Artists a ON a.artist_id = r.artist_id
WHERE a.artist_name = 'Pink Floyd'
ORDER BY r.release_date;

--How many records per artist?
SELECT a.artist_name, COUNT(*) AS num_records
FROM Artists a
LEFT JOIN Records r ON r.artist_id = a.artist_id
GROUP BY a.artist_id
ORDER BY num_records DESC, a.artist_name;

-- Active vs inactive records
SELECT is_active, COUNT(*) FROM Records GROUP BY is_active;

-- All active records
SELECT title FROM records WHERE is_active = 1;

-- Deactivate a record (soft delete)
UPDATE Records SET is_active = 0 WHERE record_id = 42;

--Basic JOINS---
-- 1A. List all records with their artist names
SELECT r.record_id, r.title, a.artist_name
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id;

-- 1B. Include extra info (genre, release date)
SELECT r.title AS record_title,
       a.artist_name,
       r.genre AS record_genre,
       r.release_date
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
ORDER BY a.artist_name, r.release_date;

--Filtering and searching---
SELECT a.artist_name, r.title, r.release_date
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
WHERE a.artist_name = 'Pink Floyd';

-- 2B. Find all Rock records (by either artist or record genre)
SELECT a.artist_name, r.title, r.genre
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
WHERE a.genre = 'Rock' OR r.genre = 'Rock';

-- 2C. Find records released after 1980
SELECT a.artist_name, r.title, r.release_date
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
WHERE r.release_date > '1980-01-01';

-- 3. Aggregations --
-- 3A. Count how many records per artist
SELECT a.artist_name, COUNT(r.record_id) AS record_count
FROM Artists a
LEFT JOIN Records r ON a.artist_id = r.artist_id
GROUP BY a.artist_id
ORDER BY record_count DESC;

-- 3B. How many total tracks per artist (sum across their records)
SELECT a.artist_name, SUM(r.total_tracks) AS total_tracks
FROM Artists a
JOIN Records r ON a.artist_id = r.artist_id
GROUP BY a.artist_id
ORDER BY total_tracks DESC;

-- 4. Conditonal Queries --





/*       Circulation System Queries     */

-- See overdue checkouts
SELECT u.username, r.title, c.due_at, 
       julianday('now') - julianday(c.due_at) AS days_overdue
FROM Checkouts c
JOIN Users u ON c.user_id = u.user_id
JOIN Records r ON c.record_id = r.record_id
WHERE c.status = 'OUT' AND c.due_at < datetime('now')
ORDER BY days_overdue DESC;

-- User checkout history
SELECT u.username, COUNT(*) AS total_checkouts
FROM Checkouts c
JOIN Users u ON c.user_id = u.user_id
GROUP BY u.username;

-- Carol returned "Fathers & Sons" by Luke CombsUPDATE Checkouts
SET returned_at = datetime('now'),
    status = 'RETURNED'
WHERE user_id = (SELECT user_id FROM Users WHERE username = 'carol')
  AND record_id = (SELECT r.record_id 
                   FROM Records r 
                   JOIN Artists a ON r.artist_id = a.artist_id 
                   WHERE r.title = 'Fathers & Sons' AND a.artist_name = 'Luke Combs')
  AND status = 'OUT';

-- Mark checkout_id 5 as returned
UPDATE Checkouts
SET returned_at = datetime('now'),
    status = 'RETURNED'
WHERE checkout_id = 5;

-- Verify checkout_id 5 return
SELECT u.username, r.title, c.status, c.checkout_at, c.due_at, c.returned_at,
       CASE 
         WHEN c.returned_at > c.due_at THEN 'LATE (' || ROUND(julianday(c.returned_at) - julianday(c.due_at), 2) || ' days)'
         ELSE 'ON TIME'
       END AS return_status
FROM Checkouts c
JOIN Users u ON c.user_id = u.user_id
JOIN Records r ON c.record_id = r.record_id
WHERE c.checkout_id = 5;

--Test "available copies" query
SELECT r.title,
       COUNT(c.copy_id) AS total_copies,
       SUM(c.status='AVAILABLE') AS available_copies
FROM Records r
LEFT JOIN Copies c ON r.record_id = c.record_id
GROUP BY r.record_id
ORDER BY available_copies DESC, r.title;
