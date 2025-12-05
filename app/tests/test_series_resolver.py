"""Tests for series_resolver module."""

import pytest
from series_resolver import (
    generate_series_id,
    normalize_series_name,
    score_series_match,
    match_books_across_sources,
    BookInSeries,
    SeriesSource,
)


class TestGenerateSeriesId:
    def test_consistent_ids(self):
        """Same input produces same ID."""
        id1 = generate_series_id("The Expanse", "James S.A. Corey")
        id2 = generate_series_id("The Expanse", "James S.A. Corey")
        assert id1 == id2

    def test_different_inputs_different_ids(self):
        """Different inputs produce different IDs."""
        id1 = generate_series_id("The Expanse", "James S.A. Corey")
        id2 = generate_series_id("Foundation", "Isaac Asimov")
        assert id1 != id2

    def test_normalization(self):
        """IDs are normalized (case, articles)."""
        id1 = generate_series_id("The Expanse")
        id2 = generate_series_id("expanse")
        assert id1 == id2


class TestNormalizeSeriesName:
    def test_strips_suffixes(self):
        assert normalize_series_name("The Expanse Series") == "expanse"
        assert normalize_series_name("Foundation Trilogy") == "foundation"

    def test_handles_empty(self):
        assert normalize_series_name("") == ""
        assert normalize_series_name(None) == ""


class TestScoreSeriesMatch:
    def test_exact_match(self):
        score = score_series_match("The Expanse", "The Expanse")
        assert score >= 50

    def test_no_match(self):
        score = score_series_match("The Expanse", "Foundation")
        assert score == 0

    def test_author_bonus(self):
        score_no_author = score_series_match("The Expanse", "The Expanse", "", "")
        score_with_author = score_series_match("The Expanse", "The Expanse", "James Corey", "James Corey")
        assert score_with_author > score_no_author


class TestMatchBooksAcrossSources:
    def test_asin_match(self):
        """ASIN exact match scores 200."""
        abs_books = [
            BookInSeries(
                id="abs1", title="Book One", title_normalized="book one",
                asin="B001234567", source=SeriesSource.ABS
            )
        ]
        hc_books = [
            {"book_id": 1, "title": "Book 1", "isbns": [{"isbn": "B001234567"}]}
        ]

        result = match_books_across_sources(abs_books, hc_books)
        assert len(result.present) == 1
        assert result.present[0]["score"] == 200

    def test_title_match(self):
        """Title exact match scores 100."""
        abs_books = [
            BookInSeries(
                id="abs1", title="Book One", title_normalized="book one",
                source=SeriesSource.ABS
            )
        ]
        hc_books = [
            {"book_id": 1, "title": "Book One"}
        ]

        result = match_books_across_sources(abs_books, hc_books)
        assert len(result.present) == 1
        assert result.present[0]["score"] >= 100

    def test_missing_detection(self):
        """Unmatched Hardcover books are marked missing."""
        abs_books = []
        hc_books = [
            {"book_id": 1, "title": "Book One"}
        ]

        result = match_books_across_sources(abs_books, hc_books)
        assert len(result.missing) == 1
        assert len(result.present) == 0

    def test_abs_only_detection(self):
        """ABS books not in Hardcover are tracked."""
        abs_books = [
            BookInSeries(
                id="abs1", title="Bonus Story", title_normalized="bonus story",
                source=SeriesSource.ABS
            )
        ]
        hc_books = [
            {"book_id": 1, "title": "Different Book"}
        ]

        result = match_books_across_sources(abs_books, hc_books)
        assert len(result.abs_only) == 1
