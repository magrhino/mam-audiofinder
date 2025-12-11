"""Book matching logic using rapidfuzz for title/author similarity."""

from dataclasses import dataclass
import re
import unicodedata
from typing import Optional

from rapidfuzz import fuzz

from abs.models import LibraryItem


@dataclass
class MatchResult:
    """Structured result from a matching attempt."""

    confidence: float
    method: str
    title_score: float = 0.0
    author_score: float = 0.0
    path_bonus: float = 0.0

    @property
    def score(self) -> int:
        """Integer score for legacy consumers."""
        return int(round(self.confidence))


NOISE_WORDS = {"a", "an", "the", "novel", "book"}


def _normalize_identifier(value: Optional[str]) -> str:
    """Normalize ASIN/ISBN by stripping separators and uppercasing."""
    if not value:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def _is_graphic_audio(author: Optional[str]) -> bool:
    if not author:
        return False
    normalized = author.lower().replace(" ", "")
    return "graphicaudio" in normalized


def _normalize_path(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.lower().replace("\\", "/").strip("/")


def _strip_noise_words(text: str) -> str:
    if not text:
        return ""
    pattern = r"\b(" + "|".join(NOISE_WORDS) + r")\b"
    return re.sub(pattern, " ", text, flags=re.IGNORECASE)


def _unicode_lower(text: str) -> str:
    return unicodedata.normalize("NFKD", text).lower()


def clean_title(title: Optional[str]) -> str:
    """Clean title for fuzzy matching (lower, strip punctuation, drop subtitles/noise)."""
    if not title:
        return ""

    text = _unicode_lower(title)
    # Keep delimiters for subtitle split, strip other punctuation
    text = re.sub(r"[^\w\s:–—-]", " ", text)
    # Primary title before subtitle markers
    text = re.split(r"[:–—-]", text)[0]
    # Remove series markers like "(Series #1)"
    text = re.sub(r"\([^)]*#\d+[^)]*\)", " ", text)
    # Remove edition phrases
    text = re.sub(r"\b\d+(st|nd|rd|th)\s+anniversary edition\b", " ", text)
    text = re.sub(r"\bedition\b", " ", text)
    # Drop common noise words and normalize whitespace
    text = _strip_noise_words(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_author(author: Optional[str]) -> str:
    """Clean author string, handling comma order and multi-author separators."""
    if not author:
        return ""

    text = _unicode_lower(author)
    text = text.replace(".", " ")

    # Multi-author separators
    multi_sep = r"\s+(?:&|and|;)\s+"
    if re.search(multi_sep, text):
        parts = re.split(multi_sep, text)
    elif text.count(",") == 1:
        # Handle "Last, First"
        last, first = [p.strip() for p in text.split(",", 1)]
        parts = [f"{first} {last}".strip()]
    else:
        parts = [text.replace(",", " ")]

    cleaned_parts = []
    for part in parts:
        part = re.sub(r"[^\w\s]", " ", part)
        part = re.sub(r"\s+", " ", part).strip()
        if part:
            cleaned_parts.append(part)

    return " & ".join(cleaned_parts)


def best_title_score(a: Optional[str], b: Optional[str]) -> float:
    """Calculate best fuzzy score between two titles."""
    clean_a = clean_title(a)
    clean_b = clean_title(b)
    if not clean_a or not clean_b:
        return 0.0
    return max(
        fuzz.token_set_ratio(clean_a, clean_b),
        fuzz.token_sort_ratio(clean_a, clean_b),
        fuzz.ratio(clean_a, clean_b),
    )


def best_author_score(a: Optional[str], b: Optional[str]) -> float:
    """Calculate best fuzzy score between authors (order-insensitive)."""
    clean_a = clean_author(a)
    clean_b = clean_author(b)
    if not clean_a or not clean_b:
        return 0.0
    return max(
        fuzz.token_sort_ratio(clean_a, clean_b),
        fuzz.ratio(clean_a, clean_b),
    )


def calculate_match_score(
    query_title: str,
    query_author: str,
    candidate: LibraryItem,
    query_asin: Optional[str] = None,
    query_isbn: Optional[str] = None,
    query_path: Optional[str] = None,
) -> MatchResult:
    """Calculate confidence and method for a candidate against a query."""

    query_asin_norm = _normalize_identifier(query_asin)
    query_isbn_norm = _normalize_identifier(query_isbn)
    candidate_asin = _normalize_identifier(candidate.asin)
    candidate_isbn = _normalize_identifier(candidate.isbn)

    # Level 1: Identifier short-circuit
    if query_asin_norm and candidate_asin and query_asin_norm == candidate_asin:
        return MatchResult(confidence=100.0, method="ASIN")
    if query_isbn_norm and candidate_isbn and query_isbn_norm == candidate_isbn:
        return MatchResult(confidence=100.0, method="ISBN")

    # Level 2: Title + Author
    title_score = best_title_score(query_title, candidate.title)
    author_score = best_author_score(query_author, candidate.author or "") if query_author else 0.0

    combined = (0.6 * title_score) + (0.4 * author_score)
    confidence = 0.0
    method = "NO_MATCH"

    graphic_audio_override = _is_graphic_audio(query_author) or _is_graphic_audio(candidate.author)
    author_conflict = False
    if query_author and not graphic_audio_override:
        author_conflict = author_score < 50 and title_score >= 85

    if query_author and author_score and combined >= 85 and not author_conflict:
        confidence = min(100.0, combined)
        method = "TITLE+AUTHOR"
    elif author_conflict:
        # Author mismatch detected - check if title is strong enough for fallback
        if title_score >= 90:
            confidence = min(100.0, title_score * 0.9)
            method = "TITLE_ONLY"
        else:
            confidence = 70.0
            method = "AUTHOR_MISMATCH"

    # Level 3: Title-only fallback (when no author provided or other cases)
    if method == "NO_MATCH" and title_score >= 90:
        confidence = min(100.0, title_score * 0.9)
        method = "TITLE_ONLY"

    path_bonus = 0.0
    if query_path and candidate.path:
        qp = _normalize_path(query_path)
        cp = _normalize_path(candidate.path)
        if qp and cp and (qp in cp or cp in qp):
            path_bonus = 2.5
            confidence = min(100.0, confidence + path_bonus)

    return MatchResult(
        confidence=confidence,
        method=method,
        title_score=title_score,
        author_score=author_score,
        path_bonus=path_bonus,
    )


def determine_verification_status(score: float) -> str:
    """Determine verification status from confidence score."""
    if score >= 85:
        return "verified"
    if score >= 70:
        return "mismatch"
    return "not_found"
