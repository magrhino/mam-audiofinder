#!/usr/bin/env python3
"""
Test Hardcover API integration.
Run this inside the container to verify Hardcover API configuration and connectivity.

Usage:
    python test_hardcover_api.py                         # Run all tests
    python test_hardcover_api.py --search "Mistborn"     # Test series search only
    python test_hardcover_api.py --series 12345          # Test series books only
    python test_hardcover_api.py --series-limits 997     # Test series books with limit variations
    python test_hardcover_api.py --author "Brandon Sanderson"  # Test author search
    python test_hardcover_api.py --framework basic       # Run basic framework tests
    python test_hardcover_api.py --limits                # Test limit variations
    python test_hardcover_api.py --fields                # Test field extraction
"""
import sys
import asyncio
import argparse
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import HARDCOVER_API_TOKEN, HARDCOVER_BASE_URL, HARDCOVER_CACHE_TTL
from hardcover_client import hardcover_client


def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_result(label, value, indent=0):
    """Print formatted result."""
    prefix = "  " * indent
    print(f"{prefix}{label:<30} {value}")


def print_request_stats(start_count: int, start_cache: int, label: str = "Test"):
    """Print request statistics."""
    end_count = hardcover_client.get_request_count()
    end_cache = hardcover_client.get_cache_hit_count()
    requests_made = end_count - start_count
    cache_hits = end_cache - start_cache
    print(f"\n📊 {label} Statistics:")
    print_result("API Requests Made:", requests_made, indent=1)
    print_result("Cache Hits:", cache_hits, indent=1)
    print_result("Total Requests (session):", end_count, indent=1)
    print_result("Total Cache Hits (session):", end_cache, indent=1)


async def wait_between_tests(seconds: float = 1.0):
    """Wait between tests to avoid rate limiting."""
    print(f"\n⏱️  Waiting {seconds}s between tests...")
    await asyncio.sleep(seconds)


async def test_configuration():
    """Test Hardcover API configuration."""
    print_header("Configuration Check")

    config_ok = True

    # Check API token
    if HARDCOVER_API_TOKEN:
        token_display = HARDCOVER_API_TOKEN[:8] + "..." + HARDCOVER_API_TOKEN[-4:] if len(HARDCOVER_API_TOKEN) > 12 else "***"
        print_result("✓ API Token:", f"Configured ({token_display})")
    else:
        print_result("✗ API Token:", "NOT CONFIGURED")
        config_ok = False

    # Check base URL
    if HARDCOVER_BASE_URL:
        print_result("✓ Base URL:", HARDCOVER_BASE_URL)
    else:
        print_result("✗ Base URL:", "NOT CONFIGURED")
        config_ok = False

    # Check cache TTL
    print_result("✓ Cache TTL:", f"{HARDCOVER_CACHE_TTL}s")

    # Check client status
    if hardcover_client.is_configured:
        print_result("✓ Client Status:", "Ready")
    else:
        print_result("✗ Client Status:", "Not configured")
        config_ok = False

    return config_ok


