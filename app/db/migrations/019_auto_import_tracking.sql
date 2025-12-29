-- Track auto-import attempts for idempotency and history
-- Target: history.db (auto_import_tracking pattern in db.py)

CREATE TABLE IF NOT EXISTS auto_import_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qb_hash TEXT NOT NULL,
    history_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    attempted_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (history_id) REFERENCES history(id) ON DELETE CASCADE
);

-- Unique constraint to prevent duplicate auto-import attempts
CREATE UNIQUE INDEX IF NOT EXISTS idx_auto_import_hash ON auto_import_tracking(qb_hash);

-- Index for querying by status
CREATE INDEX IF NOT EXISTS idx_auto_import_status ON auto_import_tracking(status);

-- Add auto_import_eligible column to history table
-- 1 = eligible for auto-import (single-book), 0 = not eligible (multi-book detected)
ALTER TABLE history ADD COLUMN auto_import_eligible INTEGER DEFAULT 1;

-- Add auto_imported column to track which items were auto-imported
-- 1 = auto-imported, 0 = manually imported
ALTER TABLE history ADD COLUMN auto_imported INTEGER DEFAULT 0;
