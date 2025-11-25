"""
English Primary Edition Resolver for Series Books

This module provides functionality to determine the correct English edition for each
position in a book series. It uses language identification (lingua), fuzzy text
matching (RapidFuzz), and popularity metrics (Hardcover users_count) to resolve
ambiguous cases.

Key Features:
- Language detection using lingua-language-detector
- Title similarity scoring using RapidFuzz partial_ratio
- Length-weighted scoring (shorter titles preferred)
- Popularity-based tiebreaking for ambiguous cases
- Database caching in series.db for performance

Architecture:
1. Group books by position (preserving fractional positions like 0.5, 2.5)
2. Score each book based on language, title similarity, and length
3. Select highest-scored book, or mark as ambiguous if within threshold
4. For ambiguous cases, fetch popularity data and select most popular
5. Cache resolved editions in series.db
"""
import logging
from lingua import Language, LanguageDetectorBuilder
from typing import Dict, List, Any, Optional
from rapidfuzz import fuzz
from sqlalchemy import text

from db.db import get_series_engine

logger = logging.getLogger("mam-audiofinder")

# Global lingua detector instance (singleton pattern)
_lingua_detector = None

# Constants
ENGLISH_LANGUAGE_THRESHOLD = 0.70  # Lingua confidence threshold for English
AMBIGUITY_THRESHOLD = 5  # Score difference threshold for ambiguity detection
SCORE_ENGLISH = 10  # Bonus for English language
SCORE_NON_ENGLISH = -10  # Penalty for non-English
SCORE_LENGTH_MAX = 5  # Max bonus/penalty for title length


def load_lingua_detector():
    """
    Load lingua language detector (singleton).

    Creates a LanguageDetector configured for English detection with confidence values.
    The detector is lightweight and requires no model files to be downloaded.

    Returns:
        LanguageDetector instance

    Raises:
        Exception: If detector creation fails
    """
    global _lingua_detector

    if _lingua_detector is not None:
        return _lingua_detector

    logger.info("🔧 Initializing lingua language detector...")

    try:
        # Build detector for English and common languages in book metadata
        # Using fewer languages improves accuracy and performance
        _lingua_detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH,
            Language.SPANISH,
            Language.FRENCH,
            Language.GERMAN,
            Language.ITALIAN,
            Language.PORTUGUESE,
            Language.CHINESE,
            Language.JAPANESE,
        ).with_preloaded_language_models().build()

        logger.info("✅ Lingua detector initialized successfully")
        return _lingua_detector

    except Exception as e:
        logger.error(f"❌ Failed to initialize lingua detector: {e}")
        raise


def is_english(text: str, threshold: float = ENGLISH_LANGUAGE_THRESHOLD) -> bool:
    """
    Detect if text is in English using lingua language identification.

    Args:
        text: Text to analyze (typically book title)
        threshold: Minimum confidence score for English detection (default: 0.70)

    Returns:
        True if detected language is English with confidence >= threshold

    Example:
        >>> is_english("All Systems Red")
        True
        >>> is_english("Libro Uno")
        False
    """
    if not text or not text.strip():
        return False

    try:
        detector = load_lingua_detector()

        # Lingua works with cleaned text (no special preprocessing needed)
        cleaned_text = text.replace('\n', ' ').strip()

        # Compute confidence values for all languages
        confidence_values = detector.compute_language_confidence_values(cleaned_text)

        if confidence_values:
            # Find English confidence (if present)
            english_confidence = 0.0
            detected_lang = None
            max_confidence = 0.0

            for conf in confidence_values:
                if conf.value > max_confidence:
                    max_confidence = conf.value
                    detected_lang = conf.language.iso_code_639_1.name.lower()

                if conf.language == Language.ENGLISH:
                    english_confidence = conf.value

            is_en = detected_lang == 'en' and english_confidence >= threshold

            logger.debug(
                f"   Lang detect: '{text[:30]}...' → {detected_lang} "
                f"(confidence: {english_confidence:.3f}, is_en: {is_en})"
            )

            return is_en

        return False

    except Exception as e:
        logger.warning(f"⚠️  Language detection failed for '{text[:30]}...': {e}")
        # Fallback: assume English if detection fails (conservative approach)
        return True


