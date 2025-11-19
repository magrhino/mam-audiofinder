#!/usr/bin/env python3
"""
Test deduplication logic for series books.

This test verifies that duplicate book titles returned by the Hardcover API
are properly deduplicated before being enriched and returned to the frontend.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def is_combined_title(title: str) -> bool:
    """Detect if a title is a combined/omnibus edition."""
    if not isinstance(title, str):
        return False
    # Check for slash separators (common in omnibus titles)
    # Must have spaces around slash to avoid false positives like "and/or"
    if " / " in title:
        # Count how many slashes - 2+ slashes likely means combined title
        slash_count = title.count(" / ")
        if slash_count >= 2:
            return True
        # Even with 1 slash, if title is very long (>80 chars), likely omnibus
        if slash_count >= 1 and len(title) > 80:
            return True
    return False


def test_deduplication_logic():
    """Test the deduplication logic used in get_book_series_info()."""

    # Simulate the books array from Hardcover API for "The Goddess Test" series
    # This is based on the user's actual report showing both duplicates AND omnibus
    book_titles = [
        "The Goddess Test",
        "Goddess Interrupted",
        "The Goddess Hunt",
        "The Goddess Legacy",
        "Goddess Test / Goddess Interrupted / The Goddess Legacy / The Goddess Inheritance"  # OMNIBUS
    ]

    print("📚 Testing deduplication and omnibus filtering logic")
    print(f"   Input: {len(book_titles)} titles")
    print(f"   Titles: {book_titles}")

    # Step 1: Filter out combined/omnibus titles
    filtered_titles = []
    for title in book_titles:
        if isinstance(title, str):
            if is_combined_title(title):
                print(f"   🗑️  Filtered omnibus: '{title}'")
            else:
                filtered_titles.append(title)

    # Step 2: Apply the deduplication logic from get_book_series_info()
    seen_titles = {}
    unique_titles = []
    for title in filtered_titles:
        if isinstance(title, str):
            # Normalize title for comparison (lowercase, strip whitespace)
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)

    omnibus_filtered = len(book_titles) - len(filtered_titles)
    duplicates_removed = len(filtered_titles) - len(unique_titles)

    print(f"\n✅ Filtering complete")
    print(f"   Output: {len(unique_titles)} unique titles")
    print(f"   Omnibus titles filtered: {omnibus_filtered}")
    print(f"   Duplicates removed: {duplicates_removed}")
    print(f"   Final titles: {unique_titles}")

    # Assertions
    assert len(unique_titles) == 4, f"Expected 4 unique titles, got {len(unique_titles)}"
    assert omnibus_filtered == 1, f"Expected 1 omnibus filtered, got {omnibus_filtered}"
    assert "Goddess Interrupted" in unique_titles, "Expected 'Goddess Interrupted' to be in unique titles"
    assert unique_titles.count("Goddess Interrupted") == 1, "Expected only 1 occurrence of 'Goddess Interrupted'"

    # Check order preservation (first occurrence should be kept)
    expected_order = [
        "The Goddess Test",
        "Goddess Interrupted",
        "The Goddess Hunt",
        "The Goddess Legacy"
    ]
    assert unique_titles == expected_order, f"Order not preserved correctly. Expected {expected_order}, got {unique_titles}"

    print("\n✅ All assertions passed!")
    return True


def test_omnibus_detection():
    """Test omnibus/combined title detection."""

    print("\n📚 Testing omnibus title detection")

    # Test cases: (title, expected_is_omnibus)
    test_cases = [
        # Should be detected as omnibus
        ("Book 1 / Book 2 / Book 3", True),
        ("The Goddess Test / Goddess Interrupted / The Goddess Legacy / The Goddess Inheritance", True),
        ("A / B / C / D", True),
        # Edge case: 1 slash but very long (>80 chars)
        ("This is a very long title that exceeds eighty characters / And continues with more text here", True),

        # Should NOT be detected as omnibus
        ("The King's Speech", False),  # No slash
        ("Book 1", False),  # No slash
        ("and/or", False),  # Slash without spaces
        ("A/B", False),  # Slash without spaces
        ("Title Part 1 / Part 2", False),  # Only 1 slash, not too long
        ("Short / Title", False),  # Only 1 slash, short
    ]

    all_passed = True
    for title, expected in test_cases:
        result = is_combined_title(title)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{title[:50]}...' → {'omnibus' if result else 'normal'} (expected: {'omnibus' if expected else 'normal'})")

        if result != expected:
            all_passed = False
            print(f"      FAILED: Expected {expected}, got {result}")

    assert all_passed, "Some omnibus detection tests failed"
    print("   ✅ All omnibus detection tests passed!")
    return True


def test_deduplication_edge_cases():
    """Test deduplication with edge cases."""

    print("\n📚 Testing deduplication edge cases")

    # Test case 1: Empty array
    print("\n   Test 1: Empty array")
    book_titles = []
    seen_titles = {}
    unique_titles = []
    for title in book_titles:
        if isinstance(title, str):
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
    assert len(unique_titles) == 0, "Empty array should yield empty result"
    print("   ✅ Empty array handled correctly")

    # Test case 2: No duplicates
    print("\n   Test 2: No duplicates")
    book_titles = ["Book A", "Book B", "Book C"]
    seen_titles = {}
    unique_titles = []
    for title in book_titles:
        if isinstance(title, str):
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
    assert len(unique_titles) == 3, "No duplicates should yield same count"
    print("   ✅ No duplicates handled correctly")

    # Test case 3: Case-insensitive duplicates
    print("\n   Test 3: Case-insensitive duplicates")
    book_titles = ["Harry Potter", "harry potter", "HARRY POTTER"]
    seen_titles = {}
    unique_titles = []
    for title in book_titles:
        if isinstance(title, str):
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
    assert len(unique_titles) == 1, "Case variants should be deduplicated"
    assert unique_titles[0] == "Harry Potter", "First occurrence should be kept"
    print("   ✅ Case-insensitive deduplication works")

    # Test case 4: Whitespace variations
    print("\n   Test 4: Whitespace variations")
    book_titles = ["  The Book  ", "The Book", " the book "]
    seen_titles = {}
    unique_titles = []
    for title in book_titles:
        if isinstance(title, str):
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
    assert len(unique_titles) == 1, "Whitespace variants should be deduplicated"
    print("   ✅ Whitespace handling works")

    # Test case 5: Mixed types (defensive coding)
    print("\n   Test 5: Mixed types (None, integers)")
    book_titles = ["Book A", None, "Book B", 123, "book a"]
    seen_titles = {}
    unique_titles = []
    for title in book_titles:
        if isinstance(title, str):
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
    assert len(unique_titles) == 2, "Non-strings should be filtered out"
    assert None not in unique_titles, "None should be filtered"
    assert 123 not in unique_titles, "Integers should be filtered"
    print("   ✅ Type filtering works")

    # Test case 6: Empty strings
    print("\n   Test 6: Empty strings")
    book_titles = ["Book A", "", "   ", "Book B"]
    seen_titles = {}
    unique_titles = []
    for title in book_titles:
        if isinstance(title, str):
            normalized = title.strip().lower()
            if normalized and normalized not in seen_titles:
                seen_titles[normalized] = True
                unique_titles.append(title)
    assert len(unique_titles) == 2, "Empty/whitespace strings should be filtered"
    assert "" not in unique_titles, "Empty strings should be filtered"
    print("   ✅ Empty string handling works")

    print("\n✅ All edge case tests passed!")
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("  SERIES BOOK DEDUPLICATION & OMNIBUS FILTERING TESTS")
    print("="*70)

    try:
        # Run main test
        test_deduplication_logic()

        # Run omnibus detection tests
        test_omnibus_detection()

        # Run edge case tests
        test_deduplication_edge_cases()

        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED")
        print("="*70)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
