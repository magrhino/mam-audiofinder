"""
Series routes for Hardcover API integration.
Handles series discovery and book listings.
"""
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Literal

from hardcover_client import hardcover_client
from abs_client import abs_client
from utils import normalize_title, normalize_author
from enrichment_tracker import get_tracker
from covers import CoverService

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
    series_author: str,
    include_audio_meta: bool = False
) -> List[dict]:
    """
    Translation layer: Enrich Hardcover books with ABS cover data.

    Fetches covers and library status from Audiobookshelf for each book,
    returning ShowcaseCard-compatible format. Uses lightweight fetch_cover
    method (not provider enrichment) for fast series loading.

    Args:
        books: Hardcover-enriched books from get_book_series_info()
        series_author: Series author for ABS lookups
        include_audio_meta: If True, fetch audiobook metadata from Hardcover (slower)

    Returns:
        List of ShowcaseCard-compatible book objects with covers and library status
    """
    audio_meta_msg = " (including audiobook metadata)" if include_audio_meta else ""
    logger.info(f"📚 Enriching {len(books)} books with ABS data{audio_meta_msg}")

    # Enrich each book with ABS data (10 concurrent requests max)
    semaphore = asyncio.Semaphore(10)

    async def enrich_single_book(book: dict) -> dict:
        """Enrich a single book with ABS cover and library status.

        Uses concurrent API calls (asyncio.gather) for faster enrichment:
        - Cover fetch from ABS (always)
        - Library check (always)
        - Hardcover audiobook metadata (only if include_audio_meta=True)
        """
        async with semaphore:
            book_title = book.get('title', '')
            book_author = book.get('author', series_author)
            book_id = book.get('book_id')

            # Initialize defaults
            cover_url = ''
            item_id = None
            description = book.get('description', '')
            in_library = False
            has_audiobook = False
            audio_seconds = None

            # Define concurrent tasks for parallel execution
            async def fetch_cover_task():
                """Fetch cover from ABS."""
                if not abs_client.is_configured:
                    return {}
                try:
                    logger.debug(f"📸 Fetching cover for '{book_title}'")
                    return await abs_client.fetch_cover(
                        title=book_title,
                        author=book_author,
                        mam_id='',
                        force_refresh=False
                    )
                except Exception as e:
                    logger.warning(f"⚠️  Failed to fetch cover for '{book_title}': {e}")
                    return {}

            async def check_library_task():
                """Check if book is in ABS library."""
                if not (abs_client.is_configured and abs_client.library_id):
                    return {}
                try:
                    return await abs_client.check_library_items([
                        (book_title, book_author)
                    ])
                except Exception as e:
                    logger.warning(f"⚠️  Failed to check library for '{book_title}': {e}")
                    return {}

            async def fetch_hardcover_task():
                """Fetch audiobook metadata from Hardcover."""
                if not hardcover_client.is_configured:
                    return []
                try:
                    logger.debug(f"🎧 Fetching audiobook metadata for '{book_title}'")
                    return await hardcover_client.search_book_advanced(
                        title=book_title,
                        author=book_author,
                        limit=1
                    )
                except Exception as e:
                    logger.warning(f"⚠️  Hardcover unavailable, defaulting has_audiobook=False for '{book_title}': {e}")
                    return []

            # Execute API calls concurrently (conditionally include Hardcover task)
            tasks = [fetch_cover_task(), check_library_task()]
            if include_audio_meta:
                tasks.append(fetch_hardcover_task())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Unpack results (2 or 3 depending on include_audio_meta)
            cover_data = results[0]
            library_check = results[1]
            hardcover_results = results[2] if include_audio_meta and len(results) > 2 else []

            # Process cover results
            if isinstance(cover_data, dict) and cover_data:
                cover_url = cover_data.get('cover_url', '')
                item_id = cover_data.get('item_id')
                if cover_data.get('description'):
                    description = cover_data.get('description')

            # Process library check results
            if isinstance(library_check, dict) and library_check:
                cache_key = f"{book_title.lower().strip()}||{book_author.lower().strip()}"
                in_library = library_check.get(cache_key, False)

            # Process hardcover results (only if include_audio_meta was True)
            hardcover_genres = []
            if include_audio_meta and isinstance(hardcover_results, list) and len(hardcover_results) > 0:
                first_result = hardcover_results[0]
                has_audiobook = first_result.get('has_audiobook', False)
                audio_seconds = first_result.get('audio_seconds')
                hardcover_genres = first_result.get('genres', [])
                logger.debug(f"🎧 Audiobook metadata: has_audiobook={has_audiobook}, duration={audio_seconds}s")

            # Persist metadata to covers.db (always save cover/description, conditionally save audiobook metadata)
            if cover_url or description or (include_audio_meta and (has_audiobook or hardcover_genres)):
                try:
                    cover_service = CoverService()
                    mam_id = f"series_{book_id}" if book_id else f"book_{book_title.lower()[:20]}"
                    metadata_json = {
                        "has_audiobook": has_audiobook,
                        "audio_seconds": audio_seconds,
                        "description_source": "hardcover" if description else "none",
                        "genres": hardcover_genres
                    }
                    await cover_service.save_cover_to_cache(
                        mam_id=mam_id,
                        cover_url=cover_url or "",
                        title=book_title,
                        author=book_author,
                        item_id=item_id,
                        description=description or "",
                        metadata_json=metadata_json
                    )
                    logger.debug(f"💾 Cached hardcover metadata for '{book_title}'")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to cache hardcover metadata for '{book_title}': {e}")

            # Return ShowcaseCard-compatible format
            result = {
                "display_title": book_title,
                "author": book_author,
                "cover_url": cover_url,
                "abs_item_id": item_id,
                "in_abs_library": in_library,
                "description": description,
                "release_year": book.get('release_year'),
                "book_id": book.get('book_id'),
                "position": book.get('position'),  # Preserve series position/numbering
                "formats": [],
                "total_versions": 1,
                "normalized_title": book_title.lower().replace(' ', '-'),
                "mam_id": None,
                "narrator": None,
                # Provider fields not populated (use on-demand enrichment endpoint for these)
                "series": [],
                "asin": None,
                "isbn": None,
                "publisher": None,
                "rating": None
            }

            # Only include audiobook metadata if it was fetched
            if include_audio_meta:
                result["has_audiobook"] = has_audiobook
                result["audio_seconds"] = audio_seconds

            return result

    # Enrich books concurrently
    enriched = await asyncio.gather(*[
        enrich_single_book(book) for book in books
    ])

    logger.info(f"✅ Enriched {len(enriched)} books with ABS data")

    return enriched


