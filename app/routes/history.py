"""
History routes for MAM Audiobook Finder.
"""
import httpx
from pathlib import Path
from fastapi import APIRouter
from sqlalchemy import text

from db import engine
from db.db import covers_engine
from config import COVERS_DIR
from qb_client import qb_login_sync
from torrent_helpers import (
    get_torrent_state,
    map_qb_state_to_display,
    validate_torrent_path,
    extract_mam_id_from_tags,
    match_torrent_to_history
)

router = APIRouter()


def _resolve_cover_url(mam_id: str, abs_cover_url: str, logger) -> str:
    """
    Resolve cover URL, falling back to ABS URL if local file doesn't exist.

    Args:
        mam_id: MAM torrent ID
        abs_cover_url: Current cover URL from history (might be local or remote)
        logger: Logger instance

    Returns:
        Valid cover URL (either local if exists, or original ABS URL)
    """
    if not abs_cover_url:
        return abs_cover_url

    # Check if it's a local cover path
    if abs_cover_url.startswith("/covers/"):
        filename = abs_cover_url.split("/")[-1]
        local_path = COVERS_DIR / filename

        # If local file exists, return it
        if local_path.exists():
            logger.debug(f"[HISTORY] Local cover exists for MAM ID {mam_id}: {abs_cover_url}")
            return abs_cover_url

        # Local file missing - look up original ABS URL from covers database
        logger.info(f"[HISTORY] Local cover missing for MAM ID {mam_id}, looking up ABS URL")
        try:
            with covers_engine.begin() as cx:
                row = cx.execute(text("""
                    SELECT cover_url FROM covers
                    WHERE mam_id = :mam_id
                    LIMIT 1
                """), {"mam_id": mam_id}).fetchone()

                if row and row[0]:
                    original_url = row[0]
                    # Make sure we're returning the remote ABS URL, not another local path
                    if not original_url.startswith("/covers/"):
                        logger.info(f"[HISTORY] Using original ABS URL for MAM ID {mam_id}: {original_url}")
                        return original_url
                    else:
                        logger.warning(f"[HISTORY] Covers DB also has local path for MAM ID {mam_id}, returning None")
                        return ""
                else:
                    logger.warning(f"[HISTORY] No cover found in covers DB for MAM ID {mam_id}")
                    return ""
        except Exception as e:
            logger.error(f"[HISTORY] Error looking up cover for MAM ID {mam_id}: {e}")
            return ""

    # It's already a remote URL (ABS or other), return as-is
    return abs_cover_url


@router.get("/api/history")
def history():
    """Get history of added torrents with live torrent states."""
    import logging
    logger = logging.getLogger("mam-audiofinder")
    logger.info("[HISTORY] /api/history endpoint called")

    # Fetch all history items
    with engine.begin() as cx:
        rows = cx.execute(text("""
            SELECT id, mam_id, title, author, narrator, dl, qb_hash, added_at, qb_status,
                   abs_cover_url, abs_item_id, imported_at,
                   abs_verify_status, abs_verify_note
            FROM history
            ORDER BY id DESC
            LIMIT 200
        """)).mappings().all()

    logger.info(f"[HISTORY] Found {len(rows)} history items in database")

    # Fix cover URLs - replace missing local files with ABS URLs
    rows_fixed = []
    for row in rows:
        row_dict = dict(row)
        if row_dict.get("mam_id") and row_dict.get("abs_cover_url"):
            row_dict["abs_cover_url"] = _resolve_cover_url(
                row_dict["mam_id"],
                row_dict["abs_cover_url"],
                logger
            )
        rows_fixed.append(row_dict)

    items = []

    # Enrich with live torrent data
    with httpx.Client(timeout=30) as client:
        try:
            qb_login_sync(client)
            logger.info("[HISTORY] Successfully logged into qBittorrent")
        except Exception as e:
            # If qBittorrent is unreachable, return basic data without enrichment
            logger.error(f"[HISTORY] qBittorrent login failed in /history: {e}")

            # Return rows with default status indicators
            enriched_items = []
            for row in rows_fixed:
                row["qb_status"] = row.get("qb_status") or "qBittorrent Offline"
                row["qb_status_color"] = "red"
                row["qb_progress"] = 0.0
                row["path_warning"] = "Cannot connect to qBittorrent to verify status"
                row["path_valid"] = False
                enriched_items.append(row)

            return {"items": enriched_items}

        # Fetch ALL torrents once for matching
        logger.info("[HISTORY] Fetching all torrents from qBittorrent for matching")
        try:
            from config import QB_URL
            torrents_resp = client.get(f"{QB_URL}/api/v2/torrents/info", params={"filter": "all"})
            all_torrents = []
            if torrents_resp.status_code == 200:
                qb_torrents = torrents_resp.json()
                if isinstance(qb_torrents, list):
                    # Extract mam_id from tags for each torrent
                    for t in qb_torrents:
                        torrent_data = {
                            "hash": t.get("hash"),
                            "name": t.get("name"),
                            "tags": t.get("tags", ""),
                            "mam_id": extract_mam_id_from_tags(t.get("tags", ""))
                        }
                        all_torrents.append(torrent_data)
                    logger.info(f"[HISTORY] Fetched {len(all_torrents)} torrents from qBittorrent")
        except Exception as e:
            logger.error(f"[HISTORY] Failed to fetch torrent list: {e}")
            all_torrents = []

        for row in rows_fixed:
            item = row
            qb_hash = item.get("qb_hash")
            hash_updated = False

            # Default values
            item["qb_status_color"] = "grey"
            item["qb_progress"] = 0.0
            item["path_warning"] = None
            item["path_valid"] = True

            # If no hash, try to find matching torrent
            if not qb_hash and all_torrents:
                logger.info(f"[HISTORY] No hash for '{item.get('title')}', attempting fallback match")
                matched_torrent = match_torrent_to_history(item, all_torrents)
                if matched_torrent:
                    qb_hash = matched_torrent.get("hash")
                    logger.info(f"[HISTORY] Matched by {'MAM ID' if matched_torrent.get('mam_id') else 'title'}: {qb_hash}")

                    # Update database with found hash for future lookups
                    try:
                        with engine.begin() as cx:
                            cx.execute(text("""
                                UPDATE history
                                SET qb_hash = :qb_hash
                                WHERE id = :id
                            """), {"qb_hash": qb_hash, "id": item.get("id")})
                        logger.info(f"[HISTORY] Updated database with hash for item {item.get('id')}")
                        hash_updated = True
                    except Exception as e:
                        logger.error(f"[HISTORY] Failed to update hash in database: {e}")
                else:
                    logger.info(f"[HISTORY] No matching torrent found for '{item.get('title')}'")

            if qb_hash:
                logger.info(f"[HISTORY] Processing item with hash: {qb_hash}, title: {item.get('title')}{' (newly matched)' if hash_updated else ''}")
                # Fetch live state
                torrent_state = get_torrent_state(qb_hash, client)
                logger.info(f"[HISTORY] Torrent state for {qb_hash}: {torrent_state}")

                if torrent_state:
                    # Map state to display format
                    display_state, color = map_qb_state_to_display(
                        torrent_state.get("state", ""),
                        torrent_state.get("progress", 0)
                    )
                    logger.info(f"[HISTORY] Mapped state: {display_state}, color: {color}")
                    item["qb_status"] = display_state
                    item["qb_status_color"] = color
                    item["qb_progress"] = torrent_state.get("progress", 0)

                    # Validate path
                    path_validation = validate_torrent_path(
                        torrent_state.get("save_path", ""),
                        torrent_state.get("content_path", "")
                    )
                    item["path_valid"] = path_validation["is_valid"]
                    item["path_warning"] = path_validation["warning"]

                    # Override color to red if path is invalid
                    if not path_validation["is_valid"]:
                        item["qb_status_color"] = "red"
                        logger.info(f"[HISTORY] Path invalid for {qb_hash}, overriding color to red")
                else:
                    # Torrent not found in qBittorrent
                    logger.warning(f"[HISTORY] Torrent not found in qBittorrent: {qb_hash}")
                    item["qb_status"] = "Not Found"
                    item["qb_status_color"] = "grey"
            else:
                logger.info(f"[HISTORY] No hash available for: {item.get('title')}")

            items.append(item)

    logger.info(f"[HISTORY] Returning {len(items)} items with enriched data")
    if items:
        logger.info(f"[HISTORY] First item sample: title={items[0].get('title')}, qb_status={items[0].get('qb_status')}, qb_status_color={items[0].get('qb_status_color')}")

    return {"items": items}


