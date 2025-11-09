-- Seed script for Copies table
-- Creates K physical copies per record with unique barcodes
PRAGMA foreign_keys = ON;

-- 1) Ensure Copies table exists
CREATE TABLE IF NOT EXISTS Copies (
  copy_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id INTEGER NOT NULL,
  barcode   TEXT NOT NULL UNIQUE,
  condition TEXT DEFAULT 'GOOD' CHECK (condition IN ('NEW','GOOD','FAIR','POOR','DAMAGED')),
  status    TEXT DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE','CHECKED_OUT','LOST','REPAIR')),
  FOREIGN KEY (record_id) REFERENCES Records(record_id) ON DELETE CASCADE
);

-- 2) Create indexes
CREATE UNIQUE INDEX IF NOT EXISTS ux_copies_barcode ON Copies(barcode);
CREATE INDEX IF NOT EXISTS idx_copies_record ON Copies(record_id);
CREATE INDEX IF NOT EXISTS idx_copies_status ON Copies(status);

BEGIN TRANSACTION;

-- 3) Generate K copies per active record using recursive CTE
-- Change the K value below to set how many copies per record (default: 3)
WITH RECURSIVE params(K) AS (VALUES(3)),  -- 👈 copies per record
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
WHERE r.is_active = 1       -- only seed active records
  AND c.copy_id IS NULL;    -- only insert missing ones (idempotent)

COMMIT;

-- 4) Show summary
SELECT 'Total copies:', COUNT(*) FROM Copies;
SELECT 'Copies per record (sample):';
SELECT r.record_id, r.title, COUNT(c.copy_id) AS num_copies
FROM Records r
LEFT JOIN Copies c ON c.record_id = r.record_id
WHERE r.is_active = 1
GROUP BY r.record_id
ORDER BY r.record_id
LIMIT 10;
