"""
Benchmark test for Hardcover API approaches.

Compares performance of different strategies for fetching book metadata:
1. Editions endpoint (by title) with deduplication by max user_count
2. search_book_advanced (individual queries per book)

Run with: pytest app/tests/test_hardcover_performance.py -v -s
Requires: HARDCOVER_API_TOKEN environment variable
"""

import asyncio
import os
import time
from typing import Dict, List, Any, Optional
import pytest

from app.hardcover_client import HardcoverClient


# Test datasets with different series sizes
TEST_SERIES = {
    "small": {
        "name": "Murderbot Diaries",
        "author": "Martha Wells",
        "books": [
            {"title": "All Systems Red", "id": 28209},
            {"title": "Artificial Condition", "id": 28210},
            {"title": "Rogue Protocol", "id": 28211},
            {"title": "Exit Strategy", "id": 28212},
            {"title": "Network Effect", "id": 95346},
        ]
    },
    "medium": {
        "name": "The Expanse",
        "author": "James S.A. Corey",
        "books": [
            {"title": "Leviathan Wakes", "id": 8855},
            {"title": "Caliban's War", "id": 12591},
            {"title": "Abaddon's Gate", "id": 16131},
            {"title": "Cibola Burn", "id": 18656},
            {"title": "Nemesis Games", "id": 22886},
            {"title": "Babylon's Ashes", "id": 25877},
            {"title": "Persepolis Rising", "id": 28335},
            {"title": "Tiamat's Wrath", "id": 40419},
            {"title": "Leviathan Falls", "id": 56030},
        ]
    },
    "large": {
        "name": "Discworld (Sample)",
        "author": "Terry Pratchett",
        "books": [
            {"title": "The Colour of Magic", "id": 601},
            {"title": "The Light Fantastic", "id": 602},
            {"title": "Equal Rites", "id": 603},
            {"title": "Mort", "id": 604},
            {"title": "Sourcery", "id": 605},
            {"title": "Wyrd Sisters", "id": 606},
            {"title": "Pyramids", "id": 607},
            {"title": "Guards! Guards!", "id": 608},
            {"title": "Eric", "id": 609},
            {"title": "Moving Pictures", "id": 610},
            {"title": "Reaper Man", "id": 611},
            {"title": "Witches Abroad", "id": 612},
            {"title": "Small Gods", "id": 613},
            {"title": "Lords and Ladies", "id": 614},
            {"title": "Men at Arms", "id": 615},
            {"title": "Soul Music", "id": 616},
            {"title": "Interesting Times", "id": 617},
            {"title": "Maskerade", "id": 618},
            {"title": "Feet of Clay", "id": 619},
            {"title": "Hogfather", "id": 620},
        ]
    }
}


class BenchmarkMetrics:
    """Container for benchmark metrics."""

    def __init__(self, approach_name: str):
        self.approach_name = approach_name
        self.total_time = 0.0
        self.total_api_calls = 0
        self.books_resolved = 0
        self.total_editions_found = 0
        self.total_editions_kept = 0
        self.results: List[Dict[str, Any]] = []
        self.errors: List[str] = []

    def add_result(self, book_title: str, editions_found: int, selected_edition_id: Optional[int],
                   selected_user_count: Optional[int], api_calls: int):
        """Add a single book result."""
        self.results.append({
            "book_title": book_title,
            "editions_found": editions_found,
            "selected_edition_id": selected_edition_id,
            "selected_user_count": selected_user_count,
            "api_calls_for_this_book": api_calls
        })
        self.total_editions_found += editions_found
        if selected_edition_id is not None:
            self.books_resolved += 1
            self.total_editions_kept += 1
        self.total_api_calls += api_calls

    def avg_time_per_book(self) -> float:
        """Calculate average time per book."""
        return self.total_time / len(self.results) if self.results else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "approach": self.approach_name,
            "total_time_seconds": round(self.total_time, 2),
            "total_api_calls": self.total_api_calls,
            "avg_time_per_book": round(self.avg_time_per_book(), 3),
            "books_resolved": self.books_resolved,
            "total_books": len(self.results),
            "success_rate": f"{(self.books_resolved / len(self.results) * 100):.1f}%" if self.results else "0%",
            "dedup_editions_found": self.total_editions_found,
            "dedup_editions_kept": self.total_editions_kept,
            "errors": self.errors,
            "sample_results": self.results[:5]  # First 5 for inspection
        }


