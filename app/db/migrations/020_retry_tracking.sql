-- Migration 020: Add retry tracking for auto-import and verification
-- Adds columns to track retry count, next retry time, and error messages

-- Add retry tracking columns to auto_import_tracking table
ALTER TABLE auto_import_tracking ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE auto_import_tracking ADD COLUMN next_retry_at TEXT;
ALTER TABLE auto_import_tracking ADD COLUMN last_error TEXT;

-- Add verification retry tracking to history table
ALTER TABLE history ADD COLUMN verify_retry_count INTEGER DEFAULT 0;
ALTER TABLE history ADD COLUMN verify_next_retry_at TEXT;
