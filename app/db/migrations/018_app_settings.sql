-- Runtime-configurable application settings
-- Target: history.db (app_settings pattern in db.py)

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Default settings (auto_import disabled by default for safety)
INSERT OR IGNORE INTO app_settings (key, value, description) VALUES
    ('auto_import_enabled', 'false', 'Enable automatic import of completed torrents');

INSERT OR IGNORE INTO app_settings (key, value, description) VALUES
    ('auto_import_flatten', 'true', 'Flatten multi-disc structure during auto-import');

INSERT OR IGNORE INTO app_settings (key, value, description) VALUES
    ('auto_import_poll_interval', '30', 'Polling interval in seconds (15-300)');
