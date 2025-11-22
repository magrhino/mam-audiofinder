"""
MAM search client and response normalization dependencies.

Provides:
- flatten: Normalize MAM API response data (handles dicts, lists, JSON strings)
- detect_format: Extract file format from torrent metadata
- mam_search_client: MAM API request builder with validation and error handling
- normalize_mam_result: Shared response transformer (flatten + detect_format)
"""

from typing import Dict, Any, List, Optional
import json
import re
import httpx
from fastapi import HTTPException

from config import MAM_COOKIE


def flatten(v):
    """Normalize MAM API response data (handles dicts, lists, JSON strings)."""
    if isinstance(v, dict):
        return ", ".join(str(x) for x in v.values())
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    return ", ".join(str(x) for x in obj.values())
                if isinstance(obj, list):
                    return ", ".join(str(x) for x in obj)
            except Exception:
                pass
        s = re.sub(r'^\{|\}$', '', s)
        parts = []
        for chunk in s.split(","):
            parts.append(chunk.split(":", 1)[-1])
        parts = [p.strip().strip('"').strip("'") for p in parts if p.strip()]
        return ", ".join(parts)
    return "" if v is None else str(v)


def detect_format(item: dict) -> str:
    """Extract file format from torrent metadata."""
    for key in ("format", "filetype", "container", "encoding", "format_name"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    name = (item.get("title") or item.get("name") or "")
    toks = re.findall(r'(?i)\b(mp3|m4b|flac|aac|ogg|opus|wav|alac|ape|epub|pdf|mobi|azw3|cbz|cbr)\b', name)
    if toks:
        uniq = list(dict.fromkeys(t.upper() for t in toks))
        return "/".join(uniq)
    return ""


async def mam_search_client(
    search_term: str,
    page: int = 1,
    perpage: int = 100,
    cats: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Builds MAM search request with headers, validates parameters, and handles errors.

    Args:
        search_term: Search query string
        page: Page number (default: 1)
        perpage: Results per page (default: 100, max: 100)
        cats: Category IDs to filter (default: [13] for Audiobooks)

    Returns:
        Dictionary containing:
            - data: Raw MAM API response
            - cache_key: Cache key for this request

    Raises:
        HTTPException: 400 for invalid parameters, 502 for MAM API errors
    """
    # Validate parameters
    if perpage > 100:
        raise HTTPException(
            status_code=400,
            detail="perpage cannot exceed 100"
        )

    if not search_term.strip():
        raise HTTPException(
            status_code=400,
            detail="search_term cannot be empty"
        )

    # Default to audiobooks category
    if cats is None:
        cats = [13]

    # Build request
    url = "https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php"
    headers = {
        "Cookie": f"mam_id={MAM_COOKIE}",
        "User-Agent": "MAM Audiobook Finder"
    }
    params = {
        "tor[text]": search_term,
        "tor[srchIn][title]": "true",
        "tor[srchIn][author]": "true",
        "tor[searchType]": "all",
        "tor[searchIn]": "torrents",
        "tor[perpage]": perpage,
        "tor[browseFlagsHideVsShow]": 0,
        "page": page,
    }

    # Add categories
    for cat in cats:
        params[f"tor[cat][]"] = cat

    # Make request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Build cache key
            cache_key = f"mam_search:{search_term}:{page}:{perpage}:{','.join(map(str, cats))}"

            return {
                "data": data,
                "cache_key": cache_key
            }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"MAM API request failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during MAM search: {str(e)}"
        )


def normalize_mam_result(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes MAM search result with flatten + detect_format + id/title extraction.

    Keeps response shape consistent across search/showcase endpoints.

    Args:
        raw_result: Raw result from MAM API

    Returns:
        Normalized result dictionary with:
            - id: MAM torrent ID
            - title: Book title
            - author_info: Author name (flattened)
            - narrator_info: Narrator name (flattened)
            - format: Detected format (MP3, M4B, etc.)
            - ... (other fields from MAM API)
    """
    # Normalize key fields using flatten and detect_format
    normalized = {
        "id": str(raw_result.get("id") or raw_result.get("tid") or ""),
        "title": raw_result.get("title") or raw_result.get("name"),
        "author_info": flatten(raw_result.get("author_info")),
        "narrator_info": flatten(raw_result.get("narrator_info")),
        "format": detect_format(raw_result),
        "size": raw_result.get("size"),
        "seeders": raw_result.get("seeders"),
        "leechers": raw_result.get("leechers"),
        "catname": raw_result.get("catname"),
        "added": raw_result.get("added"),
        "dl": raw_result.get("dl"),
        "in_abs_library": False,  # Will be updated by abs_library_check if enabled
    }

    return normalized
