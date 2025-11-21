#!/usr/bin/env python3
"""
Test ABS Provider Metadata Integration.
Run this inside the container to verify ABS provider metadata fetching.

Tests the new provider-based metadata enrichment logic via /api/search/books endpoint,
comparing it against the old fetch_item_details() method.

Usage:
    python test_abs_providers.py                        # Run all tests
    python test_abs_providers.py --provider audible     # Test specific provider
    python test_abs_providers.py --item-id abc123       # Test specific item
    python test_abs_providers.py --compare              # Comparison test only
    python test_abs_providers.py --fallback             # Test fallback logic
    python test_abs_providers.py --fields               # Field validation only
    python test_abs_providers.py --debug                # Verbose output
"""
import sys
import asyncio
import argparse
import time
import random
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ABS_BASE_URL, ABS_API_KEY, ABS_LIBRARY_ID
from abs_client import AudiobookshelfClient


# ============================================================================
# Helper Functions (matching test_hardcover_api.py style)
# ============================================================================

def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_result(label, value, indent=0):
    """Print formatted result."""
    prefix = "  " * indent
    print(f"{prefix}{label:<30} {value}")


async def wait_between_tests(seconds: float = 1.0):
    """Wait between tests to avoid rate limiting."""
    print(f"\n⏱️  Waiting {seconds}s between tests...")
    await asyncio.sleep(seconds)


def print_metadata_table(metadata: dict, indent=1):
    """Print metadata fields in a formatted table."""
    if not metadata:
        print(f"{'  ' * indent}(no metadata)")
        return

    prefix = "  " * indent

    # Define fields to display
    fields = [
        ('title', 'Title'),
        ('author', 'Author'),
        ('narrator', 'Narrator'),
        ('publisher', 'Publisher'),
        ('series', 'Series'),
        ('rating', 'Rating'),
        ('region', 'Region'),
        ('language', 'Language'),
        ('asin', 'ASIN'),
        ('isbn', 'ISBN'),
        ('description', 'Description'),
    ]

    print(f"\n{prefix}Metadata Fields:")
    for field_key, field_label in fields:
        value = metadata.get(field_key, '')

        if field_key == 'series':
            if value and isinstance(value, list):
                series_strs = []
                for s in value:
                    if isinstance(s, dict):
                        series_name = s.get('series', s.get('name', 'Unknown'))
                        sequence = s.get('sequence', '?')
                        series_strs.append(f"{series_name} #{sequence}")
                    else:
                        series_strs.append(str(s))

                series_display = ", ".join(series_strs)
                has_sequence = any(
                    s.get('sequence', '').strip().isdigit()
                    for s in value if isinstance(s, dict)
                )
                status = "✅" if has_sequence else "⚠️  (no sequence)"
                print(f"{prefix}  {status} {field_label:<20} {series_display}")
            else:
                print(f"{prefix}  ❌ {field_label:<20} (missing)")

        elif field_key == 'description':
            if value:
                char_count = len(str(value))
                print(f"{prefix}  ✅ {field_label:<20} {char_count} characters")
            else:
                print(f"{prefix}  ❌ {field_label:<20} (missing)")

        else:
            if value:
                display_val = str(value)
                if len(display_val) > 50:
                    display_val = display_val[:50] + "..."
                print(f"{prefix}  ✅ {field_label:<20} {display_val}")
            else:
                print(f"{prefix}  ❌ {field_label:<20} (missing)")


