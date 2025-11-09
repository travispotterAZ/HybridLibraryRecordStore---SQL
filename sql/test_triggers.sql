-- Test script for Checkouts/Copies triggers
-- Verifies: OUT sets copy to CHECKED_OUT; RETURNED sets copy to AVAILABLE
PRAGMA foreign_keys = ON;

-- 0) Ensure triggers are installed (run: .read sql/triggers.sql) before this test

BEGIN TRANSACTION;

-- 1) Pick one AVAILABLE copy to test with
DROP TABLE IF EXISTS _picked;
CREATE TEMP TABLE _picked AS
SELECT copy_id, record_id FROM Copies WHERE status = 'AVAILABLE' LIMIT 1;

-- If nothing picked, show a hint and end early
SELECT 'Picked copy to test with (may be empty if none available):' AS info;
SELECT * FROM _picked;

-- Show BEFORE status for the picked copy
SELECT 'BEFORE' AS phase, cp.copy_id, cp.barcode, cp.status
FROM _picked p
JOIN Copies cp ON cp.copy_id = p.copy_id;

-- 2) Ensure a test user exists
INSERT OR IGNORE INTO Users (username, email, password)
VALUES ('amanda', 'amanda@example.com', 'changeme');

-- 3) Insert an OUT checkout for the picked copy (should flip copy to CHECKED_OUT)
INSERT INTO Checkouts (user_id, copy_id, record_id, checkout_at, due_at, status)
SELECT u.user_id, p.copy_id, p.record_id, datetime('now'), datetime('now','+14 days'), 'OUT'
FROM _picked p
JOIN Users u ON u.username = 'amanda';

-- Show AFTER-OUT status
SELECT 'AFTER_OUT' AS phase, cp.copy_id, cp.barcode, cp.status
FROM _picked p
JOIN Copies cp ON cp.copy_id = p.copy_id;

-- 4) Mark the checkout as RETURNED (should flip copy back to AVAILABLE)
UPDATE Checkouts
SET status = 'RETURNED', returned_at = datetime('now')
WHERE copy_id = (SELECT copy_id FROM _picked)
  AND user_id = (SELECT user_id FROM Users WHERE username = 'amanda')
  AND status = 'OUT';

-- Show AFTER-RETURN status
SELECT 'AFTER_RETURN' AS phase, cp.copy_id, cp.barcode, cp.status
FROM _picked p
JOIN Copies cp ON cp.copy_id = p.copy_id;

-- Optional cleanup: remove the RETURNED test checkout (copy stays AVAILABLE)
DELETE FROM Checkouts
WHERE copy_id = (SELECT copy_id FROM _picked)
  AND user_id = (SELECT user_id FROM Users WHERE username = 'amanda')
  AND status = 'RETURNED';

COMMIT;

-- Final state
SELECT 'FINAL_STATE' AS phase, cp.copy_id, cp.barcode, cp.status
FROM _picked p
JOIN Copies cp ON cp.copy_id = p.copy_id;

DROP TABLE IF EXISTS _picked;
