PRAGMA foreign_keys = ON;

-- ============================================================
-- Core tables (Artists, Records)
-- ============================================================
CREATE TABLE IF NOT EXISTS Artists (
  artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
  artist_name TEXT NOT NULL UNIQUE,
  genre TEXT
);

CREATE TABLE IF NOT EXISTS Records (
  record_id INTEGER PRIMARY KEY AUTOINCREMENT,
  artist_id INTEGER,
  title TEXT NOT NULL,
  genre TEXT,
  is_active INTEGER DEFAULT 1,
  release_date TEXT,
  total_tracks INTEGER,
  FOREIGN KEY (artist_id) REFERENCES Artists(artist_id)
);

-- ============================================================
-- User management
-- ============================================================
CREATE TABLE IF NOT EXISTS Users (
  user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  username    TEXT NOT NULL UNIQUE,
  email       TEXT NOT NULL UNIQUE,
  is_admin    INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0,1)),
  password    TEXT NOT NULL,
  created_at  TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- Physical copies
-- ============================================================
CREATE TABLE IF NOT EXISTS Copies (
  copy_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id   INTEGER NOT NULL,
  barcode     TEXT NOT NULL UNIQUE,
  purchase_price NUMERIC(10,2) DEFAULT 0,
  condition   TEXT DEFAULT 'GOOD' CHECK (condition IN ('NEW','GOOD','FAIR','POOR','DAMAGED')),
  status      TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE','CHECKED_OUT','SOLD')),
  FOREIGN KEY (record_id) REFERENCES Records(record_id) ON DELETE CASCADE
);

-- ============================================================
-- Loans (checkout system)
-- ============================================================
CREATE TABLE IF NOT EXISTS Loans (
  loan_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL,
  copy_id        INTEGER NOT NULL,
  record_id      INTEGER,
  checked_out_at DATETIME NOT NULL DEFAULT (datetime('now')),
  due_at         DATETIME NOT NULL,
  returned_at    DATETIME,
  status       TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','RETURNED','PURCHASED')),
  price_at_checkout NUMERIC(10,2) NOT NULL DEFAULT 0,
  purchase_converted_at DATETIME,
  notes          TEXT,
  FOREIGN KEY (user_id)  REFERENCES Users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (copy_id)  REFERENCES Copies(copy_id) ON DELETE CASCADE,
  FOREIGN KEY (record_id) REFERENCES Records(record_id) ON DELETE SET NULL,
  CHECK (returned_at IS NULL OR returned_at >= checked_out_at),
  CHECK (due_at >= checked_out_at),
  CHECK (NOT (returned_at IS NOT NULL AND purchase_converted_at IS NOT NULL))
);