def has_accented_characters(text: str) -> bool:
    """
    Detect if text contains accented Latin characters (French, Portuguese, Spanish, etc.).

    This helps distinguish English editions from Romance language editions by checking
    for diacritical marks that don't appear in English text.

    Common accents detected:
    - French: é è ê ë ç à â ù û
    - Portuguese: ã õ á é í ó ú â ê ô ç
    - Spanish: ñ á é í ó ú ü
    - German: ä ö ü ß
    - Nordic: å æ ø

    Args:
        text: Text to analyze (typically book title)

    Returns:
        True if any accented Latin characters found, False otherwise

    Example:
        >>> has_accented_characters("Artificial Condition")
        False
        >>> has_accented_characters("Schémas artificiels")
        True
        >>> has_accented_characters("Condição Artificial")
        True
    """
    if not text:
        return False

    # Define accented characters common in non-English Latin alphabets
    accented_chars = set('áàâãäåāæçéèêëēíìîïīñóòôõöøōúùûüūýÿÁÀÂÃÄÅĀÆÇÉÈÊËĒÍÌÎÏĪÑÓÒÔÕÖØŌÚÙÛÜŪÝŸß')

    # Check if any character in text is in the accented set
    return any(char in accented_chars for char in text)


def is_latin_script(text: str) -> bool:
    """
    Detect if text uses primarily Latin/Roman alphabet (vs. Cyrillic, Chinese, Arabic, etc.).

    This helps filter out non-English editions written in completely different scripts
    before attempting more granular language detection.

    Rejected scripts:
    - Cyrillic (Russian, Ukrainian, Bulgarian, etc.)
    - Chinese (Simplified/Traditional)
    - Japanese (Hiragana, Katakana, Kanji)
    - Arabic/Hebrew
    - Korean (Hangul)
    - Greek

    Args:
        text: Text to analyze (typically book title)

    Returns:
        True if text is primarily Latin alphabet, False if non-Latin script detected

    Example:
        >>> is_latin_script("All Systems Red")
        True
        >>> is_latin_script("Schémas artificiels")
        True  # Accented but still Latin
        >>> is_latin_script("异星危机")
        False  # Chinese
        >>> is_latin_script("Штучний стан")
        False  # Cyrillic
    """
    if not text or not text.strip():
        return False

    # Count characters by script type
    latin_count = 0
    non_latin_count = 0

    for char in text:
        # Skip whitespace, punctuation, numbers
        if not char.isalpha():
            continue

        code_point = ord(char)

        # Latin alphabet ranges (including accented variants)
        # Basic Latin: U+0041-U+005A (A-Z), U+0061-U+007A (a-z)
        # Latin-1 Supplement: U+00C0-U+00FF (À-ÿ)
        # Latin Extended-A: U+0100-U+017F (Ā-ſ)
        # Latin Extended-B: U+0180-U+024F
        if (0x0041 <= code_point <= 0x005A or  # A-Z
            0x0061 <= code_point <= 0x007A or  # a-z
            0x00C0 <= code_point <= 0x00FF or  # Latin-1 Supplement (accented)
            0x0100 <= code_point <= 0x024F):   # Latin Extended
            latin_count += 1
        else:
            non_latin_count += 1

    # Require at least 70% Latin characters to consider it Latin script
    total_alpha = latin_count + non_latin_count
    if total_alpha == 0:
        return False

    latin_ratio = latin_count / total_alpha
    return latin_ratio >= 0.7


def calculate_length_weight(books_at_position: List[Dict[str, Any]]) -> Dict[int, float]:
    """
    Calculate relative length-based scoring for books at the same position.

    Shorter titles receive bonus points (likely original editions),
    longer titles receive penalties (likely omnibus/bundle editions).

    Scoring:
    - Shortest title in group: +5 points
    - Longest title in group: -5 points
    - Others: Linear interpolation between -5 and +5

    Args:
        books_at_position: List of book dicts with 'book_id' and 'title' keys

    Returns:
        Dictionary mapping book_id to length weight score (-5 to +5)

    Example:
        >>> books = [
        ...     {"book_id": 1, "title": "Book One"},
        ...     {"book_id": 2, "title": "Book One: The Complete Illustrated Edition with Bonus Content"}
        ... ]
        >>> calculate_length_weight(books)
        {1: 5.0, 2: -5.0}
    """
    if not books_at_position or len(books_at_position) == 1:
        # Single book gets neutral score
        return {books_at_position[0]['book_id']: 0.0} if books_at_position else {}

    # Calculate title lengths (including subtitle if present)
    book_lengths = []
    for book in books_at_position:
        title = book.get('title', '')
        subtitle = book.get('subtitle')
        full_title = f"{title} {subtitle}" if subtitle else title
        length = len(full_title)
        book_lengths.append((book['book_id'], length))

    # Find min/max lengths
    min_length = min(length for _, length in book_lengths)
    max_length = max(length for _, length in book_lengths)

    length_range = max_length - min_length

    # Calculate weights (linear interpolation)
    weights = {}
    for book_id, length in book_lengths:
        if length_range == 0:
            # All same length
            weights[book_id] = 0.0
        else:
            # Map from [min_length, max_length] to [+5, -5]
            normalized = (length - min_length) / length_range
            weights[book_id] = SCORE_LENGTH_MAX - (normalized * 2 * SCORE_LENGTH_MAX)

    logger.debug(f"   Length weights: {weights}")
    return weights


