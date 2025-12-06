-- Migration 017: Add multi-series mapping per library item
-- ----------------------------------------------------------------------------
-- Purpose: allow a single book to belong to multiple series by storing mappings
--          in a dedicated table keyed by library + item id + series name.
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS library_item_series (
    item_id TEXT NOT NULL,
    library_id TEXT NOT NULL,
    series_name TEXT NOT NULL,
    series_index REAL,
    PRIMARY KEY (item_id, library_id, series_name)
);

CREATE INDEX IF NOT EXISTS idx_library_item_series_series
    ON library_item_series(series_name, library_id);

CREATE INDEX IF NOT EXISTS idx_library_item_series_library
    ON library_item_series(library_id);