-- ============================================================
-- Charges (money events linked to a loan)
-- ============================================================
CREATE TABLE IF NOT EXISTS Charges (
  charge_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  loan_id     INTEGER NOT NULL REFERENCES Loans(loan_id) ON DELETE CASCADE,
  type        TEXT CHECK (type IN ('purchase')) NOT NULL,
  amount      NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
  status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','failed','void')),
  created_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- E-commerce: carts, orders, payments
-- ============================================================

-- ------------------------------------------------------------
-- Shopping cart items
-- One row per item in a user's cart. For unique vinyl copies,
-- quantity will normally be 1 and copy_id will be used.
-- record_id support lets you later sell non-unique items too.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CartItems (
  cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER NOT NULL,
  copy_id      INTEGER,  -- for unique physical copies
  record_id    INTEGER,  -- optional, for generic record-level items
  quantity     INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
  added_at     DATETIME NOT NULL DEFAULT (datetime('now')),

  FOREIGN KEY (user_id)   REFERENCES Users(user_id)   ON DELETE CASCADE,
  FOREIGN KEY (copy_id)   REFERENCES Copies(copy_id)  ON DELETE CASCADE,
  FOREIGN KEY (record_id) REFERENCES Records(record_id) ON DELETE CASCADE,

  -- Ensure at least one of copy_id or record_id is set
  CHECK (copy_id IS NOT NULL OR record_id IS NOT NULL),

  -- Prevent duplicate cart entries for the same user+copy
  UNIQUE (user_id, copy_id)
);

-- ------------------------------------------------------------
-- Orders (top-level purchase records)
-- Represents a completed checkout of one or more items.
-- You can simulate taxes now or leave them at 0.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Orders (
  order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','paid','shipped','completed','cancelled')),
  subtotal      NUMERIC(10,2) NOT NULL DEFAULT 0,
  tax_amount    NUMERIC(10,2) NOT NULL DEFAULT 0,
  total_amount  NUMERIC(10,2) NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT (datetime('now')),
  updated_at    DATETIME,

  -- Simple shipping info for now; you can normalize later if needed
  shipping_name    TEXT,
  shipping_address TEXT,
  notes            TEXT,

  FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- OrderItems (line items within an order)
-- For this project, you'll mostly use copy_id (unique vinyl).
-- record_id is optional if you ever want generic record-based items.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS OrderItems (
  order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id      INTEGER NOT NULL,
  copy_id       INTEGER,
  record_id     INTEGER,
  description   TEXT,  -- snapshot description (e.g., title, artist, condition)
  unit_price    NUMERIC(10,2) NOT NULL,
  quantity      INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
  line_total    NUMERIC(10,2) NOT NULL,

  FOREIGN KEY (order_id)  REFERENCES Orders(order_id)   ON DELETE CASCADE,
  FOREIGN KEY (copy_id)   REFERENCES Copies(copy_id)    ON DELETE SET NULL,
  FOREIGN KEY (record_id) REFERENCES Records(record_id) ON DELETE SET NULL,

  -- Must reference at least a copy or a record
  CHECK (copy_id IS NOT NULL OR record_id IS NOT NULL)
);

-- ------------------------------------------------------------
-- Payments
-- Logical payment events for an order (you can simulate them in CLI).
-- Charges table remains tied to Loans; Payments are tied to Orders.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Payments (
  payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id        INTEGER NOT NULL,
  amount          NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
  method          TEXT NOT NULL,  -- e.g. 'card','cash','test','paypal'
  status          TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','authorized','captured','failed','refunded','void')),
  transaction_ref TEXT,           -- for future payment gateway IDs
  processed_at    DATETIME NOT NULL DEFAULT (datetime('now')),

  FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE
);

-- ============================================================
-- E-commerce indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_cartitems_user ON CartItems(user_id, added_at);
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON Orders(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_orderitems_order ON OrderItems(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON Payments(order_id, processed_at);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_copies_record ON Copies(record_id);
CREATE INDEX IF NOT EXISTS idx_copies_status ON Copies(status);
CREATE INDEX IF NOT EXISTS idx_loans_user ON Loans(user_id, returned_at);
CREATE INDEX IF NOT EXISTS idx_loans_copy ON Loans(copy_id, returned_at);
CREATE INDEX IF NOT EXISTS idx_loans_due ON Loans(due_at, returned_at);
CREATE INDEX IF NOT EXISTS idx_charges_loan ON Charges(loan_id);
CREATE INDEX IF NOT EXISTS idx_charges_status ON Charges(status, created_at);

-- ============================================================
-- Constraints
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS ux_copies_barcode ON Copies(barcode);
CREATE UNIQUE INDEX IF NOT EXISTS ux_loans_active_copy ON Loans(copy_id) WHERE returned_at IS NULL;
-- Ensure one logical record per artist+title+release_date (idempotent seed)
CREATE UNIQUE INDEX IF NOT EXISTS ux_records_artist_title_release ON Records(artist_id, title, release_date);
  -- Prevnet duplicate purchase charges per loan
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_purchase_per_loan ON Charges(loan_id, type);