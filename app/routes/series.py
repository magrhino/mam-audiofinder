"""
Series routes for Hardcover API integration.
Handles series discovery and book listings.
"""
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict

from hardcover_client import hardcover_client
from abs_client import abs_client
from utils import normalize_title, normalize_author

router = APIRouter()
logger = logging.getLogger("mam-audiofinder")


def filter_omnibus_books(books: List[dict], debug: bool = False) -> List[dict]:
    """
    FastAPI dependency: Filter out combined/omnibus editions.

    Detects and removes box sets or collections that contain multiple books
    in one title (e.g., "Book 1 / Book 2 / Book 3").

    Args:
        books: List of book dictionaries with 'title' field
        debug: Enable debug logging

    Returns:
        Filtered list excluding omnibus editions
    """
    if not books:
        return books

    def is_combined_title(title: str) -> bool:
        """Detect if a title is a combined/omnibus edition."""
        if not isinstance(title, str):
            return False
        # Check for slash separators (common in omnibus titles)
        # Must have spaces around slash to avoid false positives like "and/or"
        if " / " in title:
            # Count how many slashes - 2+ slashes likely means combined title
            slash_count = title.count(" / ")
            if slash_count >= 2:
                return True
            # Even with 1 slash, if title is very long (>80 chars), likely omnibus
            if slash_count >= 1 and len(title) > 80:
                return True
        return False

    filtered_books = []
    filtered_count = 0

    for book in books:
        if not isinstance(book, dict):
            continue

        title = book.get('title', '')

        if is_combined_title(title):
            filtered_count += 1
            if debug:
                logger.debug(f"🗑️  Filtered out combined/omnibus: '{title}'")
        else:
            filtered_books.append(book)

    if filtered_count > 0:
        logger.info(f"🔍 Filtered out {filtered_count} combined/omnibus edition(s)")

    return filtered_books


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
    # Step 1: Get series info and books from Hardcover
    series_data = await hardcover_client.list_series_books(series_id)

    if not series_data:
        return None

    books = series_data.get("books", [])
    series_author = series_data.get("author_name", "")

    logger.info(f"📋 Raw books from Hardcover API ({len(books)} total): {books}")

    # Step 2: Filter out omnibus editions using dependency
    # Note: Deduplication already done by hardcover_client._deduplicate_books()
    filtered_books = filter_omnibus_books(books, debug=True)

    logger.info(f"📖 Processing {len(filtered_books)} books for series '{series_data.get('series_name')}'")

    # Step 3: Format books for output
    # Books already have basic info from list_series_books (title, subtitle, position, book_id)
    # No need for additional search_book_by_title() calls
    enriched_books = []
    for book in filtered_books:
        if not isinstance(book, dict):
            continue

        book_title = book.get("title", "")
        if not book_title:
            continue

        enriched_books.append({
            "book_id": book.get("book_id"),
            "title": book_title,
            "author": series_author,
            "author_name": series_author,
            "release_year": None,  # Not available from list_series_books
            "description": "",
            "cover_url": "",
            "subtitle": book.get("subtitle"),
            "position": book.get("position")
        })

    logger.info(f"✅ Formatted {len(enriched_books)} books with basic info")

    return {
        "series_id": series_data.get("series_id"),
        "series_name": series_data.get("series_name"),
        "author_name": series_author,
        "books": enriched_books
    }


