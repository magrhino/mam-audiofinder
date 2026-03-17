"""
Audiobookshelf verification, config guards, and library check dependencies.

Provides:
- get_abs_token: Extract X-ABS-Token from request headers
- get_current_user: Validate token and get user info from ABS
- require_admin: Verify user is admin (matches ABS_ADMIN_USER)
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
import logging
from fastapi import HTTPException, Header, Depends
import httpx

import config
from abs_client import abs_client
from utils import sanitize, next_available

logger = logging.getLogger("mam-audiofinder")


def is_abs_auth_enabled() -> bool:
    """Return True when ABS-backed auth should be enforced."""
    return bool(config.ABS_BASE_URL)


def get_abs_base_url() -> str:
    """Return the configured ABS base URL."""
    return config.ABS_BASE_URL


def get_abs_admin_username() -> str:
    """Return the configured ABS admin username."""
    return config.ABS_ADMIN_USER


# --- Token and Auth Dependencies ---

async def get_abs_token(
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token")
) -> Optional[str]:
    """
    Extract X-ABS-Token from request headers.

    Returns:
        Token string if present, None otherwise
    """
    return x_abs_token


async def require_abs_token(
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token")
) -> str:
    """
    Require X-ABS-Token header.

    Returns:
        Token string

    Raises:
        HTTPException: 401 if token not provided
    """
    if not x_abs_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login."
        )
    return x_abs_token


async def get_current_user(
    token: str = Depends(require_abs_token)
) -> Dict[str, Any]:
    """
    Validate token against ABS and get user info.

    Returns:
        User info dict with 'username', 'type', 'isActive', 'token'

    Raises:
        HTTPException: 401 if token invalid
        HTTPException: 503 if ABS not configured
    """
    abs_base_url = get_abs_base_url()
    if not abs_base_url:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf is not configured."
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{abs_base_url}/api/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token. Please login again."
                )

            data = resp.json()
            user = data.get("user", {})

            return {
                "username": user.get("username"),
                "type": user.get("type"),
                "isActive": user.get("isActive", True),
                "token": token
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="ABS server not responding"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Token validation failed"
        )


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Verify user is admin (username matches ABS_ADMIN_USER).

    Returns:
        User info dict if admin

    Raises:
        HTTPException: 403 if not admin
    """
    username = user.get("username", "")
    abs_admin_user = get_abs_admin_username()

    # Check if user matches configured admin
    if not abs_admin_user:
        logger.error("❌ ABS_ADMIN_USER not set - admin routes are unavailable")
        raise HTTPException(
            status_code=503,
            detail="Admin routes require ABS_ADMIN_USER to be configured"
        )

    if username.lower() != abs_admin_user.lower():
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user


def is_admin_user(username: str) -> bool:
    """
    Check if username is the configured admin user.

    Args:
        username: Username to check

    Returns:
        True if admin, False otherwise
    """
    abs_admin_user = get_abs_admin_username()
    if not abs_admin_user:
        return False
    return username.lower() == abs_admin_user.lower()


async def require_authenticated_user_if_configured(
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token")
) -> Optional[Dict[str, Any]]:
    """Require ABS auth only when ABS is configured."""
    if not is_abs_auth_enabled():
        return None

    if not x_abs_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login."
        )

    return await get_current_user(x_abs_token)


async def require_admin_if_configured(
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token")
) -> Optional[Dict[str, Any]]:
    """Require admin access only when ABS auth is enabled."""
    if not is_abs_auth_enabled():
        return None

    if not x_abs_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login."
        )

    user = await get_current_user(x_abs_token)
    return await require_admin(user)


# --- ABS Config Guards ---

def require_abs_config() -> None:
    """
    Validates that Audiobookshelf is configured.

    Raises:
        HTTPException: 503 if ABS_BASE_URL not set
    """
    if not get_abs_base_url():
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf is not configured. Set ABS_BASE_URL."
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
    if not get_abs_base_url():
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
