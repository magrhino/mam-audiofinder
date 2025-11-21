"""
Test enhanced ABS metadata search endpoint (/api/search/books).

Tests whether external provider metadata (Audible, Google, OpenLibrary, etc.)
via ABS provides richer data than current library-only approach.

This test suite validates if the new endpoint provides sufficient data to
replace the current fetch_item_details() logic.

Run with:
    pytest app/tests/test_enhanced_abs_metadata.py -v
    pytest app/tests/test_enhanced_abs_metadata.py -v --debug
    pytest app/tests/test_enhanced_abs_metadata.py::TestEnhancedMetadataEndpoint::test_provider_audible -v --debug

Environment:
    Test reads ABS credentials from environment variables (loaded from .env in container)
"""
import pytest
import sys
import os
import json
import random
import asyncio
from pathlib import Path
from typing import Optional, Dict, List

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_addoption(parser):
    """Add --debug flag to pytest."""
    parser.addoption(
        "--debug",
        action="store_true",
        default=False,
        help="Enable verbose debug output for test runs"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "debug: mark test to show debug output when --debug flag is used"
    )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def abs_client():
    """
    Get AudiobookshelfClient configured from environment variables.

    Uses standard config.py environment variables (already loaded from .env in container).

    Required environment variables:
        ABS_BASE_URL - Audiobookshelf server URL
        ABS_API_KEY - API key for authentication
        ABS_LIBRARY_ID - Library ID to test against
    """
    from abs_client import AudiobookshelfClient

    client = AudiobookshelfClient()

    if not client.is_configured:
        pytest.skip("⚠️  ABS not configured (check ABS_BASE_URL and ABS_API_KEY in .env)")

    if not client.library_id:
        pytest.skip("⚠️  ABS_LIBRARY_ID not configured in .env")

    return client


@pytest.fixture(scope="session")
def debug_mode(request):
    """Enable verbose debug output via --debug flag."""
    return request.config.getoption("--debug", default=False)


@pytest.fixture(scope="session")
def test_item_cache_file():
    """Path to cached test item ID file."""
    return Path("/tmp/abs_test_item_id.txt")


@pytest.fixture(scope="session")
def test_item_data_cache_file():
    """Path to cached test item data file."""
    return Path("/tmp/abs_test_item_data.json")


@pytest.fixture(scope="session")
def test_item_id(abs_client, test_item_cache_file, test_item_data_cache_file, debug_mode):
    """
    Get or create test item ID.
    - Checks /tmp/abs_test_item_id.txt
    - If not exists: randomly selects item from library, caches it
    - If exists: loads cached item_id

    Also caches item metadata for comparison tests.
    """
    # Check if cached
    if test_item_cache_file.exists():
        item_id = test_item_cache_file.read_text().strip()

        if debug_mode:
            # Load cached data if available
            if test_item_data_cache_file.exists():
                data = json.loads(test_item_data_cache_file.read_text())
                print(f"\n{'='*80}")
                print(f"📖 Using Cached Test Item")
                print(f"{'='*80}")
                print(f"  Item ID: {item_id}")
                print(f"  Title: {data.get('title', 'Unknown')}")
                print(f"  Author: {data.get('author', 'Unknown')}")
                print(f"  Cache File: {test_item_cache_file}")
                print(f"{'='*80}\n")
            else:
                print(f"\n📖 Using cached test item ID: {item_id}\n")

        return item_id

    # Select random item from library
    if debug_mode:
        print(f"\n{'='*80}")
        print(f"🎲 Selecting Random Test Item")
        print(f"{'='*80}")
        print(f"  Fetching library items...")

    # Use asyncio to run async method
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        items = loop.run_until_complete(abs_client._get_cached_library_items())
    finally:
        loop.close()

    if not items:
        pytest.skip("⚠️  No items in ABS library")

    # Select random item
    random_item = random.choice(items)
    item_id = random_item.get("id")
    metadata = random_item.get("media", {}).get("metadata", {})
    title = metadata.get("title", "Unknown")
    author = metadata.get("authorName", "Unknown")

    # Cache item ID
    test_item_cache_file.write_text(item_id)

    # Cache item data for debug output
    item_data = {
        "item_id": item_id,
        "title": title,
        "author": author,
        "narrator": metadata.get("narratorName", ""),
        "series": metadata.get("series", [])
    }
    test_item_data_cache_file.write_text(json.dumps(item_data, indent=2))

    if debug_mode:
        print(f"  Selected: {title}")
        print(f"  Author: {author}")
        print(f"  Item ID: {item_id}")
        print(f"  Cached to: {test_item_cache_file}")
        print(f"{'='*80}\n")

    return item_id