async def test_series_search(query="Mistborn", author="", limit=5):
    """Test series search functionality."""
    print_header(f"Series Search Test: '{query}'")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    try:
        print(f"\n🔍 Searching for series: '{query}'")
        if author:
            print(f"   Author filter: '{author}'")
        print(f"   Limit: {limit}")

        results = await hardcover_client.search_series(
            title=query,
            author=author,
            limit=limit
        )

        # Check if API call failed (returns None)
        if results is None:
            print("\n❌ API call failed - check logs above for details")
            return False

        print(f"\n✅ Search returned {len(results)} results\n")

        if not results:
            print("ℹ️  No series found matching query (this is OK)")
            return True

        for i, series in enumerate(results, 1):
            print(f"Result #{i}:")
            print_result("Series ID:", series.get('series_id'), indent=1)
            print_result("Name:", series.get('series_name'), indent=1)
            print_result("Author:", series.get('author_name'), indent=1)
            print_result("Book Count:", series.get('book_count'), indent=1)
            print_result("Readers:", series.get('readers_count'), indent=1)
            books = series.get('books', [])
            if books:
                print_result("Book Titles:", f"({len(books)} titles)", indent=1)
                for j, title in enumerate(books[:3], 1):  # Show first 3
                    print_result(f"  {j}.", title, indent=1)
                if len(books) > 3:
                    print_result("  ...", f"(+{len(books)-3} more)", indent=1)
            print()

        return True

    except Exception as e:
        print(f"\n❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_series_books(series_id=None, show_stats=True):
    """Test fetching books for a series."""
    if series_id is None:
        # First search for a series to test with
        print_header("Finding a test series...")
        try:
            results = await hardcover_client.search_series("Stormlight", limit=1)
            if results is None:
                print("❌ API call failed when searching for test series")
                return False
            if not results:
                print("⚠️  Could not find test series, skipping books test")
                return True
            series_id = results[0]['series_id']
            print(f"✓ Using series: {results[0]['series_name']} (ID: {series_id})")
        except Exception as e:
            print(f"❌ Failed to find test series: {e}")
            return False

    print_header(f"Series Books Test: ID {series_id}")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    try:
        if show_stats:
            start_req = hardcover_client.get_request_count()
            start_cache = hardcover_client.get_cache_hit_count()

        print(f"\n📚 Fetching books for series ID {series_id}...")

        result = await hardcover_client.list_series_books(series_id)

        if not result:
            print(f"❌ Series {series_id} not found")
            return False

        print(f"\n✅ Series found: {result['series_name']}")
        print(f"   Author: {result['author_name']}")
        print(f"   Books: {len(result['books'])}\n")

        # Note: Books are now simple title strings (limited to 5) from search endpoint
        print("   📚 Book titles:")
        for i, book_title in enumerate(result['books'], 1):
            print(f"      {i}. {book_title}")

        if not result['books']:
            print("      (no books returned)")

        if show_stats:
            print_request_stats(start_req, start_cache, f"Series Books (ID {series_id})")

        return True

    except Exception as e:
        print(f"\n❌ Books fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_series_books_limit_variations(series_id=997):
    """Test fetching books for a specific series with different limit values.

    Tests limit variations to explore how many books can be retrieved.
    Default series_id=997 as requested by user.
    Note: Pagination (offset/page) has been removed as it's non-functional.
    """
    print_header(f"Series Books Limit Test: ID {series_id}")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    # Track request statistics
    start_req = hardcover_client.get_request_count()
    start_cache = hardcover_client.get_cache_hit_count()

    # Test different limit values
    limits_to_test = [5, 10, 20, 30]

    try:
        # First, get the series info to know what we're testing
        print(f"\n📚 Testing series ID {series_id} with various limits...")

        basic_result = await hardcover_client.list_series_books(series_id)

        if not basic_result:
            print(f"❌ Series {series_id} not found")
            return False

        series_name = basic_result['series_name']
        author_name = basic_result['author_name']

        print(f"\n✅ Series: '{series_name}'")
        print(f"   Author: {author_name}")
        print(f"   Default books count: {len(basic_result['books'])}\n")

        print("="*70)
        print("Testing search with different limit values:")
        print("="*70)

        # Track unique book titles
        all_books = set()

        for limit in limits_to_test:
            print(f"\n🔍 Test with limit={limit}")

            # Search for this series by name with different limits
            search_results = await hardcover_client.search_series(
                title=series_name,
                limit=limit
            )

            if search_results is None:
                print(f"  ❌ Search failed")
                continue

            if not search_results:
                print(f"  ⚠️  No results found")
                continue

            # Find the matching series in results
            matching_series = None
            for result in search_results:
                if str(result.get('series_id')) == str(series_id):
                    matching_series = result
                    break

            if matching_series:
                books = matching_series.get('books', [])
                print(f"  ✅ Found series in results")
                print(f"     Books returned: {len(books)}")
                print(f"     Total results: {len(search_results)}")

                # Add to our collection
                books_before = len(all_books)
                for book in books:
                    all_books.add(book)
                new_books = len(all_books) - books_before

                print(f"     New unique books: {new_books}")

                # Show first few books
                if books:
                    print(f"     Sample books:")
                    for i, book in enumerate(books[:3], 1):
                        print(f"       {i}. {book}")
                    if len(books) > 3:
                        print(f"       ... (+{len(books)-3} more)")
            else:
                print(f"  ⚠️  Series {series_id} not in results")

            # Wait between requests
            await asyncio.sleep(0.5)

        print("\n" + "="*70)
        print(f"📊 Summary:")
        print(f"   Unique books discovered: {len(all_books)}")
        print(f"   Limits tested: {limits_to_test}")
        print("="*70)

        if all_books:
            print("\n📚 All unique book titles found:")
            for i, book in enumerate(sorted(all_books), 1):
                print(f"   {i}. {book}")

        print_request_stats(start_req, start_cache, f"Series {series_id} Limit Test")
        return True

    except Exception as e:
        print(f"\n❌ Limit test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rate_limiting():
    """Test rate limiting mechanism."""
    print_header("Rate Limiting Test")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    print("\n🔄 Testing rate limiter (sending 3 rapid requests)...")

    try:
        import time
        start = time.time()

        # Send 3 rapid search requests
        for i in range(3):
            print(f"\n  Request {i+1}...")
            result = await hardcover_client.search_series("Test", limit=1)
            if result is None:
                print(f"    ❌ Request {i+1} failed")
                return False

        elapsed = time.time() - start
        print(f"\n✓ Completed 3 requests in {elapsed:.2f}s")

        if elapsed < 0.5:
            print("  ✓ Rate limiter allows rapid sequential requests")
        else:
            print("  ℹ️  Some delay observed (expected if approaching limit)")

        return True

    except Exception as e:
        print(f"\n❌ Rate limiting test failed: {e}")
        return False


async def test_caching():
    """Test caching mechanism."""
    print_header("Caching Test")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    print("\n💾 Testing cache (same query twice)...")

    try:
        import time

        # First request (should hit API)
        print("\n  Request 1 (should query API)...")
        start1 = time.time()
        result1 = await hardcover_client.search_series("Mistborn", limit=3)
        time1 = time.time() - start1
        if result1 is None:
            print("  ❌ First request failed")
            return False
        print(f"  ✓ Completed in {time1:.3f}s")

        # Second request (should hit cache)
        print("\n  Request 2 (should hit cache)...")
        start2 = time.time()
        result2 = await hardcover_client.search_series("Mistborn", limit=3)
        time2 = time.time() - start2
        if result2 is None:
            print("  ❌ Second request failed")
            return False
        print(f"  ✓ Completed in {time2:.3f}s")

        # Compare results
        if result1 == result2:
            print("\n  ✓ Results match")
        else:
            print("\n  ⚠ Results differ (unexpected)")

        # Check if second request was faster (cache hit)
        if time2 < time1 * 0.5:  # At least 50% faster
            print(f"  ✓ Cache speedup detected ({time1/time2:.1f}x faster)")
        else:
            print(f"  ℹ️  No significant speedup (may still be cached)")

        return True

    except Exception as e:
        print(f"\n❌ Caching test failed: {e}")
        return False


async def test_author_series_search(author="Brandon Sanderson", limit=10):
    """Test series search by author name."""
    print_header(f"Author Series Search Test: '{author}'")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    try:
        # Track requests
        start_req = hardcover_client.get_request_count()
        start_cache = hardcover_client.get_cache_hit_count()

        print(f"\n🔍 Searching for series by author: '{author}'")
        print(f"   Limit: {limit}")

        results = await hardcover_client.get_series_by_author(
            author_name=author,
            limit=limit
        )

        if results is None:
            print("\n❌ API call failed - check logs above for details")
            print_request_stats(start_req, start_cache, "Author Series Search")
            return False

        print(f"\n✅ Search returned {len(results)} series\n")

        if not results:
            print("ℹ️  No series found for this author (this may be OK)")
            print_request_stats(start_req, start_cache, "Author Series Search")
            return True

        for i, series in enumerate(results[:5], 1):  # Show first 5
            print(f"Series #{i}:")
            print_result("Series ID:", series.get('series_id'), indent=1)
            print_result("Name:", series.get('series_name'), indent=1)
            print_result("Author:", series.get('author_name'), indent=1)
            print_result("Book Count:", series.get('book_count'), indent=1)
            books = series.get('books', [])
            if books:
                print_result("Books:", f"{len(books)} titles", indent=1)
                for j, title in enumerate(books[:3], 1):
                    print_result(f"  {j}.", title, indent=1)
            print()

        if len(results) > 5:
            print(f"   ... and {len(results) - 5} more series\n")

        print_request_stats(start_req, start_cache, "Author Series Search")
        return True

    except Exception as e:
        print(f"\n❌ Author series search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_limit_variations():
    """Test different limit values."""
    print_header("Limit Variation Tests")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    limits_to_test = [1, 5, 10, 20]
    test_query = "Stormlight"

    try:
        start_req = hardcover_client.get_request_count()
        start_cache = hardcover_client.get_cache_hit_count()

        for limit in limits_to_test:
            print(f"\n🔍 Testing limit={limit} for query '{test_query}'")

            results = await hardcover_client.search_series(test_query, limit=limit)

            if results is None:
                print(f"  ❌ API call failed for limit={limit}")
                continue

            actual_count = len(results)
            print(f"  ✅ Requested: {limit}, Received: {actual_count}")

            if actual_count <= limit:
                print(f"  ✓ Result count respects limit")
            else:
                print(f"  ⚠️  Result count exceeds limit!")

            # Wait between requests to avoid rate limiting
            if limit != limits_to_test[-1]:
                await asyncio.sleep(0.5)

        print_request_stats(start_req, start_cache, "Limit Variations")
        return True

    except Exception as e:
        print(f"\n❌ Limit variation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_field_extraction():
    """Test extraction of specific fields from series data."""
    print_header("Field Extraction Test")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    try:
        start_req = hardcover_client.get_request_count()
        start_cache = hardcover_client.get_cache_hit_count()

        print(f"\n🔍 Searching for series to test field extraction")

        results = await hardcover_client.search_series("Mistborn", limit=3)

        if results is None:
            print("\n❌ API call failed")
            print_request_stats(start_req, start_cache, "Field Extraction")
            return False

        if not results:
            print("\n⚠️  No results found")
            print_request_stats(start_req, start_cache, "Field Extraction")
            return True

        print(f"\n✅ Testing field extraction on {len(results)} series\n")

        # Fields to check
        expected_fields = ['series_id', 'series_name', 'author_name', 'book_count', 'readers_count', 'books']

        all_passed = True
        for i, series in enumerate(results, 1):
            print(f"Series #{i}: {series.get('series_name', 'Unknown')}")

            for field in expected_fields:
                if field in series:
                    value = series[field]
                    value_type = type(value).__name__
                    if field == 'books' and isinstance(value, list):
                        print_result(f"✓ {field}:", f"list[{len(value)}] - {value_type}", indent=1)
                    else:
                        print_result(f"✓ {field}:", f"{value} ({value_type})", indent=1)
                else:
                    print_result(f"✗ {field}:", "MISSING", indent=1)
                    all_passed = False

            print()

        print_request_stats(start_req, start_cache, "Field Extraction")
        return all_passed

    except Exception as e:
        print(f"\n❌ Field extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_books_by_author(author="Brandon Sanderson", limit=10):
    """Test fetching books by author with field selection."""
    print_header(f"Books By Author Test: '{author}'")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    try:
        start_req = hardcover_client.get_request_count()
        start_cache = hardcover_client.get_cache_hit_count()

        # Test with different field combinations (only valid fields)
        field_sets = [
            ["title", "description"],
            ["title"],
        ]

        for i, fields in enumerate(field_sets, 1):
            print(f"\n🔍 Test {i}: Fetching books with fields: {', '.join(fields)}")

            results = await hardcover_client.search_books_by_author(
                author_name=author,
                limit=limit,
                fields=fields
            )

            if results is None:
                print(f"  ❌ API call failed for field set {i}")
                continue

            print(f"  ✅ Retrieved {len(results)} books")

            if results:
                # Show first book as example
                first_book = results[0]
                print(f"\n  Example (first book):")
                for field in fields:
                    value = first_book.get(field)
                    if isinstance(value, list):
                        print_result(field + ":", f"[{len(value)} items]", indent=2)
                    elif isinstance(value, str) and len(value) > 60:
                        print_result(field + ":", value[:60] + "...", indent=2)
                    else:
                        print_result(field + ":", value, indent=2)

            # Wait between requests
            if i < len(field_sets):
                await asyncio.sleep(0.5)

        print_request_stats(start_req, start_cache, "Books By Author")
        return True

    except Exception as e:
        print(f"\n❌ Books by author test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pagination_formats():
    """Test pagination with offset vs page-based approaches."""
    print_header("Pagination Format Test")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping test - Hardcover API not configured")
        return False

    try:
        start_req = hardcover_client.get_request_count()
        start_cache = hardcover_client.get_cache_hit_count()

        test_query = "Mistborn"
        per_page = 5

        # Test 1: Search with per_page only (baseline)
        print(f"\n🔍 Test 1: Baseline search (per_page={per_page})")
        baseline = await hardcover_client.search_series(test_query, limit=per_page)

        if baseline is None:
            print("  ❌ Baseline search failed")
            return False

        print(f"  ✅ Baseline returned {len(baseline)} results")
        if baseline:
            print(f"     First result: {baseline[0].get('series_name')}")

        await asyncio.sleep(1.0)

        # Test 2: Try GraphQL with page parameter
        print(f"\n🔍 Test 2: GraphQL with page parameter (per_page={per_page}, page=1)")

        query_with_page = """
        query SearchSeriesWithPage($query: String!, $queryType: String!, $perPage: Int!, $page: Int!) {
          search(query: $query, query_type: $queryType, per_page: $perPage, page: $page) {
            results
          }
        }
        """

        variables_page = {
            "query": test_query,
            "queryType": "Series",
            "perPage": per_page,
            "page": 1
        }

        data_page = await hardcover_client._execute_graphql(query_with_page, variables_page)

        if data_page is None:
            print("  ❌ Page-based query failed")
        else:
            search_data = data_page.get("search", {})
            results = search_data.get("results", {})

            if isinstance(results, str):
                import json
                results = json.loads(results)

            hits = results.get("hits", []) if isinstance(results, dict) else []
            print(f"  ✅ Page-based query returned {len(hits)} hits")

            if hits and baseline:
                # Compare first result IDs
                page_first_id = hits[0].get("document", {}).get("id")
                baseline_first_id = baseline[0].get("series_id")

                if page_first_id == baseline_first_id:
                    print(f"     ✓ First result matches baseline (ID: {page_first_id})")
                else:
                    print(f"     ⚠️  Different first result (page: {page_first_id}, baseline: {baseline_first_id})")

        await asyncio.sleep(1.0)

        # Test 3: Try GraphQL with page=2 to see if pagination works
        print(f"\n🔍 Test 3: GraphQL with page=2 (per_page={per_page}, page=2)")

        variables_page2 = {
            "query": test_query,
            "queryType": "Series",
            "perPage": per_page,
            "page": 2
        }

        data_page2 = await hardcover_client._execute_graphql(query_with_page, variables_page2)

        if data_page2 is None:
            print("  ❌ Page 2 query failed")
        else:
            search_data = data_page2.get("search", {})
            results = search_data.get("results", {})

            if isinstance(results, str):
                import json
                results = json.loads(results)

            hits = results.get("hits", []) if isinstance(results, dict) else []
            print(f"  ✅ Page 2 query returned {len(hits)} hits")

            # Check if results are different from page 1
            if hits and data_page:
                page1_results = data_page.get("search", {}).get("results", {})
                if isinstance(page1_results, str):
                    page1_results = json.loads(page1_results)
                page1_hits = page1_results.get("hits", []) if isinstance(page1_results, dict) else []

                if page1_hits:
                    page1_first_id = page1_hits[0].get("document", {}).get("id")
                    page2_first_id = hits[0].get("document", {}).get("id") if hits else None

                    if page1_first_id != page2_first_id:
                        print(f"     ✓ Page 2 has different results (pagination working!)")
                        print(f"       Page 1 first: {page1_hits[0].get('document', {}).get('name')}")
                        print(f"       Page 2 first: {hits[0].get('document', {}).get('name') if hits else 'N/A'}")
                    else:
                        print(f"     ⚠️  Page 2 returns same results as page 1 (pagination may not work)")

        print_request_stats(start_req, start_cache, "Pagination Format Test")
        return True

    except Exception as e:
        print(f"\n❌ Pagination test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_framework_basic():
    """Basic testing framework - simple searches with request counting."""
    print_header("Framework: Basic Tests")

    if not hardcover_client.is_configured:
        print("⚠️  Skipping framework - Hardcover API not configured")
        return False

    # Reset counters for this framework
    hardcover_client.reset_counters()
    start_time = time.time()

    tests = [
        ("Mistborn", ""),
        ("Stormlight", ""),
        ("Kingkiller", ""),
    ]

    try:
        for query, author in tests:
            print(f"\n🔍 Searching: '{query}'")
            results = await hardcover_client.search_series(query, author=author, limit=5)

            if results is None:
                print(f"  ❌ Failed")
                continue

            print(f"  ✅ Found {len(results)} results")
            await asyncio.sleep(0.5)  # Wait between requests

        elapsed = time.time() - start_time
        print(f"\n✅ Basic framework completed in {elapsed:.2f}s")
        print_request_stats(0, 0, "Basic Framework")
        return True

    except Exception as e:
        print(f"\n❌ Basic framework failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪 "*25)
    print("  HARDCOVER API INTEGRATION TEST SUITE")
    print("🧪 "*25)

    results = []

    # Reset counters at start
    hardcover_client.reset_counters()

    # Test 1: Configuration
    results.append(("Configuration", await test_configuration()))
    await wait_between_tests(0.5)

    # Test 2: Series Search
    results.append(("Series Search", await test_series_search("Mistborn")))
    await wait_between_tests(1.0)

    # Test 3: Series Books
    results.append(("Series Books", await test_series_books()))
    await wait_between_tests(1.0)

    # Test 4: Rate Limiting
    results.append(("Rate Limiting", await test_rate_limiting()))
    await wait_between_tests(1.0)

    # Test 5: Caching
    results.append(("Caching", await test_caching()))
    await wait_between_tests(1.0)

    # Test 6: Author Series Search
    results.append(("Author Series Search", await test_author_series_search()))
    await wait_between_tests(1.0)

    # Test 7: Limit Variations
    results.append(("Limit Variations", await test_limit_variations()))
    await wait_between_tests(1.0)

    # Test 8: Field Extraction
    results.append(("Field Extraction", await test_field_extraction()))
    await wait_between_tests(1.0)

    # Test 9: Books By Author
    results.append(("Books By Author", await test_books_by_author()))
    await wait_between_tests(1.0)

    # Test 10: Series Books Limit Variations (ID 997)
    results.append(("Series Limit Variations", await test_series_books_limit_variations(997)))
    await wait_between_tests(1.0)

    # Test 11: Framework - Basic
    results.append(("Framework: Basic", await test_framework_basic()))

    # Summary
    print_header("Test Summary")
    print()

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:<25} {status}")

    print()
    print("="*70)
    print(f"  Results: {passed}/{total} tests passed")
    print("="*70)

    return passed == total


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Hardcover API integration")
    parser.add_argument("--search", metavar="QUERY", help="Test series search with query")
    parser.add_argument("--author", metavar="AUTHOR", help="Test author search or filter")
    parser.add_argument("--series", metavar="ID", type=int, help="Test series books with ID")
    parser.add_argument("--series-limits", metavar="ID", type=int, help="Test series books limit variations (default: 997)")
    parser.add_argument("--limits", action="store_true", help="Test limit variations")
    parser.add_argument("--fields", action="store_true", help="Test field extraction")
    parser.add_argument("--pagination", action="store_true", help="Test pagination formats (offset vs page)")
    parser.add_argument("--framework", metavar="NAME", choices=["basic"],
                        help="Run specific framework: basic")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")

    args = parser.parse_args()

    # Determine which tests to run
    success = True

    if args.search:
        success = await test_configuration()
        if success:
            author_filter = args.author if args.author else ""
            success = await test_series_search(args.search, author_filter)

    elif args.author:
        success = await test_configuration()
        if success:
            success = await test_author_series_search(args.author)

    elif args.series:
        success = await test_configuration()
        if success:
            success = await test_series_books(args.series)

    elif args.series_limits:
        success = await test_configuration()
        if success:
            success = await test_series_books_limit_variations(args.series_limits)

    elif args.limits:
        success = await test_configuration()
        if success:
            success = await test_limit_variations()

    elif args.fields:
        success = await test_configuration()
        if success:
            success = await test_field_extraction()

    elif args.pagination:
        success = await test_configuration()
        if success:
            success = await test_pagination_formats()

    elif args.framework:
        success = await test_configuration()
        if success:
            if args.framework == "basic":
                success = await test_framework_basic()

    else:
        # Run all tests by default
        success = await run_all_tests()

    return 0 if success else 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