async def _background_enrich_books(
    series_id: str,
    books: List[dict],
    series_author: str,
    include_audio_meta: bool = False
):
    """
    Background task to enrich books concurrently and update enrichment tracker.

    Args:
        series_id: Series identifier (used as key in tracker)
        books: List of basic book data from Hardcover
        series_author: Series author name
        include_audio_meta: If True, fetch audiobook metadata from Hardcover
    """
    tracker = get_tracker()

    try:
        logger.info(f"🔄 Starting background enrichment for series {series_id} ({len(books)} books)")

        # Enrich all books (reuses existing enrich_books_with_abs logic)
        enriched_books = await enrich_books_with_abs(
            books=books,
            series_author=series_author,
            include_audio_meta=include_audio_meta
        )

        # Update tracker with enriched books (one at a time for progress tracking)
        for book in enriched_books:
            await tracker.update_progress(series_id, book)

        logger.info(f"✅ Background enrichment complete for series {series_id}")

    except Exception as e:
        logger.error(f"❌ Background enrichment failed for series {series_id}: {e}")
        await tracker.mark_failed(series_id, str(e))


@router.get("/api/series/{series_id}/books")
async def get_series_books(
    series_id: int,
    enrich_mode: Literal["immediate", "wait", "status"] = Query(
        default="immediate",
        description="Enrichment mode: 'immediate' returns basic data and enriches in background (default), "
                    "'wait' waits for full enrichment, "
                    "'status' checks enrichment progress"
    ),
    include_audio_meta: bool = Query(
        default=False,
        description="If True, fetch audiobook metadata from Hardcover (slower). "
                    "Only applies when enrichment is performed."
    )
):
    """
    Get books in a series from Hardcover with progressive enrichment support.

    Path parameter:
        series_id: Hardcover series ID

    Query parameters:
        enrich_mode: "immediate" | "wait" | "status" (default: "wait")
            - "immediate": Return basic data immediately, enrich in background
            - "wait": Wait for full enrichment before responding (backward compatible)
            - "status": Return current enrichment status and any enriched books available

    Response (enrich_mode="immediate"):
        {
            "series_id": 49075,
            "series_name": "The Stormlight Archive",
            "author_name": "Brandon Sanderson",
            "books": [  // Basic data with positions, no covers yet
                {
                    "book_id": 123,
                    "title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "position": 1,  // Series number
                    "description": "",
                    "cover_url": ""
                }
            ],
            "enrichment_status": "pending",
            "enrichment_progress": {"total": 10, "completed": 0, "percentage": 0},
            "total": 10,
            "timestamp": "2025-11-23T10:30:00Z"
        }

    Response (enrich_mode="status"):
        {
            "series_id": 49075,
            "series_name": "The Stormlight Archive",
            "author_name": "Brandon Sanderson",
            "books": [  // Progressively enriched books (some may have covers, some may not)
                {
                    "display_title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "position": 1,
                    "cover_url": "/covers/...",  // Populated if enriched
                    "has_audiobook": true,
                    "in_abs_library": false,
                    ...
                }
            ],
            "enrichment_status": "in_progress",  // "pending" | "in_progress" | "complete" | "failed"
            "enrichment_progress": {"total": 10, "completed": 5, "percentage": 50},
            "total": 10,
            "timestamp": "2025-11-23T10:30:00Z"
        }

    Response (enrich_mode="wait"):
        {
            "series_id": 49075,
            "series_name": "The Stormlight Archive",
            "author_name": "Brandon Sanderson",
            "books": [  // Fully enriched books
                {
                    "display_title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "position": 1,
                    "cover_url": "/covers/...",
                    "has_audiobook": true,
                    "in_abs_library": true,
                    ...
                }
            ],
            "enrichment_status": "complete",
            "total": 10,
            "timestamp": "2025-11-23T10:30:00Z"
        }
    """
    if not hardcover_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Hardcover API not configured. Set HARDCOVER_API_TOKEN in environment."
        )

    logger.info(f"📚 Fetching books for series ID {series_id} (enrich_mode={enrich_mode})")

    tracker = get_tracker()
    series_id_str = str(series_id)

    try:
        from datetime import datetime

        # MODE: "status" - Check enrichment progress
        if enrich_mode == "status":
            logger.debug(f"📊 Checking enrichment status for series {series_id}")

            status_info = await tracker.get_status(series_id_str)

            if not status_info:
                # No enrichment job found, treat as if never requested
                return JSONResponse({
                    "series_id": series_id,
                    "enrichment_status": "not_found",
                    "message": "No enrichment job found for this series. Use enrich_mode=immediate to start one.",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })

            # Return enriched books (may be partial if in_progress)
            enriched_books = status_info.get("enriched_books", [])

            # Get basic series info (for series_name, author_name)
            series_info = await get_book_series_info(series_id)
            if not series_info:
                raise HTTPException(status_code=404, detail=f"Series {series_id} not found")

            response = {
                "series_id": series_id,
                "series_name": series_info['series_name'],
                "author_name": series_info['author_name'],
                "books": enriched_books,
                "enrichment_status": status_info["status"],
                "enrichment_progress": status_info["progress"],
                "total": len(enriched_books) if enriched_books else status_info["progress"]["total"],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"📊 Status: {status_info['status']}, {status_info['progress']['completed']}/{status_info['progress']['total']} books enriched")
            return JSONResponse(response)

        # MODE: "immediate" or "wait" - Fetch series data
        result = await get_book_series_info(series_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Series {series_id} not found"
            )

        # MODE: "immediate" - Return basic data, start background enrichment
        if enrich_mode == "immediate":
            logger.info(f"⚡ Returning immediate response with basic data ({len(result['books'])} books)")

            # Start enrichment job
            job = await tracker.start_job(series_id_str, len(result['books']))

            # Launch background enrichment task (non-blocking)
            if abs_client.is_configured:
                asyncio.create_task(_background_enrich_books(
                    series_id=series_id_str,
                    books=result['books'],
                    series_author=result['author_name'],
                    include_audio_meta=include_audio_meta
                ))
                audio_msg = " (with audiobook metadata)" if include_audio_meta else ""
                logger.info(f"🚀 Launched background enrichment task for series {series_id}{audio_msg}")

            response = {
                "series_id": result['series_id'],
                "series_name": result['series_name'],
                "author_name": result['author_name'],
                "books": result['books'],  # Basic data with positions
                "enrichment_status": "pending" if abs_client.is_configured else "not_configured",
                "enrichment_progress": job.get_progress(),
                "total": len(result['books']),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"✅ Returned {len(result['books'])} basic books, enrichment starting")
            return JSONResponse(response)

        # MODE: "wait" - Blocking enrichment
        if abs_client.is_configured:
            audio_msg = " (with audiobook metadata)" if include_audio_meta else ""
            logger.info(f"⏳ Applying blocking enrichment to {len(result['books'])} books{audio_msg}")

            enriched_books = await enrich_books_with_abs(
                books=result['books'],
                series_author=result['author_name'],
                include_audio_meta=include_audio_meta
            )

            response = {
                "series_id": result['series_id'],
                "series_name": result['series_name'],
                "author_name": result['author_name'],
                "books": enriched_books,
                "enrichment_status": "complete",
                "total": len(enriched_books),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"✅ Returned {len(enriched_books)} fully enriched books")
            return JSONResponse(response)
        else:
            # ABS not configured, return basic data
            logger.warning("⚠️  ABS not configured, returning basic Hardcover data")

            response = {
                "series_id": result['series_id'],
                "series_name": result['series_name'],
                "author_name": result['author_name'],
                "books": result['books'],
                "enrichment_status": "not_configured",
                "total": len(result['books']),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"✅ Returned {len(result['books'])} basic books (ABS not configured)")
            return JSONResponse(response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch series books: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch series books: {str(e)}"
        )