async def benchmark_editions_approach(client: HardcoverClient, books: List[Dict[str, str]]) -> BenchmarkMetrics:
    """
    Benchmark the editions endpoint approach.

    For each book:
    1. Query editions(where: {title: {_eq: "<title>"}})
    2. Select edition with max user_count
    3. Track API calls and timing
    """
    metrics = BenchmarkMetrics("Editions Endpoint")
    start_time = time.time()

    for book in books:
        book_title = book["title"]
        book_start = time.time()
        api_calls_this_book = 0

        try:
            # GraphQL query for editions by title
            query = """
            query GetEditionsByTitle($title: String!) {
                editions(where: {title: {_eq: $title}}) {
                    id
                    title
                    user_count
                    isbn_10
                    isbn_13
                }
            }
            """
            variables = {"title": book_title}

            result = await client._execute_graphql(query, variables)
            api_calls_this_book += 1

            if result and "editions" in result:
                editions = result["editions"]

                if editions:
                    # Deduplicate by selecting edition with max user_count
                    best_edition = max(editions, key=lambda e: e.get("user_count", 0) or 0)

                    metrics.add_result(
                        book_title=book_title,
                        editions_found=len(editions),
                        selected_edition_id=best_edition.get("id"),
                        selected_user_count=best_edition.get("user_count"),
                        api_calls=api_calls_this_book
                    )
                else:
                    # No editions found
                    metrics.add_result(
                        book_title=book_title,
                        editions_found=0,
                        selected_edition_id=None,
                        selected_user_count=None,
                        api_calls=api_calls_this_book
                    )
                    metrics.errors.append(f"No editions found for '{book_title}'")
            else:
                metrics.add_result(
                    book_title=book_title,
                    editions_found=0,
                    selected_edition_id=None,
                    selected_user_count=None,
                    api_calls=api_calls_this_book
                )
                metrics.errors.append(f"Query failed for '{book_title}'")

        except Exception as e:
            metrics.add_result(
                book_title=book_title,
                editions_found=0,
                selected_edition_id=None,
                selected_user_count=None,
                api_calls=api_calls_this_book
            )
            metrics.errors.append(f"Exception for '{book_title}': {str(e)}")

    metrics.total_time = time.time() - start_time
    return metrics


async def benchmark_advanced_search_approach(client: HardcoverClient, books: List[Dict[str, str]],
                                            author: str) -> BenchmarkMetrics:
    """
    Benchmark the search_book_advanced approach.

    For each book:
    1. Call search_book_advanced(title, author)
    2. Extract users_count from first result
    3. Track API calls and timing
    """
    metrics = BenchmarkMetrics("Advanced Search")
    start_time = time.time()

    for book in books:
        book_title = book["title"]
        book_id = book.get("id")
        api_calls_this_book = 0

        try:
            # Use search_book_advanced
            results = await client.search_book_advanced(
                title=book_title,
                author=author,
                limit=10,
                fields="id,title,author_names,users_count,has_audiobook",
                deduplicate=True
            )
            api_calls_this_book += 1

            if results:
                # Try to find exact match by book_id if available
                matched_result = None
                if book_id:
                    for result in results:
                        if result.get("id") == book_id or result.get("book_id") == book_id:
                            matched_result = result
                            break

                # Fallback to first result if no exact match
                if not matched_result:
                    matched_result = results[0]

                metrics.add_result(
                    book_title=book_title,
                    editions_found=len(results),
                    selected_edition_id=matched_result.get("id") or matched_result.get("book_id"),
                    selected_user_count=matched_result.get("users_count"),
                    api_calls=api_calls_this_book
                )
            else:
                # No results found
                metrics.add_result(
                    book_title=book_title,
                    editions_found=0,
                    selected_edition_id=None,
                    selected_user_count=None,
                    api_calls=api_calls_this_book
                )
                metrics.errors.append(f"No results for '{book_title}'")

        except Exception as e:
            metrics.add_result(
                book_title=book_title,
                editions_found=0,
                selected_edition_id=None,
                selected_user_count=None,
                api_calls=api_calls_this_book
            )
            metrics.errors.append(f"Exception for '{book_title}': {str(e)}")

    metrics.total_time = time.time() - start_time
    return metrics


