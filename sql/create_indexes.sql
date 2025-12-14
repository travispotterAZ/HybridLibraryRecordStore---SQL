-- ============================================================
-- Strategic Indexes for Catalog Search Queries
-- ============================================================
-- These indexes optimize searches on artist names, record-artist relationships,
-- and filtering on common query predicates.
--
-- Purpose: Demonstrate impact of indexing on query performance
--
-- ============================================================

-- ARTIST LOOKUPS
-- Essential for all artist name searches (LIKE queries)
CREATE INDEX IF NOT EXISTS idx_artists_name ON Artists(artist_name);

-- ARTIST GENRE FILTERING
-- For queries filtering by artist genre
CREATE INDEX IF NOT EXISTS idx_artists_genre ON Artists(genre);

-- RECORD-ARTIST RELATIONSHIPS
-- Speeds up JOIN operations from Records to Artists
-- This is the critical foreign key index
CREATE INDEX IF NOT EXISTS idx_records_artist_id ON Records(artist_id);

-- RECORD STATUS/AVAILABILITY
-- For filtering active/inactive records
CREATE INDEX IF NOT EXISTS idx_records_is_active ON Records(is_active);

-- RECORD GENRE FILTERING
-- For queries filtering by record genre
CREATE INDEX IF NOT EXISTS idx_records_genre ON Records(genre);

-- COPY-RECORD RELATIONSHIPS
-- For inventory lookups (copies by record)
CREATE INDEX IF NOT EXISTS idx_copies_record_id ON Copies(record_id);

-- LOAN-COPY RELATIONSHIPS
-- For availability checks (is a copy on loan?)
CREATE INDEX IF NOT EXISTS idx_loans_copy_id ON Loans(copy_id);

-- Optional: Compound indexes for common WHERE + ORDER BY patterns
-- These can help avoid separate sorting operations
CREATE INDEX IF NOT EXISTS idx_records_artist_is_active 
  ON Records(artist_id, is_active);

CREATE INDEX IF NOT EXISTS idx_copies_status 
  ON Copies(record_id, status);
