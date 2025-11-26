#!/usr/bin/env python3
"""
Fixture capture script for Hardcover API.

This script calls the real Hardcover API and saves responses as JSON fixtures
for use in mock mode testing.

Usage:
    # Activate virtual environment
    source tmp/bin/activate

    # Set API token
    export HARDCOVER_API_TOKEN="your-token-here"

    # Run script
    python app/tests/scripts/capture_fixtures.py

Requirements:
    - HARDCOVER_API_TOKEN must be set in environment
    - Hardcover API must be accessible
    - Write access to app/tests/fixtures/hardcover/

The script will capture fixtures for:
    - Common series searches (Foundation, Harry Potter, etc.)
    - Series book listings
    - Book searches
    - Edge cases (empty results, not found, etc.)
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# Add workspace root and app directory to path
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "app"))

from hardcover_client import HardcoverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FixtureCapturer:
    """Captures API responses and saves them as fixtures."""

    def __init__(self):
        """Initialize capturer."""
        self.client = HardcoverClient()
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "hardcover"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Fixtures directory: {self.fixtures_dir}")

    def _save_fixture(self, filename: str, data: dict):
        """Save data to a fixture file."""
        filepath = self.fixtures_dir / f"{filename}.json"

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Saved fixture: {filename}.json ({filepath.stat().st_size} bytes)")

    def _sanitize_filename(self, s: str) -> str:
        """Sanitize string for use in filename."""
        return s.replace(" ", "_").replace("/", "_")[:30]

    async def capture_search_series(self, title: str, author: str = "", limit: int = 10):
        """Capture series search fixture."""
        logger.info(f"🔍 Capturing search_series: '{title}' (author='{author}', limit={limit})")

        result = await self.client.search_series(title, author, limit)

        # Build filename
        parts = [f"title={self._sanitize_filename(title)}"]
        if author:
            parts.append(f"author={self._sanitize_filename(author)}")
        if limit != 10:
            parts.append(f"limit={limit}")

        filename = f"search_series_{'_'.join(parts)}"

        # Save as fixture
        self._save_fixture(filename, {"series": result or []})

        return result

    async def capture_list_series_books(self, series_id: int):
        """Capture series books listing fixture."""
        logger.info(f"📚 Capturing list_series_books: {series_id}")

        result = await self.client.list_series_books(series_id, deduplicate=False)

        filename = f"list_series_books_series_id={series_id}"
        self._save_fixture(filename, result or {})

        return result

    async def capture_search_book_by_title(self, title: str, author: str = "", limit: int = 5):
        """Capture book title search fixture."""
        logger.info(f"🔍 Capturing search_book_by_title: '{title}' (author='{author}', limit={limit})")

        result = await self.client.search_book_by_title(title, author, limit)

        parts = [f"title={self._sanitize_filename(title)}"]
        if author:
            parts.append(f"author={self._sanitize_filename(author)}")
        if limit != 5:
            parts.append(f"limit={limit}")

        filename = f"search_book_by_title_{'_'.join(parts)}"
        self._save_fixture(filename, {"books": result or []})

        return result

    async def capture_search_book_advanced(self, title: str, author: str = "", limit: int = 5):
        """Capture advanced book search fixture."""
        logger.info(f"🔍 Capturing search_book_advanced: '{title}' (author='{author}', limit={limit})")

        result = await self.client.search_book_advanced(title, author, limit, deduplicate=False)

        parts = [f"title={self._sanitize_filename(title)}"]
        if author:
            parts.append(f"author={self._sanitize_filename(author)}")
        if limit != 5:
            parts.append(f"limit={limit}")

        filename = f"search_book_advanced_{'_'.join(parts)}"
        self._save_fixture(filename, {"books": result or []})

        return result

    async def capture_get_books_by_ids(self, book_ids: list):
        """Capture batch book lookup fixture."""
        logger.info(f"🔍 Capturing get_books_by_ids: {book_ids}")

        result = await self.client.get_books_by_ids(book_ids, use_cache=False)

        # Convert int keys to strings for JSON
        books_dict = {str(k): v for k, v in result.items()}

        ids_str = "_".join(map(str, sorted(book_ids)))
        filename = f"get_books_by_ids_ids={ids_str}"
        self._save_fixture(filename, {"books": books_dict})

        return result

    async def capture_search_books_by_author(self, author: str, limit: int = 10):
        """Capture author book search fixture."""
        logger.info(f"🔍 Capturing search_books_by_author: '{author}' (limit={limit})")

        result = await self.client.search_books_by_author(author, limit)

        parts = [f"author={self._sanitize_filename(author)}"]
        if limit != 10:
            parts.append(f"limit={limit}")

        filename = f"search_books_by_author_{'_'.join(parts)}"
        self._save_fixture(filename, {"books": result or []})

        return result

    async def capture_all_fixtures(self):
        """Capture a comprehensive set of fixtures for testing."""
        logger.info("=" * 80)
        logger.info("🚀 Starting fixture capture...")
        logger.info("=" * 80)

        # Check API configuration
        if not self.client.is_configured:
            logger.error("❌ HARDCOVER_API_TOKEN not set! Cannot capture fixtures.")
            logger.error("   Set it with: export HARDCOVER_API_TOKEN='your-token-here'")
            return False

        try:
            # Reset counters
            HardcoverClient.reset_counters()

            # Series searches - popular series for testing
            series_searches = [
                ("Foundation", ""),
                ("Harry Potter", ""),
                ("Lord of the Rings", ""),
                ("The Expanse", ""),
                ("Discworld", "Terry Pratchett"),
                ("Mistborn", "Brandon Sanderson"),
            ]

            series_ids = []
            for title, author in series_searches:
                result = await self.capture_search_series(title, author)
                if result and len(result) > 0:
                    # Save first series ID for book listing
                    series_ids.append(result[0]["series_id"])
                await asyncio.sleep(1)  # Rate limiting

            # Series book listings
            for series_id in series_ids[:3]:  # Just first 3 to avoid too many requests
                await self.capture_list_series_books(series_id)
                await asyncio.sleep(1)

            # Book title searches
            book_searches = [
                ("Foundation", "Isaac Asimov"),
                ("Harry Potter and the Philosopher's Stone", ""),
                ("The Fellowship of the Ring", ""),
                ("Project Hail Mary", "Andy Weir"),
            ]

            for title, author in book_searches:
                await self.capture_search_book_by_title(title, author)
                await asyncio.sleep(1)

            # Advanced book searches (with audiobook metadata)
            for title, author in book_searches[:2]:  # Just first 2
                await self.capture_search_book_advanced(title, author)
                await asyncio.sleep(1)

            # Edge cases
            logger.info("📝 Capturing edge cases...")

            # Empty results
            await self.capture_search_series("ThisSeriesDoesNotExist12345XYZ", "")
            await asyncio.sleep(1)

            await self.capture_search_book_by_title("ThisBookDoesNotExist12345XYZ", "")
            await asyncio.sleep(1)

            # Get final stats
            request_count = HardcoverClient.get_request_count()
            logger.info("=" * 80)
            logger.info(f"✅ Fixture capture complete!")
            logger.info(f"📊 Total API requests: {request_count}")
            logger.info(f"📁 Fixtures saved to: {self.fixtures_dir}")
            logger.info(f"📄 Total fixtures: {len(list(self.fixtures_dir.glob('*.json')))}")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"❌ Fixture capture failed: {e}", exc_info=True)
            return False


async def main():
    """Main entry point."""
    capturer = FixtureCapturer()
    success = await capturer.capture_all_fixtures()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
