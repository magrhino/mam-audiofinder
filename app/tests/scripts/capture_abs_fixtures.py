#!/usr/bin/env python3
"""
Fixture capture script for Audiobookshelf API.

This script calls the real ABS API and saves responses as JSON fixtures
for use in mock mode testing.

Usage:
    # Activate virtual environment
    source tmp/bin/activate

    # Set ABS environment variables
    export ABS_BASE_URL="http://your-abs-server:13378"
    export ABS_API_KEY="your-api-key"
    export ABS_LIBRARY_ID="your-library-id"

    # Run script
    python app/tests/scripts/capture_abs_fixtures.py

Requirements:
    - ABS_BASE_URL, ABS_API_KEY, ABS_LIBRARY_ID must be set in environment
    - Audiobookshelf API must be accessible
    - Write access to app/tests/fixtures/abs/

The script will capture fixtures for:
    - Connection test
    - Common book verifications (Foundation, Harry Potter, etc.)
    - Cover fetches
    - Library item checks
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

from abs_client import AudiobookshelfClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ABSFixtureCapturer:
    """Captures ABS API responses and saves them as fixtures."""

    def __init__(self):
        """Initialize capturer."""
        self.client = AudiobookshelfClient()
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "abs"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Fixtures directory: {self.fixtures_dir}")

        if not self.client.is_configured:
            raise RuntimeError(
                "❌ ABS not configured. Set ABS_BASE_URL, ABS_API_KEY, ABS_LIBRARY_ID"
            )

        logger.info(f"✅ ABS configured: {self.client.base_url}")
        logger.info(f"✅ Library ID: {self.client.library_id}")

    def _save_fixture(self, filename: str, data: dict):
        """Save data to a fixture file."""
        filepath = self.fixtures_dir / f"{filename}.json"

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Saved fixture: {filename}.json ({filepath.stat().st_size} bytes)")

    def _sanitize_filename(self, s: str) -> str:
        """Sanitize string for use in filename."""
        return s.replace(" ", "_").replace("/", "_").replace("\\", "_")[:30]

    async def capture_test_connection(self):
        """Capture connection test response."""
        logger.info("🔍 Capturing test_connection")

        success, username = await self.client.test_connection()

        self._save_fixture("test_connection", {
            "success": success,
            "username": username
        })

        return (success, username)

    async def capture_verify_import(self, title: str, author: str = "", metadata: dict = None):
        """Capture import verification response."""
        logger.info(f"🔍 Capturing verify_import: '{title}' by '{author}'")

        result = await self.client.verify_import(title, author, metadata=metadata)

        # Build filename
        parts = [f"title={self._sanitize_filename(title)}"]
        if author:
            parts.append(f"author={self._sanitize_filename(author)}")

        filename = f"verify_import_{'_'.join(parts)}"

        self._save_fixture(filename, result)

        return result

    async def capture_fetch_cover(self, title: str, author: str = "", mam_id: str = ""):
        """Capture cover fetch response."""
        logger.info(f"🔍 Capturing fetch_cover: '{title}' by '{author}'")

        result = await self.client.fetch_cover(title, author, mam_id)

        # Build filename
        parts = [f"title={self._sanitize_filename(title)}"]
        if author:
            parts.append(f"author={self._sanitize_filename(author)}")

        filename = f"fetch_cover_{'_'.join(parts)}"

        self._save_fixture(filename, result)

        return result

    async def capture_check_library_items(self, items: list):
        """Capture library items check response."""
        logger.info(f"🔍 Capturing check_library_items: {len(items)} items")

        result = await self.client.check_library_items(items)

        # For default fixture, save common result
        self._save_fixture("check_library_items_default", result)

        return result

    async def capture_fetch_item_details(self, item_id: str):
        """Capture item details response."""
        logger.info(f"🔍 Capturing fetch_item_details: item_id={item_id}")

        result = await self.client.fetch_item_details(item_id)

        filename = f"fetch_item_details_item_id={item_id[:30]}"

        self._save_fixture(filename, result)

        return result

    async def run(self):
        """Capture all common fixtures."""
        logger.info("🚀 Starting ABS fixture capture...")
        logger.info("")

        # 1. Connection test
        logger.info("=" * 60)
        logger.info("STEP 1: Connection Test")
        logger.info("=" * 60)
        await self.capture_test_connection()
        logger.info("")

        # 2. Common books for verification
        # NOTE: Adjust these based on YOUR library contents
        test_books = [
            ("Foundation", "Isaac Asimov"),
            ("The Hobbit", "J.R.R. Tolkien"),
            ("Harry Potter and the Philosopher's Stone", "J.K. Rowling"),
        ]

        logger.info("=" * 60)
        logger.info("STEP 2: Import Verifications")
        logger.info("=" * 60)
        for title, author in test_books:
            try:
                await self.capture_verify_import(title, author)
            except Exception as e:
                logger.error(f"❌ Failed to capture verify_import for '{title}': {e}")
        logger.info("")

        logger.info("=" * 60)
        logger.info("STEP 3: Cover Fetches")
        logger.info("=" * 60)
        for title, author in test_books:
            try:
                await self.capture_fetch_cover(title, author)
            except Exception as e:
                logger.error(f"❌ Failed to capture fetch_cover for '{title}': {e}")
        logger.info("")

        # 3. Library check
        logger.info("=" * 60)
        logger.info("STEP 4: Library Items Check")
        logger.info("=" * 60)
        test_items = [
            ("Foundation", "Isaac Asimov"),
            ("The Hobbit", "J.R.R. Tolkien"),
            ("Harry Potter", "J.K. Rowling"),
            ("Unknown Title", "Unknown Author"),
        ]
        try:
            await self.capture_check_library_items(test_items)
        except Exception as e:
            logger.error(f"❌ Failed to capture check_library_items: {e}")
        logger.info("")

        logger.info("=" * 60)
        logger.info("✅ Fixture capture complete!")
        logger.info(f"📁 Location: {self.fixtures_dir}")
        logger.info("=" * 60)


async def main():
    """Main entry point."""
    try:
        capturer = ABSFixtureCapturer()
        await capturer.run()
        logger.info("")
        logger.info("✨ All fixtures captured successfully!")
        logger.info("")
        logger.info("📝 Next steps:")
        logger.info("   1. Review captured fixtures in app/tests/fixtures/abs/")
        logger.info("   2. Add more specific fixtures as needed for your tests")
        logger.info("   3. Run tests in mock mode: pytest app/tests/ -v")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ Fixture capture failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
