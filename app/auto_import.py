"""
Auto-Import Service for MAM Audiobook Finder.
Background service that monitors qBittorrent for completed torrents and automatically imports them.
"""
import asyncio
import logging
import re
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from sqlalchemy import text

from config import QB_URL, QB_CATEGORY, DL_DIR, LIB_DIR, IMPORT_MODE, AUDIO_EXTS, QB_POSTIMPORT_CATEGORY
from db import engine
from qb_client import qb_login as qb_login_async
from settings_service import settings_service
from utils import sanitize, next_available, extract_disc_track, try_hardlink
from dependencies.qb import map_qb_content_path
from abs_client import abs_client

logger = logging.getLogger("mam-audiofinder")

# Multi-book detection patterns
BOOK_PATTERNS = [
    re.compile(r'^book\s*(\d+)', re.IGNORECASE),
    re.compile(r'^(\d+)\s*[-–]\s*', re.IGNORECASE),
    re.compile(r'^part\s*(\d+)\s*[-–]', re.IGNORECASE),
    re.compile(r'^volume\s*(\d+)', re.IGNORECASE),
    re.compile(r'^vol\.?\s*(\d+)', re.IGNORECASE),
]


def _is_multi_book_torrent(files: list[dict], torrent_name: str) -> tuple[bool, str]:
    """
    Detect if a torrent contains multiple audiobooks.

    Args:
        files: List of file dicts with 'name' key
        torrent_name: Name of the torrent

    Returns:
        Tuple of (is_multi_book, reason)
    """
    if not files:
        return False, "No files"

    # Get all top-level directories
    top_level_dirs = set()
    for f in files:
        name = (f.get("name") or "").lstrip("/")
        if "/" in name:
            top_dir = name.split("/", 1)[0]
            top_level_dirs.add(top_dir)

    # If only one or zero top-level dirs, likely single book
    if len(top_level_dirs) <= 1:
        return False, "Single directory structure"

    # Check if directories match book patterns
    book_dirs = []
    for dir_name in top_level_dirs:
        for pattern in BOOK_PATTERNS:
            if pattern.search(dir_name):
                book_dirs.append(dir_name)
                break

    # If multiple directories match book patterns, it's multi-book
    if len(book_dirs) >= 2:
        return True, f"Multiple book directories detected: {', '.join(sorted(book_dirs)[:3])}"

    # Check for numbered directories (1, 2, 3... or 01, 02, 03...)
    numbered_dirs = []
    for dir_name in top_level_dirs:
        # Strip leading zeros and check if it's a number
        stripped = dir_name.lstrip("0")
        if stripped.isdigit() and int(stripped) <= 50:  # Reasonable book count limit
            numbered_dirs.append(dir_name)

    if len(numbered_dirs) >= 2:
        return True, f"Multiple numbered directories detected: {', '.join(sorted(numbered_dirs)[:3])}"

    # Check for common series patterns in directory names
    series_indicators = ["book", "volume", "vol", "part", "episode", "ep"]
    indicator_count = 0
    for dir_name in top_level_dirs:
        dir_lower = dir_name.lower()
        for indicator in series_indicators:
            if indicator in dir_lower:
                indicator_count += 1
                break

    if indicator_count >= 2:
        return True, f"Multiple directories with series indicators ({indicator_count} found)"

    return False, f"Single book structure ({len(top_level_dirs)} top-level dirs)"


def _copy_one(src: Path, dst: Path) -> str:
    """
    Copy/link/move a file based on IMPORT_MODE.
    Returns: "linked", "copied", or "moved"
    """
    import shutil
    dst.parent.mkdir(parents=True, exist_ok=True)
    if IMPORT_MODE == "move":
        shutil.move(src, dst)
        return "moved"
    elif IMPORT_MODE == "link":
        if try_hardlink(src, dst):
            return "linked"
        else:
            shutil.copy2(src, dst)
            return "copied"
    else:  # copy
        shutil.copy2(src, dst)
        return "copied"


