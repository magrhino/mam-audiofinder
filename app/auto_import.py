"""
Auto-Import Service for MAM Audiobook Finder.
Background service that monitors qBittorrent for completed torrents and automatically imports them.
"""
import asyncio
import logging
import re
import httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

from sqlalchemy import text

from config import QB_URL, QB_CATEGORY, DL_DIR, LIB_DIR, IMPORT_MODE, AUDIO_EXTS, QB_POSTIMPORT_CATEGORY, IMAGE_EXTS
from db import engine
from qb_client import qb_login as qb_login_async
from settings_service import settings_service
from utils import sanitize, next_available, extract_disc_track, try_hardlink
from dependencies.qb import map_qb_content_path
from abs_client import abs_client
from covers import CoverService

logger = logging.getLogger("mam-audiofinder")

# Retry configuration: exponential backoff (1min, 2min, 4min, 8min, 16min = ~31min total)
MAX_RETRY_COUNT = 5
RETRY_BACKOFF_BASE = 60  # 1 minute base

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
    Ignores directories that only contain image files (covers, artwork).

    Args:
        files: List of file dicts with 'name' key
        torrent_name: Name of the torrent

    Returns:
        Tuple of (is_multi_book, reason)
    """
    if not files:
        return False, "No files"

    # Get all top-level directories, tracking which have audio (non-image) files
    top_level_dirs = set()
    dir_has_audio = {}  # Track if each directory has audio files

    for f in files:
        name = (f.get("name") or "").lstrip("/")
        if "/" in name:
            top_dir = name.split("/", 1)[0]
            top_level_dirs.add(top_dir)

            # Check if this file is an audio file (not an image)
            file_ext = Path(name).suffix.lower()
            if file_ext not in IMAGE_EXTS:
                dir_has_audio[top_dir] = True

    # Only consider directories that have audio (non-image) files
    audio_dirs = {d for d in top_level_dirs if dir_has_audio.get(d, False)}

    # If only one or zero audio dirs, likely single book
    if len(audio_dirs) <= 1:
        return False, "Single directory structure"

    # Check if directories match book patterns
    book_dirs = []
    for dir_name in audio_dirs:
        for pattern in BOOK_PATTERNS:
            if pattern.search(dir_name):
                book_dirs.append(dir_name)
                break

    # If multiple directories match book patterns, it's multi-book
    if len(book_dirs) >= 2:
        return True, f"Multiple book directories detected: {', '.join(sorted(book_dirs)[:3])}"

    # Check for numbered directories (1, 2, 3... or 01, 02, 03...)
    numbered_dirs = []
    for dir_name in audio_dirs:
        # Strip leading zeros and check if it's a number
        stripped = dir_name.lstrip("0")
        if stripped.isdigit() and int(stripped) <= 50:  # Reasonable book count limit
            numbered_dirs.append(dir_name)

    if len(numbered_dirs) >= 2:
        return True, f"Multiple numbered directories detected: {', '.join(sorted(numbered_dirs)[:3])}"

    # Check for common series patterns in directory names
    series_indicators = ["book", "volume", "vol", "part", "episode", "ep"]
    indicator_count = 0
    for dir_name in audio_dirs:
        dir_lower = dir_name.lower()
        for indicator in series_indicators:
            if indicator in dir_lower:
                indicator_count += 1
                break

    if indicator_count >= 2:
        return True, f"Multiple directories with series indicators ({indicator_count} found)"

    return False, f"Single book structure ({len(audio_dirs)} audio dirs)"


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


def _find_best_cover_image(image_files: list[Path]) -> Optional[Path]:
    """
    Find the best cover image from a list of image files.
    Priority: cover.jpg > cover.png > folder.jpg > folder.png > first image

    Args:
        image_files: List of Path objects for image files

    Returns:
        Best image Path, or None if no images
    """
    if not image_files:
        return None

    # Priority order for cover names
    PREFERRED_NAMES = ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png']

    for preferred in PREFERRED_NAMES:
        for img in image_files:
            if img.name.lower() == preferred:
                return img

    # Fallback to first image
    return image_files[0]


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
        """Process a single import candidate with retry logic."""
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

        # Check retry eligibility (handles already-completed and backoff timing)
        if not self._should_retry(qb_hash):
            # Already tracked and not eligible for retry
            if self._is_completed_or_skipped(qb_hash):
                logger.debug(f"Auto-import: Already completed/skipped '{title}'")
            else:
                logger.debug(f"Auto-import: Waiting for retry backoff '{title}'")
            return

        # Check for multi-book structure
        is_multi_book, reason = _is_multi_book_torrent(torrent["files"], torrent["name"])
        if is_multi_book:
            logger.info(f"🚫 Auto-import skipped (multi-book): '{title}' - {reason}")
            self._mark_ineligible(history_id, qb_hash, reason)
            return

        # Track this attempt
        self._track_attempt(qb_hash, history_id, "processing")

        # Perform the import with retry on failure
        try:
            await self._do_import(candidate, torrent)
            self._track_completion(qb_hash, "completed")
            logger.info(f"🤖 Auto-import completed: '{title}'")
        except Exception as e:
            error_msg = str(e)
            self._record_failure(qb_hash, history_id, error_msg)
            logger.error(f"❌ Auto-import failed for '{title}': {error_msg}")

    def _is_completed_or_skipped(self, qb_hash: str) -> bool:
        """Check if this torrent is completed or skipped (not just failed)."""
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status FROM auto_import_tracking WHERE qb_hash = :hash"),
                {"hash": qb_hash}
            ).fetchone()
            if not row:
                return False
            return row[0] in ('completed', 'skipped')

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

    def _should_retry(self, qb_hash: str) -> bool:
        """Check if an item is eligible for retry based on count and timing."""
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT retry_count, next_retry_at
                    FROM auto_import_tracking WHERE qb_hash = :hash
                """),
                {"hash": qb_hash}
            ).fetchone()

            if not row:
                return True  # Never attempted

            retry_count = row[0] or 0
            next_retry_at = row[1]

            if retry_count >= MAX_RETRY_COUNT:
                return False  # Max retries exceeded

            if next_retry_at:
                try:
                    next_time = datetime.fromisoformat(next_retry_at.replace('Z', '+00:00'))
                    if datetime.now(timezone.utc) < next_time:
                        return False  # Not yet time to retry
                except Exception:
                    pass  # Invalid timestamp, allow retry

            return True

    def _record_failure(self, qb_hash: str, history_id: int, error: str):
        """Record failure and schedule next retry with exponential backoff."""
        with engine.begin() as conn:
            # Get current retry count
            row = conn.execute(
                text("SELECT retry_count FROM auto_import_tracking WHERE qb_hash = :hash"),
                {"hash": qb_hash}
            ).fetchone()

            retry_count = ((row[0] if row else 0) or 0) + 1

            # Calculate next retry time with exponential backoff
            if retry_count < MAX_RETRY_COUNT:
                backoff_seconds = RETRY_BACKOFF_BASE * (2 ** (retry_count - 1))
                next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                next_retry_str = next_retry.isoformat()
            else:
                next_retry_str = None  # No more retries

            conn.execute(
                text("""
                    INSERT INTO auto_import_tracking (qb_hash, history_id, status, retry_count, next_retry_at, last_error)
                    VALUES (:hash, :history_id, 'failed', :retry_count, :next_retry, :error)
                    ON CONFLICT(qb_hash) DO UPDATE SET
                        status = 'failed',
                        retry_count = :retry_count,
                        next_retry_at = :next_retry,
                        last_error = :error,
                        attempted_at = datetime('now')
                """),
                {
                    "hash": qb_hash,
                    "history_id": history_id,
                    "retry_count": retry_count,
                    "next_retry": next_retry_str,
                    "error": error[:500] if error else None  # Limit error length
                }
            )

            if retry_count < MAX_RETRY_COUNT:
                logger.info(f"🔄 Retry {retry_count}/{MAX_RETRY_COUNT} scheduled for next poll cycle (backoff: {backoff_seconds}s)")
            else:
                logger.warning(f"❌ Max retries ({MAX_RETRY_COUNT}) reached, will not retry")

    async def _copy_cover_image(self, mam_id: Optional[str], title: str, torrent_images: list[Path], dest_dir: Path):
        """
        Copy cover image to destination based on cover source priority setting.

        Priority is determined by cover_source_priority setting:
        - "shelfarr": Try Shelfarr cached cover first, fallback to torrent image
        - "torrent": Try torrent image first, fallback to Shelfarr cached cover

        Args:
            mam_id: MAM ID for Shelfarr cover lookup
            title: Book title (used for cover filename)
            torrent_images: List of image file paths from torrent
            dest_dir: Destination directory
        """
        import shutil

        cover_priority = settings_service.get("cover_source_priority") or "torrent"
        cover_service = CoverService()

        shelfarr_cover = None
        torrent_cover = _find_best_cover_image(torrent_images)

        # Try to get Shelfarr cached cover if we have a MAM ID
        if mam_id:
            try:
                shelfarr_cover = cover_service.get_local_cover_path(mam_id)
                if shelfarr_cover and not shelfarr_cover.exists():
                    shelfarr_cover = None
            except Exception as e:
                logger.debug(f"Could not get Shelfarr cover for mam_id={mam_id}: {e}")
                shelfarr_cover = None

        # Determine which cover to use based on priority
        cover_to_use = None
        cover_source = None

        if cover_priority == "shelfarr":
            # Shelfarr first, then torrent
            if shelfarr_cover:
                cover_to_use = shelfarr_cover
                cover_source = "shelfarr"
            elif torrent_cover:
                cover_to_use = torrent_cover
                cover_source = "torrent"
        else:
            # Torrent first (default), then Shelfarr
            if torrent_cover:
                cover_to_use = torrent_cover
                cover_source = "torrent"
            elif shelfarr_cover:
                cover_to_use = shelfarr_cover
                cover_source = "shelfarr"

        if not cover_to_use:
            logger.debug(f"No cover image available for '{title}'")
            return

        # Copy cover to destination
        # Use "{title}.{ext}" format for ABS to recognize
        dest_name = f"{sanitize(title)}{cover_to_use.suffix.lower()}"
        dest_path = dest_dir / dest_name

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cover_to_use, dest_path)
            logger.info(f"📷 Copied cover from {cover_source}: {cover_to_use.name} → {dest_name}")
        except Exception as e:
            logger.warning(f"Failed to copy cover image: {e}")

    async def _do_import(self, candidate: dict, torrent: dict):
        """Perform the actual import operation with image handling."""
        history_id = candidate["id"]
        mam_id = candidate.get("mam_id")
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
            # Collect audio and image files separately
            audio_files = []
            image_files = []
            for p in src_root.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() == ".cue":
                    continue

                ext = p.suffix.lower()
                if ext in IMAGE_EXTS:
                    image_files.append(p)
                elif AUDIO_EXTS is None or ext in AUDIO_EXTS:
                    audio_files.append(p)

            # Apply disc flattening if enabled (audio files only)
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

            # Handle cover image with priority setting
            await self._copy_cover_image(mam_id, title, image_files, dest_dir)

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

    async def _verify_import(self, history_id: int, title: str, author: str, dest_dir: Path, max_retries: int = 3):
        """
        Verify the import in Audiobookshelf with retry logic.

        Uses exponential backoff: 10s initial wait, then 5s, 10s, 20s retries.
        """
        initial_wait = 10
        retry_delays = [5, 10, 20]  # Exponential backoff for retries

        # Initial wait for ABS to scan
        await asyncio.sleep(initial_wait)

        last_error = None
        for attempt in range(max_retries):
            try:
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
                            SET abs_verify_status = :status,
                                abs_verify_note = :note,
                                verify_retry_count = :retry_count
                            WHERE id = :id
                        """),
                        {
                            "status": verification_result.get("status"),
                            "note": verification_result.get("note"),
                            "retry_count": attempt,
                            "id": history_id
                        }
                    )

                status = verification_result.get("status", "unknown")
                if status == "verified":
                    logger.info(f"✅ Auto-import verification successful: '{title}'")
                elif status == "unreachable" and attempt < max_retries - 1:
                    # ABS unreachable, retry
                    raise Exception("ABS unreachable, will retry")
                else:
                    logger.info(f"ℹ️ Auto-import verification status '{status}' for '{title}'")
                return  # Success or final status

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt] if attempt < len(retry_delays) else retry_delays[-1]
                    logger.warning(f"🔄 Verification attempt {attempt + 1}/{max_retries} failed for '{title}', retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"❌ Verification failed after {max_retries} attempts for '{title}': {e}")

        # All retries failed - update database with unreachable status
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE history
                    SET abs_verify_status = 'unreachable',
                        abs_verify_note = :note,
                        verify_retry_count = :retry_count
                    WHERE id = :id
                """),
                {
                    "note": f"Verification failed after {max_retries} attempts: {last_error}",
                    "retry_count": max_retries,
                    "id": history_id
                }
            )

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        """Get recent auto-import activity including retry tracking."""
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT t.id, t.qb_hash, t.history_id, t.status, t.reason,
                           t.attempted_at, t.completed_at, h.title, h.author,
                           t.retry_count, t.next_retry_at, t.last_error
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
                    "retry_count": row[9] or 0,
                    "next_retry_at": row[10],
                    "last_error": row[11],
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
