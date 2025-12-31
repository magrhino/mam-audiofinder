"""
Audiobookshelf admin routes for MAM Audiobook Finder.
Provides endpoints for library management, sync, and status monitoring.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from abs_client import get_abs_client
from abs import AbsClient
from dependencies.abs import get_abs_token, require_admin, is_admin_user, get_current_user
from settings_service import settings_service
from config import ABS_BASE_URL

router = APIRouter()
logger = logging.getLogger("mam-audiofinder")


class LibraryUpdate(BaseModel):
    """Request body for updating enabled libraries."""
    enabled_library_ids: List[str]


class LibraryResponse(BaseModel):
    """Library info for API response."""
    id: str
    name: str
    media_type: str
    icon: Optional[str] = None
    enabled: bool = False


# --- Library Management ---

@router.get("/api/abs/libraries")
async def get_libraries(
    token: Optional[str] = Depends(get_abs_token),
    user: dict = Depends(get_current_user)
):
    """
    Get all available libraries from ABS with their enabled status.

    Returns list of libraries the user has access to, marked with whether
    each is currently enabled for search.

    Response:
        {
            "ok": true,
            "libraries": [
                {"id": "lib_abc", "name": "Audiobooks", "media_type": "book", "enabled": true},
                {"id": "lib_xyz", "name": "Podcasts", "media_type": "podcast", "enabled": false}
            ],
            "is_admin": true,
            "initialized": true
        }
    """
    if not ABS_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf not configured. Set ABS_BASE_URL."
        )

    client = get_abs_client(user_token=token)

    try:
        # Fetch libraries from ABS
        libraries = await client.get_all_libraries()

        # Get enabled library IDs from settings
        enabled_ids = settings_service.get_enabled_libraries()
        initialized = settings_service.is_libraries_initialized()

        # If not initialized, auto-initialize with audiobook libraries
        if not initialized and libraries:
            lib_dicts = [
                {"id": lib.id, "name": lib.name, "media_type": lib.media_type, "icon": lib.icon}
                for lib in libraries
            ]
            settings_service.initialize_libraries(lib_dicts)
            enabled_ids = settings_service.get_enabled_libraries()
            initialized = True

        # Build response
        library_list = []
        for lib in libraries:
            library_list.append({
                "id": lib.id,
                "name": lib.name,
                "media_type": lib.media_type,
                "icon": lib.icon,
                "enabled": lib.id in enabled_ids
            })

        return JSONResponse({
            "ok": True,
            "libraries": library_list,
            "is_admin": is_admin_user(user.get("username", "")),
            "initialized": initialized
        })

    except Exception as e:
        logger.error(f"❌ Failed to get libraries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get libraries: {str(e)}"
        )


@router.put("/api/abs/libraries")
async def update_libraries(
    body: LibraryUpdate,
    admin: dict = Depends(require_admin)
):
    """
    Update which libraries are enabled for search.

    Admin only endpoint. Sets the list of library IDs that should be
    included in library checks and verification.

    Request:
        {
            "enabled_library_ids": ["lib_abc123", "lib_def456"]
        }

    Response:
        {
            "ok": true,
            "enabled_library_ids": ["lib_abc123", "lib_def456"],
            "message": "Updated 2 enabled libraries"
        }
    """
    try:
        settings_service.set_enabled_libraries(body.enabled_library_ids)

        logger.info(f"📚 Admin updated enabled libraries: {body.enabled_library_ids}")

        return JSONResponse({
            "ok": True,
            "enabled_library_ids": body.enabled_library_ids,
            "message": f"Updated {len(body.enabled_library_ids)} enabled libraries"
        })

    except Exception as e:
        logger.error(f"❌ Failed to update libraries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update libraries: {str(e)}"
        )


@router.post("/api/abs/libraries/refresh")
async def refresh_libraries(
    token: Optional[str] = Depends(get_abs_token),
    admin: dict = Depends(require_admin)
):
    """
    Refresh library list from ABS.

    Admin only endpoint. Re-fetches the library list from ABS and updates
    the cached library metadata. Does not change which libraries are enabled.

    Response:
        {
            "ok": true,
            "libraries_count": 3,
            "message": "Refreshed 3 libraries from ABS"
        }
    """
    if not ABS_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf not configured."
        )

    client = get_abs_client(user_token=token)

    try:
        libraries = await client.get_all_libraries()

        # Update cached libraries
        lib_dicts = [
            {"id": lib.id, "name": lib.name, "media_type": lib.media_type, "icon": lib.icon}
            for lib in libraries
        ]
        settings_service.set_cached_libraries(lib_dicts)

        logger.info(f"📚 Refreshed {len(libraries)} libraries from ABS")

        return JSONResponse({
            "ok": True,
            "libraries_count": len(libraries),
            "message": f"Refreshed {len(libraries)} libraries from ABS"
        })

    except Exception as e:
        logger.error(f"❌ Failed to refresh libraries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh libraries: {str(e)}"
        )


# --- Library Sync ---

@router.post("/api/abs/sync")
async def sync_library(
    token: Optional[str] = Depends(get_abs_token),
    user: dict = Depends(get_current_user)
):
    """
    Force a full library sync from Audiobookshelf.

    Syncs all enabled libraries, fetching items from ABS and storing
    them in the local SQLite database for fast lookups.

    Response:
        {
            "ok": true,
            "items_synced": 1234,
            "libraries_synced": 2,
            "message": "Successfully synced 1234 items from 2 libraries"
        }
    """
    if not ABS_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf not configured. Set ABS_BASE_URL."
        )

    enabled_ids = settings_service.get_enabled_libraries()
    if not enabled_ids:
        raise HTTPException(
            status_code=400,
            detail="No libraries enabled. Configure libraries in Settings first."
        )

    client = get_abs_client(user_token=token)

    logger.info(f"🔄 Manual library sync requested for {len(enabled_ids)} libraries")

    try:
        total_items = await client.sync_all_libraries(enabled_ids)

        logger.info(f"✅ Library sync complete: {total_items} items synced from {len(enabled_ids)} libraries")

        return JSONResponse({
            "ok": True,
            "items_synced": total_items,
            "libraries_synced": len(enabled_ids),
            "message": f"Successfully synced {total_items} items from {len(enabled_ids)} libraries"
        })

    except Exception as e:
        logger.error(f"❌ Library sync failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Library sync failed: {str(e)}"
        )


@router.get("/api/abs/status")
async def get_sync_status(
    token: Optional[str] = Depends(get_abs_token)
):
    """
    Get the current library sync status.

    Returns information about enabled libraries, sync times, and cache status.

    Response:
        {
            "configured": true,
            "enabled_libraries": ["lib_abc", "lib_xyz"],
            "libraries_count": 2,
            "initialized": true,
            "cache_status": "fresh"
        }
    """
    if not ABS_BASE_URL:
        return JSONResponse({
            "configured": False,
            "message": "Audiobookshelf not configured"
        })

    enabled_ids = settings_service.get_enabled_libraries()
    initialized = settings_service.is_libraries_initialized()
    cached_libraries = settings_service.get_cached_libraries()

    return JSONResponse({
        "configured": True,
        "enabled_libraries": enabled_ids,
        "libraries_count": len(enabled_ids),
        "initialized": initialized,
        "cached_libraries": cached_libraries,
        "message": f"{len(enabled_ids)} libraries enabled" if enabled_ids else "No libraries enabled"
    })
