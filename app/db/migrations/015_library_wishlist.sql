-- Migration 015: Create wishlist table for missing book tracking
-- ============================================================================
-- Purpose: Track books user wants to acquire (from Hardcover diff results)
-- ============================================================================

CREATE TABLE IF NOT EXISTS library_wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Book identification
    title TEXT NOT NULL,
    author TEXT,
    series_name TEXT,
    series_index REAL,

    -- External IDs
    hardcover_book_id INTEGER,
    asin TEXT,
    isbn TEXT,

    -- Cover URL from Hardcover
    cover_url TEXT,

    -- Status tracking
    status TEXT DEFAULT 'pending',  -- pending, searching, found, added, imported, cancelled

    -- MAM search tracking (once search attempted)
    mam_search_query TEXT,
    mam_search_at TEXT,
    mam_result_count INTEGER,

    -- History link (once added to qBittorrent)
    history_id INTEGER REFERENCES history(id),

    -- Timestamps
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_wishlist_status ON library_wishlist(status);
CREATE INDEX IF NOT EXISTS idx_wishlist_series ON library_wishlist(series_name);
CREATE INDEX IF NOT EXISTS idx_wishlist_hardcover_id ON library_wishlist(hardcover_book_id);