def print_benchmark_results(series_name: str, editions_metrics: BenchmarkMetrics,
                           search_metrics: BenchmarkMetrics):
    """Pretty-print comparison results."""
    print("\n" + "=" * 70)
    print(f"BENCHMARK RESULTS: {series_name}")
    print("=" * 70)

    print(f"\n📊 Books tested: {len(editions_metrics.results)}")

    # Editions approach
    print(f"\n🔹 APPROACH 1: Editions Endpoint (Deduplication)")
    print(f"   Total time: {editions_metrics.total_time:.2f}s")
    print(f"   API calls: {editions_metrics.total_api_calls}")
    print(f"   Avg per book: {editions_metrics.avg_time_per_book():.3f}s")
    print(f"   Books resolved: {editions_metrics.books_resolved}/{len(editions_metrics.results)}")
    print(f"   Editions found: {editions_metrics.total_editions_found} total → {editions_metrics.total_editions_kept} after dedup")
    if editions_metrics.errors:
        print(f"   ⚠️  Errors: {len(editions_metrics.errors)}")

    # Advanced search approach
    print(f"\n🔹 APPROACH 2: Advanced Search")
    print(f"   Total time: {search_metrics.total_time:.2f}s")
    print(f"   API calls: {search_metrics.total_api_calls}")
    print(f"   Avg per book: {search_metrics.avg_time_per_book():.3f}s")
    print(f"   Books resolved: {search_metrics.books_resolved}/{len(search_metrics.results)}")
    print(f"   Results found: {search_metrics.total_editions_found}")
    if search_metrics.errors:
        print(f"   ⚠️  Errors: {len(search_metrics.errors)}")

    # Comparison
    print(f"\n🏆 WINNER:")
    if editions_metrics.total_time < search_metrics.total_time:
        speedup = ((search_metrics.total_time - editions_metrics.total_time) / search_metrics.total_time * 100)
        print(f"   ✅ Editions Endpoint ({speedup:.1f}% faster)")
    elif search_metrics.total_time < editions_metrics.total_time:
        speedup = ((editions_metrics.total_time - search_metrics.total_time) / editions_metrics.total_time * 100)
        print(f"   ✅ Advanced Search ({speedup:.1f}% faster)")
    else:
        print(f"   🤝 Tie (same speed)")

    print(f"\n📈 API Efficiency:")
    if editions_metrics.total_api_calls < search_metrics.total_api_calls:
        diff = search_metrics.total_api_calls - editions_metrics.total_api_calls
        print(f"   ✅ Editions Endpoint ({diff} fewer calls)")
    elif search_metrics.total_api_calls < editions_metrics.total_api_calls:
        diff = editions_metrics.total_api_calls - search_metrics.total_api_calls
        print(f"   ✅ Advanced Search ({diff} fewer calls)")
    else:
        print(f"   🤝 Same ({editions_metrics.total_api_calls} calls each)")

    print(f"\n🎯 Accuracy:")
    editions_accuracy = editions_metrics.books_resolved / len(editions_metrics.results) * 100 if editions_metrics.results else 0
    search_accuracy = search_metrics.books_resolved / len(search_metrics.results) * 100 if search_metrics.results else 0
    print(f"   Editions: {editions_accuracy:.1f}% resolved")
    print(f"   Search: {search_accuracy:.1f}% resolved")

    if editions_accuracy > search_accuracy:
        print(f"   ✅ Editions more accurate")
    elif search_accuracy > editions_accuracy:
        print(f"   ✅ Search more accurate")
    else:
        print(f"   🤝 Same accuracy")

    # Sample results
    print(f"\n📝 Sample Results (first 3 books):")
    for i in range(min(3, len(editions_metrics.results))):
        ed_result = editions_metrics.results[i]
        search_result = search_metrics.results[i]
        print(f"\n   Book: {ed_result['book_title']}")
        print(f"   Editions: {ed_result['editions_found']} found, user_count={ed_result['selected_user_count']}")
        print(f"   Search: {search_result['editions_found']} found, user_count={search_result['selected_user_count']}")

    print("\n" + "=" * 70 + "\n")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HARDCOVER_API_TOKEN"),
    reason="Requires HARDCOVER_API_TOKEN for live API testing"
)
async def test_hardcover_fetch_performance_small():
    """Benchmark with small series (5-10 books)."""
    series = TEST_SERIES["small"]

    client = HardcoverClient()

    # Run both approaches
    editions_metrics = await benchmark_editions_approach(client, series["books"])
    search_metrics = await benchmark_advanced_search_approach(client, series["books"], series["author"])

    # Print results
    print_benchmark_results(f"{series['name']} ({len(series['books'])} books)",
                          editions_metrics, search_metrics)

    # Basic assertions
    assert editions_metrics.books_resolved > 0, "Editions approach should resolve at least some books"
    assert search_metrics.books_resolved > 0, "Search approach should resolve at least some books"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HARDCOVER_API_TOKEN"),
    reason="Requires HARDCOVER_API_TOKEN for live API testing"
)
async def test_hardcover_fetch_performance_medium():
    """Benchmark with medium series (15-25 books)."""
    series = TEST_SERIES["medium"]

    client = HardcoverClient()

    # Run both approaches
    editions_metrics = await benchmark_editions_approach(client, series["books"])
    search_metrics = await benchmark_advanced_search_approach(client, series["books"], series["author"])

    # Print results
    print_benchmark_results(f"{series['name']} ({len(series['books'])} books)",
                          editions_metrics, search_metrics)

    # Basic assertions
    assert editions_metrics.books_resolved > 0, "Editions approach should resolve at least some books"
    assert search_metrics.books_resolved > 0, "Search approach should resolve at least some books"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HARDCOVER_API_TOKEN"),
    reason="Requires HARDCOVER_API_TOKEN for live API testing"
)
async def test_hardcover_fetch_performance_large():
    """Benchmark with large series (40+ books) - tests deduplication heavily."""
    series = TEST_SERIES["large"]

    client = HardcoverClient()

    # Run both approaches
    editions_metrics = await benchmark_editions_approach(client, series["books"])
    search_metrics = await benchmark_advanced_search_approach(client, series["books"], series["author"])

    # Print results
    print_benchmark_results(f"{series['name']} ({len(series['books'])} books)",
                          editions_metrics, search_metrics)

    # Basic assertions
    assert editions_metrics.books_resolved > 0, "Editions approach should resolve at least some books"
    assert search_metrics.books_resolved > 0, "Search approach should resolve at least some books"

    # Verify deduplication is working
    assert editions_metrics.total_editions_found >= editions_metrics.total_editions_kept, \
        "Deduplication should reduce or maintain edition count"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HARDCOVER_API_TOKEN"),
    reason="Requires HARDCOVER_API_TOKEN for live API testing"
)
async def test_hardcover_fetch_performance_all():
    """Run all benchmarks in sequence and print summary."""
    client = HardcoverClient()

    all_results = []

    for series_key, series_data in TEST_SERIES.items():
        print(f"\n🔄 Running benchmark for {series_data['name']}...")

        editions_metrics = await benchmark_editions_approach(client, series_data["books"])
        search_metrics = await benchmark_advanced_search_approach(client, series_data["books"], series_data["author"])

        print_benchmark_results(f"{series_data['name']} ({len(series_data['books'])} books)",
                              editions_metrics, search_metrics)

        all_results.append({
            "series": series_data["name"],
            "book_count": len(series_data["books"]),
            "editions": editions_metrics.to_dict(),
            "search": search_metrics.to_dict()
        })

        # Rate limiting pause between series
        await asyncio.sleep(2)

    # Print overall summary
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)

    for result in all_results:
        print(f"\n📚 {result['series']} ({result['book_count']} books):")
        print(f"   Editions: {result['editions']['total_time_seconds']}s, {result['editions']['total_api_calls']} calls")
        print(f"   Search: {result['search']['total_time_seconds']}s, {result['search']['total_api_calls']} calls")

        # Determine winner
        if result['editions']['total_time_seconds'] < result['search']['total_time_seconds']:
            print(f"   🏆 Editions faster")
        elif result['search']['total_time_seconds'] < result['editions']['total_time_seconds']:
            print(f"   🏆 Search faster")
        else:
            print(f"   🤝 Tie")

    print("\n" + "=" * 70)
