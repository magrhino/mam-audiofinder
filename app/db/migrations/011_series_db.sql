-- ============================================================================
-- Migration 011: Create series.db tables
-- Adds permanent cache for series metadata, resolved editions, and book data
-- This migration creates the foundation for English primary edition resolution
-- ============================================================================

-- ============================================================================
-- Series Metadata Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS series_metadata (
    series_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    canonical_titles TEXT,
    cached_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================================
-- Resolved Editions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS resolved_editions (
    series_id INTEGER NOT NULL,
    position REAL NOT NULL,
    book_id INTEGER NOT NULL,
    resolution_score REAL,
    is_ambiguous INTEGER DEFAULT 0,
    resolved_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (series_id, position, book_id),
    FOREIGN KEY (series_id) REFERENCES series_metadata(series_id) ON DELETE CASCADE
);

-- ============================================================================
-- Book Metadata Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS book_metadata (
    book_id INTEGER PRIMARY KEY,
    title TEXT,
    author TEXT,
    users_count INTEGER,
    rating REAL,
    has_audiobook INTEGER DEFAULT 0,
    audio_seconds INTEGER,
    detected_language TEXT,
    language_confidence REAL,
    metadata TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Series metadata indexes
CREATE INDEX IF NOT EXISTS idx_series_metadata_title ON series_metadata(title);
CREATE INDEX IF NOT EXISTS idx_series_metadata_author ON series_metadata(author);

-- Resolved editions indexes
CREATE INDEX IF NOT EXISTS idx_resolved_series_id ON resolved_editions(series_id);
CREATE INDEX IF NOT EXISTS idx_resolved_position ON resolved_editions(series_id, position);
CREATE INDEX IF NOT EXISTS idx_resolved_book_id ON resolved_editions(book_id);

-- Book metadata indexes
CREATE INDEX IF NOT EXISTS idx_book_metadata_title ON book_metadata(title);
CREATE INDEX IF NOT EXISTS idx_book_metadata_users_count ON book_metadata(users_count);
CREATE INDEX IF NOT EXISTS idx_book_metadata_language ON book_metadata(detected_language);
CREATE INDEX IF NOT EXISTS idx_book_metadata_expires_at ON book_metadata(expires_at);

-- ============================================================================
-- Triggers (Drop first if they exist, then recreate)
-- ============================================================================

-- Auto-update updated_at timestamp on series_metadata changes
DROP TRIGGER IF EXISTS update_series_metadata_timestamp;
CREATE TRIGGER update_series_metadata_timestamp
AFTER UPDATE ON series_metadata
FOR EACH ROW
BEGIN
    UPDATE series_metadata
    SET updated_at = datetime('now')
    WHERE series_id = NEW.series_id;
END;

-- Auto-cleanup expired book metadata
DROP TRIGGER IF EXISTS cleanup_expired_book_metadata;
CREATE TRIGGER cleanup_expired_book_metadata
AFTER INSERT ON book_metadata
BEGIN
    DELETE FROM book_metadata
    WHERE expires_at IS NOT NULL
      AND datetime(expires_at) < datetime('now');
END;
