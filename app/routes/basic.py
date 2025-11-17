"""
Basic routes for health checks and configuration.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

from config import IMPORT_MODE, FLATTEN_DISCS, HARDCOVER_SERIES_LIMIT

router = APIRouter()

# Path to the Vue build output
DIST_PATH = Path("app/static/dist")
INDEX_HTML = DIST_PATH / "index.html"


@router.get("/", response_class=FileResponse)
async def home():
    """Serve the Vue SPA for the search page."""
    return FileResponse(INDEX_HTML)


@router.get("/history", response_class=FileResponse)
async def history_page():
    """Serve the Vue SPA for the history page."""
    return FileResponse(INDEX_HTML)


@router.get("/showcase", response_class=FileResponse)
async def showcase_page():
    """Serve the Vue SPA for the showcase page."""
    return FileResponse(INDEX_HTML)


@router.get("/logs", response_class=FileResponse)
async def logs_page():
    """Serve the Vue SPA for the logs page."""
    return FileResponse(INDEX_HTML)


@router.get("/series", response_class=FileResponse)
async def series_page():
    """Serve the Vue SPA for the series page."""
    return FileResponse(INDEX_HTML)


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}


@router.get("/config")
async def config():
    """Return app configuration."""
    return {
        "import_mode": IMPORT_MODE,
        "flatten_discs": FLATTEN_DISCS,
        "hardcover_series_limit": HARDCOVER_SERIES_LIMIT,
    }