def print_comparison_table(old_meta: dict, new_meta: dict):
    """Print side-by-side comparison of old vs new metadata."""
    print(f"\n{'='*80}")
    print(f"COMPARISON: Old vs New Metadata")
    print(f"{'='*80}")
    print(f"{'Field':<20} | {'Old Value':<25} | {'New Value':<25} | Status")
    print(f"{'-'*80}")

    # Define fields to compare (new_field, old_field)
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
        ('publishedYear', 'publishedYear'),
    ]

    for new_field, old_field in fields:
        old_val = old_meta.get(old_field if old_field else new_field, '')
        new_val = new_meta.get(new_field, '')

        # Format values
        if new_field == 'series':
            old_val_str = f"{len(old_val)} items" if old_val else "(missing)"
            new_val_str = f"{len(new_val)} items" if new_val else "(missing)"

            # Check for sequence numbers
            old_has_seq = any(
                s.get('sequence', '').strip()
                for s in (old_val or []) if isinstance(s, dict)
            )
            new_has_seq = any(
                s.get('sequence', '').strip()
                for s in (new_val or []) if isinstance(s, dict)
            )

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


def count_populated_fields(metadata: dict) -> int:
    """Count non-empty fields in metadata dict."""
    if not metadata:
        return 0

    count = 0
    for key, value in metadata.items():
        if value:
            # For lists, check if non-empty
            if isinstance(value, list):
                if len(value) > 0:
                    count += 1
            # For strings, check if non-blank
            elif isinstance(value, str):
                if value.strip():
                    count += 1
            # For other types, count as populated
            else:
                count += 1

    return count


# ============================================================================
# Test Functions
# ============================================================================

async def test_configuration():
    """Test ABS configuration and connectivity."""
    print_header("ABS Configuration Check")

    config_ok = True

    # Check ABS_BASE_URL
    if ABS_BASE_URL:
        print_result("✓ Base URL:", ABS_BASE_URL)
    else:
        print_result("✗ Base URL:", "NOT CONFIGURED")
        config_ok = False

    # Check ABS_API_KEY
    if ABS_API_KEY:
        key_display = ABS_API_KEY[:8] + "..." + ABS_API_KEY[-4:] if len(ABS_API_KEY) > 12 else "***"
        print_result("✓ API Key:", f"Configured ({key_display})")
    else:
        print_result("✗ API Key:", "NOT CONFIGURED")
        config_ok = False

    # Check ABS_LIBRARY_ID
    if ABS_LIBRARY_ID:
        print_result("✓ Library ID:", ABS_LIBRARY_ID)
    else:
        print_result("✗ Library ID:", "NOT CONFIGURED")
        config_ok = False

    # Test connectivity
    if config_ok:
        print("\n🔍 Testing API connectivity...")
        client = AudiobookshelfClient()
        connected = await client.test_connection()
        if connected:
            print_result("✓ Connection:", "OK", indent=1)
        else:
            print_result("✗ Connection:", "FAILED", indent=1)
            config_ok = False

    return config_ok


