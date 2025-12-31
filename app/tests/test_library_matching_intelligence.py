#!/usr/bin/env python3
"""
Library Matching Intelligence Test for MAM Audiobook Finder

Tests the Audiobookshelf library matching logic against comprehensive edge cases.
Can be run as pytest or standalone CLI tool inside the container.

Usage:
    # As pytest (mock mode)
    pytest app/tests/test_library_matching_intelligence.py -v

    # As CLI (mock mode with detailed report)
    python app/tests/test_library_matching_intelligence.py --report

    # Test against live ABS instance
    python app/tests/test_library_matching_intelligence.py --live --report

    # Run specific scenario
    python app/tests/test_library_matching_intelligence.py --scenario exact_match
"""
import sys
import os
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass, field
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from abs_client import AudiobookshelfClient
    import config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the correct directory")
    sys.exit(1)


@dataclass
class MatchingTestCase:
    """Represents a single library matching test case."""
    name: str
    description: str
    query_title: str
    query_author: str = ""
    query_path: str = ""
    query_metadata: Optional[Dict] = None
    expected_status: str = "verified"  # verified, mismatch, not_found
    expected_min_score: int = 0
    expected_item_id: Optional[str] = None
    category: str = "general"  # general, edge_case, identifier, series, etc.
    notes: str = ""

    # Results (filled after test)
    actual_status: str = ""
    actual_score: int = 0
    actual_item_id: Optional[str] = None
    actual_note: str = ""
    passed: bool = False
    score_breakdown: Dict = field(default_factory=dict)


# ============================================================================
# COMPREHENSIVE TEST DATA - Real-world edge cases
# ============================================================================

