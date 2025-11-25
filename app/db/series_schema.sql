-- ============================================================================
-- Series Database Schema
-- Permanent cache for series metadata, resolved editions, and book metadata
-- Separates series-related data from covers.db and history.db
-- ============================================================================

-- Drop existing tables to ensure clean slate
DROP TABLE IF EXISTS series_metadata;
DROP TABLE IF EXISTS resolved_editions;
DROP TABLE IF EXISTS book_metadata;

-- ============================================================================
-- Series Metadata Table
-- Stores canonical titles and author information for each series
-- ============================================================================
CREATE TABLE series_metadata (
    series_id INTEGER PRIMARY KEY,

    -- Series information
    title TEXT NOT NULL,
    author TEXT,

    -- Canonical titles per position (JSON object)
    -- Format: {"1": "Murderbot Diaries 1", "2": "Murderbot Diaries 2", ...}
    canonical_titles TEXT,

    -- Timestamps
    cached_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================================
-- Resolved Editions Table
-- Caches English primary edition resolution results
-- Stores which book was selected as primary for each position in a series
-- ============================================================================
CREATE TABLE resolved_editions (
    series_id INTEGER NOT NULL,
    position REAL NOT NULL,          -- Supports fractional positions (1, 1.5, 2.5)
    book_id INTEGER NOT NULL,

    -- Resolution metadata
    resolution_score REAL,            -- Combined score that led to selection
    is_ambiguous INTEGER DEFAULT 0,   -- 1 if multiple books tied in scoring

    -- Timestamps
    resolved_at TEXT DEFAULT (datetime('now')),

    PRIMARY KEY (series_id, position, book_id),
    FOREIGN KEY (series_id) REFERENCES series_metadata(series_id) ON DELETE CASCADE
);

-- ============================================================================
-- Book Metadata Table
-- Caches book-level metadata from Hardcover API (users_count, etc.)
-- Reduces API calls for popularity-based resolution
-- ============================================================================
CREATE TABLE book_metadata (
    book_id INTEGER PRIMARY KEY,

    -- Basic book information
    title TEXT,
    author TEXT,

    -- Popularity metrics (from Hardcover advanced search)
    users_count INTEGER,              -- Number of users who have this book
    rating REAL,                      -- Average rating

    -- Audiobook metadata
    has_audiobook INTEGER DEFAULT 0,  -- 0=unknown/no, 1=yes
    audio_seconds INTEGER,            -- Duration in seconds

    -- Language detection
    detected_language TEXT,           -- 'en', 'fr', 'es', etc.
    language_confidence REAL,         -- Lingua confidence score (0.0-1.0)

    -- Full metadata blob (JSON, for extensibility)
    -- Can store: alternative_titles, isbns, cover_url, etc.
    metadata TEXT,

    -- Timestamps
    fetched_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT                   -- Optional TTL for stale data cleanup
);

-- ============================================================================
-- Indexes for performance
-- ============================================================================

-- Series metadata indexes
CREATE INDEX idx_series_metadata_title ON series_metadata(title);
CREATE INDEX idx_series_metadata_author ON series_metadata(author);

-- Resolved editions indexes
CREATE INDEX idx_resolved_series_id ON resolved_editions(series_id);
CREATE INDEX idx_resolved_position ON resolved_editions(series_id, position);
CREATE INDEX idx_resolved_book_id ON resolved_editions(book_id);

-- Book metadata indexes
CREATE INDEX idx_book_metadata_title ON book_metadata(title);
CREATE INDEX idx_book_metadata_users_count ON book_metadata(users_count);
CREATE INDEX idx_book_metadata_language ON book_metadata(detected_language);
CREATE INDEX idx_book_metadata_expires_at ON book_metadata(expires_at);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp on series_metadata changes
CREATE TRIGGER update_series_metadata_timestamp
AFTER UPDATE ON series_metadata
FOR EACH ROW
BEGIN
    UPDATE series_metadata
    SET updated_at = datetime('now')
    WHERE series_id = NEW.series_id;
END;

-- Auto-cleanup expired book metadata (if expires_at is set)
CREATE TRIGGER cleanup_expired_book_metadata
AFTER INSERT ON book_metadata
BEGIN
    DELETE FROM book_metadata
    WHERE expires_at IS NOT NULL
      AND datetime(expires_at) < datetime('now');
END;
