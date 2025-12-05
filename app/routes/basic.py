"""
Basic routes for health checks and configuration.
SPA routing is now handled by the fallback route in app/main.py.
"""
from fastapi import APIRouter

from config import (
    IMPORT_MODE, FLATTEN_DISCS, HARDCOVER_SERIES_LIMIT,
    ABS_BASE_URL, ABS_API_KEY, ABS_LIBRARY_ID, HARDCOVER_API_TOKEN
)

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}


@router.get("/config")
async def config():
    """Return app configuration."""
    # Check if ABS is fully configured
    abs_configured = bool(ABS_BASE_URL and ABS_API_KEY and ABS_LIBRARY_ID)
    # Check if Hardcover is configured
    hardcover_configured = bool(HARDCOVER_API_TOKEN)

    return {
        "import_mode": IMPORT_MODE,
        "flatten_discs": FLATTEN_DISCS,
        "hardcover_series_limit": HARDCOVER_SERIES_LIMIT,
        "abs_base_url": ABS_BASE_URL,
        "abs_configured": abs_configured,
        "hardcover_configured": hardcover_configured,
    }
