"""
Series routes for Hardcover API integration.
Handles series discovery and book listings.
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from hardcover_client import hardcover_client
from utils import normalize_title, normalize_author

router = APIRouter()
logger = logging.getLogger("mam-audiofinder")


class SeriesSearchRequest(BaseModel):
    """Request model for series search."""
    title: str
    author: str = ""
    normalized_title: Optional[str] = None
    limit: int = 20  # Default to 20


@router.post("/api/series/search")
async def search_series(request: SeriesSearchRequest):
    """
    Search for series on Hardcover by title and/or author.

    Request:
        {
            "title": "The Way of Kings",
            "author": "Brandon Sanderson",  // optional
            "normalized_title": "way of kings",  // optional, will be computed if not provided
            "limit": 10  // optional, default 10
        }

    Response:
        {
            "query": {
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "normalized_title": "way of kings"
            },
            "hardcover_series": [
                {
                    "series_id": 49075,
                    "series_name": "The Stormlight Archive",
                    "author_name": "Brandon Sanderson",
                    "book_count": 5,
                    "readers_count": 125000
                }
            ],
            "cached": false,
            "timestamp": "2025-11-17T10:30:00Z"
        }
    """
    if not hardcover_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Hardcover API not configured. Set HARDCOVER_API_TOKEN in environment."
        )

    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    # Validate limit parameter (allowed values: 5, 10, 20, 30, 40, 50)
    ALLOWED_LIMITS = [5, 10, 20, 30, 40, 50]
    limit = request.limit if request.limit in ALLOWED_LIMITS else 20

    # Compute normalized title if not provided
    normalized_title = request.normalized_title or normalize_title(request.title)

    logger.info(f"📖 Series search request: title='{request.title}', author='{request.author}'")

    try:
        # Search Hardcover for series
        series_results = await hardcover_client.search_series(
            title=request.title,
            author=request.author,
            limit=limit
        )

        # Check if API call failed
        if series_results is None:
            raise HTTPException(
                status_code=503,
                detail="Hardcover API request failed. Check logs for details."
            )

        from datetime import datetime
        response = {
            "query": {
                "title": request.title,
                "author": request.author,
                "normalized_title": normalized_title
            },
            "hardcover_series": series_results,
            "cached": False,  # TODO: Detect cache hit from client
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        logger.info(f"✅ Series search returned {len(series_results)} results")
        return JSONResponse(response)

    except Exception as e:
        logger.error(f"❌ Series search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Series search failed: {str(e)}"
        )


async def get_book_series_info(series_id: int) -> Optional[dict]:
    """
    Backend translation composable: Get enriched book information for a series.

    This function:
    1. Fetches basic series info and book titles from list_series_books()
    2. For each book title, queries Hardcover API to get full book details
    3. Returns enriched book objects with title, authors, release_year, etc.

    Args:
        series_id: Hardcover series ID

    Returns:
        Dictionary with series info and enriched books array, or None if not found
    """
    # Step 1: Get series info and book titles
    series_data = await hardcover_client.list_series_books(series_id)

    if not series_data:
        return None

    book_titles = series_data.get("books", [])
    series_author = series_data.get("author_name", "")

    logger.info(f"📖 Enriching {len(book_titles)} books for series '{series_data.get('series_name')}'")

    # Step 2: Enrich each book title with full details
    enriched_books = []
    for book_title in book_titles:
        if not book_title or not isinstance(book_title, str):
            continue

        try:
            # Search for book details by title
            book_results = await hardcover_client.search_book_by_title(
                title=book_title,
                author=series_author,
                limit=1
            )

            if book_results and len(book_results) > 0:
                # Use the first match
                book_info = book_results[0]

                # Format authors as comma-separated string
                authors_list = book_info.get("authors", [])
                author_str = ", ".join(authors_list) if authors_list else series_author

                enriched_books.append({
                    "book_id": book_info.get("book_id"),
                    "title": book_info.get("title", book_title),
                    "author": author_str,
                    "author_name": author_str,  # Support both field names
                    "release_year": book_info.get("release_year"),
                    "description": book_info.get("description", ""),
                    "cover_url": book_info.get("cover_url", "")
                })
            else:
                # Fallback: use title only with series author
                logger.debug(f"⚠️  No detailed info found for '{book_title}', using title only")
                enriched_books.append({
                    "book_id": None,
                    "title": book_title,
                    "author": series_author,
                    "author_name": series_author,
                    "release_year": None,
                    "description": "",
                    "cover_url": ""
                })

        except Exception as e:
            logger.warning(f"⚠️  Failed to enrich book '{book_title}': {e}")
            # Add fallback entry
            enriched_books.append({
                "book_id": None,
                "title": book_title,
                "author": series_author,
                "author_name": series_author,
                "release_year": None,
                "description": "",
                "cover_url": ""
            })

    logger.info(f"✅ Enriched {len(enriched_books)} books with detailed info")

    return {
        "series_id": series_data.get("series_id"),
        "series_name": series_data.get("series_name"),
        "author_name": series_author,
        "books": enriched_books
    }


@router.get("/api/series/{series_id}/books")
async def get_series_books(series_id: int):
    """
    Get all books in a series from Hardcover with enriched details.

    Path parameter:
        series_id: Hardcover series ID

    Response:
        {
            "series_id": 49075,
            "series_name": "The Stormlight Archive",
            "author_name": "Brandon Sanderson",
            "books": [
                {
                    "book_id": 123,
                    "title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "release_year": 2010,
                    "description": "...",
                    "cover_url": "https://..."
                },
                ...
            ],
            "cached": false,
            "timestamp": "2025-11-17T10:30:00Z"
        }
    """
    if not hardcover_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Hardcover API not configured. Set HARDCOVER_API_TOKEN in environment."
        )

    logger.info(f"📚 Fetching enriched books for series ID {series_id}")

    try:
        # Use the backend translation composable to get enriched book info
        result = await get_book_series_info(series_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Series {series_id} not found"
            )

        from datetime import datetime
        result["cached"] = False  # TODO: Detect cache hit
        result["timestamp"] = datetime.utcnow().isoformat() + "Z"

        logger.info(f"✅ Returned {len(result.get('books', []))} enriched books for series '{result.get('series_name')}'")
        return JSONResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch series books: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch series books: {str(e)}"
        )


@router.get("/api/series/health")
async def series_health():
    """
    Check Hardcover API configuration and connectivity.

    Response:
        {
            "configured": true,
            "status": "ok",
            "message": "Hardcover API is configured and ready"
        }
    """
    if not hardcover_client.is_configured:
        return JSONResponse({
            "configured": False,
            "status": "not_configured",
            "message": "HARDCOVER_API_TOKEN not set"
        })

    # TODO: Add actual connectivity test if needed
    return JSONResponse({
        "configured": True,
        "status": "ok",
        "message": "Hardcover API is configured and ready"
    })