@pytest.fixture(scope="session")
def test_item_data(test_item_data_cache_file):
    """Load cached test item data."""
    if not test_item_data_cache_file.exists():
        return {}

    return json.loads(test_item_data_cache_file.read_text())


# ============================================================================
# Helper Functions
# ============================================================================

def print_debug_header(title: str, debug_mode: bool):
    """Print debug section header."""
    if not debug_mode:
        return

    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")


def print_debug_api_request(url: str, params: dict, debug_mode: bool):
    """Print debug info for API request."""
    if not debug_mode:
        return

    print(f"\nREQUEST:")
    print(f"  URL: {url}")
    print(f"  Params:")
    for key, value in params.items():
        print(f"    {key}: {value}")


def print_debug_api_response(status_code: int, results_count: int, debug_mode: bool):
    """Print debug info for API response."""
    if not debug_mode:
        return

    print(f"\nRESPONSE ({status_code}):")
    print(f"  Results: {results_count} book(s)")


def print_debug_metadata_result(result: dict, debug_mode: bool):
    """Print debug info for metadata result."""
    if not debug_mode:
        return

    print(f"\nFIRST RESULT:")
    print(f"  Title: {result.get('title', 'N/A')}")
    print(f"  Author: {result.get('author', 'N/A')}")
    print(f"  Narrator: {'✅ ' + result.get('narrator', '') if result.get('narrator') else '❌ (missing)'}")
    print(f"  Publisher: {'✅ ' + result.get('publisher', '') if result.get('publisher') else '❌ (missing)'}")

    series = result.get('series', [])
    if series:
        series_str = ", ".join([f"{s.get('series', '')} #{s.get('sequence', '?')}" for s in series])
        has_sequence = any(s.get('sequence', '').strip() for s in series)
        status = "✅" if has_sequence else "⚠️  (no sequence)"
        print(f"  Series: {status} {series_str}")
    else:
        print(f"  Series: ❌ (missing)")

    print(f"  Rating: {'✅ ' + str(result.get('rating', '')) if result.get('rating') else '❌ (missing)'}")
    print(f"  Region: {'✅ ' + result.get('region', '') if result.get('region') else '❌ (missing)'}")
    print(f"  Language: {'✅ ' + result.get('language', '') if result.get('language') else '❌ (missing)'}")
    print(f"  ASIN: {'✅ ' + result.get('asin', '') if result.get('asin') else '❌ (missing)'}")
    print(f"  ISBN: {'✅ ' + result.get('isbn', '') if result.get('isbn') else '❌ (missing)'}")


def print_debug_comparison(old_meta: dict, new_meta: dict, debug_mode: bool):
    """Print side-by-side comparison of old vs new metadata."""
    if not debug_mode:
        return

    print(f"\n{'='*80}")
    print(f"COMPARISON: Old vs New Metadata")
    print(f"{'='*80}")
    print(f"{'Field':<20} | {'Old Value':<25} | {'New Value':<25} | Status")
    print(f"{'-'*80}")

    # Define fields to compare
    fields = [
        ('narrator', 'narratorName'),
        ('publisher', 'publisher'),
        ('series', 'series'),
        ('rating', None),
        ('region', None),
        ('language', 'language'),
        ('asin', 'asin'),
        ('isbn', 'isbn'),
        ('description', 'description'),
    ]

    for new_field, old_field in fields:
        old_val = old_meta.get(old_field if old_field else new_field, '')
        new_val = new_meta.get(new_field, '')

        # Format values
        if new_field == 'series':
            old_val_str = f"{len(old_val)} items" if old_val else "(missing)"
            new_val_str = f"{len(new_val)} items" if new_val else "(missing)"

            # Check for sequence numbers
            old_has_seq = any(s.get('sequence', '').strip() for s in (old_val or []))
            new_has_seq = any(s.get('sequence', '').strip() for s in (new_val or []))

            if new_has_seq and not old_has_seq:
                status = "✅ ENHANCED"
            elif new_val and not old_val:
                status = "✅ NEW"
            elif new_val:
                status = "→ SAME"
            else:
                status = "❌ MISSING"
        elif new_field == 'description':
            old_len = len(str(old_val)) if old_val else 0
            new_len = len(str(new_val)) if new_val else 0
            old_val_str = f"{old_len} chars" if old_len > 0 else "(missing)"
            new_val_str = f"{new_len} chars" if new_len > 0 else "(missing)"

            if new_len > old_len * 1.5:
                status = "✅ ENHANCED"
            elif new_len > 0 and old_len == 0:
                status = "✅ NEW"
            elif new_len > 0:
                status = "→ SAME"
            else:
                status = "❌ MISSING"
        else:
            old_val_str = str(old_val)[:25] if old_val else "(missing)"
            new_val_str = str(new_val)[:25] if new_val else "(missing)"

            if new_val and not old_val:
                status = "✅ NEW"
            elif new_val:
                status = "→ SAME"
            else:
                status = "❌ MISSING"

        print(f"{new_field:<20} | {old_val_str:<25} | {new_val_str:<25} | {status}")

    print(f"{'='*80}\n")


