-- ============================================================================
-- Fresh Covers Database Schema
-- Created to replace migrations 005, 008, 009
-- Includes enhanced metadata fields from /api/search/books endpoint
-- ============================================================================

-- Drop existing tables to ensure clean slate
-- (Safe to run - covers.db is cache only, no critical data)
DROP TABLE IF EXISTS covers;
DROP TABLE IF EXISTS series_cache;

-- Main covers table with enhanced metadata fields
CREATE TABLE covers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mam_id TEXT UNIQUE NOT NULL,

    -- Basic book information
    title TEXT,
    author TEXT,

    -- Cover image data
    cover_url TEXT NOT NULL,
    local_file TEXT,
    file_size INTEGER,

    -- ABS integration
    abs_item_id TEXT,

    -- Enhanced metadata fields (from /api/search/books)
    narrator TEXT,                      -- NEW: Narrator name(s)
    publisher TEXT,                     -- NEW: Publisher name
    published_year TEXT,                -- NEW: Year published
    language TEXT,                      -- NEW: Language code (e.g., "English")
    region TEXT,                        -- NEW: Region code (e.g., "us", "uk")
    rating TEXT,                        -- NEW: Rating score (e.g., "4.8")
    duration INTEGER,                   -- NEW: Duration in minutes
    abridged INTEGER DEFAULT 0,         -- NEW: 0=unabridged, 1=abridged

    -- Identifiers
    asin TEXT,                          -- NEW: Amazon ASIN
    isbn TEXT,                          -- NEW: ISBN

    -- Descriptions
    abs_description TEXT,               -- HTML description
    description_plain TEXT,             -- NEW: Plain text description

    -- Series information (JSON array)
    series_data TEXT,                   -- NEW: JSON array of series objects

    -- Genre and tagging (JSON arrays)
    genres TEXT,                        -- NEW: JSON array of genres
    tags TEXT,                          -- NEW: Comma-delimited tags

    -- Full metadata blob (for future extensibility)
    abs_metadata TEXT,                  -- JSON blob with all metadata

    -- Timestamps
    fetched_at TEXT DEFAULT (datetime('now')),
    abs_metadata_fetched_at TEXT,

    -- Metadata source tracking
    description_source TEXT             -- 'abs', 'hardcover', 'provider', etc.
);

-- Series cache table (from migration 009, unchanged)
CREATE TABLE series_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,        -- 'search:{hash}' or 'series:{id}'
    cache_type TEXT NOT NULL,               -- 'search' or 'books'

    -- Search cache fields
    query_title TEXT,
    query_author TEXT,
    query_normalized TEXT,

    -- Series cache fields
    series_id INTEGER,
    series_name TEXT,
    series_author TEXT,

    -- Cache data (JSON blob)
    response_data TEXT NOT NULL,

    -- Cache metadata
    cached_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,               -- TTL: calculated from HARDCOVER_CACHE_TTL
    hit_count INTEGER DEFAULT 0
);

-- ============================================================================
-- Indexes for performance
-- ============================================================================

-- Covers table indexes
CREATE INDEX idx_covers_mam_id ON covers(mam_id);
CREATE INDEX idx_covers_abs_item_id ON covers(abs_item_id);
CREATE INDEX idx_covers_asin ON covers(asin);
CREATE INDEX idx_covers_isbn ON covers(isbn);
CREATE INDEX idx_covers_title_author ON covers(title, author);

-- Series cache indexes
CREATE INDEX idx_series_cache_key ON series_cache(cache_key);
CREATE INDEX idx_series_expires_at ON series_cache(expires_at);
CREATE INDEX idx_series_id ON series_cache(series_id);
CREATE INDEX idx_series_cache_type ON series_cache(cache_type);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-cleanup expired cache entries
CREATE TRIGGER cleanup_expired_series_cache
AFTER INSERT ON series_cache
BEGIN
    DELETE FROM series_cache
    WHERE datetime(expires_at) < datetime('now');
END;