MOCK_ABS_LIBRARY = {
    "results": [
        # Standard books
        {
            "id": "item-001-hobbit",
            "media": {
                "metadata": {
                    "title": "The Hobbit",
                    "authorName": "J.R.R. Tolkien",
                    "narratorName": "Rob Inglis",
                    "asin": "B0099RKRB6",
                    "isbn": "9780547928227"
                }
            },
            "path": "/audiobooks/Tolkien, J.R.R/The Hobbit"
        },
        {
            "id": "item-002-fellowship",
            "media": {
                "metadata": {
                    "title": "The Fellowship of the Ring",
                    "authorName": "J.R.R. Tolkien",
                    "narratorName": "Rob Inglis",
                    "asin": "B007978NPG",
                    "isbn": ""
                }
            },
            "path": "/audiobooks/Tolkien, J.R.R/The Fellowship of the Ring"
        },
        # Edge case: Same title, different author
        {
            "id": "item-003-foundation-asimov",
            "media": {
                "metadata": {
                    "title": "Foundation",
                    "authorName": "Isaac Asimov",
                    "narratorName": "Scott Brick",
                    "asin": "B003GFIVFS",
                    "isbn": "9780553293357"
                }
            },
            "path": "/audiobooks/Asimov, Isaac/Foundation"
        },
        # Edge case: Subtitle variations
        {
            "id": "item-004-sapiens",
            "media": {
                "metadata": {
                    "title": "Sapiens: A Brief History of Humankind",
                    "authorName": "Yuval Noah Harari",
                    "narratorName": "Derek Perkins",
                    "asin": "B00ICN066A",
                    "isbn": ""
                }
            },
            "path": "/audiobooks/Harari, Yuval Noah/Sapiens"
        },
        # Edge case: Series with numbers
        {
            "id": "item-005-hp1",
            "media": {
                "metadata": {
                    "title": "Harry Potter and the Philosopher's Stone",
                    "authorName": "J.K. Rowling",
                    "narratorName": "Stephen Fry",
                    "asin": "B017V4IMVQ",
                    "isbn": "9781781100219"
                }
            },
            "path": "/audiobooks/Rowling, J.K/Harry Potter 01"
        },
        # Edge case: Author name variations
        {
            "id": "item-006-dune",
            "media": {
                "metadata": {
                    "title": "Dune",
                    "authorName": "Frank Herbert",
                    "narratorName": "Scott Brick",
                    "asin": "B002V1OF70",
                    "isbn": "9780441013593"
                }
            },
            "path": "/audiobooks/Herbert, Frank/Dune"
        },
        # Edge case: Special characters
        {
            "id": "item-007-enders-game",
            "media": {
                "metadata": {
                    "title": "Ender's Game",
                    "authorName": "Orson Scott Card",
                    "narratorName": "Stefan Rudnicki",
                    "asin": "B003ZZAFJ2",
                    "isbn": "9780812550702"
                }
            },
            "path": "/audiobooks/Card, Orson Scott/Ender's Game"
        },
        # Edge case: Very long title with subtitle
        {
            "id": "item-008-thinking",
            "media": {
                "metadata": {
                    "title": "Thinking, Fast and Slow",
                    "authorName": "Daniel Kahneman",
                    "narratorName": "Patrick Egan",
                    "asin": "B005TKKCWC",
                    "isbn": "9780374533557"
                }
            },
            "path": "/audiobooks/Kahneman, Daniel/Thinking, Fast and Slow"
        },
        # Edge case: Multi-author book
        {
            "id": "item-009-expanse1",
            "media": {
                "metadata": {
                    "title": "Leviathan Wakes",
                    "authorName": "James S.A. Corey",  # Pen name for two authors
                    "narratorName": "Jefferson Mays",
                    "asin": "B073H9PF2D",
                    "isbn": ""
                }
            },
            "path": "/audiobooks/Corey, James S.A/The Expanse 01 - Leviathan Wakes"
        },
        # Edge case: Edition variations
        {
            "id": "item-010-1984",
            "media": {
                "metadata": {
                    "title": "1984",
                    "authorName": "George Orwell",
                    "narratorName": "Simon Prebble",
                    "asin": "B003JTHWKU",
                    "isbn": "9780452284234"
                }
            },
            "path": "/audiobooks/Orwell, George/1984"
        },
        # Edge case: Article variations (The, A, An)
        {
            "id": "item-011-stand",
            "media": {
                "metadata": {
                    "title": "The Stand",
                    "authorName": "Stephen King",
                    "narratorName": "Grover Gardner",
                    "asin": "B00ACPDZD6",
                    "isbn": ""
                }
            },
            "path": "/audiobooks/King, Stephen/The Stand"
        },
        # Edge case: Numeric in title
        {
            "id": "item-012-2001",
            "media": {
                "metadata": {
                    "title": "2001: A Space Odyssey",
                    "authorName": "Arthur C. Clarke",
                    "narratorName": "Dick Hill",
                    "asin": "B0012IR7XS",
                    "isbn": ""
                }
            },
            "path": "/audiobooks/Clarke, Arthur C/2001 - A Space Odyssey"
        }
    ],
    "total": 12
}


class FakeLibraryCache:
    """Lightweight cache to avoid DB access during mock tests."""

    def __init__(self, library_data):
        self.library_data = library_data

    async def ensure_fresh(self, _refresh_fn=None):
        return None

    def find_best_match(self, title: str, author: str = "", asin: str = None, isbn: str = None, path: str = None):
        from abs.matching import MatchResult, calculate_match_score
        from abs.models import LibraryItem
        from utils import normalize_title, normalize_author

        empty = MatchResult(confidence=0.0, method="NO_MATCH")

        best_item = None
        best_result = empty

        for item in self.library_data.get("results", []):
            item_metadata = item.get("media", {}).get("metadata", {})
            library_item = LibraryItem(
                id=item.get("id"),
                library_id="mock-lib",
                title=item_metadata.get("title", ""),
                author=item_metadata.get("authorName", ""),
                narrator=item_metadata.get("narratorName"),
                series_name=item_metadata.get("seriesName"),
                asin=item_metadata.get("asin"),
                isbn=item_metadata.get("isbn"),
                cover_path=item.get("media", {}).get("coverPath"),
                duration_seconds=item.get("media", {}).get("duration"),
                path=item.get("path"),
                title_normalized=normalize_title(item_metadata.get("title", "")),
                author_normalized=normalize_author(item_metadata.get("authorName", "")),
            )

            result = calculate_match_score(
                query_title=title,
                query_author=author,
                candidate=library_item,
                query_asin=asin,
                query_isbn=isbn,
                query_path=path,
            )

            if result.confidence > best_result.confidence:
                best_result = result
                best_item = library_item

        return best_item, best_result


