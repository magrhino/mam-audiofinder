"""Library browsing and series diff endpoints."""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

from abs_client import get_abs_client
from settings_service import settings_service
from hardcover_client import hardcover_client
from series_resolver import (
    SeriesSource, SeriesInfo, BookInSeries, SeriesDiffResult,
    generate_series_id, normalize_series_name, match_books_across_sources
)
from edition_resolver import resolve_english_primary_edition
from utils import normalize_title
from config import ABS_BASE_URL

logger = logging.getLogger("mam-audiofinder")

router = APIRouter(prefix="/api/library", tags=["library"])


# ============================================================================
# Response Models
# ============================================================================

class SeriesListItem(BaseModel):
    id: str
    name: str
    name_normalized: str
    author: Optional[str] = None
    book_count: int = 0
    abs_book_count: int = 0
    series_book_count: int = 0
    source: str = "abs"
    abs_series_id: Optional[str] = None
    hardcover_series_id: Optional[int] = None


class SeriesListResponse(BaseModel):
    series: List[SeriesListItem]
    source: str
    total: int
    page: int
    pages: int


class BookListItem(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    series_name: Optional[str] = None
    series_index: Optional[float] = None
    asin: Optional[str] = None
    isbn: Optional[str] = None
    cover_path: Optional[str] = None


class BookListResponse(BaseModel):
    books: List[BookListItem]
    total: int
    page: int
    pages: int


class WishlistAddRequest(BaseModel):
    hardcover_book_id: Optional[int] = None
    title: str
    author: Optional[str] = None
    series_name: Optional[str] = None
    series_index: Optional[float] = None
    asin: Optional[str] = None
    isbn: Optional[str] = None
    cover_url: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/series", response_model=SeriesListResponse)
async def list_series(
    q: Optional[str] = Query(None, description="Search query to filter series"),
    library_id: Optional[str] = Query(None, description="Filter by specific library ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
):
    """
    List series from ABS library.

    Returns series from your Audiobookshelf library, optionally filtered by
    search query or specific library ID.
    """
    logger.info(f"[LIBRARY] GET /api/library/series - q={q!r}, library_id={library_id}, page={page}, limit={limit}")
    results: List[SeriesInfo] = []

    # Get library IDs to query
    if library_id:
        library_ids = [library_id]
    else:
        library_ids = settings_service.get_enabled_libraries()

    if not ABS_BASE_URL or not x_abs_token or not library_ids:
        logger.warning("[LIBRARY] ABS not configured or no libraries enabled")
        return SeriesListResponse(
            series=[],
            source="abs",
            total=0,
            page=page,
            pages=0,
        )

    abs_client = get_abs_client(user_token=x_abs_token)

    # Fetch series from ABS library cache
    logger.info(f"[LIBRARY] Fetching series list from ABS cache (libraries: {library_ids})...")
    abs_series = await abs_client.get_series_list(library_ids)
    logger.info(f"[LIBRARY] ABS returned {len(abs_series)} series")

    for s in abs_series:
        name = s.get("name", "")
        author = s.get("author")
        book_count = s.get("book_count", 0)
        results.append(SeriesInfo(
            id=generate_series_id(name, author or ""),
            name=name,
            name_normalized=normalize_series_name(name),
            author=author,
            book_count=book_count,
            abs_book_count=book_count,
            series_book_count=book_count,
            source=SeriesSource.ABS,
        ))

    # Filter by search query if provided
    if q:
        logger.info(f"[LIBRARY] Filtering {len(results)} series by query: {q!r}")
        q_norm = normalize_series_name(q)
        results = [s for s in results if q_norm in s.name_normalized]
        logger.info(f"[LIBRARY] After filtering: {len(results)} series")

    # Paginate
    total = len(results)
    pages = (total + limit - 1) // limit
    start = (page - 1) * limit
    paginated = results[start:start + limit]
    logger.info(f"[LIBRARY] Returning {len(paginated)} series (page {page}/{pages}, total={total})")

    # Convert SeriesInfo to SeriesListItem
    series_items = []
    for s in paginated:
        item_dict = {k: v for k, v in s.__dict__.items() if k != 'source'}
        item_dict['source'] = s.source.value
        series_items.append(SeriesListItem(**item_dict))

    return SeriesListResponse(
        series=series_items,
        source="abs",
        total=total,
        page=page,
        pages=pages,
    )


@router.get("/series/{series_name}/books")
async def get_series_books(
    series_name: str,
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
):
    """Get all ABS library books in a specific series."""
    logger.info(f"[LIBRARY] GET /api/library/series/{series_name}/books")

    library_ids = settings_service.get_enabled_libraries()
    if not ABS_BASE_URL or not x_abs_token or not library_ids:
        logger.warning(f"[LIBRARY] ABS not configured, returning 503")
        raise HTTPException(503, "ABS not configured")

    abs_client = get_abs_client(user_token=x_abs_token)

    logger.info(f"[LIBRARY] Fetching books for series: {series_name}")
    books = await abs_client.get_books_in_series(series_name, library_ids)
    logger.info(f"[LIBRARY] Found {len(books)} books in series")

    return {
        "series_name": series_name,
        "books": [b.dict() for b in books],
        "count": len(books),
    }


@router.get("/series/{series_name}/diff")
async def diff_series(
    series_name: str,
    hardcover_series_id: Optional[int] = Query(None, description="Hardcover series ID if known"),
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
):
    """
    Compare series between ABS library and Hardcover.

    Returns categorized books:
    - **present**: In both ABS and Hardcover
    - **missing**: In Hardcover but not ABS
    - **abs_only**: In ABS but not Hardcover
    - **uncertain**: Ambiguous matches needing confirmation
    """
    library_ids = settings_service.get_enabled_libraries()
    if not ABS_BASE_URL or not x_abs_token or not library_ids:
        raise HTTPException(503, "ABS not configured")
    if not hardcover_client.is_configured:
        raise HTTPException(503, "Hardcover not configured")

    abs_client = get_abs_client(user_token=x_abs_token)

    # Get ABS books
    abs_books_raw = await abs_client.get_books_in_series(series_name, library_ids)
    abs_books = [
        BookInSeries(
            id=b.id,
            title=b.title,
            title_normalized=b.title_normalized or normalize_title(b.title),
            author=b.author,
            series_index=b.series_index,
            asin=b.asin,
            isbn=b.isbn,
            source=SeriesSource.ABS,
            abs_item_id=b.id,
        )
        for b in abs_books_raw
    ]

    # Get Hardcover books (raw, with canonical filter only)
    hardcover_books_raw = []
    hc_series_id = hardcover_series_id
    hc_series_name = series_name
    hc_author_name = ""

    if hardcover_series_id:
        hc_result = await hardcover_client.list_series_books(hardcover_series_id)
        if hc_result:
            hardcover_books_raw = hc_result.get("books", [])
            hc_series_name = hc_result.get("series_name", series_name)
            hc_author_name = hc_result.get("author_name", "")
    else:
        # Search by name
        hc_search = await hardcover_client.search_series(title=series_name, limit=5)
        if hc_search:
            best = hc_search[0]
            hc_series_id = best["series_id"]
            hc_result = await hardcover_client.list_series_books(hc_series_id)
            if hc_result:
                hardcover_books_raw = hc_result.get("books", [])
                hc_series_name = hc_result.get("series_name", series_name)
                hc_author_name = hc_result.get("author_name", "")

    # Apply edition resolution to filter out international editions
    hardcover_books = []
    if hardcover_books_raw and hc_series_id:
        logger.info(f"🔍 Resolving English primary editions for series diff (series_id={hc_series_id}, {len(hardcover_books_raw)} raw books)")

        # Prepare series metadata for resolver
        series_metadata = {
            'series_id': hc_series_id,
            'title': hc_series_name,
            'author': hc_author_name,
            'canonical_titles': {}
        }

        # Resolve editions to filter out international books
        resolved_editions = await resolve_english_primary_edition(
            raw_books=hardcover_books_raw,
            series_metadata=series_metadata,
            hardcover_client=hardcover_client
        )

        # Flatten resolved editions back to books list
        for position in sorted(resolved_editions.keys()):
            book_or_books = resolved_editions[position]

            if isinstance(book_or_books, list):
                # Ambiguous - include all tied candidates
                hardcover_books.extend(book_or_books)
            else:
                # Single resolved book
                hardcover_books.append(book_or_books)

        logger.info(f"✅ Resolved to {len(hardcover_books)} English edition(s) from {len(hardcover_books_raw)} raw book(s)")

    # Fallback: if Hardcover has books that ABS series mapping missed, try to find them in the library
    # Check if we have any library caches with data
    has_caches = bool(abs_client._client._library_caches)
    if has_caches and hardcover_books and library_ids:
        fallback_abs = []
        existing_abs_ids = {b.id for b in abs_books}
        for hc_book in hardcover_books:
            title = hc_book.get("title", "")
            hc_authors = hc_book.get("authors") or hc_book.get("author_names") or []
            author = hc_authors[0] if hc_authors else ""

            # Search across all library caches
            match = None
            for lib_id in library_ids:
                if lib_id in abs_client._client._library_caches:
                    cache = abs_client._client._library_caches[lib_id]
                    found_match, _score = cache.find_best_match(title=title, author=author)
                    if found_match:
                        match = found_match
                        break

            if not match or match.id in existing_abs_ids:
                continue
            fallback_abs.append(BookInSeries(
                id=match.id,
                title=match.title,
                title_normalized=match.title_normalized or normalize_title(match.title),
                author=match.author,
                series_index=match.series_index,
                asin=match.asin,
                isbn=match.isbn,
                source=SeriesSource.ABS,
                abs_item_id=match.id,
            ))
            existing_abs_ids.add(match.id)

        if fallback_abs:
            logger.info(f"➕ Added {len(fallback_abs)} ABS library fallback match(es) not mapped to series")
            abs_books.extend(fallback_abs)

    # Perform diff
    result = match_books_across_sources(abs_books, hardcover_books)
    result.series_name = series_name
    result.series_name_normalized = normalize_series_name(series_name)

    return result


@router.get("/books", response_model=BookListResponse)
async def list_books(
    q: Optional[str] = Query(None, description="Search title/author"),
    series: Optional[str] = Query(None, description="Filter by series name"),
    library_id: Optional[str] = Query(None, description="Filter by specific library ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
):
    """Paginated book browser from ABS library cache."""
    logger.info(f"[LIBRARY] GET /api/library/books - q={q!r}, series={series!r}, library_id={library_id}, page={page}, limit={limit}")

    # Get library IDs to query
    if library_id:
        library_ids = [library_id]
    else:
        library_ids = settings_service.get_enabled_libraries()

    if not ABS_BASE_URL or not x_abs_token or not library_ids:
        logger.warning("[LIBRARY] ABS not configured, returning 503")
        raise HTTPException(503, "ABS not configured")

    abs_client = get_abs_client(user_token=x_abs_token)

    # Ensure caches are fresh for all enabled libraries
    for lib_id in library_ids:
        cache = abs_client._client._get_library_cache(lib_id)
        await cache.ensure_fresh(lambda lid=lib_id: abs_client._client.get_library_items(lid))

    # Build query
    from sqlalchemy import text
    from db.db import covers_engine

    # Query across all enabled libraries
    conditions = [f"library_id IN ({','.join(':lib_' + str(i) for i in range(len(library_ids)))})"]
    params = {f"lib_{i}": lib_id for i, lib_id in enumerate(library_ids)}

    if q:
        q_norm = normalize_title(q)
        conditions.append("(title_normalized LIKE :q OR author_normalized LIKE :q)")
        params["q"] = f"%{q_norm}%"

    if series:
        conditions.append("series_name = :series")
        params["series"] = series

    where = " AND ".join(conditions)

    with covers_engine.connect() as conn:
        # Count
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM library_items WHERE {where}"),
            params
        ).scalar()

        # Fetch
        params["offset"] = (page - 1) * limit
        params["limit"] = limit

        rows = conn.execute(text(f"""
            SELECT id, title, author, series_name, series_index, asin, isbn, cover_path
            FROM library_items
            WHERE {where}
            ORDER BY title_normalized
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

    books = [
        BookListItem(
            id=r.id,
            title=r.title,
            author=r.author,
            series_name=r.series_name,
            series_index=r.series_index,
            asin=r.asin,
            isbn=r.isbn,
            cover_path=r.cover_path,
        )
        for r in rows
    ]

    logger.info(f"[LIBRARY] Returning {len(books)} books (page {page}, total={total})")

    return BookListResponse(
        books=books,
        total=total,
        page=page,
        pages=(total + limit - 1) // limit,
    )


@router.post("/wishlist")
async def add_to_wishlist(request: WishlistAddRequest):
    """Add a missing book to the acquisition wishlist."""
    from sqlalchemy import text
    from db.db import history_engine

    with history_engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO library_wishlist
            (title, author, series_name, series_index, hardcover_book_id, asin, isbn, cover_url)
            VALUES (:title, :author, :series_name, :series_index, :hc_id, :asin, :isbn, :cover_url)
            RETURNING id
        """), {
            "title": request.title,
            "author": request.author,
            "series_name": request.series_name,
            "series_index": request.series_index,
            "hc_id": request.hardcover_book_id,
            "asin": request.asin,
            "isbn": request.isbn,
            "cover_url": request.cover_url,
        })

        wishlist_id = result.scalar()

    logger.info(f"📝 Added to wishlist: '{request.title}' (ID: {wishlist_id})")

    return {"id": wishlist_id, "status": "pending"}


@router.get("/wishlist")
async def list_wishlist(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """List wishlist items."""
    from sqlalchemy import text
    from db.db import history_engine

    conditions = ["1=1"]
    params = {}

    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    with history_engine.connect() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM library_wishlist WHERE {where}"),
            params
        ).scalar()

        params["offset"] = (page - 1) * limit
        params["limit"] = limit

        rows = conn.execute(text(f"""
            SELECT * FROM library_wishlist
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

    items = [dict(r._mapping) for r in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/cover/{item_id}")
async def get_library_item_cover(
    item_id: str,
    token: Optional[str] = Query(None),
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
):
    """Proxy ABS item cover to avoid CORS issues.

    Accepts token via query param (for img src) or header (for fetch requests).
    """
    auth_token = token or x_abs_token
    if not ABS_BASE_URL or not auth_token:
        raise HTTPException(503, "ABS not configured or missing token")

    cover_url = f"{ABS_BASE_URL}/api/items/{item_id}/cover"
    headers = {"Authorization": f"Bearer {auth_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(cover_url, headers=headers)

            if response.status_code == 404:
                raise HTTPException(404, "Cover not found")
            if response.status_code != 200:
                raise HTTPException(response.status_code, "Failed to fetch cover")

            content_type = response.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"}  # Cache for 1 day
            )
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout fetching cover")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy cover for {item_id}: {e}")
        raise HTTPException(500, "Failed to fetch cover")
