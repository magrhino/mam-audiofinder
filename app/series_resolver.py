"""
Dual-source series resolution: ABS + Hardcover.
Matches series across sources and provides unified diff interface.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Literal
from enum import Enum

from utils import normalize_title, normalize_author

logger = logging.getLogger("mam-audiofinder")


class SeriesSource(Enum):
    ABS = "abs"
    HARDCOVER = "hardcover"
    BOTH = "both"


@dataclass
class SeriesInfo:
    """Unified series representation from any source."""
    id: str                          # Synthetic or native ID
    name: str
    name_normalized: str
    author: Optional[str] = None
    book_count: int = 0
    source: SeriesSource = SeriesSource.ABS

    # Source-specific IDs
    abs_series_id: Optional[str] = None
    hardcover_series_id: Optional[int] = None

    # Cross-match metadata
    cross_match_score: int = 0
    cross_match_name: Optional[str] = None


@dataclass
class BookInSeries:
    """Unified book representation within a series."""
    id: str
    title: str
    title_normalized: str
    author: Optional[str] = None
    series_index: Optional[float] = None

    # Identifiers
    asin: Optional[str] = None
    isbn: Optional[str] = None

    # Source tracking
    source: SeriesSource = SeriesSource.ABS
    abs_item_id: Optional[str] = None
    hardcover_book_id: Optional[int] = None

    # Audiobook metadata
    has_audiobook: Optional[bool] = None
    audio_seconds: Optional[int] = None

    # Cover
    cover_url: Optional[str] = None


@dataclass
class SeriesDiffResult:
    """Result of comparing series across ABS and Hardcover."""
    series_name: str
    series_name_normalized: str

    # Books present in ABS
    present: List[Dict] = field(default_factory=list)

    # Books missing from ABS (in Hardcover)
    missing: List[Dict] = field(default_factory=list)

    # Books in ABS but not in Hardcover
    abs_only: List[Dict] = field(default_factory=list)

    # Ambiguous matches
    uncertain: List[Dict] = field(default_factory=list)

    # Counts
    abs_book_count: int = 0
    hardcover_book_count: int = 0
    match_confidence: float = 0.0


def generate_series_id(series_name: str, author: str = "") -> str:
    """Generate stable synthetic series ID."""
    key = f"{normalize_title(series_name)}|{normalize_author(author or '')}"
    return f"syn_{hashlib.md5(key.encode()).hexdigest()[:12]}"


def normalize_series_name(name: str) -> str:
    """Normalize series name for cross-source matching."""
    if not name:
        return ""

    normalized = normalize_title(name)

    # Strip common suffixes
    suffixes = ["series", "trilogy", "saga", "chronicles", "cycle", "books", "novels"]
    words = normalized.split()
    if words and words[-1] in suffixes:
        words = words[:-1]

    return " ".join(words)


def score_series_match(abs_name: str, hc_name: str, abs_author: str = "", hc_author: str = "") -> int:
    """Score series match confidence (0-100)."""
    score = 0

    abs_norm = normalize_series_name(abs_name)
    hc_norm = normalize_series_name(hc_name)

    # Name matching
    if abs_norm == hc_norm:
        score += 50
    elif abs_norm in hc_norm or hc_norm in abs_norm:
        score += 30
    else:
        return 0

    # Author matching
    if abs_author and hc_author:
        abs_author_norm = normalize_author(abs_author)
        hc_author_norm = normalize_author(hc_author)
        if abs_author_norm == hc_author_norm:
            score += 30
        elif abs_author_norm in hc_author_norm or hc_author_norm in abs_author_norm:
            score += 15

    return min(score, 100)


def match_books_across_sources(
    abs_books: List[BookInSeries],
    hardcover_books: List[Dict],
) -> SeriesDiffResult:
    """
    Match books between ABS and Hardcover.

    Matching priority:
    1. ASIN exact match (score 200)
    2. ISBN exact match (score 200)
    3. Title + Author + Position (score 50-175)

    Categorization thresholds:
    - present: score >= 100
    - uncertain: score 50-99
    - missing: score < 50
    """
    result = SeriesDiffResult(
        series_name="",
        series_name_normalized="",
        abs_book_count=len(abs_books),
        hardcover_book_count=len(hardcover_books),
    )

    matched_abs_ids = set()

    for hc_book in hardcover_books:
        hc_title = hc_book.get("title", "")
        hc_title_norm = normalize_title(hc_title)
        hc_authors = hc_book.get("authors") or hc_book.get("author_names") or []
        hc_author = hc_authors[0] if hc_authors else ""
        hc_position = hc_book.get("position")

        # Extract ASIN/ISBN from Hardcover
        hc_asin, hc_isbn = None, None
        for isbn_entry in hc_book.get("isbns", []):
            if isinstance(isbn_entry, dict):
                val = isbn_entry.get("isbn", "")
            else:
                val = str(isbn_entry)
            if val.startswith("B0"):
                hc_asin = val
            elif len(val) in (10, 13) and val.replace("-", "").isdigit():
                hc_isbn = val.replace("-", "")

        best_match = None
        best_score = 0

        for abs_book in abs_books:
            # ASIN match
            if hc_asin and abs_book.asin:
                if hc_asin.lower() == abs_book.asin.lower():
                    best_match, best_score = abs_book, 200
                    break

            # ISBN match
            if hc_isbn and abs_book.isbn:
                if hc_isbn == abs_book.isbn:
                    best_match, best_score = abs_book, 200
                    break

            # Title matching
            score = 0
            if abs_book.title_normalized == hc_title_norm:
                score += 100
            elif abs_book.title_normalized in hc_title_norm or hc_title_norm in abs_book.title_normalized:
                score += 50
            else:
                continue  # No title match = skip

            # Author matching
            if abs_book.author and hc_author:
                abs_author_norm = normalize_author(abs_book.author)
                hc_author_norm = normalize_author(hc_author)
                if abs_author_norm == hc_author_norm:
                    score += 50
                elif abs_author_norm in hc_author_norm or hc_author_norm in abs_author_norm:
                    score += 25

            # Position matching
            if abs_book.series_index and hc_position:
                if abs_book.series_index == hc_position:
                    score += 25

            if score > best_score:
                best_match, best_score = abs_book, score

        # Categorize
        entry = {
            "hardcover": hc_book,
            "abs": best_match.__dict__ if best_match else None,
            "score": best_score,
        }

        if best_score >= 100:
            result.present.append(entry)
            if best_match:
                matched_abs_ids.add(best_match.id)
        elif best_score >= 50:
            result.uncertain.append(entry)
            if best_match:
                matched_abs_ids.add(best_match.id)
        else:
            result.missing.append(entry)

    # Find ABS-only books
    for abs_book in abs_books:
        if abs_book.id not in matched_abs_ids:
            result.abs_only.append({"abs": abs_book.__dict__})

    # Calculate confidence
    if len(hardcover_books) > 0:
        result.match_confidence = len(result.present) / len(hardcover_books)

    return result