async def enrich_books_with_abs(
    books: List[dict],
    series_author: str
) -> List[dict]:
    """
    Translation layer: Enrich Hardcover books with ABS cover data.

    Fetches covers and library status from Audiobookshelf for each book,
    returning ShowcaseCard-compatible format. Uses lightweight fetch_cover
    method (not provider enrichment) for fast series loading.

    Args:
        books: Hardcover-enriched books from get_book_series_info()
        series_author: Series author for ABS lookups

    Returns:
        List of ShowcaseCard-compatible book objects with covers and library status
    """
    logger.info(f"📚 Enriching {len(books)} books with ABS data")

    # Enrich each book with ABS data (10 concurrent requests max)
    semaphore = asyncio.Semaphore(10)

    async def enrich_single_book(book: dict) -> dict:
        """Enrich a single book with ABS cover and library status (lightweight, no provider enrichment)."""
        async with semaphore:
            book_title = book.get('title', '')
            book_author = book.get('author', series_author)
            book_id = book.get('book_id')

            # Lightweight cover fetching (no provider enrichment for series listing)
            cover_url = ''
            item_id = None
            description = book.get('description', '')

            if abs_client.is_configured:
                try:
                    # Use fetch_cover for fast, lightweight cover retrieval
                    logger.debug(f"📸 Fetching cover for '{book_title}'")
                    cover_data = await abs_client.fetch_cover(
                        title=book_title,
                        author=book_author,
                        mam_id='',
                        force_refresh=False
                    )
                    cover_url = cover_data.get('cover_url', '')
                    item_id = cover_data.get('item_id')
                    # If fetch_cover found item in library, use its description
                    if cover_data.get('description'):
                        description = cover_data.get('description')

                except Exception as e:
                    logger.warning(f"⚠️  Failed to fetch cover for '{book_title}': {e}")

            # Check if in ABS library
            in_library = False
            if abs_client.is_configured and abs_client.library_id:
                try:
                    library_check = await abs_client.check_library_items([
                        (book_title, book_author)
                    ])
                    cache_key = f"{book_title.lower().strip()}||{book_author.lower().strip()}"
                    in_library = library_check.get(cache_key, False)
                except Exception as e:
                    logger.warning(f"⚠️  Failed to check library for '{book_title}': {e}")

            # Fetch audiobook metadata from Hardcover
            has_audiobook = None  # null = unknown
            audio_seconds = None
            if hardcover_client.is_configured:
                try:
                    logger.debug(f"🎧 Fetching audiobook metadata for '{book_title}'")
                    hardcover_results = await hardcover_client.search_book_advanced(
                        title=book_title,
                        author=book_author,
                        limit=1
                    )
                    if hardcover_results and len(hardcover_results) > 0:
                        first_result = hardcover_results[0]
                        has_audiobook = first_result.get('has_audiobook')
                        audio_seconds = first_result.get('audio_seconds')
                        logger.debug(f"🎧 Audiobook metadata: has_audiobook={has_audiobook}, duration={audio_seconds}s")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to fetch audiobook metadata for '{book_title}': {e}")

            # Return ShowcaseCard-compatible format
            return {
                "display_title": book_title,
                "author": book_author,
                "cover_url": cover_url,
                "abs_item_id": item_id,
                "in_abs_library": in_library,
                "description": description,
                "release_year": book.get('release_year'),
                "book_id": book.get('book_id'),
                "formats": [],
                "total_versions": 1,
                "normalized_title": book_title.lower().replace(' ', '-'),
                "mam_id": None,
                "narrator": None,
                # Audiobook metadata from Hardcover
                "has_audiobook": has_audiobook,
                "audio_seconds": audio_seconds,
                # Provider fields not populated (use on-demand enrichment endpoint for these)
                "series": [],
                "asin": None,
                "isbn": None,
                "publisher": None,
                "rating": None
            }

    # Enrich books concurrently
    enriched = await asyncio.gather(*[
        enrich_single_book(book) for book in books
    ])

    logger.info(f"✅ Enriched {len(enriched)} books with ABS data")

    return enriched


@router.get("/api/series/{series_id}/books")
async def get_series_books(
    series_id: int,
    enrich_abs: bool = True
):
    """
    Get books in a series from Hardcover with optional ABS enrichment.

    Path parameter:
        series_id: Hardcover series ID

    Query parameters:
        enrich_abs: Enable ABS enrichment (covers, library check, provider metadata) (default: true)

    Response (with enrich_abs=true):
        {
            "series_id": 49075,
            "series_name": "The Stormlight Archive",
            "author_name": "Brandon Sanderson",
            "books": [
                {
                    "display_title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "cover_url": "/covers/...",
                    "in_abs_library": true,
                    "description": "...",
                    "release_year": 2010,
                    "series": [...],
                    "asin": "...",
                    "isbn": "...",
                    ...
                },
                ...
            ],
            "total": 10,
            "timestamp": "2025-11-19T10:30:00Z"
        }

    Response (with enrich_abs=false):
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
                    "cover_url": ""
                },
                ...
            ],
            "total": 10,
            "timestamp": "2025-11-19T10:30:00Z"
        }
    """
    if not hardcover_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Hardcover API not configured. Set HARDCOVER_API_TOKEN in environment."
        )

    logger.info(f"📚 Fetching books for series ID {series_id} (enrich_abs={enrich_abs})")

    try:
        # Get Hardcover-enriched books
        result = await get_book_series_info(series_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Series {series_id} not found"
            )

        from datetime import datetime

        if enrich_abs and abs_client.is_configured:
            # Apply ABS enrichment with provider metadata
            logger.info(f"🔍 Applying ABS enrichment to {len(result['books'])} books")

            enriched_books = await enrich_books_with_abs(
                books=result['books'],
                series_author=result['author_name']
            )

            response = {
                "series_id": result['series_id'],
                "series_name": result['series_name'],
                "author_name": result['author_name'],
                "books": enriched_books,
                "total": len(enriched_books),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"✅ Returned {len(enriched_books)} ABS-enriched books")
            return JSONResponse(response)
        else:
            # Return original Hardcover data (no ABS enrichment)
            if not abs_client.is_configured and enrich_abs:
                logger.warning("⚠️  ABS enrichment requested but ABS is not configured")

            response = {
                "series_id": result['series_id'],
                "series_name": result['series_name'],
                "author_name": result['author_name'],
                "books": result['books'],
                "total": len(result['books']),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"✅ Returned {len(result['books'])} Hardcover books (no ABS enrichment)")
            return JSONResponse(response)

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
