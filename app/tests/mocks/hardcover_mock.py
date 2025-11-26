"""
Mock Hardcover API client for deterministic testing.

This module provides a mock implementation of HardcoverClient that returns
pre-recorded fixture data instead of making real API calls.

Usage:
    In mock mode (LIVE_API_TESTS != "1"), this class is automatically used
    instead of the real HardcoverClient via monkeypatching in conftest.py.
"""
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("mam-audiofinder")


class FixtureNotFoundError(Exception):
    """Raised when a required fixture file is not found."""
    pass


class MockHardcoverRateLimiter:
    """Mock rate limiter that does nothing (instant responses)."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.requests = []

    async def acquire(self):
        """No-op for testing (instant responses)."""
        pass


class MockHardcoverClient:
    """Mock implementation of HardcoverClient that uses fixture data."""

    # Shared state (mirrors real client)
    _shared_client = None  # Not used in mock
    _rate_limiter: Optional[MockHardcoverRateLimiter] = None
    _request_count: int = 0
    _cache_hit_count: int = 0

    def __init__(self):
        """Initialize mock client."""
        self.base_url = "https://api.hardcover.app/v1/graphql"
        self.api_token = "mock-token-for-testing"
        self.cache_ttl = 300  # 5 minutes

        # Initialize mock rate limiter
        if MockHardcoverClient._rate_limiter is None:
            MockHardcoverClient._rate_limiter = MockHardcoverRateLimiter()
            logger.info("🔧 Initialized MOCK Hardcover rate limiter (no delays)")

        # Fixtures directory
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "hardcover"
        if not self.fixtures_dir.exists():
            logger.warning(f"⚠️  Fixtures directory not found: {self.fixtures_dir}")

    @property
    def is_configured(self) -> bool:
        """Mock always returns True."""
        return True

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
        logger.info("🔄 Reset MOCK Hardcover API counters")

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
            error_msg = (
                f"❌ FIXTURE NOT FOUND: {fixture_name}.json\n"
                f"   Expected path: {fixture_path}\n"
                f"   Available fixtures: {list(self.fixtures_dir.glob('*.json')) if self.fixtures_dir.exists() else '(directory not found)'}\n"
                f"   To create this fixture, run in LIVE mode and capture the response."
            )
            logger.error(error_msg)
            raise FixtureNotFoundError(error_msg)

        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
                logger.debug(f"📦 Loaded fixture: {fixture_name}.json")
                return data
        except json.JSONDecodeError as e:
            error_msg = f"❌ Invalid JSON in fixture {fixture_name}.json: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_fixture_name(self, method: str, **params) -> str:
        """
        Generate fixture filename based on method and parameters.

        Args:
            method: API method name (e.g., 'search_series', 'list_series_books')
            **params: Method parameters for filename construction

        Returns:
            Fixture filename (without .json extension)
        """
        # Build parameter string
        param_parts = []
        for key, value in sorted(params.items()):
            if value is not None and value != "":
                # Sanitize value for filename
                safe_value = str(value).replace(" ", "_").replace("/", "_")[:30]
                param_parts.append(f"{key}={safe_value}")

        param_str = "_".join(param_parts) if param_parts else "default"
        return f"{method}_{param_str}"

    async def _execute_graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Mock GraphQL execution - not used directly in tests.
        Individual methods override this behavior by loading specific fixtures.
        """
        # Increment counter to mimic real behavior
        MockHardcoverClient._request_count += 1
        logger.warning("⚠️  _execute_graphql called directly - tests should call specific methods")
        return None

    def _get_cache_key(self, cache_type: str, identifier: str) -> str:
        """Generate cache key (same as real client)."""
        hash_value = hashlib.md5(identifier.encode()).hexdigest()[:12]
        return f"{cache_type}:{hash_value}"

    async def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Mock cache retrieval - always returns None (no caching in tests).
        Individual tests can override caching behavior if needed.
        """
        return None

    async def _set_cache(
        self,
        cache_key: str,
        cache_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Mock cache storage - does nothing in tests."""
        pass

    async def search_series(
        self,
        title: str,
        author: str = "",
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Mock series search - loads fixture based on title.

        Expected fixture format:
        {
            "series": [
                {
                    "series_id": 123,
                    "series_name": "Foundation",
                    "author_name": "Isaac Asimov",
                    "book_count": 7,
                    "readers_count": 5000,
                    "books": ["Foundation", "Foundation and Empire", ...]
                }
            ]
        }
        """
        MockHardcoverClient._request_count += 1

        # Try to load fixture
        fixture_name = self._get_fixture_name("search_series", title=title, author=author, limit=limit)

        try:
            data = self._load_fixture(fixture_name)
            logger.info(f"✅ Mock search_series: '{title}' → {len(data.get('series', []))} results")
            return data.get("series", [])
        except FixtureNotFoundError:
            # Try without author/limit
            try:
                fixture_name = self._get_fixture_name("search_series", title=title)
                data = self._load_fixture(fixture_name)
                logger.info(f"✅ Mock search_series: '{title}' → {len(data.get('series', []))} results (fallback fixture)")
                return data.get("series", [])
            except FixtureNotFoundError:
                raise

    async def list_series_books(
        self,
        series_id: int,
        include_featured: bool = False,
        deduplicate: bool = True,
        debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Mock series books listing - loads fixture based on series_id.

        Expected fixture format:
        {
            "series_id": 123,
            "series_name": "Foundation",
            "author_name": "Isaac Asimov",
            "books_count": 7,
            "books": [
                {
                    "book_id": 456,
                    "title": "Foundation",
                    "subtitle": null,
                    "position": 1,
                    "users_count": 5000
                }
            ]
        }
        """
        MockHardcoverClient._request_count += 1

        fixture_name = self._get_fixture_name("list_series_books", series_id=series_id)

        try:
            data = self._load_fixture(fixture_name)

            # Apply deduplication if requested
            if deduplicate and data.get("books"):
                data["books"] = self._deduplicate_books(data["books"], debug=debug)

            logger.info(f"✅ Mock list_series_books: {series_id} → {len(data.get('books', []))} books")
            return data
        except FixtureNotFoundError:
            raise

    async def search_books_by_author(
        self,
        author_name: str,
        limit: int = 10,
        fields: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Mock author book search - loads fixture based on author.

        Expected fixture format:
        {
            "books": [
                {
                    "id": 123,
                    "title": "Book Title",
                    "description": "...",
                    "series_names": ["Series Name"]
                }
            ]
        }
        """
        MockHardcoverClient._request_count += 1

        fixture_name = self._get_fixture_name("search_books_by_author", author=author_name, limit=limit)

        try:
            data = self._load_fixture(fixture_name)
            logger.info(f"✅ Mock search_books_by_author: '{author_name}' → {len(data.get('books', []))} results")
            return data.get("books", [])
        except FixtureNotFoundError:
            # Try without limit
            try:
                fixture_name = self._get_fixture_name("search_books_by_author", author=author_name)
                data = self._load_fixture(fixture_name)
                return data.get("books", [])
            except FixtureNotFoundError:
                raise

    async def search_book_by_title(
        self,
        title: str,
        author: str = "",
        limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Mock book title search - loads fixture based on title.

        Expected fixture format:
        {
            "books": [
                {
                    "book_id": 123,
                    "title": "Foundation",
                    "authors": ["Isaac Asimov"],
                    "release_year": 1951,
                    "description": "...",
                    "cover_url": "https://..."
                }
            ]
        }
        """
        MockHardcoverClient._request_count += 1

        fixture_name = self._get_fixture_name("search_book_by_title", title=title, author=author, limit=limit)

        try:
            data = self._load_fixture(fixture_name)
            logger.info(f"✅ Mock search_book_by_title: '{title}' → {len(data.get('books', []))} results")
            return data.get("books", [])
        except FixtureNotFoundError:
            # Try without author/limit
            try:
                fixture_name = self._get_fixture_name("search_book_by_title", title=title)
                data = self._load_fixture(fixture_name)
                return data.get("books", [])
            except FixtureNotFoundError:
                raise

    async def search_book_advanced(
        self,
        title: str,
        author: str = "",
        limit: int = 5,
        fields: Optional[str] = None,
        sort: Optional[str] = None,
        weights: Optional[str] = None,
        deduplicate: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Mock advanced book search - loads fixture based on title.

        Expected fixture format:
        {
            "books": [
                {
                    "book_id": 123,
                    "title": "Foundation",
                    "authors": ["Isaac Asimov"],
                    "author_names": ["Isaac Asimov"],
                    "alternative_titles": ["Foundation: Part 1"],
                    "isbns": ["9780553293357"],
                    "audio_seconds": 32400,
                    "has_audiobook": true,
                    "rating": 4.5,
                    "release_year": 1951,
                    "description": "...",
                    "cover_url": "https://...",
                    "users_count": 5000
                }
            ]
        }
        """
        MockHardcoverClient._request_count += 1

        fixture_name = self._get_fixture_name("search_book_advanced", title=title, author=author, limit=limit)

        try:
            data = self._load_fixture(fixture_name)

            # Apply deduplication if requested
            if deduplicate and data.get("books"):
                data["books"] = self._deduplicate_books_by_alt_titles(data["books"])

            logger.info(f"✅ Mock search_book_advanced: '{title}' → {len(data.get('books', []))} results")
            return data.get("books", [])
        except FixtureNotFoundError:
            # Try without author/limit
            try:
                fixture_name = self._get_fixture_name("search_book_advanced", title=title)
                data = self._load_fixture(fixture_name)
                if deduplicate and data.get("books"):
                    data["books"] = self._deduplicate_books_by_alt_titles(data["books"])
                return data.get("books", [])
            except FixtureNotFoundError:
                raise

    async def get_books_by_ids(
        self,
        book_ids: List[int],
        fields: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Dict[int, Dict[str, Any]]:
        """
        Mock batch book lookup by IDs.

        Expected fixture format:
        {
            "books": {
                "123": {
                    "book_id": 123,
                    "title": "Foundation",
                    "users_count": 5000,
                    "rating": 4.5
                },
                "456": {...}
            }
        }
        """
        MockHardcoverClient._request_count += 1

        # Create fixture name with sorted IDs
        ids_str = "_".join(map(str, sorted(book_ids)))
        fixture_name = self._get_fixture_name("get_books_by_ids", ids=ids_str)

        try:
            data = self._load_fixture(fixture_name)
            books_dict = data.get("books", {})

            # Convert string keys to ints
            result = {}
            for book_id in book_ids:
                if str(book_id) in books_dict:
                    result[book_id] = books_dict[str(book_id)]

            logger.info(f"✅ Mock get_books_by_ids: {len(book_ids)} requested → {len(result)} found")
            return result
        except FixtureNotFoundError:
            raise

    async def get_series_by_author(
        self,
        author_name: str,
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Mock series by author - delegates to search_series.
        """
        return await self.search_series(title="", author=author_name, limit=limit)

    def _normalize_title(self, title: str, debug: bool = False) -> str:
        """
        Normalize title for deduplication (same logic as real client).
        """
        import re
        original = title

        normalized = title.lower()
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)
        normalized = re.sub(r',\s*(the|a|an)\s*$', '', normalized)
        normalized = re.sub(r'\b(edition|ed)\.?\s*\d+\b', '', normalized)
        normalized = re.sub(r'^(the|a|an)\s+', '', normalized)
        normalized = re.sub(r'\s+(the|a|an)\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        if debug:
            logger.debug(f"🔍 Mock title normalization: '{original}' → '{normalized}'")

        return normalized

    def _deduplicate_books(self, books: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """
        Deduplicate books by normalized title (same logic as real client).
        """
        if not books:
            return books

        if debug:
            logger.debug(f"📚 Mock deduplication starting with {len(books)} books")

        title_groups = {}
        for book in books:
            title = book.get("title", "")
            normalized = self._normalize_title(title, debug=debug)

            if normalized not in title_groups:
                title_groups[normalized] = []
            title_groups[normalized].append(book)

        deduplicated = []
        for normalized_title, book_list in title_groups.items():
            sorted_books = sorted(
                book_list,
                key=lambda b: (b.get("position") is None, b.get("position", float('inf')))
            )
            deduplicated.append(sorted_books[0])

        deduplicated.sort(key=lambda b: (b.get("position") is None, b.get("position", float('inf'))))

        logger.debug(f"📚 Mock deduplication: {len(books)} books → {len(deduplicated)} unique books")
        return deduplicated

    def _deduplicate_books_by_alt_titles(self, books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate books using alternative titles (same logic as real client).
        """
        if not books:
            return books

        book_title_sets = []
        for book in books:
            title_set = {self._normalize_title(book.get("title", ""))}
            for alt in book.get("alternative_titles", []):
                title_set.add(self._normalize_title(alt))
            book_title_sets.append((book, title_set))

        used = set()
        groups = []

        for i, (book1, titles1) in enumerate(book_title_sets):
            if i in used:
                continue

            group = [book1]
            used.add(i)

            for j, (book2, titles2) in enumerate(book_title_sets):
                if j <= i or j in used:
                    continue
                if titles1 & titles2:
                    group.append(book2)
                    used.add(j)

            groups.append(group)

        deduplicated = []
        for group in groups:
            sorted_group = sorted(
                group,
                key=lambda b: b.get("users_count", 0),
                reverse=True
            )
            deduplicated.append(sorted_group[0])

        logger.debug(f"📚 Mock alt-title deduplication: {len(books)} books → {len(deduplicated)} unique books")
        return deduplicated
