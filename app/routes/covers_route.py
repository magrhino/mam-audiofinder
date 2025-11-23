"""
Cover image serving routes for MAM Audiobook Finder.
"""
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from typing import Optional

from config import COVERS_DIR
from abs_client import abs_client
from db import engine
from covers import cover_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/covers/{filename}")
async def serve_cover(filename: str):
    """Serve cached cover images."""
    # Sanitize filename
    filename = Path(filename).name  # Remove any path traversal attempts
    filepath = COVERS_DIR / filename

    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Cover not found")

    return FileResponse(filepath)


@router.post("/covers/refresh/{mam_id}")
async def refresh_cover(mam_id: str):
    """Force refresh of a cached cover for a specific MAM ID."""

    if not mam_id:
        raise HTTPException(status_code=400, detail="Missing MAM ID")

    if not abs_client.is_configured:
        raise HTTPException(status_code=400, detail="Audiobookshelf not configured")

    with engine.begin() as cx:
        row = cx.execute(text("""
            SELECT title, author FROM history
            WHERE mam_id = :mam_id
            ORDER BY id DESC
            LIMIT 1
        """), {"mam_id": mam_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="MAM ID not found in history")

    # Remove any stale cache entries/files before fetching again
    cover_service.invalidate_cover(mam_id)

    result = await abs_client.fetch_cover(row.title or "", row.author or "", mam_id, force_refresh=True)
    if not result or not result.get("cover_url"):
        raise HTTPException(status_code=404, detail="Unable to refresh cover")

    return {
        "mam_id": mam_id,
        "cover_url": result.get("cover_url"),
        "item_id": result.get("item_id")
    }


class EnrichRequest(BaseModel):
    """Request model for on-demand metadata enrichment."""
    title: str
    author: Optional[str] = ""
    mam_id: Optional[str] = ""


@router.post("/api/covers/enrich")
async def enrich_metadata(request: EnrichRequest):
    """
    On-demand metadata enrichment for detail views.

    Calls provider APIs in parallel (audible, google, openlibrary) to fetch
    enhanced metadata including descriptions. This is only called when user
    explicitly opens a detail view.

    Request body:
        {
            "title": "Book Title",
            "author": "Author Name",  // optional
            "mam_id": "12345"        // optional
        }

    Returns:
        {
            "description": "...",
            "cover": "...",
            "asin": "...",
            "isbn": "...",
            "publisher": "...",
            "narrator": "...",
            "series": [...],
            "rating": 4.5,
            "source": "audible|google|openlibrary|none"
        }
    """
    if not abs_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Audiobookshelf not configured. Set ABS_BASE_URL and ABS_API_KEY."
        )

    if not request.title:
        raise HTTPException(status_code=400, detail="Title is required")

    logger.info(f"🔍 On-demand enrichment for: '{request.title}' by '{request.author}'")

    try:
        # Call all 3 providers in parallel
        providers = ['audible', 'google', 'openlibrary']

        async def fetch_provider(provider: str) -> tuple[str, dict]:
            """Fetch from a single provider, returning (provider_name, result)."""
            try:
                logger.debug(f"🌐 Calling provider {provider} for '{request.title}'")
                result = await abs_client._fetch_from_provider(
                    provider=provider,
                    item_id='',
                    title=request.title,
                    author=request.author or '',
                    fallback_title_only=True
                )
                return (provider, result)
            except Exception as e:
                logger.warning(f"⚠️  Provider {provider} failed: {e}")
                return (provider, {})

        # Execute all provider calls in parallel
        results = await asyncio.gather(*[fetch_provider(p) for p in providers])

        # Find first successful result
        enriched_data = {}
        source_provider = "none"
        for provider, result in results:
            if result and result.get('title'):
                enriched_data = result
                source_provider = provider
                logger.info(f"✅ Got enriched metadata from {provider}")
                break

        # If no provider succeeded, return empty metadata
        if not enriched_data:
            logger.warning(f"❌ No provider returned metadata for '{request.title}'")
            return {
                "description": "",
                "cover": "",
                "asin": None,
                "isbn": None,
                "publisher": None,
                "narrator": None,
                "series": [],
                "rating": None,
                "source": "none"
            }

        # Return enriched metadata
        return {
            "description": enriched_data.get('description', ''),
            "cover": enriched_data.get('cover', ''),
            "asin": enriched_data.get('asin'),
            "isbn": enriched_data.get('isbn'),
            "publisher": enriched_data.get('publisher'),
            "narrator": enriched_data.get('narrator'),
            "series": enriched_data.get('series', []),
            "rating": enriched_data.get('rating'),
            "source": source_provider
        }

    except Exception as e:
        logger.error(f"❌ Enrichment failed for '{request.title}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Metadata enrichment failed: {str(e)}"
        )
