"""
Search routes for MAM Audiobook Finder.
"""
import asyncio
import logging
import random
import httpx
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from fastapi.responses import JSONResponse

from config import MAM_BASE, MAM_COOKIE, ABS_BASE_URL, ABS_CHECK_LIBRARY
from abs_client import get_abs_client
from dependencies.abs import require_authenticated_user_if_configured
from mam_cache import get_cached_mam_search, cache_mam_search
from dependencies.mam import normalize_mam_result, flatten, detect_format
from utils import normalize_title, normalize_author

router = APIRouter()
logger = logging.getLogger("mam-audiofinder")


@router.post("/search")
async def search(
    payload: dict,
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
    _user: dict | None = Depends(require_authenticated_user_if_configured),
):
    """Search MAM for audiobooks with 5-minute caching."""
    if not MAM_COOKIE:
        raise HTTPException(status_code=500, detail="MAM_COOKIE not set on server")

    tor = payload.get("tor", {}) or {}
    tor.setdefault("text", "")
    tor.setdefault("srchIn", ["title", "author", "narrator"])
    tor.setdefault("searchType", "all")
    tor.setdefault("sortType", "default")
    tor.setdefault("startNumber", "0")
    tor.setdefault("main_cat", ["13"])  # Audiobooks

    # Validate perpage parameter (allowed values: 5, 10, 20, 30, 40, 50, 100)
    ALLOWED_PERPAGE = [5, 10, 20, 30, 40, 50, 100]
    perpage_raw = payload.get("perpage", 20)
    try:
        perpage = int(perpage_raw)
        if perpage not in ALLOWED_PERPAGE:
            perpage = 20  # Default fallback
    except (ValueError, TypeError):
        perpage = 20  # Default fallback
    query_text = tor.get("text", "")
    sort_type = tor.get("sortType", "default")

    # Check cache first
    cached = get_cached_mam_search(query_text, perpage, sort_type)
    if cached:
        logger.info(f"✅ Cache HIT for query='{query_text}', limit={perpage}")
        return cached

    logger.info(f"❌ Cache MISS for query='{query_text}', limit={perpage} - fetching from MAM")
    body = {"tor": tor, "perpage": perpage}

    headers = {
        "Cookie": MAM_COOKIE,
        "Content-Type": "application/json",
        "Accept": "application/json, */*",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.myanonamouse.net",
        "Referer": "https://www.myanonamouse.net/",
    }
    params = {"dlLink": "1"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{MAM_BASE}/tor/js/loadSearchJSONbasic.php",
                                  headers=headers, params=params, json=body)
    except httpx.HTTPError as e:
        logger.error(f"❌ MAM request failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=f"MAM request failed: {e}")

    if r.status_code != 200:
        logger.error(f"❌ MAM HTTP {r.status_code}: {r.text[:300]}")
        raise HTTPException(status_code=502, detail=f"MAM HTTP {r.status_code}: {r.text[:300]}")
    try:
        raw = r.json()
    except ValueError:
        logger.error(f"❌ MAM returned non-JSON: {r.text[:300]}")
        raise HTTPException(status_code=502, detail=f"MAM returned non-JSON. Body: {r.text[:300]}")

    # Normalize all results using shared MAM result normalizer
    out = [normalize_mam_result(item) for item in raw.get("data", [])]

    # Check which items exist in ABS library (if feature enabled and token available)
    if ABS_CHECK_LIBRARY and out and x_abs_token:
        try:
            # Create token-authenticated client
            client = get_abs_client(user_token=x_abs_token)

            # Extract (title, author) pairs from results
            items_to_check = [(result["title"] or "", result["author_info"] or "") for result in out]

            # Call library check
            library_results = await client.check_library_items(items_to_check)

            # Update results with library status
            for result in out:
                cache_key = f"{normalize_title(result.get('title') or '')}||{normalize_author(result.get('author_info') or '')}"
                result["in_abs_library"] = library_results.get(cache_key, False)

            logger.info(f"📚 Library check: {sum(r['in_abs_library'] for r in out)}/{len(out)} items found in ABS")
        except Exception as e:
            logger.error(f"❌ Library check failed: {e}")
            # Continue with in_abs_library=False on error

    # NOTE: We no longer fetch covers during search to avoid blocking.
    # Covers are fetched progressively via the /api/covers/fetch endpoint.
    logger.info(f"✅ Returning {len(out)} search results (covers will load progressively)")

    response_data = {
        "results": out,
        "total": raw.get("total"),
        "total_found": raw.get("total_found"),
    }

    # Cache the result for 5 minutes
    cache_mam_search(query_text, perpage, response_data, sort_type)

    return JSONResponse(response_data)


@router.get("/api/covers/fetch")
async def fetch_cover(
    mam_id: str = Query(..., description="MAM torrent ID"),
    title: str = Query("", description="Book title"),
    author: str = Query("", description="Book author"),
    max_retries: int = Query(2, description="Maximum number of retries"),
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token"),
    _user: dict | None = Depends(require_authenticated_user_if_configured),
):
    """
    Fetch cover for a specific MAM ID with retry logic.
    Returns immediately with cover URL or error.
    """
    if not ABS_BASE_URL:
        return JSONResponse({
            "mam_id": mam_id,
            "cover_url": None,
            "item_id": None,
            "error": "ABS not configured"
        })

    if not title:
        return JSONResponse({
            "mam_id": mam_id,
            "cover_url": None,
            "item_id": None,
            "error": "No title provided"
        })

    if not x_abs_token:
        return JSONResponse({
            "mam_id": mam_id,
            "cover_url": None,
            "item_id": None,
            "error": "Authentication required for cover fetching"
        })

    # Create token-authenticated client
    client = get_abs_client(user_token=x_abs_token)

    # Retry logic with exponential backoff and jitter
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                # Exponential backoff with jitter: base delay * 2^(attempt-1) + random jitter
                base_delay = 0.5 * (2 ** (attempt - 1))
                jitter = random.random() * (base_delay * 0.5)
                wait_time = base_delay + jitter
                logger.info(f"🔄 Retry {attempt}/{max_retries} for '{title}' after {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

            result = await client.fetch_cover(title, author, mam_id)

            if result and result.get("cover_url"):
                logger.info(f"✅ Cover fetch succeeded for '{title}' on attempt {attempt + 1}")
                response = {
                    "mam_id": mam_id,
                    "cover_url": result.get("cover_url"),
                    "item_id": result.get("item_id"),
                    "error": None
                }
                # Include description and metadata if available
                if result.get("description"):
                    response["description"] = result.get("description")
                if result.get("metadata"):
                    response["metadata"] = result.get("metadata")
                return JSONResponse(response)
            else:
                # No cover found, but not an error - don't retry
                logger.info(f"ℹ️  No cover found for '{title}'")
                return JSONResponse({
                    "mam_id": mam_id,
                    "cover_url": None,
                    "item_id": None,
                    "error": "No cover found"
                })

        except httpx.ReadTimeout as e:
            last_error = f"Timeout: {e}"
            logger.warning(f"⏱️  Timeout fetching cover for '{title}' (attempt {attempt + 1}/{max_retries + 1})")
            continue
        except httpx.ConnectTimeout as e:
            last_error = f"Connection timeout: {e}"
            logger.warning(f"⏱️  Connection timeout for '{title}' (attempt {attempt + 1}/{max_retries + 1})")
            continue
        except httpx.HTTPError as e:
            last_error = f"HTTP error: {e}"
            logger.warning(f"❌ HTTP error fetching cover for '{title}': {e}")
            continue
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.error(f"❌ Unexpected error fetching cover for '{title}': {e}")
            continue

    # All retries exhausted
    logger.error(f"❌ All {max_retries + 1} attempts failed for '{title}': {last_error}")
    return JSONResponse({
        "mam_id": mam_id,
        "cover_url": None,
        "item_id": None,
        "error": last_error
    })
