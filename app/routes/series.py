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

    logger.info(f"📋 Raw book titles from Hardcover API ({len(book_titles)} total): {book_titles}")

    # Step 1: Filter out combined/omnibus titles (e.g., "Book 1 / Book 2 / Book 3")
    # These are box sets or collections that contain multiple books in one title
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

    filtered_titles = []
    for title in book_titles:
        if isinstance(title, str):
            if is_combined_title(title):
                logger.warning(f"🗑️  Filtered out combined/omnibus title: '{title}'")
            else:
                filtered_titles.append(title)

    if len(filtered_titles) < len(book_titles):
        logger.info(f"🔍 Filtered out {len(book_titles) - len(filtered_titles)} combined/omnibus title(s)")

    # Step 2: Deduplicate book titles (Hardcover API sometimes returns duplicates)
    # Use dict to preserve order while removing case-insensitive duplicates
    seen_titles = {}
    unique_titles = []
    for title in filtered_titles:
        if isinstance(title, str):
            # Normalize title for comparison (lowercase, strip whitespace)
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
            else:
                # Log each duplicate found
                logger.warning(f"⚠️  Duplicate book title detected and removed: '{title}'")

    if len(unique_titles) < len(filtered_titles):
        logger.warning(f"🔍 Deduplication: Removed {len(filtered_titles) - len(unique_titles)} duplicate(s) from series '{series_data.get('series_name')}'")
        logger.info(f"   Before dedup: {filtered_titles}")
        logger.info(f"   After dedup: {unique_titles}")

    logger.info(f"📖 Enriching {len(unique_titles)} unique books for series '{series_data.get('series_name')}'")

    # Step 3: Enrich each book title with full details
    enriched_books = []
    for book_title in unique_titles:
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


async def enrich_books_with_abs(
    books: List[dict],
    series_author: str,
    per_page: int = 5,
    page: int = 1
) -> dict:
    """
    Translation layer: Enrich Hardcover books with ABS data.

    Fetches covers and library status from Audiobookshelf for each book,
    returning ShowcaseCard-compatible format with pagination.

    Args:
        books: Hardcover-enriched books from get_book_series_info()
        series_author: Series author for ABS lookups
        per_page: Number of books per page (default: 5)
        page: Page number, 1-indexed (default: 1)

    Returns:
        Dictionary with:
        - books: List of ShowcaseCard-compatible book objects
        - total: Total number of books
        - page: Current page number
        - per_page: Books per page
        - total_pages: Total number of pages
        - has_next: Whether there's a next page
        - has_prev: Whether there's a previous page
    """
    logger.info(f"📚 Enriching {len(books)} books with ABS data (page {page}, per_page {per_page})")

    # Calculate pagination indices (page is 1-indexed)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    paginated_books = books[start_idx:end_idx]
    total_pages = (len(books) + per_page - 1) // per_page  # Ceiling division

    logger.info(f"📄 Processing books {start_idx + 1}-{min(end_idx, len(books))} of {len(books)}")

    # Enrich each book with ABS data (5 concurrent requests max)
    semaphore = asyncio.Semaphore(5)

    async def enrich_single_book(book: dict) -> dict:
        """Enrich a single book with ABS cover and library status."""
        async with semaphore:
            book_title = book.get('title', '')
            book_author = book.get('author', series_author)

            # Fetch ABS cover (with cache)
            cover_data = {}
            if abs_client.is_configured:
                try:
                    cover_data = await abs_client.fetch_cover(
                        title=book_title,
                        author=book_author,
                        mam_id='',  # No MAM ID for Hardcover books
                        force_refresh=False
                    )
                except Exception as e:
                    logger.warning(f"⚠️  Failed to fetch ABS cover for '{book_title}': {e}")

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

            # Return ShowcaseCard-compatible format
            return {
                "display_title": book_title,
                "author": book_author,
                "cover_url": cover_data.get('cover_url', ''),
                "abs_item_id": cover_data.get('item_id'),
                "in_abs_library": in_library,
                "description": book.get('description', ''),
                "release_year": book.get('release_year'),
                "book_id": book.get('book_id'),
                "formats": [],  # N/A for Hardcover
                "total_versions": 1,  # Always 1 for Hardcover
                "normalized_title": book_title.lower().replace(' ', '-'),
                # Additional metadata for potential future use
                "mam_id": None,  # No MAM ID for Hardcover books
                "narrator": None  # Not available from Hardcover
            }

    # Enrich books concurrently
    enriched = await asyncio.gather(*[
        enrich_single_book(book) for book in paginated_books
    ])

    logger.info(f"✅ Enriched {len(enriched)} books with ABS data")

    return {
        "books": enriched,
        "total": len(books),
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


@router.get("/api/series/{series_id}/books")
async def get_series_books(
    series_id: int,
    per_page: int = 5,
    page: int = 1,
    enrich_abs: bool = True
):
    """
    Get books in a series from Hardcover with optional ABS enrichment and pagination.

    Path parameter:
        series_id: Hardcover series ID

    Query parameters:
        per_page: Number of books per page (default: 5, max: 50)
        page: Page number, 1-indexed (default: 1)
        enrich_abs: Enable ABS enrichment (covers, library check) (default: true)

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
                    ...
                },
                ...
            ],
            "total": 10,
            "page": 1,
            "per_page": 5,
            "total_pages": 2,
            "has_next": true,
            "has_prev": false,
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
                    "cover_url": "https://..."  // Hardcover URL
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

    # Validate pagination parameters
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")

    if per_page < 1 or per_page > 50:
        raise HTTPException(status_code=400, detail="per_page must be between 1 and 50")

    logger.info(f"📚 Fetching books for series ID {series_id} (page={page}, per_page={per_page}, enrich_abs={enrich_abs})")

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
            # Apply ABS enrichment + pagination
            logger.info(f"🔍 Applying ABS enrichment to {len(result['books'])} books")

            enriched_result = await enrich_books_with_abs(
                books=result['books'],
                series_author=result['author_name'],
                per_page=per_page,
                page=page
            )

            response = {
                "series_id": result['series_id'],
                "series_name": result['series_name'],
                "author_name": result['author_name'],
                **enriched_result,  # books, total, page, per_page, total_pages, has_next, has_prev
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"✅ Returned {len(enriched_result['books'])} ABS-enriched books (page {page}/{enriched_result['total_pages']})")
            return JSONResponse(response)
        else:
            # Return original Hardcover data (no ABS enrichment, no pagination)
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
