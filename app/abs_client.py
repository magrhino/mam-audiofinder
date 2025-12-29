"""
Compatibility shim for legacy abs_client imports.

This module provides backward compatibility for existing code that imports
from abs_client. It wraps the new app.abs.AbsClient and converts Pydantic
models to the legacy dict format.

DEPRECATED: New code should import from app.abs instead.
"""

import logging
from typing import List, Tuple, Dict, Optional

from abs.client import AbsClient
from abs.config import AbsConfig

# Import config values for backward compatibility with tests that monkeypatch
from config import (
    ABS_BASE_URL,
    ABS_API_KEY,
    ABS_LIBRARY_ID,
    ABS_VERIFY_TIMEOUT,
    ABS_LIBRARY_CACHE_TTL,
)

logger = logging.getLogger("mam-audiofinder")


class AudiobookshelfClient:
    """
    Legacy compatibility wrapper for AbsClient.

    This class wraps the new AbsClient and provides the same interface
    as the old AudiobookshelfClient for backward compatibility.
    """

    def __init__(self):
        """Initialize wrapped client from environment or module-level variables."""
        # For backward compatibility with tests that monkeypatch module-level variables,
        # we read from the module namespace instead of config directly
        import abs_client as self_module
        config = AbsConfig(
            base_url=self_module.ABS_BASE_URL,
            api_key=self_module.ABS_API_KEY,
            library_id=self_module.ABS_LIBRARY_ID,
            verify_timeout=self_module.ABS_VERIFY_TIMEOUT,
            cache_ttl=self_module.ABS_LIBRARY_CACHE_TTL,
        )
        self._client = AbsClient(config)
        self.base_url = self._client.config.base_url
        self.api_key = self._client.config.api_key
        self.library_id = self._client.config.library_id

    @property
    def config(self):
        """Expose the inner client's config for routes that need direct access."""
        return self._client.config

    @property
    def is_configured(self) -> bool:
        """Check if Audiobookshelf is configured."""
        return self._client.is_configured

    async def test_connection(self) -> bool:
        """
        Test Audiobookshelf API connectivity.

        Maps to: AbsClient.ping()
        """
        if not self.is_configured:
            logger.info("ℹ️  Audiobookshelf integration not configured (skipping connectivity test)")
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

    async def check_library_items(self, items: List[Tuple[str, str]]) -> Dict[str, bool]:
        """
        Check which items exist in the Audiobookshelf library.

        Args:
            items: List of (title, author) tuples to check

        Returns:
            Dict mapping "{title}||{author}" to boolean (True if in library, False otherwise)

        Maps to: AbsClient.check_library_presence()
        """
        if not self.is_configured or not self.library_id:
            logger.debug("📚 ABS not fully configured, skipping library check")
            return {f"{title}||{author}": False for title, author in items}

        if not items:
            return {}

        logger.info(f"📚 Checking {len(items)} items against ABS library")

        try:
            results = await self._client.check_library_presence(items)
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
        force_refresh: bool = False
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

        try:
            result = await self._client.fetch_cover(
                title=title,
                author=author,
                mam_id=mam_id,
                force_refresh=force_refresh,
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
        metadata: dict = None
    ) -> dict:
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

        try:
            result = await self._client.verify_import(
                title=title,
                author=author,
                library_path=library_path,
                metadata=metadata,
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


# Global singleton instance for backward compatibility
abs_client = AudiobookshelfClient()

# Re-export for legacy imports
__all__ = ["abs_client", "AudiobookshelfClient", "AbsClient"]
