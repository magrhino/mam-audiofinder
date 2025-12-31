-- Speed up library lookups by normalized title/author
CREATE INDEX IF NOT EXISTS idx_library_items_title_norm
  ON library_items (library_id, title_normalized);

CREATE INDEX IF NOT EXISTS idx_library_items_author_norm
  ON library_items (library_id, author_normalized);