async def test_item_selection(item_id: Optional[str] = None, debug: bool = False) -> Tuple[Optional[str], dict]:
    """
    Select test item (random or specific) and cache it.

    Returns:
        (item_id, item_data) tuple
    """
    print_header("Test Item Selection")

    cache_file = Path("/tmp/abs_test_item.json")
    client = AudiobookshelfClient()

    # If item_id provided, use it
    if item_id:
        print(f"\n🎯 Using provided item ID: {item_id}")

        try:
            details = await client.fetch_item_details(item_id)
            if not details:
                print("❌ Failed to fetch item details")
                return None, {}

            metadata = details.get('metadata', {})
            item_data = {
                'item_id': item_id,
                'title': metadata.get('title', 'Unknown'),
                'author': metadata.get('authorName', 'Unknown'),
                'narrator': metadata.get('narratorName', ''),
                'publisher': metadata.get('publisher', ''),
            }

            # Cache for future runs
            cache_file.write_text(json.dumps(item_data, indent=2))

            print_result("Title:", item_data['title'], indent=1)
            print_result("Author:", item_data['author'], indent=1)

            return item_id, item_data

        except Exception as e:
            print(f"❌ Error fetching item: {e}")
            return None, {}

    # Check cache
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            print(f"\n📦 Using cached item:")
            print_result("Item ID:", cached.get('item_id', 'Unknown'), indent=1)
            print_result("Title:", cached.get('title', 'Unknown'), indent=1)
            print_result("Author:", cached.get('author', 'Unknown'), indent=1)

            if debug:
                print_result("Cache File:", str(cache_file), indent=1)

            return cached.get('item_id'), cached
        except Exception as e:
            print(f"⚠️  Failed to load cache: {e}")
            # Continue to random selection

    # Select random item from library
    print(f"\n🎲 Selecting random item from library...")

    try:
        items = await client._get_cached_library_items()

        if not items:
            print("❌ No items in library")
            return None, {}

        print(f"   Found {len(items)} items in library")

        # Select random item
        random_item = random.choice(items)
        item_id = random_item.get('id')
        metadata = random_item.get('media', {}).get('metadata', {})

        item_data = {
            'item_id': item_id,
            'title': metadata.get('title', 'Unknown'),
            'author': metadata.get('authorName', 'Unknown'),
            'narrator': metadata.get('narratorName', ''),
            'publisher': metadata.get('publisher', ''),
        }

        # Cache for future runs
        cache_file.write_text(json.dumps(item_data, indent=2))

        print(f"\n✅ Selected item:")
        print_result("Item ID:", item_id, indent=1)
        print_result("Title:", item_data['title'], indent=1)
        print_result("Author:", item_data['author'], indent=1)
        print_result("Cached to:", str(cache_file), indent=1)

        return item_id, item_data

    except Exception as e:
        print(f"❌ Failed to select item: {e}")
        import traceback
        traceback.print_exc()
        return None, {}