def check_series_success(result: dict) -> bool:
    """
    Check if result contains series with numeric sequence.
    Success criteria: series array with at least one entry having a sequence number.
    """
    series = result.get('series', [])
    if not series:
        return False

    # Check if any series entry has a numeric sequence
    for s in series:
        sequence = s.get('sequence', '').strip()
        if sequence and sequence.isdigit():
            return True

    return False


# ============================================================================
# Test Classes
# ============================================================================

class TestEnhancedMetadataEndpoint:
    """Test /api/search/books endpoint functionality."""

    @pytest.mark.asyncio
    async def test_provider_audible(self, abs_client, test_item_id, test_item_data, debug_mode):
        """Test Audible provider via /api/search/books."""
        print_debug_header("PROVIDER TEST: audible", debug_mode)

        # Get item metadata for title/author
        title = test_item_data.get('title', '')
        author = test_item_data.get('author', '')

        if debug_mode:
            print(f"  Item ID: {test_item_id}")
            print(f"  Title: {title}")
            print(f"  Author: {author}")

        # Call enhanced endpoint (to be implemented)
        result = await abs_client.fetch_enhanced_metadata_test(
            item_id=test_item_id,
            providers=["audible"]
        )

        # Verify result structure
        assert result is not None
        assert 'new_metadata' in result
        assert 'old_metadata' in result

        new_meta = result['new_metadata']
        print_debug_metadata_result(new_meta, debug_mode)

        # Check for series with sequence
        has_series_success = check_series_success(new_meta)

        if debug_mode:
            if has_series_success:
                print(f"\n✅ SUCCESS: Series with sequence found!")
            else:
                print(f"\n⚠️  NO SERIES SEQUENCE: Will try next provider")

        # Print comparison
        print_debug_comparison(result['old_metadata'], new_meta, debug_mode)

    @pytest.mark.asyncio
    async def test_provider_google(self, abs_client, test_item_id, test_item_data, debug_mode):
        """Test Google provider via /api/search/books."""
        print_debug_header("PROVIDER TEST: google", debug_mode)

        title = test_item_data.get('title', '')
        author = test_item_data.get('author', '')

        if debug_mode:
            print(f"  Item ID: {test_item_id}")
            print(f"  Title: {title}")
            print(f"  Author: {author}")

        result = await abs_client.fetch_enhanced_metadata_test(
            item_id=test_item_id,
            providers=["google"]
        )

        assert result is not None
        new_meta = result['new_metadata']
        print_debug_metadata_result(new_meta, debug_mode)

        has_series_success = check_series_success(new_meta)

        if debug_mode:
            if has_series_success:
                print(f"\n✅ SUCCESS: Series with sequence found!")
            else:
                print(f"\n⚠️  NO SERIES SEQUENCE")

        print_debug_comparison(result['old_metadata'], new_meta, debug_mode)

    @pytest.mark.asyncio
    async def test_provider_openlibrary(self, abs_client, test_item_id, test_item_data, debug_mode):
        """Test OpenLibrary provider via /api/search/books."""
        print_debug_header("PROVIDER TEST: openlibrary", debug_mode)

        title = test_item_data.get('title', '')
        author = test_item_data.get('author', '')

        if debug_mode:
            print(f"  Item ID: {test_item_id}")
            print(f"  Title: {title}")
            print(f"  Author: {author}")

        result = await abs_client.fetch_enhanced_metadata_test(
            item_id=test_item_id,
            providers=["openlibrary"]
        )

        assert result is not None
        new_meta = result['new_metadata']
        print_debug_metadata_result(new_meta, debug_mode)

        has_series_success = check_series_success(new_meta)

        if debug_mode:
            if has_series_success:
                print(f"\n✅ SUCCESS: Series with sequence found!")
            else:
                print(f"\n⚠️  NO SERIES SEQUENCE")

        print_debug_comparison(result['old_metadata'], new_meta, debug_mode)

    @pytest.mark.asyncio
    async def test_stop_at_first_series_success(self, abs_client, test_item_id, test_item_data, debug_mode):
        """Test that provider iteration stops at first series success."""
        print_debug_header("TEST: Stop at First Success", debug_mode)

        providers = ["audible", "google", "openlibrary"]

        result = await abs_client.fetch_enhanced_metadata_test(
            item_id=test_item_id,
            providers=providers
        )

        assert result is not None
        assert 'provider_used' in result
        assert 'success' in result

        if debug_mode:
            print(f"  Providers Tried: {', '.join(providers)}")
            print(f"  Provider Used: {result.get('provider_used', 'N/A')}")
            print(f"  Success: {result.get('success', False)}")

            if result.get('success'):
                print(f"\n✅ Stopped at first successful provider: {result.get('provider_used')}")
            else:
                print(f"\n⚠️  No provider returned series with sequence")