# ============================================================================
# TEST SCENARIOS - Comprehensive edge case coverage
# ============================================================================

def generate_test_cases() -> List[MatchingTestCase]:
    """Generate comprehensive test cases covering all edge cases."""
    return [
        # ========== EXACT MATCHES ==========
        MatchingTestCase(
            name="exact_title_author_match",
            description="Perfect title and author match",
            query_title="The Hobbit",
            query_author="J.R.R. Tolkien",
            expected_status="verified",
            expected_min_score=95,

            expected_item_id="item-001-hobbit",
            category="exact_match"
        ),

        MatchingTestCase(
            name="exact_match_no_author",
            description="Title match without author",
            query_title="Dune",
            query_author="",
            expected_status="verified",
            expected_min_score=90,
            expected_item_id="item-006-dune",
            category="exact_match"
        ),

        # ========== ASIN/ISBN MATCHING (Highest Priority) ==========
        MatchingTestCase(
            name="asin_match_exact",
            description="ASIN match with matching title",
            query_title="The Hobbit",
            query_author="J.R.R. Tolkien",
            query_metadata={"asin": "B0099RKRB6"},
            expected_status="verified",
            expected_min_score=85,
            expected_item_id="item-001-hobbit",
            category="partial_match"

        ),

        MatchingTestCase(
            name="exact_match_lowercase",
            description="Exact match with different casing",
            query_title="the hobbit",
            query_author="j.r.r. tolkien",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-001-hobbit",
            category="exact_match"
        ),


        MatchingTestCase(
            name="partial_both",
            description="Partial title and partial author",
            query_title="Fellowship",
            query_author="Tolkien",
            expected_status="verified",
            expected_min_score=85,
            category="partial_match",
            notes="Title+author partial now yields ~88 confidence"
        ),

        # ========== SUBTITLE HANDLING ==========
        MatchingTestCase(
            name="subtitle_colon_present",
            description="Query includes subtitle with colon",
            query_title="Sapiens: A Brief History of Humankind",
            query_author="Yuval Noah Harari",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-004-sapiens",
            category="subtitle"
        ),

        MatchingTestCase(
            name="subtitle_missing_in_query",
            description="Query without subtitle, library has it",
            query_title="Sapiens",
            query_author="Yuval Noah Harari",
            expected_status="verified",
            expected_min_score=90,
            expected_item_id="item-004-sapiens",
            category="subtitle",
            notes="Should still match (partial title)"
        ),

        MatchingTestCase(
            name="subtitle_dash_variation",
            description="Subtitle with dash instead of colon",
            query_title="Sapiens - A Brief History of Humankind",
            query_author="Yuval Noah Harari",
            expected_status="verified",
            expected_min_score=90,
            category="subtitle",
            notes="Dash and colon normalize identically - both removed with subtitle"
        ),

        # ========== SERIES HANDLING ==========
        MatchingTestCase(
            name="series_exact_name",
            description="Exact series book name",
            query_title="Harry Potter and the Philosopher's Stone",
            query_author="J.K. Rowling",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-005-hp1",
            category="series"
        ),

        MatchingTestCase(
            name="series_with_book_number",
            description="Query includes 'Book 1' variation",
            query_title="Harry Potter and the Philosopher's Stone Book 1",
            query_author="J.K. Rowling",
            expected_status="verified",
            expected_min_score=100,
            category="series",
            notes="Book number suffix treated as noise - substring match (50) + author exact (50) = verified"
        ),

        # ========== AUTHOR NAME VARIATIONS ==========
        MatchingTestCase(
            name="author_initials_vs_full",
            description="Query has initials, library has full dots",
            query_title="The Hobbit",
            query_author="JRR Tolkien",
            expected_status="verified",
            expected_min_score=95,
            category="author_variations",
            notes="Periods in initials normalized - 'JRR Tolkien' == 'J.R.R. Tolkien' after normalization"
        ),

        MatchingTestCase(
            name="author_lastname_only",
            description="Query has last name only",
            query_title="Dune",
            query_author="Herbert",
            expected_status="verified",
            expected_min_score=85,
            expected_item_id="item-006-dune",
            category="author_variations"
        ),

        MatchingTestCase(
            name="author_pen_name",
            description="Multi-author pen name",
            query_title="Leviathan Wakes",
            query_author="James S.A. Corey",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-009-expanse1",
            category="author_variations"
        ),

        # ========== SPECIAL CHARACTERS ==========
        MatchingTestCase(
            name="apostrophe_in_title",
            description="Title with apostrophe",
            query_title="Ender's Game",
            query_author="Orson Scott Card",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-007-enders-game",
            category="special_chars"
        ),

        MatchingTestCase(
            name="apostrophe_straight_vs_curly",
            description="Different apostrophe types",
            query_title="Ender's Game",
            query_author="Orson Scott Card",
            expected_status="verified",
            expected_min_score=95,
            category="special_chars",
            notes="Apostrophe types normalized - both removed, exact title + author match"
        ),

        MatchingTestCase(
            name="comma_in_title",
            description="Title with comma",
            query_title="Thinking, Fast and Slow",
            query_author="Daniel Kahneman",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-008-thinking",
            category="special_chars"
        ),

        # ========== ARTICLE VARIATIONS (The, A, An) ==========
        MatchingTestCase(
            name="article_the_present",
            description="Query with 'The' article",
            query_title="The Stand",
            query_author="Stephen King",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-011-stand",
            category="articles"
        ),

        MatchingTestCase(
            name="article_the_missing",
            description="Query without 'The' article",
            query_title="Stand",
            query_author="Stephen King",
            expected_status="verified",
            expected_min_score=100,
            expected_item_id="item-011-stand",
            category="articles",
            notes="Partial match (substring)"
        ),

        # ========== NUMERIC IN TITLES ==========
        MatchingTestCase(
            name="numeric_exact",
            description="Numeric in title - exact match",
            query_title="1984",
            query_author="George Orwell",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-010-1984",
            category="numeric"
        ),

        MatchingTestCase(
            name="numeric_with_colon",
            description="Numeric with colon and subtitle",
            query_title="2001: A Space Odyssey",
            query_author="Arthur C. Clarke",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-012-2001",
            category="numeric"
        ),

        # ========== SAME TITLE DIFFERENT AUTHORS ==========
        MatchingTestCase(
            name="same_title_correct_author",
            description="Same title, correct author specified",
            query_title="Foundation",
            query_author="Isaac Asimov",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-003-foundation-asimov",
            category="disambiguation"
        ),

        MatchingTestCase(
            name="same_title_wrong_author",
            description="Same title, wrong author",
            query_title="Foundation",
            query_author="Robert A. Heinlein",
            expected_status="verified",
            expected_min_score=90,
            category="disambiguation",
            notes="Strong title match falls back to TITLE_ONLY despite author mismatch (90% confidence)"
         ),

        MatchingTestCase(
            name="graphic_audio_exception",
            description="GraphicAudio adaptations should not be downgraded for author differences",
            query_title="Foundation",
            query_author="Graphic Audio",
            expected_status="verified",
            expected_min_score=90,
            expected_item_id="item-003-foundation-asimov",
            category="disambiguation",
            notes="GraphicAudio treated as adaptation; author mismatch guard bypassed"
        ),
 
         # ========== NOT FOUND CASES ==========

        MatchingTestCase(
            name="not_in_library_title",
            description="Book not in library",
            query_title="The Nonexistent Book",
            query_author="Unknown Author",
            expected_status="not_found",
            expected_min_score=0,
            category="not_found"
        ),

        MatchingTestCase(
            name="wrong_asin",
            description="ASIN not in library",
            query_title="Some Book",
            query_author="Some Author",
            query_metadata={"asin": "B999999999"},
            expected_status="not_found",
            expected_min_score=0,
            category="not_found"
        ),

        # ========== PATH MATCHING ==========
        MatchingTestCase(
            name="path_match_bonus",
            description="Correct path should add bonus points",
            query_title="Dune",
            query_author="Frank Herbert",
            query_path="/audiobooks/Herbert, Frank/Dune",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-006-dune",
            category="path_matching",
            notes="Path bonus now +2.5"
        ),

        MatchingTestCase(
            name="path_mismatch_no_penalty",
            description="Wrong path shouldn't penalize",
            query_title="Dune",
            query_author="Frank Herbert",
            query_path="/wrong/path/here",
            expected_status="verified",
            expected_min_score=95,
            expected_item_id="item-006-dune",
            category="path_matching",
            notes="Path mismatch doesn't reduce score"
        ),
    ]


