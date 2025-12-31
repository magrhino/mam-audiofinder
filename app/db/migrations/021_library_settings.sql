-- Migration 021: Library settings for multi-library support
-- Stores which libraries are enabled for search and other library preferences

-- Add enabled_library_ids setting (JSON array of library IDs)
INSERT OR IGNORE INTO app_settings (key, value, description)
VALUES ('enabled_library_ids', '[]', 'JSON array of enabled ABS library IDs for search');

-- Add libraries_initialized flag (set to true after first library sync)
INSERT OR IGNORE INTO app_settings (key, value, description)
VALUES ('libraries_initialized', 'false', 'Whether libraries have been initialized from ABS');

-- Add cached_libraries setting (JSON array of library metadata for display)
INSERT OR IGNORE INTO app_settings (key, value, description)
VALUES ('cached_libraries', '[]', 'Cached library metadata from ABS for display');
