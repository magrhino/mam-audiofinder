"""Title/author/ASIN matching logic for verification."""

from typing import Optional
from abs.models import LibraryItem
from utils import normalize_title, normalize_author

# Scoring constants
SCORE_ASIN_MATCH = 200
SCORE_ISBN_MATCH = 200
SCORE_TITLE_EXACT = 100
SCORE_TITLE_PARTIAL = 50
SCORE_AUTHOR_EXACT = 50
SCORE_AUTHOR_PARTIAL = 25
SCORE_PATH_MATCH = 25
THRESHOLD_VERIFIED = 100
THRESHOLD_MISMATCH = 50


def calculate_match_score(
    query_title: str,
    query_author: str,
    candidate: LibraryItem,
    query_asin: Optional[str] = None,
    query_isbn: Optional[str] = None,
    query_path: Optional[str] = None,
) -> int:
    """Calculate match score between query and library item."""

    # ASIN/ISBN exact match (highest priority)
    if query_asin and candidate.asin:
        if query_asin.lower() == candidate.asin.lower():
            return SCORE_ASIN_MATCH

    if query_isbn and candidate.isbn:
        if query_isbn.lower() == candidate.isbn.lower():
            return SCORE_ISBN_MATCH

    score = 0

    # Title matching
    query_title_norm = normalize_title(query_title)
    candidate_title_norm = candidate.title_normalized or normalize_title(candidate.title)

    if query_title_norm == candidate_title_norm:
        score += SCORE_TITLE_EXACT
    elif query_title_norm in candidate_title_norm or candidate_title_norm in query_title_norm:
        score += SCORE_TITLE_PARTIAL
    else:
        return 0  # No title match = no match

    # Author matching
    if query_author:
        query_author_norm = normalize_author(query_author)
        candidate_author_norm = candidate.author_normalized or normalize_author(candidate.author or "")

        if query_author_norm == candidate_author_norm:
            score += SCORE_AUTHOR_EXACT
        elif query_author_norm in candidate_author_norm or candidate_author_norm in query_author_norm:
            score += SCORE_AUTHOR_PARTIAL
        else:
            # Author explicitly provided but doesn't match
            # Cap score to prevent false verification when author is wrong
            if score >= SCORE_TITLE_EXACT:  # Title exact match (100 pts)
                score = THRESHOLD_MISMATCH + 25  # Cap to 75 (mismatch range)
    else:
        score += 10  # No author to verify

    # Path matching
    if query_path and candidate.path:
        query_path_norm = query_path.lower().replace("\\", "/").strip("/")
        candidate_path_norm = candidate.path.lower().replace("\\", "/").strip("/")
        if query_path_norm in candidate_path_norm or candidate_path_norm in query_path_norm:
            score += SCORE_PATH_MATCH

    return score


def determine_verification_status(score: int) -> str:
    """Determine verification status from score."""
    if score >= THRESHOLD_VERIFIED:
        return "verified"
    elif score >= THRESHOLD_MISMATCH:
        return "mismatch"
    else:
        return "not_found"