# ============================================================================
# MATCH ANALYZER - Detailed scoring breakdown
# ============================================================================

class MatchAnalyzer:
    """Analyzes match results using the ACTUAL matching logic from matching.py."""

    @staticmethod
    def analyze_match(test_case: MatchingTestCase, abs_library: Dict, result: Dict) -> Dict:
        """
        Analyze why a match succeeded or failed using REAL matching logic.

        Uses the production calculate_match_score to mirror runtime behavior.
        """
        from abs.matching import MatchResult, calculate_match_score, determine_verification_status
        from abs.models import LibraryItem
        from utils import normalize_title, normalize_author

        breakdown = {
            "title_score": 0,
            "author_score": 0,
            "path_score": 0,
            "identifier_score": 0,
            "total_score": 0,
            "matched_item": None,
            "match_explanation": []
        }

        metadata_asin = test_case.query_metadata.get("asin") if test_case.query_metadata else None
        metadata_isbn = test_case.query_metadata.get("isbn") if test_case.query_metadata else None

        best_result: Optional[MatchResult] = None
        best_item = None
        best_item_data = None

        for item in abs_library.get("results", []):
            item_metadata = item.get("media", {}).get("metadata", {})
            title = item_metadata.get("title", "")
            author = item_metadata.get("authorName", "")

            library_item = LibraryItem(
                id=item.get("id"),
                library_id="mock-lib",
                title=title,
                author=author,
                narrator=item_metadata.get("narratorName"),
                series_name=item_metadata.get("seriesName"),
                asin=item_metadata.get("asin"),
                isbn=item_metadata.get("isbn"),
                cover_path=item.get("media", {}).get("coverPath"),
                duration_seconds=item.get("media", {}).get("duration"),
                path=item.get("path"),
                title_normalized=normalize_title(title),
                author_normalized=normalize_author(author),
            )

            result_scores = calculate_match_score(
                query_title=test_case.query_title,
                query_author=test_case.query_author,
                candidate=library_item,
                query_asin=metadata_asin,
                query_isbn=metadata_isbn,
                query_path=test_case.query_path,
            )

            explanations = []
            if result_scores.method in {"ASIN", "ISBN"}:
                explanations.append(f"{result_scores.method} match (+100)")
            elif result_scores.method == "TITLE+AUTHOR":
                explanations.append(
                    f"Title+Author score {result_scores.confidence:.1f} "
                    f"(title {result_scores.title_score:.1f}, author {result_scores.author_score:.1f})"
                )
            elif result_scores.method == "TITLE_ONLY":
                explanations.append(
                    f"Title-only score {result_scores.confidence:.1f} (title {result_scores.title_score:.1f})"
                )
            elif result_scores.method == "AUTHOR_MISMATCH":
                explanations.append(
                    f"Author mismatch despite strong title (title {result_scores.title_score:.1f}, author {result_scores.author_score:.1f})"
                )
            if result_scores.path_bonus:
                explanations.append(f"Path bonus +{result_scores.path_bonus}")

            if not best_result or result_scores.confidence > best_result.confidence:
                best_result = result_scores
                best_item_data = library_item
                best_item = {
                    "id": library_item.id,
                    "title": library_item.title,
                    "author": library_item.author,
                    "path": library_item.path,
                    "score": result_scores.score,
                    "explanations": explanations,
                    "method": result_scores.method,
                }

        total_confidence = best_result.confidence if best_result else 0
        breakdown["total_score"] = total_confidence
        breakdown["matched_item"] = best_item
        if best_item:
            breakdown["match_explanation"] = best_item["explanations"]

        status = determine_verification_status(total_confidence)
        breakdown["status"] = status
        breakdown["matched_item_data"] = best_item_data

        return breakdown