def score_book_for_position(
    book: Dict[str, Any],
    canonical_title: Optional[str],
    length_weight: float
) -> float:
    """
    Calculate combined score for a book at a specific series position.

    Scoring formula:
        score = language_score + similarity_score + length_weight

    Where:
        language_score = +10 if English, -10 otherwise
        similarity_score = RapidFuzz partial_ratio(title, canonical_title) [0-100]
        length_weight = Relative length bonus/penalty [-5 to +5]

    Args:
        book: Book dictionary with 'title' and optional 'subtitle' keys
        canonical_title: Reference English title for this position (from series metadata)
        length_weight: Pre-calculated length weight for this book

    Returns:
        Combined score (typically range: -5 to 115)

    Example:
        >>> book = {"title": "All Systems Red", "subtitle": None}
        >>> score_book_for_position(book, "Murderbot Diaries 1", 3.5)
        78.5  # Assuming English detected and 65% title match
    """
    title = book.get('title', '')
    subtitle = book.get('subtitle')

    # Combine title and subtitle for full comparison
    full_title = f"{title} {subtitle}" if subtitle else title

    # Component 1: Language detection
    is_en = is_english(full_title)
    language_score = SCORE_ENGLISH if is_en else SCORE_NON_ENGLISH

    # Component 2: Title similarity (if canonical title provided)
    similarity_score = 0
    if canonical_title:
        # Use RapidFuzz partial_ratio (best for substring matching)
        similarity_score = fuzz.partial_ratio(full_title.lower(), canonical_title.lower())

        logger.debug(
            f"   Title similarity: '{full_title[:40]}' <> '{canonical_title[:40]}' "
            f"= {similarity_score}/100"
        )

    # Component 3: Length weight (already calculated)
    # Pre-calculated to avoid recalculating for each book

    # Combined score
    total_score = language_score + similarity_score + length_weight

    logger.debug(
        f"   Score breakdown: lang={language_score}, similarity={similarity_score}, "
        f"length={length_weight:.1f} → total={total_score:.1f}"
    )

    return total_score


