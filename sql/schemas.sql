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
  condition   TEXT DEFAULT 'GOOD' CHECK (condition IN ('NEW','GOOD','FAIR','POOR','DAMAGED')),
  status      TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE','CHECKED_OUT','LOST','REPAIR')),
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
CREATE UNIQUE INDEX IF NOT EXISTS ux_records_artist_title_release
  ON Records(artist_id, title, release_date);