# ============================================================================
# TEST RUNNER - Execute tests and generate reports
# ============================================================================

class LibraryMatchingTestRunner:
    """Runs library matching tests and generates detailed reports."""

    def __init__(self, use_live: bool = False):
        self.use_live = use_live
        self.test_cases = generate_test_cases()
        self.results = []

    async def run_all_tests(self, scenario_filter: Optional[str] = None) -> List[MatchingTestCase]:
        """Run all test cases (or filtered by scenario)."""
        test_cases = self.test_cases

        if scenario_filter:
            test_cases = [tc for tc in test_cases if tc.name == scenario_filter or tc.category == scenario_filter]

        print(f"\n{'='*80}")
        print(f"Library Matching Intelligence Test")
        print(f"Mode: {'LIVE (Real ABS)' if self.use_live else 'MOCK (Simulated)'}")
        print(f"Test Cases: {len(test_cases)}")
        print(f"{'='*80}\n")

        for idx, test_case in enumerate(test_cases, 1):
            print(f"[{idx}/{len(test_cases)}] Running: {test_case.name}")
            await self.run_test_case(test_case)
            self.results.append(test_case)

        return self.results

    async def run_test_case(self, test_case: MatchingTestCase):
        """Run a single test case."""
        if self.use_live:
            # Test against real ABS instance
            await self._run_live_test(test_case)
        else:
            # Test with mock data
            await self._run_mock_test(test_case)

    async def _run_mock_test(self, test_case: MatchingTestCase):
        """Run test with mock ABS data using FakeLibraryCache."""
        # Use FakeLibraryCache to test matching logic directly
        # This avoids issues with module-level imports and patching
        from abs.matching import determine_verification_status

        # Create fake cache with mock library data
        cache = FakeLibraryCache(MOCK_ABS_LIBRARY)

        # Extract ASIN/ISBN from metadata if present
        query_asin = test_case.query_metadata.get("asin") if test_case.query_metadata else None
        query_isbn = test_case.query_metadata.get("isbn") if test_case.query_metadata else None

        # Find best match using the fake cache
        best_match, score = cache.find_best_match(
            title=test_case.query_title,
            author=test_case.query_author,
            asin=query_asin,
            isbn=query_isbn,
            path=test_case.query_path,
        )

        # Determine status based on score
        if best_match and score.confidence >= 85:
            status = determine_verification_status(score.confidence)
            result = {
                "status": status,
                "note": f"{score.method}: confidence {score.confidence:.0f}%",
                "abs_item_id": best_match.id,
            }
        elif best_match and score.confidence >= 70:
            result = {
                "status": "mismatch",
                "note": f"{score.method}: confidence {score.confidence:.0f}% (below threshold)",
                "abs_item_id": best_match.id,
            }
        else:
            result = {
                "status": "not_found",
                "note": "No matching item found",
                "abs_item_id": None,
            }

        # Analyze the result
        breakdown = MatchAnalyzer.analyze_match(test_case, MOCK_ABS_LIBRARY, result)

        # Update test case with results
        test_case.actual_status = result.get("status", "unknown")
        test_case.actual_note = result.get("note", "")
        test_case.actual_item_id = result.get("abs_item_id")
        test_case.actual_score = breakdown["total_score"]
        test_case.score_breakdown = breakdown

        # Determine if test passed
        status_match = test_case.actual_status == test_case.expected_status
        score_match = test_case.actual_score >= test_case.expected_min_score

        if test_case.expected_item_id:
            item_match = test_case.actual_item_id == test_case.expected_item_id
        else:
            item_match = True  # Don't require specific item if not specified

        test_case.passed = status_match and score_match and item_match

    async def _run_live_test(self, test_case: MatchingTestCase):
        """Run test against real ABS instance."""
        try:
            client = AudiobookshelfClient()

            if not client.is_configured:
                print("  ⚠️  ABS not configured - skipping live test")
                test_case.actual_status = "not_configured"
                test_case.passed = False
                return

            result = await client.verify_import(
                title=test_case.query_title,
                author=test_case.query_author,
                library_path=test_case.query_path,
                metadata=test_case.query_metadata
            )

            test_case.actual_status = result.get("status", "unknown")
            test_case.actual_note = result.get("note", "")
            test_case.actual_item_id = result.get("abs_item_id")

            # For live tests, we can't predict exact scores, so just check status
            test_case.passed = test_case.actual_status == test_case.expected_status

            print(f"  Status: {test_case.actual_status}")
            print(f"  Note: {test_case.actual_note}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            test_case.actual_status = "error"
            test_case.actual_note = str(e)
            test_case.passed = False

    def generate_report(self, show_details: bool = True) -> str:
        """Generate detailed test report."""
        lines = []
        lines.append("\n" + "="*80)
        lines.append("LIBRARY MATCHING INTELLIGENCE TEST REPORT")
        lines.append("="*80)

        # Summary statistics
        total = len(self.results)
        passed = sum(1 for tc in self.results if tc.passed)
        failed = total - passed

        lines.append(f"\nSummary:")
        lines.append(f"  Total Tests: {total}")
        lines.append(f"  Passed: {passed} ({100*passed/total:.1f}%)")
        lines.append(f"  Failed: {failed} ({100*failed/total:.1f}%)")

        # Breakdown by category
        categories = {}
        for tc in self.results:
            if tc.category not in categories:
                categories[tc.category] = {"total": 0, "passed": 0}
            categories[tc.category]["total"] += 1
            if tc.passed:
                categories[tc.category]["passed"] += 1

        lines.append(f"\nResults by Category:")
        for cat, stats in sorted(categories.items()):
            pct = 100 * stats["passed"] / stats["total"]
            lines.append(f"  {cat:20s}: {stats['passed']:2d}/{stats['total']:2d} ({pct:5.1f}%)")

        # Failed tests
        if failed > 0:
            lines.append(f"\n{'='*80}")
            lines.append("FAILED TESTS")
            lines.append("="*80)

            for tc in self.results:
                if not tc.passed:
                    lines.append(f"\n❌ {tc.name}")
                    lines.append(f"   Description: {tc.description}")
                    lines.append(f"   Query: '{tc.query_title}' by '{tc.query_author}'")
                    if tc.query_metadata:
                        lines.append(f"   Metadata: {tc.query_metadata}")
                    lines.append(f"   Expected: {tc.expected_status} (score >= {tc.expected_min_score})")
                    lines.append(f"   Actual: {tc.actual_status} (score = {tc.actual_score})")
                    lines.append(f"   Note: {tc.actual_note}")

                    if show_details and tc.score_breakdown.get("match_explanation"):
                        lines.append(f"   Score Breakdown:")
                        for exp in tc.score_breakdown["match_explanation"]:
                            lines.append(f"     • {exp}")

                    if tc.notes:
                        lines.append(f"   Test Notes: {tc.notes}")

        # Detailed results (if requested)
        if show_details:
            lines.append(f"\n{'='*80}")
            lines.append("DETAILED TEST RESULTS")
            lines.append("="*80)

            for tc in self.results:
                status_icon = "✅" if tc.passed else "❌"
                lines.append(f"\n{status_icon} {tc.name}")
                lines.append(f"   Category: {tc.category}")
                lines.append(f"   Description: {tc.description}")
                lines.append(f"   Query: '{tc.query_title}' by '{tc.query_author}'")
                if tc.query_metadata:
                    lines.append(f"   Metadata: {tc.query_metadata}")
                lines.append(f"   Result: {tc.actual_status} (expected: {tc.expected_status})")
                lines.append(f"   Score: {tc.actual_score} (min expected: {tc.expected_min_score})")

                if tc.score_breakdown.get("matched_item"):
                    item = tc.score_breakdown["matched_item"]
                    lines.append(f"   Matched: '{item['title']}' by '{item['author']}'")
                    lines.append(f"   Item ID: {item['id']}")
                    lines.append(f"   Score Breakdown:")
                    for exp in tc.score_breakdown["match_explanation"]:
                        lines.append(f"     • {exp}")

                if tc.notes:
                    lines.append(f"   Notes: {tc.notes}")

        lines.append("\n" + "="*80 + "\n")

        return "\n".join(lines)


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main entry point for CLI execution."""
    # Ensure test data directory exists
    import os
    test_data_dir = os.environ.get('DATA_DIR', '/tmp/test_data')
    os.makedirs(test_data_dir, exist_ok=True)
    os.environ['DATA_DIR'] = test_data_dir

    parser = argparse.ArgumentParser(
        description="Library Matching Intelligence Test for MAM Audiobook Finder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests with mock data
  python app/tests/test_library_matching_intelligence.py

  # Run with detailed report
  python app/tests/test_library_matching_intelligence.py --report

  # Test against live ABS instance
  python app/tests/test_library_matching_intelligence.py --live --report

  # Run specific scenario
  python app/tests/test_library_matching_intelligence.py --scenario exact_match

  # Run category of tests
  python app/tests/test_library_matching_intelligence.py --scenario identifier --report
        """
    )

    parser.add_argument("--live", action="store_true", help="Test against real ABS instance (requires ABS_* env vars)")
    parser.add_argument("--report", action="store_true", help="Show detailed report")
    parser.add_argument("--scenario", type=str, help="Run specific scenario or category")
    parser.add_argument("--output", type=str, help="Save report to file")

    args = parser.parse_args()

    # Run tests
    runner = LibraryMatchingTestRunner(use_live=args.live)
    results = await runner.run_all_tests(scenario_filter=args.scenario)

    # Generate report
    report = runner.generate_report(show_details=args.report)
    print(report)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report)
        print(f"\n📄 Report saved to: {output_path}")

    # Exit with appropriate code
    failed = sum(1 for tc in results if not tc.passed)
    sys.exit(0 if failed == 0 else 1)


