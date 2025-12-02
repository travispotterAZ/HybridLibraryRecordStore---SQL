-- Triggers to keep Copies.status in sync with Loans activity
PRAGMA foreign_keys = ON;

-- Cleanup any old Checkouts triggers (no-op if absent)
DROP TRIGGER IF EXISTS trg_checkout_out;
DROP TRIGGER IF EXISTS trg_checkout_return;
DROP TRIGGER IF EXISTS trg_checkout_delete_out;

-- When a loan is created and is active (returned_at IS NULL), mark the copy as CHECKED_OUT
CREATE TRIGGER IF NOT EXISTS trg_loan_insert_out
AFTER INSERT ON Loans
WHEN NEW.returned_at IS NULL
BEGIN
  UPDATE Copies
  SET status = 'CHECKED_OUT'
  WHERE copy_id = NEW.copy_id;
END;

-- When a loan is returned (returned_at becomes NOT NULL), mark the copy as AVAILABLE
CREATE TRIGGER IF NOT EXISTS trg_loan_return
AFTER UPDATE OF returned_at ON Loans
WHEN NEW.returned_at IS NOT NULL
BEGIN
  UPDATE Copies
  SET status = 'AVAILABLE'
  WHERE copy_id = NEW.copy_id;
END;

-- If an active loan row is deleted, free the copy
CREATE TRIGGER IF NOT EXISTS trg_loan_delete_active
AFTER DELETE ON Loans
WHEN OLD.returned_at IS NULL
BEGIN
  UPDATE Copies
  SET status = 'AVAILABLE'
  WHERE copy_id = OLD.copy_id;
END;

-- ------------------------------------------------------------
-- Cart/Loan coordination
-- Ensure a copy can't be loaned while it's in any cart,
-- and prevent the same copy from being in multiple carts.
-- ------------------------------------------------------------

-- Unique index so a given copy_id can appear in at most one cart row
CREATE UNIQUE INDEX IF NOT EXISTS ux_cartitems_copy_unique
ON CartItems(copy_id)
WHERE copy_id IS NOT NULL;

-- Block loan inserts if the copy is currently in any cart
CREATE TRIGGER IF NOT EXISTS trg_loan_block_if_in_cart
BEFORE INSERT ON Loans
WHEN EXISTS (
  SELECT 1
  FROM CartItems ci
  WHERE ci.copy_id = NEW.copy_id
)
BEGIN
  SELECT RAISE(ABORT, 'Copy is currently in a cart');
END;
