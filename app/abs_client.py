"""
Compatibility shim for legacy abs_client imports.

This module provides backward compatibility for existing code that imports
from abs_client. It wraps the new app.abs.AbsClient and converts Pydantic
models to the legacy dict format.

DEPRECATED: New code should import from app.abs instead and use token-based auth.

ARCHITECTURE NOTE:
- User tokens are now required for ABS API calls (replaces static API key)
- Library IDs are stored in settings and managed dynamically
- Routes should use AbsClient.from_env(user_token=token) for authenticated calls
"""

import logging
from typing import List, Tuple, Dict, Optional

from abs.client import AbsClient
from abs.config import AbsConfig

# Import config values for backward compatibility with tests that monkeypatch
from config import (
    ABS_BASE_URL,
    ABS_VERIFY_TIMEOUT,
    ABS_LIBRARY_CACHE_TTL,
)

logger = logging.getLogger("mam-audiofinder")


def get_enabled_library_ids() -> List[str]:
    """Get enabled library IDs from settings.

    Returns list of library IDs that should be searched.
    This is populated when admin configures libraries in Settings.
    """
    try:
        from settings_service import settings_service
        return settings_service.get_enabled_libraries()
    except Exception:
        return []


class AudiobookshelfClient:
    """
    Legacy compatibility wrapper for AbsClient.

    This class wraps the new AbsClient and provides the same interface
    as the old AudiobookshelfClient for backward compatibility.

    NOTE: Methods now accept an optional `user_token` parameter for auth.
    Without a token, most API calls will fail.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize wrapped client from environment or module-level variables."""
        config = AbsConfig(
            base_url=ABS_BASE_URL,
            verify_timeout=ABS_VERIFY_TIMEOUT,
            cache_ttl=ABS_LIBRARY_CACHE_TTL,
        )
        self._client = AbsClient(config, user_token=user_token)
        self._user_token = user_token
        self.base_url = self._client.config.base_url

    def with_token(self, token: str) -> "AudiobookshelfClient":
        """Create a new client instance with the given token."""
        return AudiobookshelfClient(user_token=token)

    @property
    def config(self):
        """Expose the inner client's config for routes that need direct access."""
        return self._client.config

    @property
    def is_configured(self) -> bool:
        """Check if Audiobookshelf is configured (base URL set)."""
        return self._client.is_configured

    @property
    def has_token(self) -> bool:
        """Check if a user token is available."""
        return self._client.has_token

    async def test_connection(self) -> bool:
        """
        Test Audiobookshelf API connectivity.

        Maps to: AbsClient.ping()
        """
        if not self.is_configured:
            logger.info("ℹ️  Audiobookshelf integration not configured (skipping connectivity test)")
            return False

        if not self.has_token:
            logger.warning("⚠️  No user token available for connection test")
            return False

        try:
            logger.info(f"🔍 Testing Audiobookshelf API connection to {self.base_url}...")
            result = await self._client.ping()

            if result:
                logger.info(f"✅ Audiobookshelf API connected successfully")
            else:
                logger.error(f"❌ Audiobookshelf API test failed")

            return result

        except Exception as e:
            logger.error(f"❌ Audiobookshelf API test failed with exception: {e}")
            return False

    async def check_library_items(
        self,
        items: List[Tuple[str, str]],
        library_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Check which items exist in the Audiobookshelf library.

        Args:
            items: List of (title, author) tuples to check
            library_ids: Optional list of library IDs to check (uses settings if not provided)

        Returns:
            Dict mapping "{title}||{author}" to boolean (True if in library, False otherwise)

        Maps to: AbsClient.check_library_presence()
        """
        if library_ids is None:
            library_ids = get_enabled_library_ids()

        if not self.is_configured or not library_ids:
            logger.debug("📚 ABS not fully configured, skipping library check")
            return {f"{title}||{author}": False for title, author in items}

        if not self.has_token:
            logger.debug("📚 No user token available, skipping library check")
            return {f"{title}||{author}": False for title, author in items}

        if not items:
            return {}

        logger.info(f"📚 Checking {len(items)} items against ABS library")

        try:
            results = await self._client.check_library_presence(items, library_ids)
            logger.info(f"✅ Library check complete: {sum(results.values())}/{len(results)} items found in library")
            return results
        except Exception as e:
            logger.error(f"❌ Failed to check library items: {e}")
            return {f"{title}||{author}": False for title, author in items}

    async def fetch_cover(
        self,
        title: str,
        author: str = "",
        mam_id: str = "",
        force_refresh: bool = False,
        library_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Fetch cover image URL from Audiobookshelf.

        Returns dict with 'cover_url' and 'item_id' if found, else empty dict.

        Maps to: AbsClient.fetch_cover()
        """
        logger.info(f"🔍 Fetching cover for: '{title}' by '{author}' (MAM ID: {mam_id or 'N/A'})")

        if not self.is_configured:
            logger.warning(f"⚠️  ABS not configured, skipping cover fetch for '{title}'")
            return {}

        if not title:
            logger.warning(f"⚠️  No title provided, skipping cover fetch")
            return {}

        if library_ids is None:
            library_ids = get_enabled_library_ids()

        try:
            result = await self._client.fetch_cover(
                title=title,
                author=author,
                mam_id=mam_id,
                force_refresh=force_refresh,
                library_ids=library_ids,
            )

            # Convert Pydantic model to dict
            result_dict = {}
            if result.cover_url:
                result_dict["cover_url"] = result.cover_url
            if result.item_id:
                result_dict["item_id"] = result.item_id
            if result.is_local:
                result_dict["is_local"] = result.is_local
            if result.description:
                result_dict["description"] = result.description
            if result.metadata:
                result_dict["metadata"] = result.metadata

            if result_dict:
                logger.info(f"✅ Found cover for '{title}'")
            else:
                logger.warning(f"❌ No cover found for '{title}'")

            return result_dict

        except Exception as e:
            logger.error(f"❌ Error fetching cover: {e}")
            return {}

    async def verify_import(
        self,
        title: str,
        author: str = "",
        library_path: str = "",
        metadata: dict = None,
        library_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Verify that an imported item exists in Audiobookshelf library.

        Args:
            title: Book title (from torrent or metadata.json)
            author: Author name (from torrent or metadata.json)
            library_path: Path where book was imported
            metadata: Optional dict from metadata.json with enhanced matching data
            library_ids: Optional list of library IDs to search (uses settings if not provided)

        Returns dict with:
            - status: 'verified', 'mismatch', 'not_found', 'unreachable', or 'not_configured'
            - note: Diagnostic message explaining the status
            - abs_item_id: ABS item ID if found, else None

        Maps to: AbsClient.verify_import()
        """
        logger.info(f"🔍 Verifying import in ABS: '{title}' by '{author}' at '{library_path}'")

        if not self.is_configured:
            logger.info("ℹ️  Audiobookshelf not configured, skipping verification")
            return {
                "status": "not_configured",
                "note": "ABS integration not configured",
                "abs_item_id": None
            }

        if not self.has_token:
            logger.warning("⚠️  No user token available for verification")
            return {
                "status": "not_configured",
                "note": "No authentication token available",
                "abs_item_id": None
            }

        if library_ids is None:
            library_ids = get_enabled_library_ids()

        if not library_ids:
            logger.warning("⚠️  No libraries enabled for search")
            return {
                "status": "not_configured",
                "note": "No libraries enabled for search",
                "abs_item_id": None
            }

        if not title:
            logger.warning("⚠️  No title provided for verification")
            return {
                "status": "not_found",
                "note": "No title provided",
                "abs_item_id": None
            }

        try:
            result = await self._client.verify_import(
                title=title,
                author=author,
                library_path=library_path,
                metadata=metadata,
                library_ids=library_ids,
            )

            # Convert Pydantic model to dict
            result_dict = {
                "status": result.status,
                "note": result.note,
                "abs_item_id": result.abs_item_id,
            }

            if result.status == "verified":
                logger.info(f"✅ Verified: {result.note}")
            elif result.status == "mismatch":
                logger.warning(f"⚠️  Mismatch: {result.note}")
            else:
                logger.warning(f"❌ Not found: {result.note}")

            return result_dict

        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return {
                "status": "unreachable",
                "note": f"Verification failed: {str(e)}",
                "abs_item_id": None
            }

    async def fetch_item_details(self, item_id: str) -> dict:
        """
        Fetch full item metadata from ABS.

        Args:
            item_id: ABS item ID

        Returns:
            Dict with item details including description and metadata

        Maps to: AbsClient.fetch_item_details()
        """
        if not self.is_configured or not item_id:
            return {}

        try:
            result = await self._client.fetch_item_details(item_id)
            return result or {}
        except Exception as e:
            logger.error(f"❌ Error fetching item details: {e}")
            return {}

    async def get_all_libraries(self):
        """
        Fetch all libraries accessible to the user.

        Returns:
            List of Library objects
        """
        return await self._client.get_all_libraries()

    async def sync_library(self, library_id: str) -> int:
        """Force sync a specific library."""
        return await self._client.sync_library(library_id)

    async def sync_all_libraries(self, library_ids: Optional[List[str]] = None) -> int:
        """Force sync all enabled libraries."""
        if library_ids is None:
            library_ids = get_enabled_library_ids()
        return await self._client.sync_all_libraries(library_ids)

    async def get_series_list(self, library_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch series list from specified libraries.

        If library_ids is None, uses enabled libraries from settings.

        Args:
            library_ids: Optional list of library IDs to query

        Returns:
            List of series dicts with name, book_count, author, etc.

        Maps to: AbsClient.get_series_list()
        """
        if library_ids is None:
            library_ids = get_enabled_library_ids()

        if not library_ids:
            logger.debug("📚 No libraries enabled, skipping series list")
            return []

        if not self.has_token:
            logger.debug("📚 No user token available, skipping series list")
            return []

        try:
            return await self._client.get_series_list(library_ids)
        except Exception as e:
            logger.error(f"❌ Failed to get series list: {e}")
            return []

    async def get_books_in_series(
        self,
        series_name: str,
        library_ids: Optional[List[str]] = None
    ) -> List:
        """
        Get all books in a specific series from specified libraries.

        If library_ids is None, uses enabled libraries from settings.

        Args:
            series_name: Name of the series to query
            library_ids: Optional list of library IDs to query

        Returns:
            List of LibraryItem objects for books in the series

        Maps to: AbsClient.get_books_in_series()
        """
        if library_ids is None:
            library_ids = get_enabled_library_ids()

        if not library_ids:
            logger.debug("📚 No libraries enabled, skipping series books")
            return []

        if not self.has_token:
            logger.debug("📚 No user token available, skipping series books")
            return []

        try:
            return await self._client.get_books_in_series(series_name, library_ids)
        except Exception as e:
            logger.error(f"❌ Failed to get books in series '{series_name}': {e}")
            return []

    async def _fetch_from_provider(
        self,
        provider: str,
        item_id: str,
        title: str,
        author: str = "",
        fallback_title_only: bool = True
    ) -> dict:
        """
        Fetch enhanced metadata from external provider via ABS.

        Args:
            provider: Provider name (audible, google, openlibrary)
            item_id: ABS library item ID (optional)
            title: Book title
            author: Author name (optional)
            fallback_title_only: Use title-only search if author search fails

        Returns:
            Dict with enhanced metadata fields, or empty dict on error

        Maps to: AbsClient.fetch_from_provider()
        """
        return await self._client.fetch_from_provider(
            provider=provider,
            title=title,
            author=author,
            item_id=item_id,
            fallback_title_only=fallback_title_only,
        )

    async def _update_description_after_verification(
        self,
        item_id: str,
        title: str,
        author: str
    ):
        """
        Legacy method for updating description after verification.

        This method is deprecated and maintained only for backward compatibility.
        The new client handles description fetching differently.
        """
        logger.warning("⚠️  _update_description_after_verification is deprecated")
        # For now, just fetch and return details
        return await self.fetch_item_details(item_id)


def get_abs_client(user_token: Optional[str] = None) -> AudiobookshelfClient:
    """
    Factory function to create an ABS client with optional token.

    This is the preferred way to get an ABS client in routes that have
    access to the user's token from the request context.
    """
    return AudiobookshelfClient(user_token=user_token)


# Global singleton instance for backward compatibility (no token - limited functionality)
# Routes that need full functionality should use get_abs_client(token) instead
abs_client = AudiobookshelfClient()

# Re-export for legacy imports
__all__ = ["abs_client", "AudiobookshelfClient", "AbsClient", "get_abs_client"]
