"""Async Audiobookshelf client."""

import logging
import asyncio
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
import httpx

from abs.config import AbsConfig
from abs.models import LibraryItem, VerificationResult, CoverResult, LibrarySyncStatus
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
    """Async Audiobookshelf client with connection pooling and caching."""

    _shared_client: Optional[httpx.AsyncClient] = None
    _semaphore: Optional[asyncio.Semaphore] = None

    def __init__(self, config: AbsConfig):
        self.config = config
        self._library_cache: Optional[LibraryCache] = None

        if config.library_id:
            self._library_cache = LibraryCache(config.library_id, config.cache_ttl)

        if AbsClient._shared_client is None:
            AbsClient._shared_client = httpx.AsyncClient(
                timeout=8.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
            )

        if AbsClient._semaphore is None:
            AbsClient._semaphore = asyncio.Semaphore(10)

    @classmethod
    def from_env(cls) -> "AbsClient":
        """Create client from environment variables."""
        return cls(AbsConfig.from_env())

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    @property
    def library_cache(self) -> Optional[LibraryCache]:
        return self._library_cache

    # --- Connectivity ---

    async def ping(self) -> bool:
        """Test API connectivity."""
        if not self.is_configured:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/me",
                headers=headers,
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"❌ ABS ping failed: {e}")
            return False

    # --- Library Operations ---

    async def get_library_items(self, force_refresh: bool = False) -> List[dict]:
        """Fetch all library items from ABS API."""
        if not self.is_configured or not self.config.library_id:
            return []

        async with self._semaphore:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/libraries/{self.config.library_id}/items",
                headers=headers,
                params={"limit": 10000, "minified": "1"},
            )

            if r.status_code != 200:
                logger.warning(f"⚠️ Library fetch failed: HTTP {r.status_code}")
                return []

            data = r.json()
            return data.get("results", [])

    async def check_library_presence(
        self,
        items: List[Tuple[str, str]]
    ) -> Dict[str, bool]:
        """Check which (title, author) pairs exist in library."""
        if not self._library_cache:
            return {f"{t}||{a}": False for t, a in items}

        await self._library_cache.ensure_fresh(self.get_library_items)
        return self._library_cache.check_presence(items)

    async def sync_library(self) -> int:
        """Force full library sync."""
        if not self._library_cache:
            return 0
        return await self._library_cache.full_sync(self.get_library_items)

    def get_sync_status(self) -> Optional[LibrarySyncStatus]:
        """Get library sync status."""
        if not self._library_cache:
            return None
        return self._library_cache.get_sync_status()

    async def get_series_list(self) -> List[Dict]:
        """
        Fetch series list from ABS filterdata endpoint.

        Returns:
            List of series: [{"id": "...", "name": "...", "books": [...]}]
        """
        if not self.is_configured or not self.config.library_id:
            return []

        async with self._semaphore:
            url = f"{self.config.base_url}/api/libraries/{self.config.library_id}"
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            params = {"include": "filterdata"}

            try:
                r = await self._shared_client.get(url, headers=headers, params=params)
                if r.status_code == 200:
                    data = r.json()
                    filterdata = data.get("filterdata", {})
                    series_list = filterdata.get("series", [])
                    logger.info(f"📚 Fetched {len(series_list)} series from ABS")
                    return series_list
                return []
            except Exception as e:
                logger.error(f"❌ Failed to fetch ABS series: {e}")
                return []

    async def get_books_in_series(self, series_name: str) -> List[LibraryItem]:
        """Get all books in a specific series from library cache."""
        if not self._library_cache:
            return []

        await self._library_cache.ensure_fresh(self.get_library_items)
        return self._library_cache.get_series_books(series_name)

    # --- Verification ---

    async def verify_import(
        self,
        title: str,
        author: str = "",
        library_path: str = "",
        metadata: Optional[dict] = None,
    ) -> VerificationResult:
        """Verify imported item exists in ABS library."""

        if not self.is_configured:
            return VerificationResult(
                status="not_configured",
                note="ABS integration not configured",
            )

        if not self._library_cache:
            return VerificationResult(
                status="not_configured",
                note="ABS_LIBRARY_ID not configured",
            )

        # Ensure cache is fresh
        await self._library_cache.ensure_fresh(self.get_library_items)

        # Extract identifiers from metadata
        asin = metadata.get("asin") if metadata else None
        isbn = metadata.get("isbn") if metadata else None

        # Find best match
        match, score = self._library_cache.find_best_match(
            title=title,
            author=author,
            asin=asin,
            isbn=isbn,
            path=library_path,
        )

        if not match:
            return VerificationResult(
                status="not_found",
                note="Not found in library",
            )

        status = determine_verification_status(score)

        if status == "verified":
            note = f"Found in library: '{match.title}' by '{match.author}'"
            if score >= 200:
                note = f"ASIN/ISBN match: '{match.title}' by '{match.author}'"
        elif status == "mismatch":
            note = f"Partial match: '{match.title}' by '{match.author}' (score: {score})"
        else:
            note = f"Weak match: '{match.title}' (score: {score})"

        return VerificationResult(
            status=status,
            note=note,
            abs_item_id=match.id,
            matched_title=match.title,
            score=score,
        )

    # --- Covers ---

    async def fetch_cover(
        self,
        title: str,
        author: str = "",
        mam_id: str = "",
        force_refresh: bool = False,
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

        if not self.is_configured:
            return CoverResult()

        async with self._semaphore:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}

            # Try search/covers endpoint
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/search/covers",
                headers=headers,
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

            # Fallback to library search
            if self._library_cache:
                await self._library_cache.ensure_fresh(self.get_library_items)
                match, _ = self._library_cache.find_best_match(title, author)
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
        if not self.is_configured or not item_id:
            return None

        async with self._semaphore:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            r = await self._shared_client.get(
                f"{self.config.base_url}/api/items/{item_id}",
                headers=headers,
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
