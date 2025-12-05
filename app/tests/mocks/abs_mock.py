"""
Mock Audiobookshelf API client for deterministic testing.

This module provides a mock implementation of AudiobookshelfClient that returns
pre-recorded fixture data instead of making real API calls.

Usage:
    In mock mode (LIVE_API_TESTS != "1"), this class is automatically used
    instead of the real AudiobookshelfClient via monkey-patching in conftest.py.
"""
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from utils import normalize_title, normalize_author

logger = logging.getLogger("mam-audiofinder")


class FixtureNotFoundError(Exception):
    """Raised when a required fixture file is not found."""
    pass


class MockABSClient:
    """Mock implementation of AudiobookshelfClient that uses fixture data."""

    # Class-level counters (shared across instances, like real client)
    _request_count: int = 0
    _cache_hit_count: int = 0

    def __init__(self):
        """Initialize mock ABS client."""
        # Try to read from abs_client module to respect monkeypatched values
        try:
            import abs_client
            self.base_url = abs_client.ABS_BASE_URL if hasattr(abs_client, 'ABS_BASE_URL') else "http://mock-abs:13378"
            self.api_key = abs_client.ABS_API_KEY if hasattr(abs_client, 'ABS_API_KEY') else "mock-abs-api-key"
            self.library_id = abs_client.ABS_LIBRARY_ID if hasattr(abs_client, 'ABS_LIBRARY_ID') else "mock-library-id"
        except (ImportError, AttributeError):
            # Fallback to defaults if abs_client not available
            self.base_url = "http://mock-abs:13378"
            self.api_key = "mock-abs-api-key"
            self.library_id = "mock-library-id"

        # In-memory cache for library items (same as real client)
        self._library_cache: Dict[str, Tuple[bool, float]] = {}
        self._library_items_cache: Optional[Tuple[List[dict], float]] = None
        self._metadata_cache: Dict[str, Tuple[dict, float]] = {}

        # Fixtures directory
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "abs"
        if not self.fixtures_dir.exists():
            logger.warning(f"⚠️  ABS fixtures directory not found: {self.fixtures_dir}")

        logger.info("🔧 Initialized MOCK ABS client (fixture-based)")

    @property
    def is_configured(self) -> bool:
        """Check if ABS is configured (respects monkeypatched values)."""
        return bool(self.base_url and self.api_key)

    @classmethod
    def get_request_count(cls) -> int:
        """Get mock request count."""
        return cls._request_count

    @classmethod
    def get_cache_hit_count(cls) -> int:
        """Get mock cache hit count."""
        return cls._cache_hit_count

    @classmethod
    def reset_counters(cls):
        """Reset mock counters."""
        cls._request_count = 0
        cls._cache_hit_count = 0
        logger.info("🔄 Reset MOCK ABS counters")

    def _load_fixture(self, fixture_name: str) -> Dict[str, Any]:
        """
        Load a fixture file by name.

        Args:
            fixture_name: Name of fixture file (without .json extension)

        Returns:
            Parsed JSON data from fixture

        Raises:
            FixtureNotFoundError: If fixture file doesn't exist
        """
        fixture_path = self.fixtures_dir / f"{fixture_name}.json"

        if not fixture_path.exists():
            available_fixtures = list(self.fixtures_dir.glob('*.json')) if self.fixtures_dir.exists() else []
            error_msg = (
                f"❌ ABS FIXTURE NOT FOUND: {fixture_name}.json\n"
                f"   Expected path: {fixture_path}\n"
                f"   Available fixtures: {[f.name for f in available_fixtures]}\n"
                f"   To create this fixture, run capture_abs_fixtures.py script with live ABS instance."
            )
            logger.error(error_msg)
            raise FixtureNotFoundError(error_msg)

        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
                logger.debug(f"📦 Loaded ABS fixture: {fixture_name}.json")
                MockABSClient._request_count += 1
                return data
        except json.JSONDecodeError as e:
            error_msg = f"❌ Invalid JSON in ABS fixture {fixture_name}.json: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_fixture_name(self, method: str, **params) -> str:
        """
        Generate fixture filename based on method and parameters.

        Args:
            method: API method name (e.g., 'verify_import', 'fetch_cover')
            **params: Method parameters for filename construction

        Returns:
            Fixture filename (without .json extension)
        """
        # Build parameter string using fixed order to match capture script convention
        # Order: title, author, library_path, metadata (then any remaining keys alphabetically)
        param_order = ['title', 'author', 'library_path', 'metadata']
        param_parts = []

        # Process known keys in fixed order
        for key in param_order:
            if key in params:
                value = params[key]
                if value is not None and value != "":
                    # Sanitize value for filename
                    safe_value = str(value).replace(" ", "_").replace("/", "_").replace("\\", "_")[:30]
                    param_parts.append(f"{key}={safe_value}")

        # Process any remaining keys alphabetically (for future compatibility)
        for key, value in sorted(params.items()):
            if key not in param_order and value is not None and value != "":
                safe_value = str(value).replace(" ", "_").replace("/", "_").replace("\\", "_")[:30]
                param_parts.append(f"{key}={safe_value}")

        param_str = "_".join(param_parts) if param_parts else "default"
        return f"{method}_{param_str}"

    async def test_connection(self) -> bool:
        """
        Mock ABS connection test.

        Returns:
            bool: True if connection successful, False otherwise
        """
        logger.debug("🔧 MOCK test_connection called")

        # Check if configured
        if not self.is_configured:
            logger.info("ℹ️  MOCK ABS not configured, returning False")
            return False

        try:
            fixture = self._load_fixture("test_connection")
            success = fixture.get("success", True)
            username = fixture.get("username", "MockUser")
            logger.info(f"✅ MOCK ABS connection test: {username}")
            return success
        except FixtureNotFoundError:
            # Default response if no fixture - assume success if configured
            logger.info("✅ MOCK ABS connection test (default): True")
            return True

    async def check_library_items(self, items: List[Tuple[str, str]]) -> Dict[str, bool]:
        """
        Mock library items check.

        Args:
            items: List of (title, author) tuples to check

        Returns:
            Dict mapping "{title}||{author}" to boolean (True if in library)
        """
        if not items:
            return {}

        logger.info(f"🔧 MOCK check_library_items: checking {len(items)} items")

        # Try to load fixture based on items hash (for specific queries)
        items_hash = hashlib.md5(json.dumps(sorted(items)).encode()).hexdigest()[:8]
        fixture_name = f"check_library_items_{items_hash}"

        try:
            fixture = self._load_fixture(fixture_name)
            logger.info(f"📦 Loaded specific library check fixture: {fixture_name}")
            return fixture
        except FixtureNotFoundError:
            # Fall back to default fixture
            try:
                fixture = self._load_fixture("check_library_items_default")
                logger.info("📦 Loaded default library check fixture")

                # Return results for requested items (default to False if not in fixture)
                results = {}
                for title, author in items:
                    cache_key = f"{normalize_title(title)}||{normalize_author(author)}"
                    # Check if this exact key is in the fixture
                    results[cache_key] = fixture.get(cache_key, False)

                return results
            except FixtureNotFoundError:
                # If no fixture at all, return all False
                logger.warning("⚠️  No library check fixtures found, returning all False")
                return {f"{normalize_title(title)}||{normalize_author(author)}": False
                        for title, author in items}

    async def fetch_cover(self, title: str, author: str = "", mam_id: str = "", force_refresh: bool = False) -> dict:
        """
        Mock cover fetch from ABS.

        Args:
            title: Book title
            author: Author name
            mam_id: MAM ID (optional)
            force_refresh: Force refresh (ignored in mock)

        Returns:
            Dict with 'cover_url', 'item_id', optionally 'description' and 'metadata'
        """
        if not title:
            return {}

        logger.info(f"🔧 MOCK fetch_cover: '{title}' by '{author}'")

        # Generate fixture name
        fixture_name = self._get_fixture_name("fetch_cover", title=title, author=author)

        try:
            fixture = self._load_fixture(fixture_name)
            logger.info(f"📦 Loaded cover fixture: {fixture_name}")
            return fixture
        except FixtureNotFoundError:
            # Try without author (fallback)
            if author:
                try:
                    fallback_name = self._get_fixture_name("fetch_cover", title=title)
                    fixture = self._load_fixture(fallback_name)
                    logger.info(f"📦 Loaded cover fixture (fallback): {fallback_name}")
                    return fixture
                except FixtureNotFoundError:
                    pass

            # No fixture found
            logger.warning(f"⚠️  No cover fixture found for '{title}'")
            return {}

    async def verify_import(self, title: str, author: str = "", library_path: str = "", metadata: dict = None) -> dict:
        """
        Mock import verification in ABS.

        Args:
            title: Book title
            author: Author name
            library_path: Path where book was imported
            metadata: Optional metadata dict

        Returns:
            Dict with:
                - status: 'verified', 'mismatch', 'not_found', 'unreachable', 'not_configured'
                - note: Diagnostic message
                - abs_item_id: ABS item ID if found
        """
        # Check if ABS is configured
        if not self.is_configured:
            return {
                "status": "not_configured",
                "note": "ABS integration not configured",
                "abs_item_id": None
            }

        if not self.library_id:
            return {
                "status": "not_configured",
                "note": "ABS_LIBRARY_ID not configured",
                "abs_item_id": None
            }

        if not title:
            return {
                "status": "not_found",
                "note": "No title provided",
                "abs_item_id": None
            }

        logger.info(f"🔧 MOCK verify_import: '{title}' by '{author}'")

        # Generate fixture name
        fixture_name = self._get_fixture_name("verify_import", title=title, author=author)

        try:
            fixture = self._load_fixture(fixture_name)
            logger.info(f"📦 Loaded verification fixture: {fixture_name}")
            return fixture
        except FixtureNotFoundError:
            # Try without author (fallback)
            if author:
                try:
                    fallback_name = self._get_fixture_name("verify_import", title=title)
                    fixture = self._load_fixture(fallback_name)
                    logger.info(f"📦 Loaded verification fixture (fallback): {fallback_name}")
                    return fixture
                except FixtureNotFoundError:
                    pass

            # No fixture found - return not_found
            logger.warning(f"⚠️  No verification fixture found for '{title}', returning not_found")
            return {
                "status": "not_found",
                "note": "Not found in library (mock)",
                "abs_item_id": None
            }

    async def fetch_item_details(self, item_id: str) -> dict:
        """
        Mock item details fetch from ABS.

        Args:
            item_id: ABS item ID

        Returns:
            Dict with full metadata including description, metadata, item_id
            Empty dict {} if not found
        """
        if not item_id:
            return {}

        logger.info(f"🔧 MOCK fetch_item_details: item_id={item_id}")

        # Generate fixture name
        fixture_name = f"fetch_item_details_item_id={item_id[:30]}"

        try:
            fixture = self._load_fixture(fixture_name)
            logger.info(f"📦 Loaded item details fixture: {fixture_name}")
            return fixture
        except FixtureNotFoundError:
            # Try generic fixture
            try:
                fixture = self._load_fixture("fetch_item_details_default")
                logger.info("📦 Loaded default item details fixture")
                return fixture
            except FixtureNotFoundError:
                logger.warning(f"⚠️  No item details fixture found for item {item_id}")
                return {}

    async def _get_cached_library_items(self) -> List[dict]:
        """
        Mock cached library items fetch.
        In mock mode, we don't actually cache, just return empty list.
        """
        logger.debug("🔧 MOCK _get_cached_library_items called")
        return []

    def _match_library_item(self, title: str, author: str, library_items: List[dict]) -> bool:
        """
        Mock library item matching.
        In mock mode, this is not used (check_library_items uses fixtures directly).
        """
        logger.debug(f"🔧 MOCK _match_library_item: '{title}' by '{author}'")
        return False

    async def _update_description_after_verification(self, item_id: str, title: str, author: str):
        """
        Mock description update after verification.
        In mock mode, this is a no-op.
        """
        logger.debug(f"🔧 MOCK _update_description_after_verification: item_id={item_id}")
        pass


# Global singleton instance (mirrors real ABS client pattern)
abs_client = MockABSClient()
