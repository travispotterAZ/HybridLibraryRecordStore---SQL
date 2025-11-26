-- auto_convert_overdue_loans.sql
-- Converts overdue ACTIVE loans into purchases:
--  - Creates a purchase charge (pending)
--  - Marks the loan as PURCHASED
--  - Marks the copy as SOLD

BEGIN TRANSACTION;

-- 1) Collect all loans that should be converted in this run
--    Criteria:
--      - status = 'ACTIVE'
--      - not returned
--      - not already converted to purchase
--      - due_at is in the past
DROP TABLE IF EXISTS OverdueLoansToConvert;

CREATE TEMP TABLE OverdueLoansToConvert AS
SELECT
  loan_id,
  copy_id,
  price_at_checkout
FROM Loans
WHERE
  status = 'ACTIVE'
  AND returned_at IS NULL
  AND purchase_converted_at IS NULL
  AND due_at < datetime('now');

-- 2) Insert purchase charges for those loans
--    Avoid duplicate purchase charges for the same loan
INSERT INTO Charges (loan_id, type, amount, status)
SELECT
  o.loan_id,
  'purchase',
  o.price_at_checkout,
  'pending'
FROM OverdueLoansToConvert AS o
LEFT JOIN Charges AS c
  ON c.loan_id = o.loan_id
 AND c.type = 'purchase'
 AND c.status IN ('pending','paid','failed')  -- treat any existing as "don't create another"
WHERE c.charge_id IS NULL;

-- 3) Update Loans to mark them as PURCHASED
UPDATE Loans
SET
  status = 'PURCHASED',
  purchase_converted_at = datetime('now')
WHERE loan_id IN (
  SELECT loan_id FROM OverdueLoansToConvert
);

-- 4) Update Copies to mark them as SOLD
UPDATE Copies
SET status = 'SOLD'
WHERE copy_id IN (
  SELECT DISTINCT copy_id FROM OverdueLoansToConvert
);

-- 5) Clean up temp table
DROP TABLE IF EXISTS OverdueLoansToConvert;

COMMIT;
