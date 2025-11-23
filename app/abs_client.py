"""
Audiobookshelf API client for MAM Audiobook Finder.
Handles API communication with Audiobookshelf server.
"""
import logging
import httpx
import time
import asyncio
import json
from typing import Optional, List, Tuple, Dict

from config import ABS_BASE_URL, ABS_API_KEY, ABS_LIBRARY_ID, ABS_VERIFY_TIMEOUT, ABS_LIBRARY_CACHE_TTL
from covers import cover_service

logger = logging.getLogger("mam-audiofinder")


class AudiobookshelfClient:
    """Client for interacting with Audiobookshelf API."""

    # Shared HTTP client for connection pooling (class-level)
    _shared_client: Optional[httpx.AsyncClient] = None
    # Semaphore to limit concurrent requests to ABS (max 10 concurrent)
    _request_semaphore: Optional[asyncio.Semaphore] = None

    def __init__(self):
        """Initialize Audiobookshelf client."""
        self.base_url = ABS_BASE_URL
        self.api_key = ABS_API_KEY
        self.library_id = ABS_LIBRARY_ID
        # In-memory cache for library items: {cache_key: (result, timestamp)}
        self._library_cache: Dict[str, Tuple[bool, float]] = {}
        self._library_items_cache: Optional[Tuple[List[dict], float]] = None
        # In-memory cache for item metadata: {item_id: (metadata_dict, timestamp)}
        self._metadata_cache: Dict[str, Tuple[dict, float]] = {}

        # Initialize shared client and semaphore if not already done
        if AudiobookshelfClient._shared_client is None:
            AudiobookshelfClient._shared_client = httpx.AsyncClient(
                timeout=8.0,  # Reduced from 30s to fail fast and free semaphore slots
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
            )
            logger.info("🔧 Initialized shared HTTP client for ABS requests (8s timeout)")

        if AudiobookshelfClient._request_semaphore is None:
            AudiobookshelfClient._request_semaphore = asyncio.Semaphore(10)
            logger.info("🔧 Initialized request semaphore (max 10 concurrent ABS requests)")

    @property
    def is_configured(self) -> bool:
        """Check if Audiobookshelf is configured."""
        return bool(self.base_url and self.api_key)

    async def test_connection(self) -> bool:
        """Test Audiobookshelf API connectivity."""
        if not self.is_configured:
            logger.info("ℹ️  Audiobookshelf integration not configured (skipping connectivity test)")
            return False

        try:
            logger.info(f"🔍 Testing Audiobookshelf API connection to {self.base_url}...")
            headers = {"Authorization": f"Bearer {self.api_key}"}

            r = await self._shared_client.get(f"{self.base_url}/api/me", headers=headers)

            if r.status_code == 200:
                data = r.json()
                username = data.get("username", "unknown")
                logger.info(f"✅ Audiobookshelf API connected successfully (user: {username})")
                return True
            else:
                logger.error(f"❌ Audiobookshelf API test failed: HTTP {r.status_code}")
                logger.error(f"   Response: {r.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"❌ Audiobookshelf API test failed with exception: {e}")
            return False

    async def check_library_items(self, items: List[Tuple[str, str]]) -> Dict[str, bool]:
        """
        Check which items exist in the Audiobookshelf library.

        Args:
            items: List of (title, author) tuples to check

        Returns:
            Dict mapping "{title}||{author}" to boolean (True if in library, False otherwise)

        Uses in-memory caching with TTL to reduce API calls.
        """
        if not self.is_configured or not self.library_id:
            logger.debug("📚 ABS not fully configured, skipping library check")
            # Return all False if not configured
            return {f"{title}||{author}": False for title, author in items}

        if not items:
            return {}

        logger.info(f"📚 Checking {len(items)} items against ABS library")

        # Fetch library items with caching
        try:
            library_items = await self._get_cached_library_items()
        except Exception as e:
            logger.error(f"❌ Failed to fetch library items: {e}")
            # Return all False on error
            return {f"{title}||{author}": False for title, author in items}

        # Check each item against library
        results = {}
        for title, author in items:
            cache_key = f"{title.lower().strip()}||{author.lower().strip()}"

            # Check cache first
            if cache_key in self._library_cache:
                cached_result, cached_time = self._library_cache[cache_key]
                if time.time() - cached_time < ABS_LIBRARY_CACHE_TTL:
                    results[cache_key] = cached_result
                    continue

            # Check if item exists in library
            in_library = self._match_library_item(title, author, library_items)

            # Cache the result
            self._library_cache[cache_key] = (in_library, time.time())
            results[cache_key] = in_library

        logger.info(f"✅ Library check complete: {sum(results.values())}/{len(results)} items found in library")
        return results

    async def _get_cached_library_items(self) -> List[dict]:
        """
        Fetch library items from ABS with caching.
        Cache is invalidated after ABS_LIBRARY_CACHE_TTL seconds.
        """
        current_time = time.time()

        # Check if cache is valid
        if self._library_items_cache:
            cached_items, cached_time = self._library_items_cache
            if current_time - cached_time < ABS_LIBRARY_CACHE_TTL:
                logger.debug(f"📦 Using cached library items ({len(cached_items)} items)")
                return cached_items

        # Fetch fresh data
        logger.info(f"🌐 Fetching library items from ABS")
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=ABS_VERIFY_TIMEOUT) as client:
            r = await client.get(
                f"{self.base_url}/api/libraries/{self.library_id}/items",
                headers=headers,
                params={"limit": 1000, "minified": "1"}  # Minified for performance
            )

            if r.status_code != 200:
                logger.warning(f"⚠️  Library fetch failed: HTTP {r.status_code}")
                raise Exception(f"HTTP {r.status_code}")

            data = r.json()
            items = data.get("results", [])

            # Cache the results
            self._library_items_cache = (items, current_time)
            logger.info(f"📦 Cached {len(items)} library items")

            return items

    def _match_library_item(self, title: str, author: str, library_items: List[dict]) -> bool:
        """
        Check if a title/author pair matches any item in the library.
        Uses fuzzy matching similar to verify_import logic.

        Args:
            title: Book title to search for
            author: Author name to search for
            library_items: List of library items from ABS API

        Returns:
            True if a match is found, False otherwise
        """
        if not title:
            return False

        title_lower = title.lower().strip()
        author_lower = author.lower().strip() if author else ""

        for item in library_items:
            item_metadata = item.get("media", {}).get("metadata", {})
            item_title = (item_metadata.get("title") or "").lower().strip()
            item_author = (item_metadata.get("authorName") or "").lower().strip()

            # Calculate match score
            score = 0
            title_match = False

            # Exact title match
            if item_title == title_lower:
                score += 100
                title_match = True
            # Title contains or is contained
            elif title_lower in item_title or item_title in title_lower:
                score += 50
                title_match = True

            if not title_match:
                continue

            # Author matching
            if author_lower:
                if item_author == author_lower:
                    score += 50
                elif author_lower in item_author or item_author in author_lower:
                    score += 25
            else:
                # No author to verify, count as match
                score += 10

            # Accept matches with score >= 50 (at least partial title match)
            if score >= 50:
                logger.debug(f"✓ Match found: '{item_title}' by '{item_author}' (score: {score})")
                return True

        return False

    async def fetch_cover(self, title: str, author: str = "", mam_id: str = "", force_refresh: bool = False) -> dict:
        """
        Fetch cover image URL from Audiobookshelf.
        Returns dict with 'cover_url' and 'item_id' if found, else empty dict.
        Checks cache first if mam_id is provided.
        """
        logger.info(f"🔍 Fetching cover for: '{title}' by '{author}' (MAM ID: {mam_id or 'N/A'})")

        # Check cache first
        if mam_id and not force_refresh:
            cached = cover_service.get_cached_cover(mam_id)
            if cached:
                if cached.get("needs_heal") and cached.get("source_cover_url"):
                    logger.info(f"🩹 Healing missing cover file for MAM ID {mam_id}")
                    await cover_service.save_cover_to_cache(
                        mam_id,
                        cached.get("source_cover_url"),
                        cached.get("title") or title,
                        cached.get("author") or author,
                        cached.get("item_id")
                    )
                    healed = cover_service.get_cached_cover(mam_id)
                    if healed:
                        cached = healed
                if cached.get("cover_url"):
                    return cached

        if not self.is_configured:
            logger.warning(f"⚠️  ABS not configured, skipping cover fetch for '{title}'")
            return {}

        if not title:
            logger.warning(f"⚠️  No title provided, skipping cover fetch")
            return {}

        # Use semaphore to limit concurrent requests to ABS
        async with self._request_semaphore:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                params = {"title": title}
                if author:
                    params["author"] = author

                logger.info(f"🌐 Calling ABS /api/search/covers with params: {params}")

                # Use shared client instead of creating new one
                # Try the search/covers endpoint first
                r = await self._shared_client.get(
                    f"{self.base_url}/api/search/covers",
                    headers=headers,
                    params=params,
                    timeout=8.0  # Per-request timeout for cover fetching
                )

                logger.info(f"📡 ABS /api/search/covers response: HTTP {r.status_code}")

                if r.status_code == 200:
                    data = r.json()
                    results = data.get("results", [])
                    logger.info(f"📊 Got {len(results)} results from /api/search/covers")

                    if results and len(results) > 0:
                        # Take the first result
                        first_result = results[0]
                        cover_url = None
                        if isinstance(first_result, str):
                            # It's just a URL
                            cover_url = first_result
                            logger.info(f"✅ Found cover URL (string): {cover_url}")
                        elif isinstance(first_result, dict):
                            # It might have more structure
                            cover_url = first_result.get("cover") or first_result.get("url") or str(first_result)
                            logger.info(f"✅ Found cover URL (dict): {cover_url}")

                        if cover_url:
                            # Cache the result if we have a MAM ID
                            if mam_id:
                                await cover_service.save_cover_to_cache(mam_id, cover_url, title, author, None)
                                # Get the potentially updated cover URL (local path)
                                cached = cover_service.get_cached_cover(mam_id)
                                if cached:
                                    return cached
                            return {"cover_url": cover_url, "item_id": None}
                    else:
                        logger.warning(f"⚠️  No results from /api/search/covers")
                else:
                    logger.warning(f"⚠️  /api/search/covers failed: {r.text[:200]}")

                # If no results from search/covers, try searching library items
                if self.library_id:
                    logger.info(f"🔍 Trying library search with ID: {self.library_id}")
                    # Search within library using filter (using shared client)
                    r = await self._shared_client.get(
                        f"{self.base_url}/api/libraries/{self.library_id}/items",
                        headers=headers,
                        params={"limit": 5, "minified": "1"},
                        timeout=8.0  # Per-request timeout for library search
                    )

                    logger.info(f"📡 ABS library items response: HTTP {r.status_code}")

                    if r.status_code == 200:
                        data = r.json()
                        results = data.get("results", [])
                        logger.info(f"📊 Got {len(results)} items from library")

                        # Simple title matching (case-insensitive)
                        title_lower = title.lower()
                        for item in results:
                            item_title = (item.get("media", {}).get("metadata", {}).get("title") or "").lower()
                            if title_lower in item_title or item_title in title_lower:
                                item_id = item.get("id")
                                if item_id:
                                    # Build cover URL
                                    cover_url = f"{self.base_url}/api/items/{item_id}/cover"
                                    logger.info(f"✅ Found cover in library: {cover_url}")

                                    # Fetch full item metadata (including description)
                                    item_details = await self.fetch_item_details(item_id)
                                    description = item_details.get("description", "") if item_details else ""
                                    metadata_json = item_details.get("metadata", {}) if item_details else {}

                                    # Cache the result if we have a MAM ID
                                    if mam_id:
                                        await cover_service.save_cover_to_cache(
                                            mam_id, cover_url, title, author, item_id,
                                            description=description,
                                            metadata_json=metadata_json
                                        )
                                        # Get the potentially updated cover URL (local path)
                                        cached = cover_service.get_cached_cover(mam_id)
                                        if cached:
                                            return cached

                                    result = {"cover_url": cover_url, "item_id": item_id}
                                    if description:
                                        result["description"] = description
                                    if metadata_json:
                                        result["metadata"] = metadata_json
                                    return result
                        logger.warning(f"⚠️  No matching items in library for '{title}'")
                    else:
                        logger.warning(f"⚠️  Library search failed: {r.text[:200]}")
                else:
                    logger.info(f"ℹ️  No ABS_LIBRARY_ID configured, skipping library search")

                logger.warning(f"❌ No cover found for '{title}'")
                return {}

            except Exception as e:
                # Don't fail the whole request if ABS is down
                logger.error(f"❌ Audiobookshelf cover fetch failed for '{title}': {type(e).__name__}: {e}")
                return {}

    async def verify_import(self, title: str, author: str = "", library_path: str = "", metadata: dict = None) -> dict:
        """
        Verify that an imported item exists in Audiobookshelf library.

        Args:
            title: Book title (from torrent or metadata.json)
            author: Author name (from torrent or metadata.json)
            library_path: Path where book was imported
            metadata: Optional dict from metadata.json with enhanced matching data

        Returns dict with:
            - status: 'verified', 'mismatch', 'not_found', 'unreachable', or 'not_configured'
            - note: Diagnostic message explaining the status
            - abs_item_id: ABS item ID if found, else None

        Implements retry logic with exponential backoff (max 3 attempts).
        """
        logger.info(f"🔍 Verifying import in ABS: '{title}' by '{author}' at '{library_path}'")

        # Check if ABS is configured
        if not self.is_configured:
            logger.info("ℹ️  Audiobookshelf not configured, skipping verification")
            return {
                "status": "not_configured",
                "note": "ABS integration not configured",
                "abs_item_id": None
            }

        if not self.library_id:
            logger.warning("⚠️  ABS_LIBRARY_ID not configured, cannot verify import")
            return {
                "status": "not_configured",
                "note": "ABS_LIBRARY_ID not configured",
                "abs_item_id": None
            }

        if not title:
            logger.warning("⚠️  No title provided for verification")
            return {
                "status": "not_found",
                "note": "No title provided",
                "abs_item_id": None
            }

        # Retry logic with exponential backoff (max 3 attempts)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}

                logger.info(f"🌐 Calling ABS /api/libraries/{self.library_id}/items (attempt {attempt}/{max_attempts})")

                async with httpx.AsyncClient(timeout=ABS_VERIFY_TIMEOUT) as client:
                    # Search library items - use large limit to get all items
                    r = await client.get(
                        f"{self.base_url}/api/libraries/{self.library_id}/items",
                        headers=headers,
                        params={"limit": 1000, "minified": "0"}  # Get full metadata for comparison
                    )

                    logger.info(f"📡 ABS library items response: HTTP {r.status_code}")

                    if r.status_code != 200:
                        logger.warning(f"⚠️  Library search failed: {r.text[:200]}")
                        # If this is the last attempt, return unreachable
                        if attempt == max_attempts:
                            return {
                                "status": "unreachable",
                                "note": f"ABS API returned HTTP {r.status_code}",
                                "abs_item_id": None
                            }
                        # Otherwise, retry with exponential backoff
                        import asyncio
                        wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s
                        logger.info(f"⏳ Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    data = r.json()
                    results = data.get("results", [])
                    logger.info(f"📊 Got {len(results)} items from library")

                    # Search for matching items
                    title_lower = title.lower().strip()
                    author_lower = author.lower().strip() if author else ""

                    # Enhanced matching with metadata.json
                    metadata_authors = []
                    metadata_asin = None
                    metadata_isbn = None
                    if metadata:
                        metadata_authors = [a.lower().strip() for a in metadata.get("authors", []) if a]
                        metadata_asin = metadata.get("asin", "")
                        metadata_isbn = metadata.get("isbn", "")

                    best_match = None
                    best_match_score = 0

                    for item in results:
                        item_metadata = item.get("media", {}).get("metadata", {})
                        item_title = (item_metadata.get("title") or "").lower().strip()
                        item_author = (item_metadata.get("authorName") or "").lower().strip()
                        item_asin = (item_metadata.get("asin") or "").lower().strip()
                        item_isbn = (item_metadata.get("isbn") or "").lower().strip()
                        item_id = item.get("id")
                        item_path = item.get("path", "")

                        # Calculate match score
                        score = 0
                        title_match = False
                        author_match = False

                        # ASIN/ISBN matching (highest priority - exact identifier match)
                        if metadata_asin and item_asin and metadata_asin.lower() == item_asin:
                            score += 200  # Very high score for ASIN match
                            title_match = True
                            author_match = True
                            logger.info(f"🎯 ASIN match found: {metadata_asin}")
                        elif metadata_isbn and item_isbn and metadata_isbn.lower() == item_isbn:
                            score += 200  # Very high score for ISBN match
                            title_match = True
                            author_match = True
                            logger.info(f"🎯 ISBN match found: {metadata_isbn}")
                        else:
                            # Exact title match
                            if item_title == title_lower:
                                score += 100
                                title_match = True
                            # Title contains or is contained
                            elif title_lower in item_title or item_title in title_lower:
                                score += 50
                                title_match = True

                            # Author matching with metadata.json support
                            if metadata_authors:
                                # Check if any metadata author matches item author
                                for meta_author in metadata_authors:
                                    if meta_author == item_author:
                                        score += 50
                                        author_match = True
                                        break
                                    elif meta_author in item_author or item_author in meta_author:
                                        score += 25
                                        author_match = True
                                        break
                            elif author_lower:
                                # Fallback to simple author matching
                                if item_author == author_lower:
                                    score += 50
                                    author_match = True
                                elif author_lower in item_author or item_author in author_lower:
                                    score += 25
                                    author_match = True
                            else:
                                # No author to verify, count as match
                                author_match = True
                                score += 10

                            # Path matching (if provided)
                            if library_path and item_path:
                                # Normalize paths for comparison
                                lib_path_norm = library_path.lower().replace("\\", "/").strip("/")
                                item_path_norm = item_path.lower().replace("\\", "/").strip("/")
                                if lib_path_norm in item_path_norm or item_path_norm in lib_path_norm:
                                    score += 25

                        # Update best match if this is better
                        if score > best_match_score and title_match:
                            best_match_score = score
                            best_match = {
                                "item_id": item_id,
                                "title": item_metadata.get("title"),
                                "author": item_metadata.get("authorName"),
                                "path": item_path,
                                "title_match": title_match,
                                "author_match": author_match,
                                "score": score
                            }

                    # Evaluate best match
                    if not best_match:
                        logger.warning(f"❌ No matching item found in ABS for '{title}'")
                        return {
                            "status": "not_found",
                            "note": f"Not found in library",
                            "abs_item_id": None
                        }

                    # Check for mismatches - adjusted thresholds for ASIN/ISBN matches
                    if best_match_score >= 200:
                        # ASIN/ISBN match - highest confidence
                        logger.info(f"✅ Import verified in ABS via ASIN/ISBN: '{best_match['title']}' by '{best_match['author']}' (ID: {best_match['item_id']})")

                        # Fetch and save description/metadata for verified import
                        await self._update_description_after_verification(best_match["item_id"], title, author)

                        return {
                            "status": "verified",
                            "note": f"ASIN/ISBN match: '{best_match['title']}' by '{best_match['author']}'",
                            "abs_item_id": best_match["item_id"]
                        }
                    elif best_match_score >= 100:
                        # Perfect title + author match
                        logger.info(f"✅ Import verified in ABS: '{best_match['title']}' by '{best_match['author']}' (ID: {best_match['item_id']})")

                        # Fetch and save description/metadata for verified import
                        await self._update_description_after_verification(best_match["item_id"], title, author)

                        return {
                            "status": "verified",
                            "note": f"Found in library: '{best_match['title']}' by '{best_match['author']}'",
                            "abs_item_id": best_match["item_id"]
                        }
                    else:
                        # Partial match - report as mismatch with details
                        if not best_match["author_match"] and author:
                            note = f"Author mismatch: expected '{author}' found '{best_match['author']}'"
                        elif best_match_score < 50:
                            note = f"Weak match: '{best_match['title']}' (score: {best_match_score})"
                        else:
                            note = f"Partial match: '{best_match['title']}' by '{best_match['author']}' (score: {best_match_score})"

                        logger.warning(f"⚠️  {note}")
                        return {
                            "status": "mismatch",
                            "note": note,
                            "abs_item_id": best_match["item_id"]
                        }

            except httpx.TimeoutException as e:
                logger.error(f"⏱️  ABS verification timeout (attempt {attempt}/{max_attempts}): {e}")
                if attempt == max_attempts:
                    return {
                        "status": "unreachable",
                        "note": f"Timeout after {max_attempts} attempts",
                        "abs_item_id": None
                    }
                # Retry with exponential backoff
                import asyncio
                wait_time = 2 ** (attempt - 1)
                logger.info(f"⏳ Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            except Exception as e:
                # Don't fail the import if verification errors
                logger.error(f"❌ ABS verification failed (attempt {attempt}/{max_attempts}): {type(e).__name__}: {e}")
                if attempt == max_attempts:
                    return {
                        "status": "unreachable",
                        "note": f"Error: {type(e).__name__}: {str(e)[:100]}",
                        "abs_item_id": None
                    }
                # Retry with exponential backoff
                import asyncio
                wait_time = 2 ** (attempt - 1)
                logger.info(f"⏳ Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

        # Should never reach here, but just in case
        return {
            "status": "unreachable",
            "note": "Unknown error during verification",
            "abs_item_id": None
        }

    async def fetch_item_details(self, item_id: str) -> dict:
        """
        DEPRECATED: This method only works for items already in the ABS library.
        Use _fetch_from_provider() instead for enriched metadata that works with
        non-library items (search results, showcase view).

        Fetch full item metadata from Audiobookshelf.

        Args:
            item_id: ABS item ID to fetch details for

        Returns:
            Dict with full metadata including:
            - description: Book synopsis/description (if available)
            - metadata: Full metadata object from ABS (excluding chapters)
            - item_id: The ABS item ID
            Empty dict {} if fetch fails or item not found.

        Uses in-memory caching with TTL to reduce API calls.

        TODO: Remove after verifying _fetch_from_provider() works correctly in production.
        """
        if not self.is_configured:
            logger.debug("📚 ABS not configured, skipping item details fetch")
            return {}

        if not item_id:
            logger.warning("⚠️  No item_id provided for fetch_item_details")
            return {}

        # Check cache first
        current_time = time.time()
        if item_id in self._metadata_cache:
            cached_metadata, cached_time = self._metadata_cache[item_id]
            if current_time - cached_time < ABS_LIBRARY_CACHE_TTL:
                logger.debug(f"📦 Using cached metadata for item {item_id}")
                return cached_metadata

        logger.info(f"🌐 Fetching item details from ABS for item {item_id}")

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Use shared client with semaphore to limit concurrent requests
            async with self._request_semaphore:
                r = await self._shared_client.get(
                    f"{self.base_url}/api/items/{item_id}",
                    headers=headers,
                    params={"expanded": "1"}  # Get expanded metadata
                )

                logger.info(f"📡 ABS item details response: HTTP {r.status_code}")

                if r.status_code != 200:
                    logger.warning(f"⚠️  Item details fetch failed: HTTP {r.status_code}")
                    return {}

                data = r.json()

                # Extract relevant metadata (exclude chapters to save space)
                media = data.get("media", {})
                metadata = media.get("metadata", {})

                # Build result with description and full metadata
                result = {
                    "item_id": item_id,
                    "description": metadata.get("description", ""),
                    "metadata": {
                        # Core fields
                        "title": metadata.get("title", ""),
                        "subtitle": metadata.get("subtitle", ""),
                        "authors": metadata.get("authors", []),
                        "authorName": metadata.get("authorName", ""),
                        "narratorName": metadata.get("narratorName", ""),
                        "narrators": metadata.get("narrators", []),
                        "series": metadata.get("series", []),
                        "genres": metadata.get("genres", []),
                        "tags": metadata.get("tags", []),
                        "publisher": metadata.get("publisher", ""),
                        "publishedYear": metadata.get("publishedYear", ""),
                        "publishedDate": metadata.get("publishedDate", ""),
                        "language": metadata.get("language", ""),
                        "isbn": metadata.get("isbn", ""),
                        "asin": metadata.get("asin", ""),
                        "description": metadata.get("description", ""),
                        "explicit": metadata.get("explicit", False),
                        "abridged": metadata.get("abridged", False),
                        # Media info (duration, etc.)
                        "duration": media.get("duration"),
                        "size": media.get("size"),
                        "coverPath": media.get("coverPath", ""),
                    }
                }

                # Cache the result
                self._metadata_cache[item_id] = (result, current_time)
                logger.info(f"✅ Fetched and cached metadata for '{metadata.get('title', 'Unknown')}'")

                return result

        except Exception as e:
            logger.error(f"❌ Failed to fetch item details for {item_id}: {type(e).__name__}: {e}")
            return {}

    async def _update_description_after_verification(self, item_id: str, title: str, author: str):
        """
        Fetch description and metadata from ABS after successful import verification.
        Updates both covers cache and history table with description/metadata.

        Args:
            item_id: ABS item ID from verification
            title: Book title for matching history/covers records
            author: Author name for cover cache lookup
        """
        if not item_id:
            logger.debug("⏭️  No item_id provided, skipping description update")
            return

        try:
            logger.info(f"📝 Fetching description for verified import: '{title}' (item_id: {item_id})")

            # Fetch full metadata including description
            item_details = await self.fetch_item_details(item_id)
            if not item_details:
                logger.warning(f"⚠️  Failed to fetch item details for {item_id}, skipping description update")
                return

            description = item_details.get("description", "")
            metadata_json = item_details.get("metadata", {})

            if not description and not metadata_json:
                logger.debug(f"ℹ️  No description or metadata available for item {item_id}")
                return

            # Import here to avoid circular import
            from covers import cover_service
            from db import covers_engine, engine
            from sqlalchemy import text
            from datetime import datetime

            # Update covers cache (search by title/author since we may not have mam_id)
            try:
                with covers_engine.begin() as cx:
                    # Update by abs_item_id if available, otherwise by title/author
                    result = cx.execute(text("""
                        UPDATE covers
                        SET abs_description = :description,
                            abs_metadata = :metadata,
                            abs_metadata_fetched_at = :fetched_at,
                            abs_item_id = :item_id
                        WHERE abs_item_id = :item_id
                           OR (title = :title AND author = :author)
                    """), {
                        "description": description if description else None,
                        "metadata": json.dumps(metadata_json) if metadata_json else None,
                        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "item_id": item_id,
                        "title": title,
                        "author": author
                    })

                    if result.rowcount > 0:
                        logger.info(f"✅ Updated {result.rowcount} cover cache row(s) with description for '{title}'")
                    else:
                        logger.debug(f"ℹ️  No cover cache rows found to update for '{title}'")
            except Exception as e:
                logger.warning(f"⚠️  Failed to update covers cache (non-critical): {e}")

            # Update history table
            try:
                with engine.begin() as cx:
                    result = cx.execute(text("""
                        UPDATE history
                        SET abs_description = :description,
                            abs_metadata = :metadata,
                            abs_description_source = 'post_import',
                            abs_item_id = :item_id
                        WHERE title = :title
                           OR abs_item_id = :item_id
                    """), {
                        "description": description if description else None,
                        "metadata": json.dumps(metadata_json) if metadata_json else None,
                        "item_id": item_id,
                        "title": title
                    })

                    if result.rowcount > 0:
                        logger.info(f"✅ Updated {result.rowcount} history row(s) with description for '{title}'")
                    else:
                        logger.debug(f"ℹ️  No history rows found to update for '{title}'")
            except Exception as e:
                logger.warning(f"⚠️  Failed to update history table (non-critical): {e}")

        except Exception as e:
            # Don't fail verification if description fetch fails
            logger.error(f"❌ Failed to update description after verification: {type(e).__name__}: {e}")

    async def fetch_enhanced_metadata_test(
        self,
        item_id: str = None,
        providers: List[str] = None
    ) -> dict:
        """
        ⚠️  LEGACY TEST METHOD - DO NOT USE IN PRODUCTION

        Test method to fetch enhanced metadata from external providers via /api/search/books.

        This method validates whether the new endpoint provides sufficient data to
        replace the current fetch_item_details() logic.

        Args:
            item_id: ABS library item ID. If None, selects random item.
            providers: List of providers to try (default: ["audible", "google", "openlibrary"])

        Returns:
            Dict with test results:
            {
                "old_metadata": {...},       # Current fetch_item_details() result
                "new_metadata": {...},       # Enhanced provider metadata
                "comparison": {...},         # Field-by-field comparison
                "success": bool,             # Series with sequence found?
                "provider_used": str         # Which provider succeeded
            }
        """
        if not self.is_configured:
            logger.warning("⚠️  ABS not configured for enhanced metadata test")
            return {
                "old_metadata": {},
                "new_metadata": {},
                "comparison": {},
                "success": False,
                "provider_used": None
            }

        # If no item_id, select random item
        if not item_id:
            import random
            items = await self._get_cached_library_items()
            if not items:
                logger.warning("⚠️  No items in library for test")
                return {
                    "old_metadata": {},
                    "new_metadata": {},
                    "comparison": {},
                    "success": False,
                    "provider_used": None
                }

            random_item = random.choice(items)
            item_id = random_item.get("id")
            logger.info(f"📖 Selected random item for test: {item_id}")

        # Get item metadata for title/author
        item_details = await self.fetch_item_details(item_id)
        if not item_details:
            logger.warning(f"⚠️  Could not fetch item details for {item_id}")
            return {
                "old_metadata": {},
                "new_metadata": {},
                "comparison": {},
                "success": False,
                "provider_used": None
            }

        old_metadata = item_details.get("metadata", {})
        title = old_metadata.get("title", "")
        author = old_metadata.get("authorName", "")

        # Default providers
        if not providers:
            providers = ["audible", "google", "openlibrary"]

        logger.info(f"🔍 Testing enhanced metadata for '{title}' by '{author}'")
        logger.info(f"   Providers to try: {', '.join(providers)}")

        # Try each provider until success (series with sequence)
        for provider in providers:
            logger.info(f"   → Trying provider: {provider}")

            try:
                # Fetch enhanced metadata from provider
                enhanced_result = await self._fetch_from_provider(
                    provider=provider,
                    item_id=item_id,
                    title=title,
                    author=author,
                    fallback_title_only=True
                )

                if not enhanced_result:
                    logger.info(f"     ✗ No results from {provider}")
                    continue

                # Check for series with sequence (success criteria)
                series = enhanced_result.get("series", [])
                has_series_sequence = any(
                    s.get("sequence", "").strip().isdigit() if isinstance(s, dict) else False
                    for s in series
                )

                if has_series_sequence:
                    logger.info(f"     ✅ SUCCESS: {provider} returned series with sequence!")

                    return {
                        "old_metadata": old_metadata,
                        "new_metadata": enhanced_result,
                        "comparison": self._compare_metadata(old_metadata, enhanced_result),
                        "success": True,
                        "provider_used": provider
                    }
                else:
                    logger.info(f"     ⚠️  No series sequence from {provider}")

            except Exception as e:
                logger.warning(f"     ✗ Provider {provider} failed: {type(e).__name__}: {e}")
                continue

        # No provider succeeded
        logger.warning(f"⚠️  No provider returned series with sequence")

        return {
            "old_metadata": old_metadata,
            "new_metadata": {},
            "comparison": {},
            "success": False,
            "provider_used": None
        }

    async def _fetch_from_provider(
        self,
        provider: str,
        item_id: str,
        title: str,
        author: str = "",
        fallback_title_only: bool = True
    ) -> dict:
        """
        Fetch enhanced metadata from a specific provider.

        Uses /api/search/books endpoint with provider parameter.

        Args:
            provider: Provider name (audible, google, openlibrary, etc.)
            item_id: ABS library item ID
            title: Book title
            author: Author name (optional)
            fallback_title_only: Use title-only search if author search fails

        Returns:
            Dict with enhanced metadata fields, or empty dict on error
        """
        if not self.is_configured:
            return {}

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Build search parameters
            params = {
                "provider": provider,
                "fallbackTitleOnly": "1" if fallback_title_only else "0",
                "title": title,
                "id": item_id  # Item ID allows provider to enrich with library data
            }

            if author:
                params["author"] = author

            logger.debug(f"🌐 Calling /api/search/books with provider={provider}")

            # Use semaphore to limit concurrent requests
            async with self._request_semaphore:
                r = await self._shared_client.get(
                    f"{self.base_url}/api/search/books",
                    headers=headers,
                    params=params,
                    timeout=6.0  # Per-request timeout: fail fast for slow providers
                )

                logger.debug(f"📡 Provider {provider} response: HTTP {r.status_code}")

                if r.status_code != 200:
                    logger.warning(f"⚠️  Provider {provider} returned HTTP {r.status_code}")
                    return {}

                data = r.json()
                results = data if isinstance(data, list) else data.get("results", [])

                if not results:
                    logger.debug(f"ℹ️  No results from provider {provider}")
                    return {}

                # Take first result (ignoring matchConfidence as per requirements)
                first_result = results[0]

                logger.debug(f"✅ Got result from {provider}: {first_result.get('title', 'Unknown')}")

                return first_result

        except Exception as e:
            logger.error(f"❌ Failed to fetch from provider {provider}: {type(e).__name__}: {e}")
            return {}

    def _compare_metadata(self, old_meta: dict, new_meta: dict) -> dict:
        """
        Compare old and new metadata field by field.

        Returns dict with comparison results:
        {
            "field_name": {
                "old": "value",
                "new": "value",
                "status": "new|enhanced|same|missing"
            }
        }
        """
        comparison = {}

        # Fields to compare (new_field, old_field)
        fields = [
            ("narrator", "narratorName"),
            ("publisher", "publisher"),
            ("series", "series"),
            ("rating", None),
            ("region", None),
            ("language", "language"),
            ("asin", "asin"),
            ("isbn", "isbn"),
            ("description", "description"),
            ("publishedYear", "publishedYear"),
        ]

        for new_field, old_field in fields:
            old_val = old_meta.get(old_field if old_field else new_field, '')
            new_val = new_meta.get(new_field, '')

            # Determine status
            if new_field == "series":
                old_has_seq = any(s.get("sequence", "").strip() for s in (old_val or []))
                new_has_seq = any(s.get("sequence", "").strip() for s in (new_val or []))

                if new_has_seq and not old_has_seq:
                    status = "enhanced"
                elif new_val and not old_val:
                    status = "new"
                elif new_val:
                    status = "same"
                else:
                    status = "missing"
            elif new_field == "description":
                old_len = len(str(old_val)) if old_val else 0
                new_len = len(str(new_val)) if new_val else 0

                if new_len > old_len * 1.5:
                    status = "enhanced"
                elif new_len > 0 and old_len == 0:
                    status = "new"
                elif new_len > 0:
                    status = "same"
                else:
                    status = "missing"
            else:
                if new_val and not old_val:
                    status = "new"
                elif new_val:
                    status = "same"
                else:
                    status = "missing"

            comparison[new_field] = {
                "old": old_val,
                "new": new_val,
                "status": status
            }

        return comparison


# Global instance
abs_client = AudiobookshelfClient()