class AutoImportService:
    """
    Background service that monitors qBittorrent for completed torrents
    and automatically imports single-book audiobooks.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._enabled = False
        self._poll_interval = 30
        self._flatten = True
        self._lock = asyncio.Lock()
        self._last_poll_time: Optional[datetime] = None
        self._pending_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def poll_interval(self) -> int:
        return self._poll_interval

    @property
    def last_poll_time(self) -> Optional[datetime]:
        return self._last_poll_time

    @property
    def pending_count(self) -> int:
        return self._pending_count

    async def start(self):
        """Start the auto-import background task."""
        if self._running:
            return

        await self.reload_settings()
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"🚀 Auto-import service started (enabled={self._enabled}, interval={self._poll_interval}s)")

    async def stop(self):
        """Stop the auto-import background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Auto-import service stopped")

    async def reload_settings(self):
        """Reload settings from database."""
        config = settings_service.get_auto_import_config()
        self._enabled = config["enabled"]
        self._flatten = config["flatten"]
        self._poll_interval = max(15, min(300, config["poll_interval"]))
        logger.debug(f"Auto-import settings reloaded: enabled={self._enabled}, flatten={self._flatten}, interval={self._poll_interval}")

    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                # Reload settings each poll to pick up runtime changes
                await self.reload_settings()

                if self._enabled:
                    await self._check_and_import()
                    self._last_poll_time = datetime.now(timezone.utc)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Auto-import poll error: {e}")

            await asyncio.sleep(self._poll_interval)

    async def _check_and_import(self):
        """Check for completed torrents and trigger auto-import."""
        async with self._lock:
            # Get import candidates from history
            candidates = self._get_import_candidates()
            self._pending_count = len(candidates)

            if not candidates:
                logger.debug("Auto-import: No candidates found")
                return

            logger.debug(f"Auto-import: Found {len(candidates)} candidate(s)")

            # Get completed torrents from qBittorrent
            try:
                completed_torrents = await self._get_completed_torrents()
            except Exception as e:
                logger.error(f"Failed to fetch completed torrents: {e}")
                return

            if not completed_torrents:
                logger.debug("Auto-import: No completed torrents")
                return

            # Match candidates to completed torrents
            for candidate in candidates:
                try:
                    await self._process_candidate(candidate, completed_torrents)
                except Exception as e:
                    logger.error(f"❌ Auto-import failed for '{candidate['title']}': {e}")

    def _get_import_candidates(self) -> list[dict]:
        """Get history items eligible for auto-import."""
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, mam_id, title, author, narrator, qb_hash, qb_status,
                       auto_import_eligible
                FROM history
                WHERE qb_status != 'imported'
                  AND imported_at IS NULL
                  AND (auto_import_eligible IS NULL OR auto_import_eligible = 1)
                ORDER BY added_at ASC
                LIMIT 20
            """)).fetchall()

            return [
                {
                    "id": row[0],
                    "mam_id": row[1],
                    "title": row[2],
                    "author": row[3],
                    "narrator": row[4],
                    "qb_hash": row[5],
                    "qb_status": row[6],
                    "auto_import_eligible": row[7],
                }
                for row in rows
            ]

    async def _get_completed_torrents(self) -> list[dict]:
        """Get completed torrents from qBittorrent."""
        async with httpx.AsyncClient(timeout=30) as client:
            await qb_login_async(client)

            r = await client.get(
                f"{QB_URL}/api/v2/torrents/info",
                params={"category": QB_CATEGORY, "filter": "completed"}
            )
            r.raise_for_status()
            infos = r.json() if isinstance(r.json(), list) else []

            torrents = []
            for t in infos:
                h = t.get("hash")
                if not h:
                    continue

                # Get files to determine structure
                fr = await client.get(f"{QB_URL}/api/v2/torrents/files", params={"hash": h})
                files = fr.json() if fr.status_code == 200 else []

                # Extract MAM ID from tags
                tags = t.get("tags", "")
                mam_id = None
                match = re.search(r'mamid=(\d+)', tags)
                if match:
                    mam_id = match.group(1)

                torrents.append({
                    "hash": h,
                    "name": t.get("name"),
                    "save_path": t.get("save_path"),
                    "content_path": t.get("content_path", ""),
                    "state": t.get("state"),
                    "mam_id": mam_id,
                    "files": files,
                })

            return torrents

    async def _process_candidate(self, candidate: dict, torrents: list[dict]):
        """Process a single import candidate."""
        history_id = candidate["id"]
        qb_hash = candidate.get("qb_hash")
        mam_id = str(candidate.get("mam_id") or "").strip()
        title = candidate.get("title", "")

        # Find matching torrent
        torrent = None
        for t in torrents:
            # Match by hash first
            if qb_hash and t["hash"] == qb_hash:
                torrent = t
                break
            # Match by MAM ID
            if mam_id and t.get("mam_id") == mam_id:
                torrent = t
                break

        if not torrent:
            logger.debug(f"Auto-import: No matching torrent for '{title}'")
            return

        qb_hash = torrent["hash"]

        # Check if already tracked (idempotency)
        if self._is_already_tracked(qb_hash):
            logger.debug(f"Auto-import: Already tracked '{title}'")
            return

        # Check for multi-book structure
        is_multi_book, reason = _is_multi_book_torrent(torrent["files"], torrent["name"])
        if is_multi_book:
            logger.info(f"🚫 Auto-import skipped (multi-book): '{title}' - {reason}")
            self._mark_ineligible(history_id, qb_hash, reason)
            return

        # Track this attempt
        self._track_attempt(qb_hash, history_id, "processing")

        # Perform the import
        try:
            await self._do_import(candidate, torrent)
            self._track_completion(qb_hash, "completed")
            logger.info(f"🤖 Auto-import completed: '{title}'")
        except Exception as e:
            self._track_completion(qb_hash, "failed", str(e))
            raise

    def _is_already_tracked(self, qb_hash: str) -> bool:
        """Check if this torrent is already tracked."""
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM auto_import_tracking WHERE qb_hash = :hash"),
                {"hash": qb_hash}
            ).fetchone()
            return row is not None

    def _mark_ineligible(self, history_id: int, qb_hash: str, reason: str):
        """Mark a history item as ineligible for auto-import."""
        with engine.begin() as conn:
            # Update history
            conn.execute(
                text("UPDATE history SET auto_import_eligible = 0 WHERE id = :id"),
                {"id": history_id}
            )
            # Track as skipped
            conn.execute(
                text("""
                    INSERT INTO auto_import_tracking (qb_hash, history_id, status, reason)
                    VALUES (:hash, :history_id, 'skipped', :reason)
                    ON CONFLICT(qb_hash) DO UPDATE SET status = 'skipped', reason = excluded.reason
                """),
                {"hash": qb_hash, "history_id": history_id, "reason": reason}
            )

    def _track_attempt(self, qb_hash: str, history_id: int, status: str):
        """Track an auto-import attempt."""
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO auto_import_tracking (qb_hash, history_id, status)
                    VALUES (:hash, :history_id, :status)
                    ON CONFLICT(qb_hash) DO UPDATE SET status = excluded.status, attempted_at = datetime('now')
                """),
                {"hash": qb_hash, "history_id": history_id, "status": status}
            )

    def _track_completion(self, qb_hash: str, status: str, reason: str = None):
        """Track completion of an auto-import attempt."""
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE auto_import_tracking
                    SET status = :status, reason = :reason, completed_at = datetime('now')
                    WHERE qb_hash = :hash
                """),
                {"hash": qb_hash, "status": status, "reason": reason}
            )

    async def _do_import(self, candidate: dict, torrent: dict):
        """Perform the actual import operation."""
        history_id = candidate["id"]
        author = sanitize(candidate.get("author") or "Unknown Author")
        title = sanitize(candidate.get("title") or torrent["name"])
        qb_hash = torrent["hash"]
        content_path = torrent["content_path"]

        # Map qB's internal paths to this container's paths
        src_root = map_qb_content_path(content_path, validate_exists=False)

        if not src_root.exists():
            raise ValueError(f"Source path not found: {src_root}")

        # Destination: /library/Author/Title
        lib = Path(LIB_DIR)
        author_dir = lib / author
        author_dir.mkdir(parents=True, exist_ok=True)
        dest_dir = next_available(author_dir / title)

        # Copy files
        files_copied = 0
        if src_root.is_file():
            if src_root.suffix.lower() != ".cue":
                _copy_one(src_root, dest_dir / src_root.name)
                files_copied = 1
        else:
            # Collect audio files
            audio_files = []
            for p in src_root.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() == ".cue":
                    continue
                if AUDIO_EXTS is None or p.suffix.lower() in AUDIO_EXTS:
                    audio_files.append(p)

            # Apply disc flattening if enabled
            if self._flatten and audio_files:
                files_with_info = []
                for p in audio_files:
                    disc_num, track_num, ext = extract_disc_track(p, src_root)
                    files_with_info.append((disc_num, track_num, ext, p))

                files_with_info.sort(key=lambda x: (x[0], x[1]))

                for idx, (disc_num, track_num, ext, src_path) in enumerate(files_with_info, start=1):
                    new_name = f"Part {idx:03d}{ext}"
                    _copy_one(src_path, dest_dir / new_name)
                    files_copied += 1
            else:
                for p in audio_files:
                    rel = p.relative_to(src_root)
                    _copy_one(p, dest_dir / rel)
                    files_copied += 1

        if files_copied == 0:
            raise ValueError("No audio files found to import")

        # Update history
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE history
                    SET qb_status = 'imported',
                        imported_at = :ts,
                        auto_imported = 1
                    WHERE id = :id
                """),
                {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "id": history_id}
            )

            # Update qb_hash if we didn't have it
            if not candidate.get("qb_hash"):
                conn.execute(
                    text("UPDATE history SET qb_hash = :hash WHERE id = :id"),
                    {"hash": qb_hash, "id": history_id}
                )

        # Change qB category (best effort)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                await qb_login_async(client)
                await client.post(
                    f"{QB_URL}/api/v2/torrents/setCategory",
                    data={"hashes": qb_hash, "category": QB_POSTIMPORT_CATEGORY}
                )
        except Exception:
            pass

        # Verify import (best effort, non-blocking)
        asyncio.create_task(self._verify_import(history_id, title, author, dest_dir))

    async def _verify_import(self, history_id: int, title: str, author: str, dest_dir: Path):
        """Verify the import in Audiobookshelf (background task)."""
        try:
            # Wait for ABS to scan
            await asyncio.sleep(10)

            verification_result = await abs_client.verify_import(
                title=title,
                author=author,
                library_path=str(dest_dir)
            )

            # Update database
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE history
                        SET abs_verify_status = :status, abs_verify_note = :note
                        WHERE id = :id
                    """),
                    {
                        "status": verification_result.get("status"),
                        "note": verification_result.get("note"),
                        "id": history_id
                    }
                )

            status = verification_result.get("status", "unknown")
            if status == "verified":
                logger.info(f"✅ Auto-import verification successful: '{title}'")
            else:
                logger.info(f"ℹ️ Auto-import verification status '{status}' for '{title}'")

        except Exception as e:
            logger.warning(f"Auto-import verification failed for '{title}': {e}")

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        """Get recent auto-import activity."""
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT t.id, t.qb_hash, t.history_id, t.status, t.reason,
                           t.attempted_at, t.completed_at, h.title, h.author
                    FROM auto_import_tracking t
                    LEFT JOIN history h ON t.history_id = h.id
                    ORDER BY t.attempted_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "qb_hash": row[1],
                    "history_id": row[2],
                    "status": row[3],
                    "reason": row[4],
                    "attempted_at": row[5],
                    "completed_at": row[6],
                    "title": row[7],
                    "author": row[8],
                }
                for row in rows
            ]


# Global singleton
_auto_import_service: Optional[AutoImportService] = None


def get_auto_import_service() -> AutoImportService:
    """Get the global auto-import service singleton."""
    global _auto_import_service
    if _auto_import_service is None:
        _auto_import_service = AutoImportService()
    return _auto_import_service