async def resolve_english_primary_edition(
    raw_books: List[Dict[str, Any]],
    series_metadata: Dict[str, Any],
    hardcover_client
) -> Dict[float, Any]:
    """
    Determine the correct English edition for each series position.

    Main entry point for edition resolution. Groups books by position,
    scores each book, resolves ambiguities, and returns a dictionary
    mapping position to selected book(s).

    Process:
    1. Group books by exact position value (preserves fractional positions)
    2. For each position group:
       a. Load canonical title from series metadata
       b. Calculate length weights for all books in group
       c. Score each book (language + similarity + length)
       d. Select highest-scored book
       e. If multiple books within ambiguity threshold, fetch popularity
    3. Cache resolved editions to series.db
    4. Return dictionary: {position: book_dict} or {position: [book_dict, ...]} if ambiguous

    Args:
        raw_books: List of book dicts from hardcover_client.list_series_books()
                   Expected keys: book_id, title, subtitle, position
        series_metadata: Dict with keys:
                         - series_id: Hardcover series ID
                         - title: Series title
                         - author: Series author
                         - canonical_titles: Dict mapping position to canonical English title
        hardcover_client: HardcoverClient instance for API calls

    Returns:
        Dictionary mapping position (float) to resolved book dict or list of books.
        Single book: {1: {...}, 2: {...}}
        Ambiguous:   {1: [{...}, {...}], 2: {...}}

    Example:
        >>> series_meta = {
        ...     "series_id": 123,
        ...     "title": "Murderbot Diaries",
        ...     "author": "Martha Wells",
        ...     "canonical_titles": {1: "Murderbot Diaries 1", 2: "Murderbot Diaries 2"}
        ... }
        >>> result = await resolve_english_primary_edition(raw_books, series_meta, client)
        >>> result
        {1.0: {'book_id': 28209, 'title': 'All Systems Red', ...}, 2.0: {'book_id': 28210, ...}}
    """
    if not raw_books:
        logger.info("ℹ️  No books to resolve")
        return {}

    series_id = series_metadata.get('series_id')
    canonical_titles = series_metadata.get('canonical_titles', {})

    logger.info(f"🔍 Resolving English primary editions for series {series_id} ({len(raw_books)} books)")

    # Step 1: Group books by position
    # Use exact position values - DO NOT round fractional positions
    position_groups: Dict[float, List[Dict[str, Any]]] = {}

    for book in raw_books:
        position = book.get('position')
        if position is None:
            logger.warning(f"⚠️  Book {book.get('book_id')} missing position, skipping")
            continue

        # Ensure position is float for consistent dictionary keys
        position = float(position)

        if position not in position_groups:
            position_groups[position] = []

        position_groups[position].append(book)

    logger.info(f"📚 Grouped into {len(position_groups)} position(s)")
    logger.debug(f"   Positions: {sorted(position_groups.keys())}")

    # Step 2: Resolve each position group
    resolved_editions = {}

    for position in sorted(position_groups.keys()):
        books_at_position = position_groups[position]

        logger.info(f"\n🔍 Position {position}: {len(books_at_position)} edition(s)")

        # Log all candidates
        for idx, book in enumerate(books_at_position):
            logger.debug(f"   [{idx+1}] {book.get('title')} (ID: {book.get('book_id')})")

        # Single book - no resolution needed
        if len(books_at_position) == 1:
            resolved_editions[position] = books_at_position[0]
            logger.info(f"   ✅ Single edition, selected: {books_at_position[0].get('title')}")
            continue

        # Multiple books - need resolution using new accent-aware algorithm

        # STEP 1: Filter to Latin script only (hard reject: Chinese, Cyrillic, etc.)
        latin_candidates = [book for book in books_at_position if is_latin_script(book.get('title', ''))]

        logger.debug(f"   Step 1: Filtering to Latin script only → {len(latin_candidates)} candidates")

        if not latin_candidates:
            # No Latin script books found - select first book as fallback
            logger.warning("   ⚠️  No Latin-script books found, selecting first book")
            resolved_editions[position] = books_at_position[0]
            continue

        # STEP 2: Filter to accent-free candidates (soft reject: French, Portuguese, Spanish, etc.)
        accent_free_candidates = [book for book in latin_candidates if not has_accented_characters(book.get('title', ''))]

        logger.debug(f"   Step 2: Filtering accent-free → {len(accent_free_candidates)} candidates")

        # Fallback to all Latin candidates if no accent-free books
        if accent_free_candidates:
            candidates = accent_free_candidates
        else:
            logger.warning("   ⚠️  No accent-free candidates, falling back to all Latin-script books")
            candidates = latin_candidates

        # Single candidate after filtering - select immediately
        if len(candidates) == 1:
            selected_book = candidates[0]
            resolved_editions[position] = selected_book
            logger.info(f"   ✅ Single candidate after filtering, selected: {selected_book.get('title')}")
            continue

        # STEP 3: Fetch popularity for remaining candidates (use existing data if available)
        logger.debug(f"   Step 3: Fetching popularity for {len(candidates)} candidates...")

        # First, check if books already have users_count from list_series_books()
        for book in candidates:
            if '_users_count' not in book and 'users_count' in book:
                book['_users_count'] = book['users_count']

        # Identify candidates missing users_count data
        missing_ids = [book['book_id'] for book in candidates if '_users_count' not in book]

        if missing_ids:
            logger.debug(f"   📦 Fetching {len(missing_ids)} missing user counts via API...")
            popularity_data = await hardcover_client.get_books_by_ids(
                missing_ids,
                fields=['users_count'],
                use_cache=True
            )

            # Augment missing candidates with popularity data
            for book in candidates:
                if '_users_count' not in book:
                    book_id = book['book_id']
                    book_meta = popularity_data.get(book_id, {})
                    book['_users_count'] = book_meta.get('users_count', 0)
        else:
            logger.debug(f"   ✅ All candidates already have users_count (skipped API call)")

        # Log popularity data for all candidates
        for book in candidates:
            logger.debug(
                f"   📊 Book {book['book_id']} ('{book.get('title')[:40]}'): "
                f"users_count={book['_users_count']}"
            )

        # STEP 4: Select by highest popularity
        max_popularity = max(book.get('_users_count', 0) for book in candidates)
        popular_candidates = [book for book in candidates if book.get('_users_count', 0) == max_popularity]

        logger.debug(f"   Step 4: Selecting by popularity (max={max_popularity}) → {len(popular_candidates)} candidates")

        # Single winner by popularity
        if len(popular_candidates) == 1:
            selected_book = popular_candidates[0]
            selected_book.pop('_users_count', None)  # Clean up internal field
            resolved_editions[position] = selected_book
            logger.info(
                f"   ✅ Selected by popularity: {selected_book.get('title')} "
                f"(users_count={max_popularity})"
            )
            continue

        # STEP 5: Popularity tied - use similarity + length scoring as tiebreaker
        logger.warning(
            f"   ⚠️  Popularity tied at {max_popularity}, using similarity tiebreaker "
            f"for {len(popular_candidates)} candidates"
        )

        # Get canonical title for this position (if available)
        canonical_title = canonical_titles.get(position) or canonical_titles.get(int(position))

        if canonical_title:
            logger.debug(f"   Canonical title: '{canonical_title}'")
        else:
            logger.debug("   No canonical title provided")

        # Calculate length weights for tied group
        length_weights = calculate_length_weight(popular_candidates)

        # Score tied candidates
        scored_candidates = []
        for book in popular_candidates:
            book_id = book['book_id']
            length_weight = length_weights.get(book_id, 0.0)

            score = score_book_for_position(book, canonical_title, length_weight)

            scored_candidates.append({
                **book,  # Keep all original fields
                '_score': score,
                '_length_weight': length_weight
            })

            logger.debug(
                f"   Tiebreaker: Book {book_id} ('{book.get('title')[:40]}'): score={score:.1f}"
            )

        # Sort by score (descending)
        scored_candidates.sort(key=lambda b: b['_score'], reverse=True)

        # Select highest-scored candidate
        selected_book = scored_candidates[0]

        # Remove internal fields
        selected_book.pop('_users_count', None)
        selected_book.pop('_score', None)
        selected_book.pop('_length_weight', None)

        resolved_editions[position] = selected_book
        logger.info(
            f"   ✅ Selected via tiebreaker: {selected_book.get('title')} "
            f"(ID: {selected_book.get('book_id')}, score: {scored_candidates[0]['_score']:.1f})"
        )

    # Step 3: Cache resolved editions to series.db
    try:
        engine = get_series_engine()

        with engine.begin() as conn:
            # Update or insert series metadata
            conn.execute(
                text("""
                    INSERT OR REPLACE INTO series_metadata
                    (series_id, title, author, canonical_titles, updated_at)
                    VALUES (:series_id, :title, :author, :canonical_titles, datetime('now'))
                """),
                {
                    "series_id": series_id,
                    "title": series_metadata.get('title'),
                    "author": series_metadata.get('author'),
                    "canonical_titles": str(canonical_titles)  # JSON stored as string
                }
            )

            # Cache resolved editions
            for position, book_or_books in resolved_editions.items():
                books_to_cache = book_or_books if isinstance(book_or_books, list) else [book_or_books]

                for book in books_to_cache:
                    is_ambiguous = isinstance(book_or_books, list)

                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO resolved_editions
                            (series_id, position, book_id, resolution_score, is_ambiguous, resolved_at)
                            VALUES (:series_id, :position, :book_id, :score, :is_ambiguous, datetime('now'))
                        """),
                        {
                            "series_id": series_id,
                            "position": position,
                            "book_id": book['book_id'],
                            "score": book.get('_score'),  # May be None if already removed
                            "is_ambiguous": int(is_ambiguous)
                        }
                    )

        logger.info(f"💾 Cached {len(resolved_editions)} resolved edition(s) to series.db")

    except Exception as e:
        logger.warning(f"⚠️  Failed to cache resolved editions: {e}")
        # Don't fail the entire operation if caching fails

    logger.info(f"\n✅ Resolution complete: {len(resolved_editions)} position(s) resolved")

    return resolved_editions