@router.delete("/api/history/{row_id}")
def delete_history(row_id: int):
    """Delete a history entry."""
    with engine.begin() as cx:
        cx.execute(text("DELETE FROM history WHERE id = :id"), {"id": row_id})
    return {"ok": True}


@router.post("/api/history/{row_id}/verify")
async def verify_history_item(row_id: int):
    """Manually trigger verification for a history item."""
    import logging
    from pathlib import Path
    import json
    from config import LIB_DIR

    logger = logging.getLogger("mam-audiofinder")
    logger.info(f"[VERIFY] Manual verification requested for history ID {row_id}")

    # Get history item details
    with engine.begin() as cx:
        row = cx.execute(
            text("SELECT id, title, author, imported_at FROM history WHERE id = :id"),
            {"id": row_id}
        ).mappings().first()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="History item not found")

    if not row["imported_at"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Item not yet imported")

    title = row["title"] or ""
    author = row["author"] or ""

    # Try to find the imported directory
    from utils import sanitize
    title_san = sanitize(title)
    author_san = sanitize(author)

    # Construct likely path
    lib = Path(LIB_DIR)
    potential_paths = [
        lib / author_san / title_san,
        lib / author / title,  # Try unsanitized as fallback
    ]

    dest_dir = None
    for path in potential_paths:
        if path.exists():
            dest_dir = path
            logger.info(f"📂 Found import directory: {dest_dir}")
            break

    if not dest_dir:
        logger.warning(f"⚠️  Could not find import directory for '{title}'")
        return {
            "ok": False,
            "status": "not_found",
            "note": "Import directory not found - may have been moved or deleted"
        }

    # Read metadata.json
    metadata_path = dest_dir / "metadata.json"
    metadata = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            logger.info(f"📖 Read metadata.json for verification")
        except Exception as e:
            logger.warning(f"⚠️  Failed to read metadata.json: {e}")

    # Perform verification
    from abs_client import abs_client

    verify_title = metadata.get("title", title) if metadata else title
    verify_authors = metadata.get("authors", [author]) if metadata else [author]
    verify_author = ", ".join(verify_authors) if verify_authors else author

    logger.info(f"🔍 Re-verifying '{verify_title}' by '{verify_author}'")

    verification_result = await abs_client.verify_import(
        title=verify_title,
        author=verify_author,
        library_path=str(dest_dir),
        metadata=metadata
    )

    # Update database with new verification results
    with engine.begin() as cx:
        cx.execute(
            text("""
                UPDATE history
                SET abs_verify_status=:status, abs_verify_note=:note
                WHERE id=:id
            """),
            {
                "status": verification_result.get("status"),
                "note": verification_result.get("note"),
                "id": row_id
            }
        )

    logger.info(f"✅ Verification updated: {verification_result.get('status')}")

    return {
        "ok": True,
        "verification": verification_result
    }
