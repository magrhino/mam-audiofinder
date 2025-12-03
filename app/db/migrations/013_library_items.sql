-- Migration 013: Create library_items cache tables for ABS library integration
-- ============================================================================
-- Purpose: SQLite-backed ABS library cache for presence checks and verification matching
--
-- Changes:
-- - Create library_items table with normalized search fields
-- - Create library_sync_status table for sync tracking
-- - Add indexes for efficient title/author/ASIN/ISBN lookups
--
-- Context: Part of abscli integration - replaces in-memory caching with persistent
-- SQLite storage for better performance and library presence checking.
-- ============================================================================

-- ABS library item cache for presence checks and verification matching
CREATE TABLE IF NOT EXISTS library_items (
    id TEXT PRIMARY KEY,
    library_id TEXT NOT NULL,

    -- Core metadata
    title TEXT NOT NULL,
    author TEXT,
    narrator TEXT,
    series_name TEXT,

    -- Identifiers for verification matching
    asin TEXT,
    isbn TEXT,

    -- Additional metadata
    cover_path TEXT,
    duration_seconds REAL,
    path TEXT,

    -- Pre-computed normalized fields for indexed lookup
    title_normalized TEXT,
    author_normalized TEXT,

    -- Sync tracking
    synced_at TEXT DEFAULT (datetime('now')),

    UNIQUE(id, library_id)
);

CREATE INDEX IF NOT EXISTS idx_library_items_title_norm
    ON library_items(title_normalized);
CREATE INDEX IF NOT EXISTS idx_library_items_author_norm
    ON library_items(author_normalized);
CREATE INDEX IF NOT EXISTS idx_library_items_asin
    ON library_items(asin) WHERE asin IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_library_items_isbn
    ON library_items(isbn) WHERE isbn IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_library_items_library
    ON library_items(library_id);

-- Sync status tracking
CREATE TABLE IF NOT EXISTS library_sync_status (
    library_id TEXT PRIMARY KEY,
    last_full_sync TEXT,
    last_item_count INTEGER,
    sync_in_progress INTEGER DEFAULT 0
);
