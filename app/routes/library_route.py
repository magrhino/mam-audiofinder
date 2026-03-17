"""Library browsing and series diff endpoints."""

import asyncio
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

from sqlalchemy import bindparam, text

from abs_client import get_abs_client
from dependencies.abs import (
    require_admin_if_configured,
    require_authenticated_user_if_configured,
)
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
    # New fields for UI enhancement
    hardcover_link_confidence: float = 0.0
    hardcover_series_name: Optional[str] = None
    missing_count: int = 0
    completion_percentage: int = 100


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


class SeriesLinkRequest(BaseModel):
    """Request to link a series to a Hardcover series."""
    hardcover_series_id: int
    hardcover_series_name: Optional[str] = None
    hardcover_author_name: Optional[str] = None
    hardcover_book_count: Optional[int] = None
    confidence: float = 1.0  # 1.0 = manual override


class SeriesLinkResponse(BaseModel):
    """Response after linking a series."""
    success: bool
    series_name: str
    hardcover_series_id: int
    hardcover_series_name: Optional[str] = None
    link_confidence: float
    linked_by: str


# ============================================================================
# Background Auto-Link Helper
# ============================================================================

async def _background_auto_link(unlinked_series: List[dict]):
    """Background task to auto-link series to Hardcover.

    Searches Hardcover for each unlinked series and persists the link.
    Rate-limited to avoid hammering the Hardcover API.
    """
    from sqlalchemy import text
    from db.db import covers_engine

    for s in unlinked_series:
        name = s["name"]
        name_norm = s["name_normalized"]

        try:
            # Search Hardcover for this series
            hc_results = await hardcover_client.search_series(title=name, limit=1)
            if not hc_results:
                logger.debug(f"🔍 No Hardcover match for '{name}'")
                continue

            best = hc_results[0]
            hc_series_id = best["series_id"]
            hc_series_name = best["series_name"]
            hc_author = best.get("author_name", "")
            hc_book_count = best.get("book_count", 0)

            # Persist link
            with covers_engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO series_hardcover_link
                    (series_name, series_name_normalized, library_id,
                     hardcover_series_id, hardcover_series_name, hardcover_author_name,
                     hardcover_book_count, link_confidence, linked_by)
                    VALUES (:name, :name_norm, NULL, :hc_id, :hc_name, :hc_author,
                            :hc_count, 0.7, 'auto')
                    ON CONFLICT(series_name_normalized, library_id) DO NOTHING
                """), {
                    "name": name,
                    "name_norm": name_norm,
                    "hc_id": hc_series_id,
                    "hc_name": hc_series_name,
                    "hc_author": hc_author,
                    "hc_count": hc_book_count,
                })
            logger.info(f"🔗 Background auto-linked '{name}' → HC ID {hc_series_id} ({hc_book_count} books)")
        except Exception as e:
            logger.warning(f"Failed to auto-link '{name}': {e}")

        # Rate limit to avoid hammering Hardcover API
        await asyncio.sleep(0.5)


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
    _user: dict | None = Depends(require_authenticated_user_if_configured),
):
    """
    List series from ABS library.

    Returns series from your Audiobookshelf library, optionally filtered by
    search query or specific library ID. Includes Hardcover linking status
    and missing book counts when available.
    """
    from sqlalchemy import text
    from db.db import covers_engine

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

    # Fetch all Hardcover links for efficient lookup
    hardcover_links = {}
    try:
        with covers_engine.connect() as conn:
            stmt = text("""
                SELECT series_name_normalized, hardcover_series_id, hardcover_series_name,
                       hardcover_book_count, link_confidence, linked_by
                FROM series_hardcover_link
                WHERE library_id IS NULL OR library_id IN :library_ids
            """).bindparams(bindparam("library_ids", expanding=True))
            rows = conn.execute(stmt, {"library_ids": library_ids}).fetchall()

            for row in rows:
                hardcover_links[row.series_name_normalized] = {
                    'hardcover_series_id': row.hardcover_series_id,
                    'hardcover_series_name': row.hardcover_series_name,
                    'hardcover_book_count': row.hardcover_book_count or 0,
                    'link_confidence': row.link_confidence or 0.0,
                    'linked_by': row.linked_by,
                }
            logger.info(f"[LIBRARY] Loaded {len(hardcover_links)} Hardcover links")
    except Exception as e:
        logger.warning(f"[LIBRARY] Failed to load Hardcover links: {e}")

    for s in abs_series:
        name = s.get("name", "")
        author = s.get("author")
        book_count = s.get("book_count", 0)
        name_norm = normalize_series_name(name)

        # Look up Hardcover link
        link = hardcover_links.get(name_norm, {})
        hc_series_id = link.get('hardcover_series_id')
        hc_series_name = link.get('hardcover_series_name')
        hc_book_count = link.get('hardcover_book_count', 0)
        link_confidence = link.get('link_confidence', 0.0)

        # Calculate missing count and completion percentage
        series_book_count = hc_book_count if hc_book_count > 0 else book_count
        missing_count = max(0, series_book_count - book_count)
        completion_pct = int((book_count / series_book_count * 100)) if series_book_count > 0 else 100

        results.append(SeriesInfo(
            id=generate_series_id(name, author or ""),
            name=name,
            name_normalized=name_norm,
            author=author,
            book_count=book_count,
            abs_book_count=book_count,
            series_book_count=series_book_count,
            source=SeriesSource.ABS,
            hardcover_series_id=hc_series_id,
        ))

        # Store extra fields for later conversion
        results[-1]._extra = {
            'hardcover_link_confidence': link_confidence,
            'hardcover_series_name': hc_series_name,
            'missing_count': missing_count,
            'completion_percentage': completion_pct,
        }

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

    # Convert SeriesInfo to SeriesListItem with extra fields
    series_items = []
    for s in paginated:
        item_dict = {k: v for k, v in s.__dict__.items() if k not in ('source', '_extra')}
        item_dict['source'] = s.source.value

        # Add extra fields from link data
        extra = getattr(s, '_extra', {})
        item_dict['hardcover_link_confidence'] = extra.get('hardcover_link_confidence', 0.0)
        item_dict['hardcover_series_name'] = extra.get('hardcover_series_name')
        item_dict['missing_count'] = extra.get('missing_count', 0)
        item_dict['completion_percentage'] = extra.get('completion_percentage', 100)

        series_items.append(SeriesListItem(**item_dict))

    # Launch background auto-link for unlinked series (if Hardcover is configured)
    if hardcover_client.is_configured:
        unlinked = [
            {"name": s.name, "name_normalized": s.name_normalized}
            for s in results
            if not getattr(s, '_extra', {}).get('hardcover_link_confidence', 0)
        ]
        if unlinked:
            asyncio.create_task(_background_auto_link(unlinked))
            logger.info(f"🚀 Launched background auto-link for {len(unlinked)} unlinked series")

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
    _user: dict | None = Depends(require_authenticated_user_if_configured),
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
    _user: dict | None = Depends(require_authenticated_user_if_configured),
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

            # Auto-link series when found via name search (not when ID was provided)
            if hc_series_id:
                from db.db import covers_engine
                name_norm = normalize_series_name(series_name)
                try:
                    with covers_engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO series_hardcover_link
                            (series_name, series_name_normalized, library_id,
                             hardcover_series_id, hardcover_series_name, hardcover_author_name,
                             hardcover_book_count, link_confidence, linked_by)
                            VALUES (:name, :name_norm, NULL, :hc_id, :hc_name, :hc_author,
                                    :hc_count, 0.8, 'auto')
                            ON CONFLICT(series_name_normalized, library_id) DO NOTHING
                        """), {
                            "name": series_name,
                            "name_norm": name_norm,
                            "hc_id": hc_series_id,
                            "hc_name": hc_series_name,
                            "hc_author": hc_author_name,
                            "hc_count": len(hardcover_books_raw),
                        })
                    logger.info(f"🔗 Auto-linked '{series_name}' to Hardcover ID {hc_series_id}")
                except Exception as e:
                    logger.warning(f"Failed to auto-link series: {e}")

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

    # Include Hardcover metadata in response for frontend linking
    result.hardcover_series_id = hc_series_id
    result.hardcover_series_name = hc_series_name
    result.hardcover_book_count = len(hardcover_books)

    return result


