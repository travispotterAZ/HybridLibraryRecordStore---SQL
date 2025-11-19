PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Assume: loan_id = 2, copy_id = 4 (adjust as needed)

-- 1) Mark the loan as returned
UPDATE Loans
SET returned_at = datetime('now')
WHERE loan_id = 2
  AND returned_at IS NULL;

-- 2) Set the copy back to AVAILABLE
UPDATE Copies
SET status = 'AVAILABLE'
WHERE copy_id = 4
  AND status = 'CHECKED_OUT';

-- 3) Void any pending purchase charge for this loan
UPDATE Charges
SET status = 'void'
WHERE loan_id = 2
  AND status = 'pending';

COMMIT;
