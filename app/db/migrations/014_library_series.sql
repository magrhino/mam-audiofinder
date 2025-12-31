-- Migration 014: Add series tracking to library_items
-- ============================================================================
-- Purpose: Enable series-level grouping and position tracking for library diff
-- ============================================================================

-- Add series index column for book position in series
ALTER TABLE library_items ADD COLUMN series_index REAL;

-- Index for series grouping queries
CREATE INDEX IF NOT EXISTS idx_library_items_series_name
    ON library_items(series_name) WHERE series_name IS NOT NULL;

-- Composite index for series + position queries
CREATE INDEX IF NOT EXISTS idx_library_items_series_order
    ON library_items(library_id, series_name, series_index);
