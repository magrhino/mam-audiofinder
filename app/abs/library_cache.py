"""SQLite-backed library cache with async sync."""

import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy import text

from db.db import covers_engine
from utils import normalize_title, normalize_author
from abs.models import LibraryItem, LibrarySyncStatus
from abs.matching import calculate_match_score, determine_verification_status

logger = logging.getLogger("mam-audiofinder")


class LibraryCache:
    """SQLite-backed ABS library cache with TTL-aware sync."""

    STALE_THRESHOLD = 300      # 5 min - use cache, background refresh
    EXPIRED_THRESHOLD = 3600   # 1 hour - block until refresh

    def __init__(self, library_id: str, ttl: int = 300):
        self.library_id = library_id
        self.ttl = ttl
        self._sync_lock = asyncio.Lock()
        self._sync_in_progress = False

    def get_sync_status(self) -> LibrarySyncStatus:
        """Get current sync status from database."""
        with covers_engine.connect() as conn:
            row = conn.execute(text("""
                SELECT library_id, last_full_sync, last_item_count, sync_in_progress
                FROM library_sync_status WHERE library_id = :lib_id
            """), {"lib_id": self.library_id}).fetchone()

            if row:
                last_sync = row.last_full_sync
                cache_age = 0
                if last_sync:
                    sync_time = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
                    cache_age = (datetime.utcnow() - sync_time.replace(tzinfo=None)).total_seconds()

                return LibrarySyncStatus(
                    library_id=row.library_id,
                    last_full_sync=last_sync,
                    last_item_count=row.last_item_count or 0,
                    sync_in_progress=bool(row.sync_in_progress),
                    cache_age_seconds=cache_age,
                )

            return LibrarySyncStatus(
                library_id=self.library_id,
                cache_age_seconds=float('inf'),
            )

    def count(self) -> int:
        """Count cached items."""
        with covers_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM library_items WHERE library_id = :lib_id
            """), {"lib_id": self.library_id}).fetchone()
            return result[0] if result else 0

    async def ensure_fresh(self, fetch_func) -> None:
        """Ensure cache is fresh, refreshing if needed."""
        status = self.get_sync_status()

        if status.cache_age_seconds > self.EXPIRED_THRESHOLD:
            await self.full_sync(fetch_func)
        elif status.cache_age_seconds > self.STALE_THRESHOLD:
            asyncio.create_task(self.full_sync(fetch_func))

    async def full_sync(self, fetch_func) -> int:
        """Full sync from ABS API."""
        async with self._sync_lock:
            if self._sync_in_progress:
                return self.count()

            self._sync_in_progress = True
            self._set_sync_in_progress(True)

            try:
                logger.info(f"🔄 Starting full library sync for {self.library_id}")
                items = await fetch_func()
                self._upsert_items(items)
                self._update_sync_status(len(items))
                logger.info(f"✅ Library sync complete: {len(items)} items")
                return len(items)
            finally:
                self._sync_in_progress = False
                self._set_sync_in_progress(False)

    def _set_sync_in_progress(self, in_progress: bool) -> None:
        """Update sync-in-progress flag."""
        with covers_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO library_sync_status (library_id, sync_in_progress)
                VALUES (:lib_id, :in_progress)
                ON CONFLICT(library_id) DO UPDATE SET sync_in_progress = :in_progress
            """), {"lib_id": self.library_id, "in_progress": int(in_progress)})

    def _upsert_items(self, items: List[dict]) -> None:
        """Bulk upsert items with pre-computed normalized fields."""
        with covers_engine.begin() as conn:
            # Clear existing items for this library
            conn.execute(text("""
                DELETE FROM library_items WHERE library_id = :lib_id
            """), {"lib_id": self.library_id})

            for item in items:
                metadata = item.get("media", {}).get("metadata", {})
                title = metadata.get("title", "")
                author = metadata.get("authorName", "")

                conn.execute(text("""
                    INSERT INTO library_items
                    (id, library_id, title, author, narrator, series_name,
                     asin, isbn, cover_path, duration_seconds, path,
                     title_normalized, author_normalized, synced_at)
                    VALUES
                    (:id, :lib_id, :title, :author, :narrator, :series,
                     :asin, :isbn, :cover, :duration, :path,
                     :title_norm, :author_norm, datetime('now'))
                """), {
                    "id": item.get("id"),
                    "lib_id": self.library_id,
                    "title": title,
                    "author": author,
                    "narrator": metadata.get("narratorName"),
                    "series": metadata.get("seriesName"),
                    "asin": metadata.get("asin"),
                    "isbn": metadata.get("isbn"),
                    "cover": item.get("media", {}).get("coverPath"),
                    "duration": item.get("media", {}).get("duration"),
                    "path": item.get("path"),
                    "title_norm": normalize_title(title),
                    "author_norm": normalize_author(author),
                })

    def _update_sync_status(self, count: int) -> None:
        """Update sync status after successful sync."""
        with covers_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO library_sync_status (library_id, last_full_sync, last_item_count, sync_in_progress)
                VALUES (:lib_id, datetime('now'), :count, 0)
                ON CONFLICT(library_id) DO UPDATE SET
                    last_full_sync = datetime('now'),
                    last_item_count = :count,
                    sync_in_progress = 0
            """), {"lib_id": self.library_id, "count": count})

    def check_presence(self, items: List[Tuple[str, str]]) -> Dict[str, bool]:
        """Check presence of (title, author) pairs in library."""
        results = {}

        with covers_engine.connect() as conn:
            for title, author in items:
                cache_key = f"{title}||{author}"
                title_norm = normalize_title(title)
                author_norm = normalize_author(author)

                row = conn.execute(text("""
                    SELECT 1 FROM library_items
                    WHERE library_id = :lib_id
                      AND title_normalized = :title_norm
                      AND (author_normalized = :author_norm
                           OR author_normalized LIKE :author_pattern
                           OR :author_norm LIKE '%' || author_normalized || '%')
                    LIMIT 1
                """), {
                    "lib_id": self.library_id,
                    "title_norm": title_norm,
                    "author_norm": author_norm,
                    "author_pattern": f"%{author_norm}%",
                }).fetchone()

                results[cache_key] = row is not None

        return results

    def find_best_match(
        self,
        title: str,
        author: str,
        asin: Optional[str] = None,
        isbn: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Tuple[Optional[LibraryItem], int]:
        """Find best matching library item with score."""

        with covers_engine.connect() as conn:
            # Priority 1: ASIN exact match
            if asin:
                row = conn.execute(text("""
                    SELECT * FROM library_items
                    WHERE library_id = :lib_id AND asin = :asin
                """), {"lib_id": self.library_id, "asin": asin}).fetchone()
                if row:
                    return self._row_to_item(row), 200

            # Priority 2: ISBN exact match
            if isbn:
                row = conn.execute(text("""
                    SELECT * FROM library_items
                    WHERE library_id = :lib_id AND isbn = :isbn
                """), {"lib_id": self.library_id, "isbn": isbn}).fetchone()
                if row:
                    return self._row_to_item(row), 200

            # Priority 3: Title/author fuzzy match
            title_norm = normalize_title(title)
            candidates = conn.execute(text("""
                SELECT * FROM library_items
                WHERE library_id = :lib_id
                  AND (title_normalized = :title_norm
                       OR title_normalized LIKE :title_pattern
                       OR :title_norm LIKE '%' || title_normalized || '%')
                LIMIT 10
            """), {
                "lib_id": self.library_id,
                "title_norm": title_norm,
                "title_pattern": f"%{title_norm}%",
            }).fetchall()

            if not candidates:
                return None, 0

            # Score candidates
            best_item = None
            best_score = 0

            for row in candidates:
                item = self._row_to_item(row)
                score = calculate_match_score(
                    query_title=title,
                    query_author=author,
                    candidate=item,
                    query_asin=asin,
                    query_isbn=isbn,
                    query_path=path,
                )
                if score > best_score:
                    best_score = score
                    best_item = item

            return best_item, best_score

    def _row_to_item(self, row) -> LibraryItem:
        """Convert database row to LibraryItem model."""
        return LibraryItem(
            id=row.id,
            library_id=row.library_id,
            title=row.title,
            author=row.author,
            narrator=row.narrator,
            series_name=row.series_name,
            asin=row.asin,
            isbn=row.isbn,
            cover_path=row.cover_path,
            duration_seconds=row.duration_seconds,
            path=row.path,
            title_normalized=row.title_normalized,
            author_normalized=row.author_normalized,
        )