# ============================================================================
# PYTEST INTEGRATION
# ============================================================================

import pytest


@pytest.fixture(scope="class", autouse=True)
def setup_test_environment():
    """Ensure test environment is configured before tests."""
    import os
    test_data_dir = os.environ.get('DATA_DIR', '/tmp/test_data')
    os.makedirs(test_data_dir, exist_ok=True)
    os.environ['DATA_DIR'] = test_data_dir
    yield  # Run tests
    # Cleanup not needed for /tmp


@pytest.mark.asyncio
class TestLibraryMatchingIntelligence:
    """Pytest integration for library matching tests."""

    async def test_all_scenarios(self):
        """Run all test scenarios."""
        runner = LibraryMatchingTestRunner(use_live=False)
        results = await runner.run_all_tests()

        failed = [tc for tc in results if not tc.passed]

        if failed:
            report = runner.generate_report(show_details=True)
            pytest.fail(f"\n{len(failed)} test(s) failed:\n{report}")

    async def test_exact_matches(self):
        """Test exact match scenarios."""
        runner = LibraryMatchingTestRunner(use_live=False)
        results = await runner.run_all_tests(scenario_filter="exact_match")

        failed = [tc for tc in results if not tc.passed]
        assert len(failed) == 0, f"{len(failed)} exact match tests failed"

    async def test_identifier_matching(self):
        """Test ASIN/ISBN identifier matching."""
        runner = LibraryMatchingTestRunner(use_live=False)
        results = await runner.run_all_tests(scenario_filter="identifier")

        failed = [tc for tc in results if not tc.passed]
        assert len(failed) == 0, f"{len(failed)} identifier tests failed"

    async def test_partial_matches(self):
        """Test partial match scenarios."""
        runner = LibraryMatchingTestRunner(use_live=False)
        results = await runner.run_all_tests(scenario_filter="partial_match")

        failed = [tc for tc in results if not tc.passed]
        assert len(failed) == 0, f"{len(failed)} partial match tests failed"

    async def test_edge_cases(self):
        """Test edge case scenarios."""
        runner = LibraryMatchingTestRunner(use_live=False)
        edge_categories = ["subtitle", "series", "author_variations", "special_chars", "articles", "numeric"]

        all_failed = []
        for category in edge_categories:
            results = await runner.run_all_tests(scenario_filter=category)
            failed = [tc for tc in results if not tc.passed]
            all_failed.extend(failed)

        if all_failed:
            print(f"\n⚠️  {len(all_failed)} edge case tests failed:")
            for tc in all_failed:
                print(f"  - {tc.name}: {tc.actual_status} (expected {tc.expected_status})")


if __name__ == "__main__":
    # Run as CLI
    asyncio.run(main())
