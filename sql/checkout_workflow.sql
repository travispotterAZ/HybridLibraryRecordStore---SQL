PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ============================================================
-- Step 1: Insert the loan for user_id = , copy_id = 
-- ============================================================
INSERT INTO Loans (
  user_id,
  copy_id,
  record_id,
  due_at,
  price_at_checkout,
  notes
)
SELECT
  2,                          -- user_id
  c.copy_id,                  -- copy_id
  c.record_id,                -- record_id
  datetime('now','+7 days'),  -- due_at
  39.99,                      -- price_at_checkout
  'Standard 7-day checkout'
FROM Copies c
WHERE c.copy_id = 22
  AND c.status = 'AVAILABLE';


-- ============================================================
-- Step 2: Mark the copy as CHECKED_OUT (only if it was available)
-- ============================================================
UPDATE Copies
SET status = 'CHECKED_OUT'
WHERE copy_id = 22
  AND status = 'AVAILABLE';


-- ============================================================
-- Step 3: (Optional but recommended)
-- Create a pending purchase charge for this loan
-- ============================================================
INSERT INTO Charges (loan_id, type, amount, status)
VALUES (
  (SELECT MAX(loan_id) FROM Loans),   -- the loan we just created
  'purchase',
  39.99,
  'pending'
);

COMMIT;
