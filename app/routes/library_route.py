"""Library browsing and series diff endpoints."""

import logging
from typing import Optional, Literal, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

from abs.client import AbsClient
from hardcover_client import hardcover_client
from series_resolver import (
    SeriesSource, SeriesInfo, BookInSeries, SeriesDiffResult,
    generate_series_id, normalize_series_name, match_books_across_sources
)
from edition_resolver import resolve_english_primary_edition
from utils import normalize_title

logger = logging.getLogger("mam-audiofinder")

router = APIRouter(prefix="/api/library", tags=["library"])

# Initialize ABS client
abs_client = AbsClient.from_env()


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
    source: Literal["abs", "hardcover", "both"] = "abs",
    q: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """
    List series from configured source(s).

    - **abs**: Series from ABS library (fast, shows what you own)
    - **hardcover**: Search Hardcover catalog (requires query)
    - **both**: Merge results with cross-matching
    """
    logger.info(f"[LIBRARY] GET /api/library/series - source={source}, q={q!r}, page={page}, limit={limit}")
    results: List[SeriesInfo] = []

    # Fetch from ABS (multi-series aware via cache)
    if source in ("abs", "both"):
        logger.info(f"[LIBRARY] Checking ABS: is_configured={abs_client.is_configured}")
        if abs_client.is_configured:
            logger.info(f"[LIBRARY] Fetching series list from ABS cache...")
            abs_series = await abs_client.get_series_list()
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

    # Fetch from Hardcover (requires query)
    if source in ("hardcover", "both") and q:
        logger.info(f"[LIBRARY] Checking Hardcover: is_configured={hardcover_client.is_configured}")
        if hardcover_client.is_configured:
            logger.info(f"[LIBRARY] Searching Hardcover for query: {q!r}")
            hc_results = await hardcover_client.search_series(title=q, limit=20)
            logger.info(f"[LIBRARY] Hardcover returned {len(hc_results) if hc_results else 0} series")

            if hc_results:
                for s in hc_results:
                    name = s.get("series_name", "")
                    author = s.get("author_name", "")
                    series_book_count = s.get("book_count", 0)
                    results.append(SeriesInfo(
                        id=generate_series_id(name, author),
                        name=name,
                        name_normalized=normalize_series_name(name),
                        author=author,
                        book_count=series_book_count,
                        abs_book_count=0,
                        series_book_count=series_book_count,
                        source=SeriesSource.HARDCOVER,
                        hardcover_series_id=s.get("series_id"),
                    ))

    # Filter ABS results by query
    if q and source == "abs":
        logger.info(f"[LIBRARY] Filtering {len(results)} ABS series by query: {q!r}")
        q_norm = normalize_series_name(q)
        results = [s for s in results if q_norm in s.name_normalized]
        logger.info(f"[LIBRARY] After filtering: {len(results)} series")

    # Paginate
    total = len(results)
    pages = (total + limit - 1) // limit
    start = (page - 1) * limit
    paginated = results[start:start + limit]
    logger.info(f"[LIBRARY] Returning {len(paginated)} series (page {page}/{pages}, total={total})")

    # Convert SeriesInfo to SeriesListItem, avoiding duplicate 'source' kwarg
    series_items = []
    for s in paginated:
        item_dict = {k: v for k, v in s.__dict__.items() if k != 'source'}
        item_dict['source'] = s.source.value
        series_items.append(SeriesListItem(**item_dict))

    return SeriesListResponse(
        series=series_items,
        source=source,
        total=total,
        page=page,
        pages=pages,
    )


@router.get("/series/{series_name}/books")
async def get_series_books(series_name: str):
    """Get all ABS library books in a specific series."""
    logger.info(f"[LIBRARY] GET /api/library/series/{series_name}/books")

    if not abs_client.is_configured:
        logger.warning(f"[LIBRARY] ABS not configured, returning 503")
        raise HTTPException(503, "ABS not configured")

    logger.info(f"[LIBRARY] Fetching books for series: {series_name}")
    books = await abs_client.get_books_in_series(series_name)
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
):
    """
    Compare series between ABS library and Hardcover.

    Returns categorized books:
    - **present**: In both ABS and Hardcover
    - **missing**: In Hardcover but not ABS
    - **abs_only**: In ABS but not Hardcover
    - **uncertain**: Ambiguous matches needing confirmation
    """
    if not abs_client.is_configured:
        raise HTTPException(503, "ABS not configured")
    if not hardcover_client.is_configured:
        raise HTTPException(503, "Hardcover not configured")

    # Get ABS books
    abs_books_raw = await abs_client.get_books_in_series(series_name)
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
    if abs_client._library_cache and hardcover_books:
        fallback_abs = []
        existing_abs_ids = {b.id for b in abs_books}
        for hc_book in hardcover_books:
            title = hc_book.get("title", "")
            hc_authors = hc_book.get("authors") or hc_book.get("author_names") or []
            author = hc_authors[0] if hc_authors else ""
            match, _score = abs_client._library_cache.find_best_match(title=title, author=author)
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
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Paginated book browser from ABS library cache."""
    logger.info(f"[LIBRARY] GET /api/library/books - q={q!r}, series={series!r}, page={page}, limit={limit}")

    if not abs_client.is_configured:
        logger.warning(f"[LIBRARY] ABS not configured, returning 503")
        raise HTTPException(503, "ABS not configured")

    if not abs_client._library_cache:
        logger.warning(f"[LIBRARY] Library cache not initialized, returning 503")
        raise HTTPException(503, "Library cache not initialized")

    await abs_client._library_cache.ensure_fresh(abs_client.get_library_items)

    # Build query
    from sqlalchemy import text
    from db.db import covers_engine

    conditions = ["library_id = :lib_id"]
    params = {"lib_id": abs_client.config.library_id}

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
async def get_library_item_cover(item_id: str):
    """Proxy ABS item cover to avoid CORS issues."""
    if not abs_client.is_configured:
        raise HTTPException(503, "ABS not configured")

    cover_url = f"{abs_client.config.base_url}/api/items/{item_id}/cover"
    headers = {"Authorization": f"Bearer {abs_client.config.api_key}"}

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
