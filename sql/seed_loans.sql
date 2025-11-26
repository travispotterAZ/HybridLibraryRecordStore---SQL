BEGIN TRANSACTION;

----------------------------------------------------------------
-- 1) ACTIVE — NOT YET DUE
-- Should remain ACTIVE after auto-conversion script
----------------------------------------------------------------
INSERT INTO Loans (
  user_id, copy_id, record_id,
  checked_out_at, due_at,
  status, price_at_checkout
)
SELECT
  1 AS user_id,
  1 AS copy_id,
  record_id,
  datetime('now', '-2 days') AS checked_out_at,
  datetime('now', '+5 days') AS due_at,
  'ACTIVE' AS status,
  purchase_price AS price_at_checkout
FROM Copies WHERE copy_id = 1;

UPDATE Copies SET status = 'CHECKED_OUT' WHERE copy_id = 1;

----------------------------------------------------------------
-- 2) ACTIVE — OVERDUE BY 3 DAYS
-- Should be converted to PURCHASED
----------------------------------------------------------------
INSERT INTO Loans (
  user_id, copy_id, record_id,
  checked_out_at, due_at,
  status, price_at_checkout
)
SELECT
  2,
  2,
  record_id,
  datetime('now', '-10 days'),
  datetime('now', '-3 days'),
  'ACTIVE',
  purchase_price
FROM Copies WHERE copy_id = 5;

UPDATE Copies SET status = 'CHECKED_OUT' WHERE copy_id = 2;

----------------------------------------------------------------
-- 3) RETURNED — Should remain RETURNED
----------------------------------------------------------------
INSERT INTO Loans (
  user_id, copy_id, record_id,
  checked_out_at, due_at, returned_at,
  status, price_at_checkout
)
SELECT
  3,
  3,
  record_id,
  datetime('now', '-7 days'),
  datetime('now', '-3 days'),
  datetime('now', '-1 day'),
  'RETURNED',
  purchase_price
FROM Copies WHERE copy_id = 3;

UPDATE Copies SET status = 'AVAILABLE' WHERE copy_id = 10;

----------------------------------------------------------------
-- 4) ACTIVE — OVERDUE BY 1 DAY
-- Should also be converted to PURCHASED
----------------------------------------------------------------
INSERT INTO Loans (
  user_id, copy_id, record_id,
  checked_out_at, due_at,
  status, price_at_checkout
)
SELECT
  1,
  4,
  record_id,
  datetime('now', '-6 days'),
  datetime('now', '-1 days'),
  'ACTIVE',
  purchase_price
FROM Copies WHERE copy_id = 4;

UPDATE Copies SET status = 'CHECKED_OUT' WHERE copy_id = 15;

----------------------------------------------------------------

COMMIT;
