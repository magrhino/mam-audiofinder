"""SQLite-backed library cache with async sync."""

import asyncio
import logging
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy import text, bindparam

from db.db import covers_engine
from utils import normalize_title, normalize_author
from abs.models import LibraryItem, LibrarySyncStatus
from abs.matching import calculate_match_score

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
        """Bulk upsert items with pre-computed normalized fields (multi-series aware)."""
        with covers_engine.begin() as conn:
            # Reset cache for this library before inserting fresh data
            conn.execute(text("""
                DELETE FROM library_items WHERE library_id = :lib_id
            """), {"lib_id": self.library_id})
            conn.execute(text("""
                DELETE FROM library_item_series WHERE library_id = :lib_id
            """), {"lib_id": self.library_id})

            item_rows = []
            series_rows = []

            def parse_series_tokens(raw_name: Optional[str], sequence_value) -> List[Tuple[Optional[str], Optional[float]]]:
                if not isinstance(raw_name, str):
                    return []

                parts = [p.strip() for p in raw_name.split(',') if p and p.strip()]
                results: List[Tuple[Optional[str], Optional[float]]] = []

                for part in parts:
                    base = part
                    index = None

                    if sequence_value is not None:
                        try:
                            index = float(sequence_value)
                        except (ValueError, TypeError):
                            index = None

                    match = re.match(r"^(.*?)(?:\s*#\s*(\d+(?:\.\d+)?))$", base)
                    if match:
                        base = match.group(1).strip()
                        if index is None:
                            try:
                                index = float(match.group(2))
                            except (ValueError, TypeError):
                                index = None
                    else:
                        base = base.strip()

                    if base:
                        results.append((base, index))

                return results

            for item in items:
                metadata = item.get("media", {}).get("metadata", {})
                title = metadata.get("title", "")
                author = metadata.get("authorName", "")

                raw_series_name = metadata.get("seriesName")
                series_list = metadata.get("series", []) if isinstance(metadata.get("series", []), list) else []

                item_series_rows = []
                seen_keys = set()

                # Collect all series mappings for this item from explicit series list
                for series_entry in series_list:
                    if not isinstance(series_entry, dict):
                        continue
                    raw_name = series_entry.get("name") or raw_series_name
                    tokens = parse_series_tokens(raw_name, series_entry.get("sequence"))
                    for mapped_name, mapped_index in tokens:
                        key = (mapped_name, mapped_index)
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        item_series_rows.append({
                            "item_id": item.get("id"),
                            "lib_id": self.library_id,
                            "series": mapped_name,
                            "series_index": mapped_index,
                        })

                # Fallback: parse seriesName if series array missing
                if not item_series_rows and raw_series_name:
                    tokens = parse_series_tokens(raw_series_name, None)
                    for mapped_name, mapped_index in tokens:
                        key = (mapped_name, mapped_index)
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        item_series_rows.append({
                            "item_id": item.get("id"),
                            "lib_id": self.library_id,
                            "series": mapped_name,
                            "series_index": mapped_index,
                        })

                series_rows.extend(item_series_rows)

                # Preserve backward-compatible single-series columns using the first mapping (if any)
                series_name = None
                series_index = None
                if item_series_rows:
                    first_mapping = item_series_rows[0]
                    series_name = first_mapping["series"]
                    series_index = first_mapping["series_index"]

                item_rows.append({
                    "id": item.get("id"),
                    "lib_id": self.library_id,
                    "title": title,
                    "author": author,
                    "narrator": metadata.get("narratorName"),
                    "series": series_name,
                    "series_index": series_index,
                    "asin": metadata.get("asin"),
                    "isbn": metadata.get("isbn"),
                    "cover": item.get("media", {}).get("coverPath"),
                    "duration": item.get("media", {}).get("duration"),
                    "path": item.get("path"),
                    "title_norm": normalize_title(title),
                    "author_norm": normalize_author(author),
                })

            if item_rows:
                conn.execute(text("""
                    INSERT INTO library_items
                    (id, library_id, title, author, narrator, series_name, series_index,
                     asin, isbn, cover_path, duration_seconds, path,
                     title_normalized, author_normalized, synced_at)
                    VALUES
                    (:id, :lib_id, :title, :author, :narrator, :series, :series_index,
                     :asin, :isbn, :cover, :duration, :path,
                     :title_norm, :author_norm, datetime('now'))
                """), item_rows)

            if series_rows:
                conn.execute(text("""
                    INSERT INTO library_item_series
                    (item_id, library_id, series_name, series_index)
                    VALUES
                    (:item_id, :lib_id, :series, :series_index)
                """), series_rows)

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
        """Check presence of (title, author) pairs in library with a single query."""
        if not items:
            return {}

        normalized_pairs = []
        title_norms = set()
        for title, author in items:
            title_norm = normalize_title(title)
            author_norm = normalize_author(author)
            normalized_pairs.append((title_norm, author_norm))
            title_norms.add(title_norm)

        results: Dict[str, bool] = {f"{t}||{a}": False for t, a in normalized_pairs}

        with covers_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT title_normalized, author_normalized
                    FROM library_items
                    WHERE library_id = :lib_id
                      AND title_normalized IN :title_norms
                """)
                .bindparams(bindparam("title_norms", expanding=True)),
                {"lib_id": self.library_id, "title_norms": list(title_norms)},
            ).fetchall()

            by_title = {}
            for row in rows:
                by_title.setdefault(row.title_normalized, []).append(row.author_normalized)

            for title_norm, author_norm in normalized_pairs:
                key = f"{title_norm}||{author_norm}"
                authors = by_title.get(title_norm)
                if not authors:
                    continue

                for candidate_author in authors:
                    if candidate_author == author_norm:
                        results[key] = True
                        break
                    if author_norm in candidate_author or candidate_author in author_norm:
                        results[key] = True
                        break

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

    def get_series_books(self, series_name: str) -> List[LibraryItem]:
        """Get all books belonging to a series (multi-series aware)."""
        with covers_engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT li.*, sis.series_name AS mapped_series_name, sis.series_index AS mapped_series_index
                FROM library_item_series sis
                JOIN library_items li
                  ON li.id = sis.item_id AND li.library_id = sis.library_id
                WHERE sis.library_id = :lib_id
                  AND sis.series_name = :name
                ORDER BY sis.series_index NULLS LAST, li.title_normalized
            """), {
                "lib_id": self.library_id,
                "name": series_name,
            }).fetchall()

            return [self._row_to_item(row) for row in rows]

    def get_series_summary(self) -> List[Dict]:
        """Get aggregated series summary (supports books mapped to multiple series)."""
        with covers_engine.connect() as conn:
            series_rows = conn.execute(text("""
                SELECT sis.series_name,
                       sis.series_index,
                       li.author
                FROM library_item_series sis
                JOIN library_items li
                  ON li.id = sis.item_id AND li.library_id = sis.library_id
                WHERE sis.library_id = :lib_id
            """), {"lib_id": self.library_id}).fetchall()

        summaries: Dict[str, Dict] = {}
        for row in series_rows:
            entry = summaries.setdefault(row.series_name, {
                "name": row.series_name,
                "book_count": 0,
                "first_index": None,
                "last_index": None,
                "authors": [],
            })
            entry["book_count"] += 1
            if row.series_index is not None:
                if entry["first_index"] is None or row.series_index < entry["first_index"]:
                    entry["first_index"] = row.series_index
                if entry["last_index"] is None or row.series_index > entry["last_index"]:
                    entry["last_index"] = row.series_index
            if row.author:
                entry["authors"].append(row.author)

        # Derive most common author for each series
        from collections import Counter
        result = []
        for entry in summaries.values():
            author = None
            if entry["authors"]:
                counts = Counter(entry["authors"])
                author = counts.most_common(1)[0][0]
            result.append({
                "name": entry["name"],
                "book_count": entry["book_count"],
                "first_index": entry["first_index"],
                "last_index": entry["last_index"],
                "author": author,
            })

        return sorted(result, key=lambda x: x["name"])

    def _row_to_item(self, row) -> LibraryItem:
        """Convert database row to LibraryItem model."""
        series_index = getattr(row, 'mapped_series_index', None)
        if series_index is None:
            series_index = getattr(row, 'series_index', None)

        return LibraryItem(
            id=row.id,
            library_id=row.library_id,
            title=row.title,
            author=row.author,
            narrator=row.narrator,
            series_name=getattr(row, 'mapped_series_name', None) or row.series_name,
            series_index=series_index,
            asin=row.asin,
            isbn=row.isbn,
            cover_path=row.cover_path,
            duration_seconds=row.duration_seconds,
            path=row.path,
            title_normalized=row.title_normalized,
            author_normalized=row.author_normalized,
        )
