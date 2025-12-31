"""Async Audiobookshelf client with user token authentication."""

import logging
import asyncio
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
import httpx

from abs.config import AbsConfig
from abs.models import LibraryItem, VerificationResult, CoverResult, LibrarySyncStatus, Library
from abs.library_cache import LibraryCache
from abs.matching import determine_verification_status

if TYPE_CHECKING:
    from covers import CoverService

logger = logging.getLogger("mam-audiofinder")


def _get_cover_service():
    """Lazy import of cover_service to avoid initialization issues."""
    from covers import get_cover_service
    return get_cover_service()


class AbsClient:
    """Async Audiobookshelf client with connection pooling and user token auth.

    Authentication is handled via user tokens passed at runtime, not static API keys.
    Library IDs are managed dynamically via settings, not environment variables.
    """

    _shared_client: Optional[httpx.AsyncClient] = None
    _semaphore: Optional[asyncio.Semaphore] = None

    def __init__(self, config: AbsConfig, user_token: Optional[str] = None):
        """Initialize ABS client.

        Args:
            config: ABS configuration (base_url, timeouts, etc.)
            user_token: User authentication token (from ABS login)
        """
        self.config = config
        self.user_token = user_token
        self._library_caches: Dict[str, LibraryCache] = {}

        if AbsClient._shared_client is None:
            AbsClient._shared_client = httpx.AsyncClient(
                timeout=8.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
            )

        if AbsClient._semaphore is None:
            AbsClient._semaphore = asyncio.Semaphore(10)

    @classmethod
    def from_env(cls, user_token: Optional[str] = None) -> "AbsClient":
        """Create client from environment variables."""
        return cls(AbsConfig.from_env(), user_token=user_token)

    def with_token(self, token: str) -> "AbsClient":
        """Create a new client instance with the given token."""
        return AbsClient(self.config, user_token=token)

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    @property
    def has_token(self) -> bool:
        return bool(self.user_token)

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers using user token."""
        if not self.user_token:
            return {}
        return {"Authorization": f"Bearer {self.user_token}"}

    def _get_library_cache(self, library_id: str) -> LibraryCache:
        """Get or create a library cache for the given library ID."""
        if library_id not in self._library_caches:
            self._library_caches[library_id] = LibraryCache(library_id, self.config.cache_ttl)
        return self._library_caches[library_id]

    # --- Connectivity ---

    async def ping(self) -> bool:
        """Test API connectivity using user token."""
        if not self.is_configured or not self.has_token:
            return False

        try:
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/me",
                headers=self._get_headers(),
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"❌ ABS ping failed: {e}")
            return False

    # --- Library Discovery ---

    async def get_all_libraries(self) -> List[Library]:
        """Fetch all libraries accessible to the user.

        Returns:
            List of Library objects with id, name, mediaType, etc.
        """
        if not self.is_configured or not self.has_token:
            return []

        try:
            async with self._semaphore:
                r = await self._shared_client.get(
                    f"{self.config.base_url}/api/libraries",
                    headers=self._get_headers(),
                )

                if r.status_code != 200:
                    logger.warning(f"⚠️ Failed to fetch libraries: HTTP {r.status_code}")
                    return []

                data = r.json()
                libraries = []
                for lib_data in data.get("libraries", []):
                    libraries.append(Library(
                        id=lib_data.get("id", ""),
                        name=lib_data.get("name", ""),
                        media_type=lib_data.get("mediaType", ""),
                        icon=lib_data.get("icon", ""),
                        folders=lib_data.get("folders", []),
                    ))

                logger.info(f"📚 Found {len(libraries)} libraries")
                return libraries

        except Exception as e:
            logger.error(f"❌ Failed to fetch libraries: {e}")
            return []

    # --- Library Operations ---

    async def get_library_items(
        self,
        library_id: str,
        force_refresh: bool = False
    ) -> List[dict]:
        """Fetch all library items from ABS API for a specific library."""
        if not self.is_configured or not self.has_token or not library_id:
            return []

        async with self._semaphore:
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/libraries/{library_id}/items",
                headers=self._get_headers(),
                params={"limit": 10000, "minified": "1"},
            )

            if r.status_code != 200:
                logger.warning(f"⚠️ Library fetch failed: HTTP {r.status_code}")
                return []

            data = r.json()
            return data.get("results", [])

    async def get_all_library_items(
        self,
        library_ids: List[str],
        force_refresh: bool = False
    ) -> List[dict]:
        """Fetch items from multiple libraries."""
        if not library_ids:
            return []

        all_items = []
        for lib_id in library_ids:
            items = await self.get_library_items(lib_id, force_refresh)
            # Tag items with their library ID
            for item in items:
                item["_library_id"] = lib_id
            all_items.extend(items)

        return all_items

    async def check_library_presence(
        self,
        items: List[Tuple[str, str]],
        library_ids: List[str]
    ) -> Dict[str, bool]:
        """Check which (title, author) pairs exist in specified libraries."""
        if not library_ids:
            return {f"{t}||{a}": False for t, a in items}

        # Collect results from all enabled libraries
        results = {}
        for lib_id in library_ids:
            cache = self._get_library_cache(lib_id)

            async def get_items():
                return await self.get_library_items(lib_id)

            await cache.ensure_fresh(get_items)
            lib_results = cache.check_presence(items)

            # Merge results - True if found in ANY library
            for key, found in lib_results.items():
                if found:
                    results[key] = True
                elif key not in results:
                    results[key] = False

        return results

    async def sync_library(self, library_id: str) -> int:
        """Force full library sync for a specific library."""
        if not library_id:
            return 0

        cache = self._get_library_cache(library_id)

        async def get_items():
            return await self.get_library_items(library_id)

        return await cache.full_sync(get_items)

    async def sync_all_libraries(self, library_ids: List[str]) -> int:
        """Force full sync for all specified libraries."""
        total = 0
        for lib_id in library_ids:
            count = await self.sync_library(lib_id)
            total += count
        return total

    def get_sync_status(self, library_id: str) -> Optional[LibrarySyncStatus]:
        """Get library sync status for a specific library."""
        if library_id not in self._library_caches:
            return None
        return self._library_caches[library_id].get_sync_status()

    async def get_series_list(self, library_ids: List[str]) -> List[Dict]:
        """Fetch series list from all specified libraries."""
        all_series = {}

        for lib_id in library_ids:
            cache = self._get_library_cache(lib_id)

            async def get_items():
                return await self.get_library_items(lib_id)

            await cache.ensure_fresh(get_items)
            series_list = cache.get_series_summary()

            # Merge series from different libraries
            for series in series_list:
                name = series.get("name", "")
                if name in all_series:
                    # Merge book counts
                    all_series[name]["count"] = all_series[name].get("count", 0) + series.get("count", 0)
                else:
                    all_series[name] = series

        return list(all_series.values())

    async def get_books_in_series(
        self,
        series_name: str,
        library_ids: List[str]
    ) -> List[LibraryItem]:
        """Get all books in a specific series from specified libraries."""
        all_books = []

        for lib_id in library_ids:
            cache = self._get_library_cache(lib_id)

            async def get_items():
                return await self.get_library_items(lib_id)

            await cache.ensure_fresh(get_items)
            books = cache.get_series_books(series_name)
            all_books.extend(books)

        return all_books

    # --- Verification ---

    async def verify_import(
        self,
        title: str,
        author: str = "",
        library_path: str = "",
        metadata: Optional[dict] = None,
        library_ids: Optional[List[str]] = None,
    ) -> VerificationResult:
        """Verify imported item exists in ABS library."""

        if not self.is_configured:
            return VerificationResult(
                status="not_configured",
                note="ABS integration not configured",
            )

        if not self.has_token:
            return VerificationResult(
                status="not_configured",
                note="No authentication token available",
            )

        if not library_ids:
            return VerificationResult(
                status="not_configured",
                note="No libraries enabled for search",
            )

        # Extract identifiers from metadata
        asin = metadata.get("asin") if metadata else None
        isbn = metadata.get("isbn") if metadata else None

        # Search across all enabled libraries
        best_match = None
        best_result = None

        for lib_id in library_ids:
            cache = self._get_library_cache(lib_id)

            async def get_items():
                return await self.get_library_items(lib_id)

            await cache.ensure_fresh(get_items)

            match, result = cache.find_best_match(
                title=title,
                author=author,
                asin=asin,
                isbn=isbn,
                path=library_path,
            )

            if match and (not best_match or result.score > best_result.score):
                best_match = match
                best_result = result

        if not best_match:
            return VerificationResult(
                status="not_found",
                note="Not found in library",
            )

        status = determine_verification_status(best_result.confidence)

        if best_result.method in {"ASIN", "ISBN"}:
            note = f"{best_result.method} match: '{best_match.title}' by '{best_match.author}'"
        elif status == "verified":
            note = f"Strong match ({best_result.method}): '{best_match.title}' by '{best_match.author}' (score: {best_result.score})"
        elif status == "mismatch":
            note = f"Partial match: '{best_match.title}' by '{best_match.author}' (score: {best_result.score})"
        else:
            note = f"Weak match: '{best_match.title}' (score: {best_result.score})"

        return VerificationResult(
            status=status,
            note=note,
            abs_item_id=best_match.id,
            matched_title=best_match.title,
            score=best_result.score,
        )

    # --- Covers ---

    async def fetch_cover(
        self,
        title: str,
        author: str = "",
        mam_id: str = "",
        force_refresh: bool = False,
        library_ids: Optional[List[str]] = None,
    ) -> CoverResult:
        """Fetch cover image from ABS."""

        # Check cache first
        if mam_id and not force_refresh:
            cached = _get_cover_service().get_cached_cover(mam_id)
            if cached and cached.get("cover_url"):
                return CoverResult(
                    cover_url=cached.get("cover_url"),
                    item_id=cached.get("item_id"),
                    is_local=cached.get("is_local", False),
                    description=cached.get("description"),
                    metadata=cached.get("metadata"),
                )

        if not self.is_configured or not self.has_token:
            return CoverResult()

        async with self._semaphore:
            # Try search/covers endpoint
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/search/covers",
                headers=self._get_headers(),
                params={"title": title, "author": author} if author else {"title": title},
            )

            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if results:
                    cover_url = results[0] if isinstance(results[0], str) else results[0].get("cover")
                    if cover_url and mam_id:
                        await _get_cover_service().save_cover_to_cache(mam_id, cover_url, title, author)
                        cached = _get_cover_service().get_cached_cover(mam_id)
                        if cached:
                            return CoverResult(
                                cover_url=cached.get("cover_url"),
                                item_id=cached.get("item_id"),
                                is_local=cached.get("is_local", False),
                            )
                    return CoverResult(cover_url=cover_url)

            # Fallback to library search if library IDs provided
            if library_ids:
                for lib_id in library_ids:
                    cache = self._get_library_cache(lib_id)

                    async def get_items():
                        return await self.get_library_items(lib_id)

                    await cache.ensure_fresh(get_items)
                    match, _ = cache.find_best_match(title, author)
                    if match and match.id:
                        cover_url = f"{self.config.base_url}/api/items/{match.id}/cover"
                        if mam_id:
                            await _get_cover_service().save_cover_to_cache(mam_id, cover_url, title, author, match.id)
                            cached = _get_cover_service().get_cached_cover(mam_id)
                            if cached:
                                return CoverResult(
                                    cover_url=cached.get("cover_url"),
                                    item_id=match.id,
                                    is_local=cached.get("is_local", False),
                                )
                        return CoverResult(cover_url=cover_url, item_id=match.id)

        return CoverResult()

    # --- Item Details ---

    async def fetch_item_details(self, item_id: str) -> Optional[dict]:
        """Fetch full item metadata from ABS."""
        if not self.is_configured or not self.has_token or not item_id:
            return None

        async with self._semaphore:
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/items/{item_id}",
                headers=self._get_headers(),
                params={"expanded": "1"},
            )

            if r.status_code != 200:
                return None

            data = r.json()
            media = data.get("media", {})
            metadata = media.get("metadata", {})

            return {
                "item_id": item_id,
                "description": metadata.get("description", ""),
                "metadata": metadata,
            }

    # --- Provider Search ---

    async def fetch_from_provider(
        self,
        provider: str,
        title: str,
        author: str = "",
        item_id: str = "",
        fallback_title_only: bool = True,
    ) -> dict:
        """
        Fetch enhanced metadata from external provider via ABS.

        Uses /api/search/books endpoint with provider parameter.

        Args:
            provider: Provider name (audible, google, openlibrary)
            title: Book title
            author: Author name (optional)
            item_id: ABS library item ID (optional, for enrichment)
            fallback_title_only: Use title-only search if author search fails

        Returns:
            Dict with enhanced metadata fields, or empty dict on error
        """
        if not self.is_configured or not self.has_token:
            return {}

        try:
            async with self._semaphore:
                params = {
                    "provider": provider,
                    "fallbackTitleOnly": "1" if fallback_title_only else "0",
                    "title": title,
                }

                if author:
                    params["author"] = author
                if item_id:
                    params["id"] = item_id

                logger.debug(f"🌐 Calling /api/search/books with provider={provider}")

                r = await self._shared_client.get(
                    f"{self.config.base_url}/api/search/books",
                    headers=self._get_headers(),
                    params=params,
                    timeout=6.0,
                )

                if r.status_code != 200:
                    logger.warning(f"⚠️  Provider {provider} returned HTTP {r.status_code}")
                    return {}

                data = r.json()
                results = data if isinstance(data, list) else data.get("results", [])

                if not results:
                    logger.debug(f"ℹ️  No results from provider {provider}")
                    return {}

                logger.debug(f"✅ Got result from {provider}: {results[0].get('title', 'Unknown')}")
                return results[0]

        except Exception as e:
            logger.error(f"❌ Failed to fetch from provider {provider}: {e}")
            return {}