@router.get("/books", response_model=BookListResponse)
async def list_books(
    q: Optional[str] = Query(None, description="Search title/author"),
    series: Optional[str] = Query(None, description="Filter by series name"),
    library_id: Optional[str] = Query(None, description="Filter by specific library ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
    _user: dict | None = Depends(require_authenticated_user_if_configured),
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
async def add_to_wishlist(
    request: WishlistAddRequest,
    _user: dict | None = Depends(require_authenticated_user_if_configured),
):
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
    _user: dict | None = Depends(require_authenticated_user_if_configured),
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


@router.post("/series/{series_name}/link", response_model=SeriesLinkResponse)
async def link_series_to_hardcover(
    series_name: str,
    request: SeriesLinkRequest,
    library_id: Optional[str] = Query(None, description="Scope link to specific library"),
    _admin: dict | None = Depends(require_admin_if_configured),
):
    """
    Link a library series to a specific Hardcover series.

    This creates a persistent mapping that will be used for future diff operations,
    avoiding repeated searches. Manual links (confidence=1.0) take precedence over
    auto-links.
    """
    from sqlalchemy import text
    from db.db import covers_engine

    name_normalized = normalize_series_name(series_name)
    linked_by = "manual" if request.confidence >= 1.0 else "auto"

    with covers_engine.begin() as conn:
        # Upsert the link
        conn.execute(text("""
            INSERT INTO series_hardcover_link
            (series_name, series_name_normalized, library_id, hardcover_series_id,
             hardcover_series_name, hardcover_author_name, hardcover_book_count,
             link_confidence, linked_by)
            VALUES (:name, :name_norm, :lib_id, :hc_id, :hc_name, :hc_author, :hc_count, :conf, :by)
            ON CONFLICT(series_name_normalized, library_id)
            DO UPDATE SET
                hardcover_series_id = :hc_id,
                hardcover_series_name = :hc_name,
                hardcover_author_name = :hc_author,
                hardcover_book_count = :hc_count,
                link_confidence = :conf,
                linked_by = :by,
                linked_at = datetime('now')
        """), {
            "name": series_name,
            "name_norm": name_normalized,
            "lib_id": library_id,
            "hc_id": request.hardcover_series_id,
            "hc_name": request.hardcover_series_name,
            "hc_author": request.hardcover_author_name,
            "hc_count": request.hardcover_book_count,
            "conf": request.confidence,
            "by": linked_by,
        })

    logger.info(f"🔗 Linked series '{series_name}' to Hardcover ID {request.hardcover_series_id} ({linked_by})")

    return SeriesLinkResponse(
        success=True,
        series_name=series_name,
        hardcover_series_id=request.hardcover_series_id,
        hardcover_series_name=request.hardcover_series_name,
        link_confidence=request.confidence,
        linked_by=linked_by,
    )


@router.delete("/series/{series_name}/link")
async def unlink_series(
    series_name: str,
    library_id: Optional[str] = Query(None, description="Scope to specific library"),
    _admin: dict | None = Depends(require_admin_if_configured),
):
    """Remove the Hardcover link for a series."""
    from sqlalchemy import text
    from db.db import covers_engine

    name_normalized = normalize_series_name(series_name)

    with covers_engine.begin() as conn:
        if library_id:
            result = conn.execute(text("""
                DELETE FROM series_hardcover_link
                WHERE series_name_normalized = :name_norm AND library_id = :lib_id
            """), {"name_norm": name_normalized, "lib_id": library_id})
        else:
            result = conn.execute(text("""
                DELETE FROM series_hardcover_link
                WHERE series_name_normalized = :name_norm AND library_id IS NULL
            """), {"name_norm": name_normalized})

    deleted = result.rowcount > 0
    logger.info(f"🔗 Unlinked series '{series_name}' (deleted={deleted})")

    return {"success": deleted, "series_name": series_name}


@router.get("/series/{series_name}/link")
async def get_series_link(
    series_name: str,
    library_id: Optional[str] = Query(None, description="Scope to specific library"),
    _user: dict | None = Depends(require_authenticated_user_if_configured),
):
    """Get the current Hardcover link for a series."""
    from sqlalchemy import text
    from db.db import covers_engine

    name_normalized = normalize_series_name(series_name)

    with covers_engine.connect() as conn:
        # Try library-specific first, then global
        row = conn.execute(text("""
            SELECT * FROM series_hardcover_link
            WHERE series_name_normalized = :name_norm
              AND (library_id = :lib_id OR library_id IS NULL)
            ORDER BY library_id DESC NULLS LAST
            LIMIT 1
        """), {"name_norm": name_normalized, "lib_id": library_id}).fetchone()

    if not row:
        return {"linked": False, "series_name": series_name}

    return {
        "linked": True,
        "series_name": row.series_name,
        "hardcover_series_id": row.hardcover_series_id,
        "hardcover_series_name": row.hardcover_series_name,
        "hardcover_author_name": row.hardcover_author_name,
        "hardcover_book_count": row.hardcover_book_count,
        "link_confidence": row.link_confidence,
        "linked_by": row.linked_by,
        "linked_at": row.linked_at,
    }


@router.get("/cover/{item_id}")
async def get_library_item_cover(
    item_id: str,
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
    _user: dict | None = Depends(require_authenticated_user_if_configured),
):
    """Proxy ABS item cover to avoid CORS issues.

    Requires ABS auth via X-ABS-Token header.
    """
    if not ABS_BASE_URL or not x_abs_token:
        raise HTTPException(503, "ABS not configured or missing token")

    cover_url = f"{ABS_BASE_URL}/api/items/{item_id}/cover"
    headers = {"Authorization": f"Bearer {x_abs_token}"}

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