class FetchAudioRequest(BaseModel):
    """Request model for fetching audiobook metadata."""
    book_indices: Optional[List[int]] = None  # None or empty list = all books


@router.post("/api/series/{series_id}/books/fetch-audio")
async def fetch_series_audio_metadata(
    series_id: int,
    request: FetchAudioRequest
):
    """
    Fetch audiobook metadata for specific books in a series (or all books).

    This endpoint allows on-demand fetching of audiobook metadata from Hardcover
    without blocking the initial series load. Metadata is persisted to covers.db.

    Path parameter:
        series_id: Hardcover series ID

    Request body:
        {
            "book_indices": [1, 2, 3]  // List of book positions, or null/[] for all books
        }

    Response:
        {
            "series_id": 49075,
            "enriched_count": 3,
            "books": [  // Enriched book objects with audiobook metadata
                {
                    "book_id": 123,
                    "title": "The Way of Kings",
                    "author": "Brandon Sanderson",
                    "position": 1,
                    "has_audiobook": true,
                    "audio_seconds": 45360,
                    ...
                }
            ],
            "errors": []  // List of errors for any books that failed
        }
    """
    if not hardcover_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Hardcover API not configured. Set HARDCOVER_API_TOKEN in environment."
        )

    logger.info(f"🎧 Fetching audiobook metadata for series {series_id}, indices={request.book_indices}")

    try:
        # Get basic series info
        series_info = await get_book_series_info(series_id)
        if not series_info:
            raise HTTPException(
                status_code=404,
                detail=f"Series {series_id} not found"
            )

        books = series_info['books']
        series_author = series_info['author_name']

        # Filter to requested indices if provided
        if request.book_indices:
            books_to_enrich = [
                book for book in books
                if book.get('position') in request.book_indices
            ]
            if not books_to_enrich:
                raise HTTPException(
                    status_code=400,
                    detail=f"No books found at positions {request.book_indices}"
                )
        else:
            # None or empty list = enrich all books
            books_to_enrich = books

        logger.info(f"📋 Enriching audiobook metadata for {len(books_to_enrich)} books")

        # Enrich books with audiobook metadata only (include_audio_meta=True)
        enriched_books = await enrich_books_with_abs(
            books=books_to_enrich,
            series_author=series_author,
            include_audio_meta=True
        )

        # Track any errors during enrichment
        errors = []
        successful_books = []

        for book in enriched_books:
            # Verify audiobook metadata was fetched
            if book.get('has_audiobook') is not None:
                successful_books.append(book)
            else:
                errors.append({
                    "title": book.get('display_title'),
                    "position": book.get('position'),
                    "error": "Failed to fetch audiobook metadata"
                })

        response = {
            "series_id": series_id,
            "enriched_count": len(successful_books),
            "books": successful_books,
            "errors": errors
        }

        logger.info(f"✅ Enriched audiobook metadata for {len(successful_books)}/{len(books_to_enrich)} books")
        return JSONResponse(response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch audiobook metadata for series {series_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch audiobook metadata: {str(e)}"
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
