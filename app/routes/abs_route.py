"""
Audiobookshelf admin routes for MAM Audiobook Finder.
Provides endpoints for library sync management and status monitoring.
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from abs_client import abs_client

router = APIRouter()
logger = logging.getLogger("mam-audiofinder")


@router.post("/api/abs/sync")
async def sync_library():
    """
    Force a full library sync from Audiobookshelf.

    This endpoint triggers a complete refresh of the library cache,
    fetching all items from the configured ABS library and storing
    them in the local SQLite database for fast lookups.

    Response:
        {
            "ok": true,
            "items_synced": 1234,
            "library_id": "lib_abc123",
            "message": "Successfully synced 1234 items from library"
        }
    """
    if not abs_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf not configured. Set ABS_BASE_URL and ABS_API_KEY."
        )

    if not abs_client.library_id:
        raise HTTPException(
            status_code=503,
            detail="ABS_LIBRARY_ID not configured. Cannot sync without a library ID."
        )

    logger.info(f"🔄 Manual library sync requested for library {abs_client.library_id}")

    try:
        # Trigger full sync using the new client's sync method
        items_count = await abs_client._client.sync_library()

        logger.info(f"✅ Library sync complete: {items_count} items synced")

        return JSONResponse({
            "ok": True,
            "items_synced": items_count,
            "library_id": abs_client.library_id,
            "message": f"Successfully synced {items_count} items from library"
        })

    except Exception as e:
        logger.error(f"❌ Library sync failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Library sync failed: {str(e)}"
        )


@router.get("/api/abs/status")
async def get_sync_status():
    """
    Get the current library sync status.

    Returns information about the last sync time, item count,
    cache age, and whether a sync is currently in progress.

    Response:
        {
            "library_id": "lib_abc123",
            "last_full_sync": "2025-12-03T10:30:00Z",
            "last_item_count": 1234,
            "sync_in_progress": false,
            "cache_age_seconds": 3600.5,
            "cache_status": "stale",  // "fresh" | "stale" | "expired" | "empty"
            "configured": true
        }
    """
    if not abs_client.is_configured:
        return JSONResponse({
            "configured": False,
            "message": "Audiobookshelf not configured"
        })

    if not abs_client.library_id:
        return JSONResponse({
            "configured": True,
            "library_id": None,
            "message": "ABS_LIBRARY_ID not configured"
        })

    try:
        # Get sync status from the new client
        status = abs_client._client.get_sync_status()

        if not status:
            return JSONResponse({
                "configured": True,
                "library_id": abs_client.library_id,
                "last_full_sync": None,
                "last_item_count": 0,
                "sync_in_progress": False,
                "cache_age_seconds": float('inf'),
                "cache_status": "empty"
            })

        # Determine cache status based on age
        cache_age = status.cache_age_seconds
        if cache_age == float('inf'):
            cache_status = "empty"
        elif cache_age < 300:  # 5 minutes
            cache_status = "fresh"
        elif cache_age < 3600:  # 1 hour
            cache_status = "stale"
        else:
            cache_status = "expired"

        return JSONResponse({
            "library_id": status.library_id,
            "last_full_sync": status.last_full_sync,
            "last_item_count": status.last_item_count,
            "sync_in_progress": status.sync_in_progress,
            "cache_age_seconds": cache_age,
            "cache_status": cache_status,
            "configured": True
        })

    except Exception as e:
        logger.error(f"❌ Failed to get sync status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}"
        )
