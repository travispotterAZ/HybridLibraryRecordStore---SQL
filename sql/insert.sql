-- Insert an artist (or update their genre if they already exist)
INSERT INTO Artists (artist_name, genre)
VALUES ('Pink Floyd', 'Progressive Rock')
ON CONFLICT(artist_name) DO UPDATE SET genre = excluded.genre
RETURNING artist_id;

--Insert a record for a known artist_id
INSERT INTO Records (artist_id, title, genre, is_active, release_date, total_tracks)
VALUES (/*artist_id*/ 1, 'The Dark Side of the Moon', 'Progressive Rock', 1, '1973-03-01', 10);



---             NEED TO DEBUG           ---
--Insert a record by artist name, creating the artist if needed
WITH upsert_artist AS (
  INSERT INTO Artists (artist_name, genre)
  VALUES ('Fleetwood Mac', 'Rock')
  ON CONFLICT(artist_name) DO UPDATE SET genre = COALESCE(Artists.genre, excluded.genre)
  RETURNING artist_id
),
got AS (
  SELECT artist_id FROM upsert_artist
  UNION ALL
  SELECT artist_id FROM Artists WHERE artist_name = 'Fleetwood Mac'
)
INSERT INTO Records (artist_id, title, genre, is_active, release_date, total_tracks)
SELECT artist_id, 'Rumours', 'Rock', 1, '1977-02-04', 11
FROM got
RETURNING record_id;