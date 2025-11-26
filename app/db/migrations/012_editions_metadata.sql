-- Migration 012: Add edition metadata fields to book_metadata table
-- ============================================================================
-- Purpose: Support editions endpoint optimization
--
-- Changes:
-- - Add language field to store edition language (English, French, etc.)
-- - Add reading_format field to store format (Read, Listened, etc.)
-- - Add index on language for faster filtering
--
-- Context: The editions endpoint returns richer metadata than books endpoint,
-- including language and reading format which enables audiobook detection
-- without additional API calls.
-- ============================================================================

-- Add language field to book_metadata table
ALTER TABLE book_metadata ADD COLUMN language TEXT;

-- Add reading_format field to book_metadata table
ALTER TABLE book_metadata ADD COLUMN reading_format TEXT;

-- Index for language filtering queries
CREATE INDEX IF NOT EXISTS idx_book_metadata_language ON book_metadata(language);

-- Note: has_audiobook column already exists from migration 011
-- Note: This migration is idempotent (uses IF NOT EXISTS)
