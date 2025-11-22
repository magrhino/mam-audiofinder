"""
Audiobookshelf verification, config guards, and library check dependencies.

Provides:
- require_abs_config: Fail fast when ABS not configured
- abs_library_check: Batch library presence checker with caching
- abs_import_verifier: Wraps verify_import with metadata/title fallback
- load_metadata_with_retry: Async metadata.json polling with retries
- ensure_library_destination: Create sanitized author/title folders
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
import json
from fastapi import HTTPException

from config import ABS_BASE_URL, ABS_API_KEY
from abs_client import abs_client
from utils import sanitize, next_available


def require_abs_config() -> None:
    """
    Validates that Audiobookshelf is configured.

    Raises:
        HTTPException: 503 if ABS_BASE_URL or ABS_API_KEY not set
    """
    if not ABS_BASE_URL or not ABS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf is not configured. Set ABS_BASE_URL and ABS_API_KEY."
        )


async def abs_library_check(
    items: List[Dict[str, Any]],
    cache_enabled: bool = True
) -> Dict[str, bool]:
    """
    Batch checks library presence for items with optional caching.

    Args:
        items: List of items to check (must have 'id' field)
        cache_enabled: Whether to use cache (default: True)

    Returns:
        Dictionary mapping item ID to library presence (True/False)

    Raises:
        HTTPException: 503 if ABS not configured
    """
    require_abs_config()

    if not items:
        return {}

    # Extract IDs
    item_ids = [item.get("id") for item in items if item.get("id")]

    if not item_ids:
        return {}

    try:
        # Use abs_client.check_library_items with caching
        results = await abs_client.check_library_items(item_ids)
        return results

    except Exception as e:
        # Don't fail the request if library check fails
        # Just log and return empty dict
        print(f"⚠️ Library check failed: {e}")
        return {}


async def abs_import_verifier(
    import_path: Path,
    title: str,
    author: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Wraps abs_client.verify_import with metadata/title fallback and error handling.

    Args:
        import_path: Path to imported content
        title: Book title
        author: Book author
        metadata: Optional metadata dictionary (from metadata.json)

    Returns:
        Dictionary containing:
            - status: 'verified', 'mismatch', 'not_found', 'unreachable', 'not_configured'
            - note: Human-readable verification note
            - abs_item_id: ABS item ID if verified
            - matched_title: Matched title if verified
            - score: Match score if available

    Raises:
        HTTPException: Only for critical errors (not for verification failures)
    """
    # Check if ABS is configured
    if not ABS_BASE_URL or not ABS_API_KEY:
        return {
            "status": "not_configured",
            "note": "Audiobookshelf not configured",
            "abs_item_id": None,
            "matched_title": None,
            "score": 0
        }

    try:
        # Call abs_client.verify_import with retry logic
        result = await abs_client.verify_import(
            import_path=str(import_path),
            expected_title=title,
            expected_author=author,
            metadata=metadata
        )

        return {
            "status": result.get("status", "unreachable"),
            "note": result.get("note", ""),
            "abs_item_id": result.get("abs_item_id"),
            "matched_title": result.get("matched_title"),
            "score": result.get("score", 0)
        }

    except Exception as e:
        print(f"⚠️ Verification failed: {e}")
        return {
            "status": "unreachable",
            "note": f"Verification error: {str(e)}",
            "abs_item_id": None,
            "matched_title": None,
            "score": 0
        }


async def load_metadata_with_retry(
    metadata_path: Path,
    max_attempts: int = 30,
    sleep_seconds: float = 2.0
) -> Optional[Dict[str, Any]]:
    """
    Polls metadata.json with configured retry attempts and sleep intervals.

    Args:
        metadata_path: Path to metadata.json
        max_attempts: Maximum polling attempts (default: 30)
        sleep_seconds: Sleep duration between attempts (default: 2.0)

    Returns:
        Metadata dictionary if found, None if not found after max attempts
    """
    for attempt in range(max_attempts):
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                print(f"✅ Metadata loaded after {attempt + 1} attempts")
                return metadata
            except json.JSONDecodeError as e:
                print(f"⚠️ Metadata JSON decode error (attempt {attempt + 1}): {e}")
                # Continue polling - ABS might still be writing

        if attempt < max_attempts - 1:
            await asyncio.sleep(sleep_seconds)

    print(f"⚠️ Metadata not found after {max_attempts} attempts")
    return None


def ensure_library_destination(
    library_root: Path,
    author: str,
    title: str
) -> Path:
    """
    Creates author/title folder structure with sanitization and collision handling.

    Args:
        library_root: Root library directory
        author: Author name (will be sanitized)
        title: Book title (will be sanitized)

    Returns:
        Destination path (created with parents)

    Raises:
        HTTPException: 500 if directory creation fails
    """
    # Sanitize names
    safe_author = sanitize(author)
    safe_title = sanitize(title)

    # Build base destination
    base_dest = library_root / safe_author / safe_title

    # Handle collisions with next_available
    dest = next_available(base_dest)

    # Create directory structure
    try:
        dest.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created destination: {dest}")
        return dest

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create destination directory: {str(e)}"
        )