async def test_provider(
    provider: str,
    item_id: str,
    title: str,
    author: str,
    debug: bool = False
) -> Tuple[bool, dict]:
    """
    Test a specific provider.

    Returns:
        (success, metadata) tuple
    """
    print_header(f"Provider Test: {provider}")

    if not item_id:
        print("⚠️  No item ID available, skipping test")
        return False, {}

    print(f"\n🔍 Fetching metadata from '{provider}' provider")
    print_result("Item ID:", item_id, indent=1)
    print_result("Title:", title, indent=1)
    print_result("Author:", author, indent=1)

    client = AudiobookshelfClient()

    try:
        # Fetch from provider
        print(f"\n🌐 Calling /api/search/books with provider={provider}...")

        result = await client._fetch_from_provider(
            provider=provider,
            item_id=item_id,
            title=title,
            author=author,
            fallback_title_only=True
        )

        if not result:
            print(f"\n❌ No results from '{provider}' provider")
            return False, {}

        print(f"\n✅ Got result from '{provider}'")

        # Display metadata fields
        print_metadata_table(result, indent=1)

        # Check for series with sequence (success criteria)
        series = result.get('series', [])
        has_sequence = any(
            s.get('sequence', '').strip().isdigit()
            for s in series if isinstance(s, dict)
        )

        # Count populated fields
        field_count = count_populated_fields(result)

        print(f"\n📊 Statistics:")
        print_result("Fields Populated:", field_count, indent=1)
        print_result("Has Series:", "Yes" if series else "No", indent=1)
        print_result("Has Sequence:", "Yes ✅" if has_sequence else "No", indent=1)

        if has_sequence:
            print(f"\n✅ SUCCESS: Series with sequence found!")
            return True, result
        else:
            print(f"\n⚠️  No series sequence found")
            return False, result

    except Exception as e:
        print(f"\n❌ Provider test failed: {type(e).__name__}: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False, {}


async def test_old_vs_new_comparison(item_id: str, debug: bool = False) -> bool:
    """Compare old fetch_item_details vs new provider-based fetch."""
    print_header("Comparison: Old vs New Metadata Methods")

    if not item_id:
        print("⚠️  No item ID available, skipping test")
        return False

    client = AudiobookshelfClient()

    try:
        # OLD METHOD: fetch_item_details
        print("\n🔍 Fetching via OLD method (fetch_item_details)...")
        old_result = await client.fetch_item_details(item_id)

        if not old_result:
            print("   ❌ Old method returned no data")
            return False

        old_meta = old_result.get('metadata', {})
        old_fields = count_populated_fields(old_meta)
        print(f"   ✓ Got {old_fields} populated fields")

        await asyncio.sleep(1.0)  # Rate limit

        # NEW METHOD: provider-based fetch
        print("\n🔍 Fetching via NEW method (multi-provider)...")
        test_result = await client.fetch_enhanced_metadata_test(
            item_id=item_id,
            providers=["audible", "google", "openlibrary"]
        )

        new_meta = test_result.get('new_metadata', {})
        new_fields = count_populated_fields(new_meta)
        provider_used = test_result.get('provider_used', 'none')
        success = test_result.get('success', False)

        print(f"   ✓ Got {new_fields} populated fields")
        print(f"   ✓ Provider used: {provider_used or 'none'}")
        print(f"   ✓ Success: {success}")

        # Print comparison table
        print_comparison_table(old_meta, new_meta)

        # Summary
        print(f"📊 Summary:")
        print_result("Old Method Fields:", old_fields, indent=1)
        print_result("New Method Fields:", new_fields, indent=1)
        print_result("Improvement:", f"+{new_fields - old_fields} fields", indent=1)

        if debug:
            print("\n🐛 Debug: Full comparison result:")
            comparison = test_result.get('comparison', {})
            for field, data in comparison.items():
                print(f"   {field}: {data.get('status')}")

        # Validation: New method should provide >= fields
        if new_fields >= old_fields:
            print(f"\n✅ New method provides more or equal fields")
            return True
        else:
            print(f"\n⚠️  New method provides fewer fields ({new_fields} < {old_fields})")
            return False

    except Exception as e:
        print(f"\n❌ Comparison test failed: {type(e).__name__}: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False


async def test_field_validation(metadata: dict) -> bool:
    """Validate critical fields are populated."""
    print_header("Field Validation")

    if not metadata:
        print("⚠️  No metadata provided, skipping test")
        return False

    # Check narrator/publisher (critical for audiobooks)
    has_narrator = bool(metadata.get('narrator', '').strip())
    has_publisher = bool(metadata.get('publisher', '').strip())

    print(f"\n📋 Critical Fields:")

    if has_narrator:
        print_result("✓ Narrator:", metadata.get('narrator'), indent=1)
    else:
        print_result("✗ Narrator:", "Missing", indent=1)

    if has_publisher:
        print_result("✓ Publisher:", metadata.get('publisher'), indent=1)
    else:
        print_result("✗ Publisher:", "Missing", indent=1)

    # Check series
    series = metadata.get('series', [])
    if series:
        series_strs = []
        for s in series:
            if isinstance(s, dict):
                series_name = s.get('series', s.get('name', 'Unknown'))
                sequence = s.get('sequence', '?')
                series_strs.append(f"{series_name} #{sequence}")
            else:
                series_strs.append(str(s))

        series_str = ", ".join(series_strs)
        print_result("✓ Series:", series_str, indent=1)

        # Check for numeric sequence
        has_sequence = any(
            s.get('sequence', '').strip().isdigit()
            for s in series if isinstance(s, dict)
        )
        if has_sequence:
            print_result("✓ Sequence:", "Numeric sequence found", indent=1)
        else:
            print_result("⚠ Sequence:", "No numeric sequence", indent=1)
    else:
        print_result("✗ Series:", "Missing", indent=1)

    # Check ASIN/ISBN
    has_asin = bool(metadata.get('asin', '').strip())
    has_isbn = bool(metadata.get('isbn', '').strip())

    if has_asin:
        print_result("✓ ASIN:", metadata.get('asin'), indent=1)
    else:
        print_result("✗ ASIN:", "Missing", indent=1)

    if has_isbn:
        print_result("✓ ISBN:", metadata.get('isbn'), indent=1)
    else:
        print_result("✗ ISBN:", "Missing", indent=1)

    # Check description
    description = metadata.get('description', '')
    if description:
        char_count = len(str(description))
        print_result("✓ Description:", f"{char_count} characters", indent=1)
    else:
        print_result("✗ Description:", "Missing", indent=1)

    # Validation: At least narrator OR publisher should exist
    print(f"\n📊 Validation Results:")
    if has_narrator or has_publisher:
        print_result("✅ Critical Fields:", "At least one populated", indent=1)
        return True
    else:
        print_result("❌ Critical Fields:", "Both narrator and publisher missing", indent=1)
        return False


async def test_provider_fallback(item_id: str, title: str, author: str, debug: bool = False) -> bool:
    """Test provider fallback logic (try multiple until success)."""
    print_header("Provider Fallback Test")

    if not item_id:
        print("⚠️  No item ID available, skipping test")
        return False

    providers = ["audible", "google", "openlibrary"]
    print(f"\n🔄 Testing fallback sequence: {' → '.join(providers)}")
    print(f"   Goal: Stop at first provider with series + sequence\n")

    client = AudiobookshelfClient()

    try:
        # Use the built-in fallback logic
        print("🌐 Calling fetch_enhanced_metadata_test()...")
        result = await client.fetch_enhanced_metadata_test(
            item_id=item_id,
            providers=providers
        )

        success = result.get('success', False)
        provider_used = result.get('provider_used', None)
        new_meta = result.get('new_metadata', {})

        print(f"\n📊 Fallback Results:")
        print_result("Providers Tried:", ', '.join(providers), indent=1)
        print_result("Provider Used:", provider_used or 'none', indent=1)
        print_result("Success:", success, indent=1)

        if new_meta:
            field_count = count_populated_fields(new_meta)
            print_result("Fields Populated:", field_count, indent=1)

        if success and provider_used:
            print(f"\n✅ SUCCESS: Stopped at provider '{provider_used}'")

            # Display what was found
            series = new_meta.get('series', [])
            if series:
                print(f"\n   Series found:")
                for s in series:
                    if isinstance(s, dict):
                        series_name = s.get('series', s.get('name', 'Unknown'))
                        sequence = s.get('sequence', '?')
                        print(f"     - {series_name} #{sequence}")

            return True
        else:
            print(f"\n⚠️  No provider returned series with sequence")

            if debug:
                print("\n🐛 Debug: Tried all providers without success")

            return False

    except Exception as e:
        print(f"\n❌ Fallback test failed: {type(e).__name__}: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False


async def run_all_tests(item_id: Optional[str] = None, wait_time: float = 1.5, debug: bool = False):
    """Run all tests sequentially."""
    print("\n" + "🧪 "*30)
    print("  ABS PROVIDER METADATA TEST SUITE")
    print("🧪 "*30)

    results = []
    start_time = time.time()

    # Test 1: Configuration
    results.append(("Configuration", await test_configuration()))
    await wait_between_tests(0.5)

    # Test 2: Item Selection
    selected_item_id, item_data = await test_item_selection(item_id, debug)
    if not selected_item_id:
        print("\n❌ Cannot proceed without test item")
        return False

    title = item_data.get('title', '')
    author = item_data.get('author', '')

    await wait_between_tests(1.0)

    # Test 3: Provider - Audible
    success_audible, meta_audible = await test_provider("audible", selected_item_id, title, author, debug)
    results.append(("Provider: audible", success_audible))
    await wait_between_tests(wait_time)

    # Test 4: Provider - Google
    success_google, meta_google = await test_provider("google", selected_item_id, title, author, debug)
    results.append(("Provider: google", success_google))
    await wait_between_tests(wait_time)

    # Test 5: Provider - OpenLibrary
    success_openlibrary, meta_openlibrary = await test_provider("openlibrary", selected_item_id, title, author, debug)
    results.append(("Provider: openlibrary", success_openlibrary))
    await wait_between_tests(wait_time)

    # Test 6: Old vs New Comparison
    results.append(("Old vs New Comparison", await test_old_vs_new_comparison(selected_item_id, debug)))
    await wait_between_tests(1.0)

    # Test 7: Field Validation (use first successful provider metadata)
    test_metadata = meta_audible if meta_audible else (meta_google if meta_google else meta_openlibrary)
    if test_metadata:
        results.append(("Field Validation", await test_field_validation(test_metadata)))
        await wait_between_tests(1.0)
    else:
        print("\n⚠️  Skipping field validation - no metadata available")
        results.append(("Field Validation", False))

    # Test 8: Provider Fallback
    results.append(("Provider Fallback", await test_provider_fallback(selected_item_id, title, author, debug)))

    # Summary
    elapsed = time.time() - start_time

    print_header("Test Summary")
    print()

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:<30} {status}")

    print()
    print("="*80)
    print(f"  Results: {passed}/{total} tests passed")
    print(f"  Time: {elapsed:.2f}s")
    print("="*80)

    return passed == total


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test ABS Provider Metadata Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_abs_providers.py                        # Run all tests
  python test_abs_providers.py --provider audible     # Test specific provider
  python test_abs_providers.py --item-id abc123       # Test specific item
  python test_abs_providers.py --compare              # Comparison test only
  python test_abs_providers.py --fallback             # Test fallback logic
  python test_abs_providers.py --fields               # Field validation only
  python test_abs_providers.py --debug                # Verbose output
        """
    )

    parser.add_argument("--provider", metavar="NAME",
                       choices=["audible", "google", "openlibrary", "itunes"],
                       help="Test specific provider only")
    parser.add_argument("--item-id", metavar="ID",
                       help="Test with specific item ID")
    parser.add_argument("--compare", action="store_true",
                       help="Run comparison test only")
    parser.add_argument("--fallback", action="store_true",
                       help="Test provider fallback logic")
    parser.add_argument("--fields", action="store_true",
                       help="Test field validation only")
    parser.add_argument("--config", action="store_true",
                       help="Test configuration only")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--wait", type=float, default=1.5,
                       help="Wait time between provider tests (default: 1.5s)")

    args = parser.parse_args()

    success = True

    # Configuration check
    if args.config:
        success = await test_configuration()
        return 0 if success else 1

    # Get test item
    item_id, item_data = await test_item_selection(args.item_id, args.debug)
    if not item_id:
        print("\n❌ Failed to get test item")
        return 1

    title = item_data.get('title', '')
    author = item_data.get('author', '')

    await wait_between_tests(1.0)

    # Route to specific tests
    if args.provider:
        # Test specific provider
        success = await test_configuration()
        if success:
            success, metadata = await test_provider(args.provider, item_id, title, author, args.debug)

    elif args.compare:
        # Comparison test only
        success = await test_configuration()
        if success:
            success = await test_old_vs_new_comparison(item_id, args.debug)

    elif args.fallback:
        # Fallback test only
        success = await test_configuration()
        if success:
            success = await test_provider_fallback(item_id, title, author, args.debug)

    elif args.fields:
        # Field validation only - need to fetch metadata first
        success = await test_configuration()
        if success:
            print("\n🔍 Fetching metadata for field validation...")
            success_fetch, metadata = await test_provider("audible", item_id, title, author, args.debug)
            if metadata:
                await wait_between_tests(1.0)
                success = await test_field_validation(metadata)
            else:
                print("❌ Failed to fetch metadata")
                success = False

    else:
        # Run all tests by default
        success = await run_all_tests(args.item_id, args.wait, args.debug)

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
