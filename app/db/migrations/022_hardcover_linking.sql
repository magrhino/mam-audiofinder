-- Migration 022: Add Hardcover series linking
-- ============================================================================
-- Purpose: Enable persistent linking of ABS series names to Hardcover series IDs
--          for faster diff operations and manual override capability.
-- ============================================================================

-- Table to store series -> Hardcover links
CREATE TABLE IF NOT EXISTS series_hardcover_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_name TEXT NOT NULL,
    series_name_normalized TEXT NOT NULL,
    library_id TEXT,  -- Optional: link can be library-specific or global (NULL)
    hardcover_series_id INTEGER NOT NULL,
    hardcover_series_name TEXT,
    hardcover_author_name TEXT,
    hardcover_book_count INTEGER,
    link_confidence REAL DEFAULT 0.0,  -- 0.0-1.0, 1.0 = manual override
    linked_at TEXT DEFAULT (datetime('now')),
    linked_by TEXT DEFAULT 'auto',  -- 'auto' or 'manual'
    UNIQUE(series_name_normalized, library_id)
);

-- Index for quick lookups by series name
CREATE INDEX IF NOT EXISTS idx_series_hardcover_link_name
    ON series_hardcover_link(series_name_normalized);

-- Index for Hardcover ID lookups (for reverse mapping)
CREATE INDEX IF NOT EXISTS idx_series_hardcover_link_hc_id
    ON series_hardcover_link(hardcover_series_id);

-- Index for library-scoped queries
CREATE INDEX IF NOT EXISTS idx_series_hardcover_link_library
    ON series_hardcover_link(library_id) WHERE library_id IS NOT NULL;