class TestMetadataComparison:
    """Compare old vs new metadata fetch methods."""

    @pytest.mark.asyncio
    async def test_field_coverage_comparison(self, abs_client, test_item_id, debug_mode):
        """Compare field coverage between old and new methods."""
        print_debug_header("FIELD COVERAGE COMPARISON", debug_mode)

        result = await abs_client.fetch_enhanced_metadata_test(item_id=test_item_id)

        old_meta = result['old_metadata']
        new_meta = result['new_metadata']

        # Count populated fields
        old_fields = sum(1 for v in old_meta.values() if v)
        new_fields = sum(1 for v in new_meta.values() if v)

        if debug_mode:
            print(f"  Old Method Fields: {old_fields}")
            print(f"  New Method Fields: {new_fields}")
            print(f"  Improvement: {new_fields - old_fields} additional fields")

        # New method should provide at least as many fields
        assert new_fields >= old_fields, "New method should provide at least as many fields as old method"

    @pytest.mark.asyncio
    async def test_narrator_publisher_presence(self, abs_client, test_item_id, debug_mode):
        """Verify narrator and publisher fields are populated."""
        print_debug_header("NARRATOR & PUBLISHER VALIDATION", debug_mode)

        result = await abs_client.fetch_enhanced_metadata_test(item_id=test_item_id)
        new_meta = result['new_metadata']

        has_narrator = bool(new_meta.get('narrator', '').strip())
        has_publisher = bool(new_meta.get('publisher', '').strip())

        if debug_mode:
            print(f"  Narrator: {'✅ ' + new_meta.get('narrator', '') if has_narrator else '❌ Missing'}")
            print(f"  Publisher: {'✅ ' + new_meta.get('publisher', '') if has_publisher else '❌ Missing'}")

        # At least one should be populated for audiobooks
        assert has_narrator or has_publisher, "Either narrator or publisher should be populated"


class TestAllProviders:
    """Test all configured providers systematically."""

    @pytest.mark.asyncio
    async def test_all_providers_sequentially(self, abs_client, test_item_id, debug_mode):
        """Test all providers in sequence until success."""
        print_debug_header("ALL PROVIDERS TEST", debug_mode)

        providers = ["audible", "google", "openlibrary", "itunes"]

        for provider in providers:
            if debug_mode:
                print(f"\n--- Trying Provider: {provider} ---")

            try:
                result = await abs_client.fetch_enhanced_metadata_test(
                    item_id=test_item_id,
                    providers=[provider]
                )

                new_meta = result['new_metadata']
                has_success = check_series_success(new_meta)

                if debug_mode:
                    print(f"  Result: {'✅ SUCCESS' if has_success else '⚠️  No series sequence'}")

                if has_success:
                    if debug_mode:
                        print(f"\n🎉 SUCCESS: {provider} returned series with sequence!")
                    break

            except Exception as e:
                if debug_mode:
                    print(f"  Error: {e}")
                continue
