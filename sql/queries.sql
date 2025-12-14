
-- Catalog browse
SELECT record_id, title, genre, release_date, total_tracks, is_active
FROM Records
ORDER BY release_date DESC, record_id;

-- Records with artist info (alphabetical)
SELECT r.record_id, a.artist_name, r.title, r.genre, r.release_date, r.total_tracks, r.is_active
FROM Records r
JOIN Artists a ON a.artist_id = r.artist_id
ORDER BY a.artist_name, r.title;

-- Records by a specific artist
SELECT r.*
FROM Records r
JOIN Artists a ON a.artist_id = r.artist_id
WHERE a.artist_name = :artist_name
ORDER BY r.release_date;

-- Records by title keyword
SELECT r.record_id, r.title, a.artist_name, r.genre, r.release_date
FROM Records r
JOIN Artists a ON a.artist_id = r.artist_id
WHERE r.title LIKE :title_like
ORDER BY r.release_date DESC;

-- Active records by artist (filtered)
SELECT r.record_id, r.title, a.artist_name
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
WHERE r.is_active = 1 AND a.artist_name LIKE :artist_like
ORDER BY r.title;

-- Rock records by artist or record genre
SELECT a.artist_name, r.title, r.genre
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
WHERE a.genre = 'Rock' OR r.genre = 'Rock';

-- Records released after a date
SELECT a.artist_name, r.title, r.release_date
FROM Records r
JOIN Artists a ON r.artist_id = a.artist_id
WHERE r.release_date > :released_after
ORDER BY r.release_date;

-- Aggregations
SELECT a.artist_name, COUNT(*) AS num_records
FROM Artists a
LEFT JOIN Records r ON r.artist_id = a.artist_id
GROUP BY a.artist_id
ORDER BY num_records DESC, a.artist_name
LIMIT 25;

SELECT a.artist_name, SUM(r.total_tracks) AS total_tracks
FROM Artists a
JOIN Records r ON a.artist_id = r.artist_id
GROUP BY a.artist_id
ORDER BY total_tracks DESC
LIMIT 25;

SELECT r.genre, COUNT(*) AS records_in_genre
FROM Records r
GROUP BY r.genre
ORDER BY records_in_genre DESC;

SELECT is_active, COUNT(*) AS cnt
FROM Records
GROUP BY is_active;

-- Availability: total vs available copies per record
SELECT r.title,
       COUNT(c.copy_id) AS total_copies,
       SUM(c.status = 'AVAILABLE') AS available_copies
FROM Records r
LEFT JOIN Copies c ON r.record_id = c.record_id
GROUP BY r.record_id
ORDER BY available_copies DESC, r.title;

-- Inventory by status
SELECT c.status, COUNT(*) AS copies
FROM Copies c
GROUP BY c.status
ORDER BY copies DESC;

-- Active loans with days until due (negative means overdue)
SELECT l.loan_id,
       u.username,
       r.title,
       l.due_at,
       ROUND(julianday(l.due_at) - julianday('now'), 2) AS days_until_due
FROM Loans l
JOIN Users u ON u.user_id = l.user_id
JOIN Records r ON r.record_id = l.record_id
WHERE l.status = 'ACTIVE'
ORDER BY l.due_at;

-- Overdue loans
SELECT l.loan_id,
       u.username,
       r.title,
       l.due_at,
       ROUND(julianday('now') - julianday(l.due_at), 2) AS days_overdue
FROM Loans l
JOIN Users u ON u.user_id = l.user_id
JOIN Records r ON r.record_id = l.record_id
WHERE l.status = 'ACTIVE' AND l.due_at < datetime('now')
ORDER BY days_overdue DESC;

-- User loan counts
SELECT u.username, COUNT(*) AS active_loans
FROM Loans l
JOIN Users u ON u.user_id = l.user_id
WHERE l.status = 'ACTIVE'
GROUP BY u.user_id
ORDER BY active_loans DESC, u.username;
