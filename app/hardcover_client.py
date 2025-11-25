"""
Hardcover API client for MAM Audiobook Finder.
Handles GraphQL API communication with Hardcover for series discovery.
"""
import logging
import httpx
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import text

from config import (
    HARDCOVER_API_TOKEN,
    HARDCOVER_BASE_URL,
    HARDCOVER_CACHE_TTL,
    HARDCOVER_RATE_LIMIT
)
from db.db import get_db_engine

logger = logging.getLogger("mam-audiofinder")


class HardcoverRateLimiter:
    """Rate limiter for Hardcover API (60 requests per minute)."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.requests: List[datetime] = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to stay within rate limit."""
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)

            # Remove requests older than 1 minute
            self.requests = [ts for ts in self.requests if ts > cutoff]

            if len(self.requests) >= self.rpm:
                # Calculate sleep time
                oldest = self.requests[0]
                sleep_until = oldest + timedelta(minutes=1)
                sleep_seconds = (sleep_until - now).total_seconds()

                if sleep_seconds > 0:
                    # Add random jitter to avoid thundering herd
                    import random
                    jitter = random.uniform(0.05, 0.2)
                    await asyncio.sleep(sleep_seconds + jitter)
                    logger.info(f"⏱️  Rate limit: slept {sleep_seconds + jitter:.2f}s")

            self.requests.append(datetime.now())


class HardcoverClient:
    """Client for interacting with Hardcover GraphQL API."""

    # Shared HTTP client for connection pooling
    _shared_client: Optional[httpx.AsyncClient] = None
    _rate_limiter: Optional[HardcoverRateLimiter] = None
    # Request counting (class-level for all instances)
    _request_count: int = 0
    _cache_hit_count: int = 0

    def __init__(self):
        """Initialize Hardcover client."""
        self.base_url = HARDCOVER_BASE_URL
        self.api_token = HARDCOVER_API_TOKEN
        self.cache_ttl = HARDCOVER_CACHE_TTL

        # Initialize shared client if not already done
        if HardcoverClient._shared_client is None:
            HardcoverClient._shared_client = httpx.AsyncClient(
                timeout=25.0,  # Below API's 30s max
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
            logger.info("🔧 Initialized shared HTTP client for Hardcover requests")

        # Initialize rate limiter
        if HardcoverClient._rate_limiter is None:
            HardcoverClient._rate_limiter = HardcoverRateLimiter(HARDCOVER_RATE_LIMIT)
            logger.info(f"🔧 Initialized Hardcover rate limiter ({HARDCOVER_RATE_LIMIT} req/min)")

    @property
    def is_configured(self) -> bool:
        """Check if Hardcover API is configured."""
        return bool(self.api_token)

    @classmethod
    def get_request_count(cls) -> int:
        """Get total number of API requests made."""
        return cls._request_count

    @classmethod
    def get_cache_hit_count(cls) -> int:
        """Get total number of cache hits."""
        return cls._cache_hit_count

    @classmethod
    def reset_counters(cls):
        """Reset request and cache counters (useful for testing)."""
        cls._request_count = 0
        cls._cache_hit_count = 0
        logger.info("🔄 Reset Hardcover API counters")

    async def _execute_graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a GraphQL query with rate limiting and retry logic.

        Args:
            query: GraphQL query string
            variables: Query variables
            max_retries: Maximum number of retries on failure

        Returns:
            GraphQL response data or None on failure
        """
        if not self.is_configured:
            logger.warning("⚠️  Hardcover API not configured (missing HARDCOVER_API_TOKEN)")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # Acquire rate limit token
                await self._rate_limiter.acquire()

                # Increment request counter
                HardcoverClient._request_count += 1

                # Execute request
                response = await self._shared_client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )

                # Log response for debugging (only in non-200 cases or at debug level)
                if response.status_code != 200:
                    logger.debug(f"🔍 Response status: {response.status_code}")
                    logger.debug(f"🔍 Response headers: {dict(response.headers)}")
                    logger.debug(f"🔍 Response body: {response.text[:500]}")

                # Handle rate limiting (429)
                if response.status_code == 429:
                    # Exponential backoff: 2s, 4s, 8s
                    import random
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"⏱️  Rate limited (429), backing off {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    continue

                # Handle other HTTP errors
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.error(f"❌ Hardcover API error: {last_error}")

                    # Retry on 5xx errors
                    if response.status_code >= 500 and attempt < max_retries:
                        import random
                        backoff = (2 ** attempt) + random.uniform(0, 1)
                        logger.info(f"🔄 Retrying after {backoff:.1f}s...")
                        await asyncio.sleep(backoff)
                        continue
                    return None

                # Parse response
                data = response.json()

                # Check for GraphQL errors
                if "errors" in data:
                    logger.error(f"❌ GraphQL errors: {data['errors']}")
                    return None

                # Log successful response structure at debug level
                result_data = data.get("data")
                if result_data:
                    logger.debug(f"✅ GraphQL response keys: {list(result_data.keys())}")

                return result_data

            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning(f"⏱️  Hardcover request timeout (attempt {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    import random
                    await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.error(f"❌ Hardcover request failed: {last_error}")
                if attempt < max_retries:
                    import random
                    await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue

        logger.error(f"❌ All {max_retries + 1} attempts failed: {last_error}")
        return None

    def _get_cache_key(self, cache_type: str, identifier: str) -> str:
        """Generate cache key for a query."""
        # Hash identifier for consistent key length
        hash_value = hashlib.md5(identifier.encode()).hexdigest()[:12]
        return f"{cache_type}:{hash_value}"

    async def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached data if not expired."""
        try:
            engine = get_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT response_data, expires_at, hit_count
                        FROM series_cache
                        WHERE cache_key = :key
                        AND datetime(expires_at) > datetime('now')
                    """),
                    {"key": cache_key}
                ).fetchone()

                if result:
                    # Update hit count
                    conn.execute(
                        text("UPDATE series_cache SET hit_count = hit_count + 1 WHERE cache_key = :key"),
                        {"key": cache_key}
                    )
                    conn.commit()

                    # Increment class-level cache hit counter
                    HardcoverClient._cache_hit_count += 1

                    logger.info(f"✅ Cache HIT for {cache_key} (hits: {result[2] + 1})")
                    return json.loads(result[0])

                logger.info(f"❌ Cache MISS for {cache_key}")
                return None

        except Exception as e:
            logger.error(f"❌ Cache retrieval error: {e}")
            return None

    async def _set_cache(
        self,
        cache_key: str,
        cache_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store data in cache with TTL."""
        try:
            engine = get_db_engine()
            expires_at = datetime.now() + timedelta(seconds=self.cache_ttl)

            with engine.connect() as conn:
                # Build metadata fields
                meta_fields = metadata or {}

                conn.execute(
                    text("""
                        INSERT OR REPLACE INTO series_cache
                        (cache_key, cache_type, response_data, expires_at,
                         query_title, query_author, query_normalized,
                         series_id, series_name, series_author)
                        VALUES
                        (:key, :type, :data, :expires,
                         :title, :author, :normalized,
                         :series_id, :series_name, :series_author)
                    """),
                    {
                        "key": cache_key,
                        "type": cache_type,
                        "data": json.dumps(data),
                        "expires": expires_at.isoformat(),
                        "title": meta_fields.get("title"),
                        "author": meta_fields.get("author"),
                        "normalized": meta_fields.get("normalized"),
                        "series_id": meta_fields.get("series_id"),
                        "series_name": meta_fields.get("series_name"),
                        "series_author": meta_fields.get("series_author"),
                    }
                )
                conn.commit()

                logger.info(f"💾 Cached {cache_key} (TTL: {self.cache_ttl}s)")

        except Exception as e:
            logger.error(f"❌ Cache storage error: {e}")

    async def search_series(
        self,
        title: str,
        author: str = "",
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for series by title and/or author.

        Args:
            title: Series name to search for
            author: Author name (optional)
            limit: Maximum number of results (default: 10)

        Returns:
            List of series dictionaries with keys:
            - series_id: Hardcover series ID
            - series_name: Series name
            - author_name: Primary author
            - book_count: Number of books
            - readers_count: Total readers
            - books: List of book titles (strings, up to 5 books from search results)
            Returns None if API call fails, empty list [] if no results found.
        """
        if not self.is_configured:
            return None

        # Generate cache key
        cache_key = self._get_cache_key("search", f"{title}|{author}|limit{limit}")

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached.get("series", [])

        # Build GraphQL query using Hardcover's search function
        query = """
        query SearchSeries($query: String!, $queryType: String!, $perPage: Int!) {
          search(query: $query, query_type: $queryType, per_page: $perPage) {
            results
          }
        }
        """

        variables = {
            "query": title,
            "queryType": "Series",
            "perPage": limit
        }

        logger.info(f"🔍 Searching Hardcover for series: '{title}' (author: '{author}', limit: {limit})")

        # Execute query
        data = await self._execute_graphql(query, variables)

        if data is None:
            # API call failed
            return None

        if "search" not in data:
            logger.warning(f"⚠️  No search results in response for '{title}'")
            return []

        search_data = data["search"]

        # Log the search response structure for debugging
        logger.debug(f"🔍 Search response keys: {list(search_data.keys())}")

        # According to API docs, response structure is:
        # { "search": { "results": { "found": N, "hits": [...] } } }
        results = search_data.get("results")

        if results is None:
            logger.warning(f"⚠️  No results field in search response for '{title}'")
            return []

        # Handle string response (legacy/unexpected format)
        if isinstance(results, str):
            import json
            try:
                results = json.loads(results)
                logger.debug("📝 Parsed results from JSON string (legacy format)")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse results JSON: {e}")
                return []

        # Expected format: results is a dict with 'found' and 'hits' keys
        if isinstance(results, dict):
            found_count = results.get("found", 0)
            hits = results.get("hits", [])

            logger.debug(f"🔍 Results structure: found={found_count}, hits={len(hits)}")

            if not hits:
                logger.info(f"ℹ️  No series found matching '{title}' (found={found_count})")
                return []

            # Process hits array
            series_list = []
            for idx, hit in enumerate(hits):
                # Each hit has a 'document' field containing the actual data
                doc = hit.get("document", {})

                # Log first item structure for debugging
                if idx == 0:
                    logger.debug(f"🔍 First hit keys: {list(hit.keys())}")
                    logger.debug(f"🔍 First document keys: {list(doc.keys()) if isinstance(doc, dict) else 'Not a dict'}")

                # Extract series fields including books array
                books = doc.get("books", [])
                # Ensure books is a list (may be strings or empty)
                if not isinstance(books, list):
                    books = []

                series_list.append({
                    "series_id": doc.get("id"),
                    "series_name": doc.get("name", ""),
                    "author_name": doc.get("author_name", ""),
                    "book_count": doc.get("primary_books_count", doc.get("books_count", doc.get("book_count", 0))),
                    "readers_count": doc.get("readers_count", 0),
                    "books": books  # Array of book title strings (up to 5)
                })

        # Fallback: if results is already a list (old/unexpected format)
        elif isinstance(results, list):
            logger.debug(f"🔍 Results is a list (unexpected format), processing {len(results)} items")

            if len(results) == 0:
                logger.info(f"ℹ️  No series found matching '{title}'")
                return []

            series_list = []
            for idx, item in enumerate(results):
                # Typesense may wrap the actual document in a 'document' field
                doc = item.get("document", item) if isinstance(item, dict) else item

                # Log first item structure for debugging
                if idx == 0:
                    logger.debug(f"🔍 First result keys: {list(doc.keys()) if isinstance(doc, dict) else 'Not a dict'}")

                # Extract fields with defensive fallbacks including books array
                books = doc.get("books", [])
                if not isinstance(books, list):
                    books = []

                series_list.append({
                    "series_id": doc.get("id"),
                    "series_name": doc.get("name", ""),
                    "author_name": doc.get("author_name", ""),
                    "book_count": doc.get("primary_books_count", doc.get("books_count", doc.get("book_count", 0))),
                    "readers_count": doc.get("readers_count", 0),
                    "books": books  # Array of book title strings (up to 5)
                })

        else:
            logger.error(f"❌ Unexpected results type: {type(results)}")
            return []

        logger.info(f"✅ Found {len(series_list)} series matches")

        # Cache results
        await self._set_cache(
            cache_key,
            "search",
            {"series": series_list},
            {"title": title, "author": author, "normalized": title.lower()}
        )

        return series_list

    def _normalize_title(self, title: str, debug: bool = False) -> str:
        """
        Normalize title for deduplication by removing articles, punctuation, and whitespace.

        Args:
            title: Book title to normalize
            debug: If True, log normalization steps

        Returns:
            Normalized title string (lowercase, no articles/punctuation/series markers)
        """
        import re
        original = title

        # Convert to lowercase
        normalized = title.lower()

        # Remove qualifiers in parentheses/brackets (Illustrated, Unabridged, etc.)
        # Do this BEFORE punctuation removal to catch the parentheses
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)

        # Remove trailing articles: ", the", ", a", ", an"
        normalized = re.sub(r',\s*(the|a|an)\s*$', '', normalized)

        # Remove only edition markers (not volume/book/part numbers which distinguish separate volumes)
        # Keep volume numbers for graphic novels and multi-volume works (Vol. 1, Vol. 2, etc.)
        normalized = re.sub(r'\b(edition|ed)\.?\s*\d+\b', '', normalized)

        # Remove leading articles (the, a, an)
        normalized = re.sub(r'^(the|a|an)\s+', '', normalized)

        # Remove ALL internal articles (with spaces around them)
        normalized = re.sub(r'\s+(the|a|an)\s+', ' ', normalized)

        # Remove punctuation (colons, dashes, apostrophes, quotes, etc.)
        # Keep only alphanumeric and spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Normalize whitespace (multiple spaces to single space)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        if debug:
            logger.debug(f"🔍 Title normalization: '{original}' → '{normalized}'")

        return normalized

    def _deduplicate_books(self, books: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """
        Deduplicate books by normalized title, keeping the one with lowest position.

        Args:
            books: List of book dictionaries with 'title' and 'position' keys
            debug: If True, log detailed deduplication process

        Returns:
            Deduplicated list of books
        """
        if not books:
            return books

        if debug:
            logger.debug(f"📚 Deduplication starting with {len(books)} books")

        # Group by normalized title
        title_groups = {}
        for book in books:
            title = book.get("title", "")
            normalized = self._normalize_title(title, debug=debug)

            if normalized not in title_groups:
                title_groups[normalized] = []
            title_groups[normalized].append(book)

        if debug:
            logger.debug(f"📚 Grouped into {len(title_groups)} unique normalized titles")
            for normalized_title, book_list in title_groups.items():
                if len(book_list) > 1:
                    logger.debug(f"   Duplicates found for '{normalized_title}':")
                    for book in book_list:
                        logger.debug(f"      - '{book.get('title')}' (ID: {book.get('id', book.get('book_id'))}, Position: {book.get('position')})")

        # Keep book with lowest position for each title
        deduplicated = []
        for normalized_title, book_list in title_groups.items():
            # Sort by position (handle None values)
            sorted_books = sorted(
                book_list,
                key=lambda b: (b.get("position") is None, b.get("position", float('inf')))
            )
            kept_book = sorted_books[0]
            deduplicated.append(kept_book)

            if debug and len(book_list) > 1:
                logger.debug(f"   ✓ Kept '{kept_book.get('title')}' (Position: {kept_book.get('position')})")

        # Sort final list by position
        deduplicated.sort(key=lambda b: (b.get("position") is None, b.get("position", float('inf'))))

        logger.debug(f"📚 Deduplication: {len(books)} books → {len(deduplicated)} unique books")

        return deduplicated

    async def list_series_books(
        self,
        series_id: int,
        include_featured: bool = False,
        deduplicate: bool = True,
        debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        List books in a series using GraphQL book_series relationship.

        Uses the Hardcover GraphQL API to fetch complete book details with ordering.
        Filters for non-canonical books (canonical_id is null).

        Args:
            series_id: Hardcover series ID
            include_featured: DEPRECATED - Parameter ignored (Hardcover API does not support featured filter)
            deduplicate: If True, remove duplicate books by normalized title (default: True)
            debug: If True, log detailed book information (default: False)

        Returns:
            Dictionary with keys:
            - series_id: Hardcover series ID
            - series_name: Series name
            - author_name: Primary author
            - books_count: Total number of books in series
            - books: List of book dictionaries with:
                - book_id: Hardcover book ID
                - title: Book title
                - subtitle: Book subtitle (may be None)
                - position: Position in series (float or int)
            Returns None if series not found or API fails.
        """
        if not self.is_configured:
            return None

        # Log deprecation warning if include_featured is used
        if include_featured:
            logger.warning("⚠️  include_featured parameter is deprecated and ignored (Hardcover API does not support featured filter)")

        # Generate cache key with parameters (exclude deprecated featured param)
        cache_key = self._get_cache_key("series", f"{series_id}|dedup:{deduplicate}")

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        # Build GraphQL query (removed featured filter - API doesn't support it)
        query = """
        query GetBooksBySeries($seriesId: Int!) {
          series_by_pk(id: $seriesId) {
            id
            name
            author {
              name
            }
            books_count
            book_series(
              order_by: {position: asc}
              where: {
                book: {
                  canonical_id: {_is_null: true}
                }
              }
            ) {
              position
              book {
                id
                title
                subtitle
                users_count
              }
            }
          }
        }
        """

        variables = {"seriesId": series_id}

        logger.info(f"📚 Fetching series books for ID {series_id} (dedup={deduplicate})")

        data = await self._execute_graphql(query, variables)

        if not data or "series_by_pk" not in data or not data["series_by_pk"]:
            logger.warning(f"⚠️  Series {series_id} not found")
            return None

        series_data = data["series_by_pk"]
        series_name = series_data["name"]
        author_obj = series_data.get("author", {})
        author_name = author_obj.get("name", "") if author_obj else ""
        books_count = series_data.get("books_count", 0)

        logger.info(f"✅ Found series: '{series_name}' by {author_name} ({books_count} total books)")

        # Extract books from book_series relationship
        book_series = series_data.get("book_series", [])
        books = []

        for bs in book_series:
            book_data = bs.get("book", {})
            position = bs.get("position")

            books.append({
                "book_id": book_data.get("id"),
                "title": book_data.get("title", ""),
                "subtitle": book_data.get("subtitle"),
                "position": position,
                "users_count": book_data.get("users_count", 0)
            })

        logger.info(f"✅ Retrieved {len(books)} books from GraphQL")

        # Debug logging: show all books if requested
        if debug and books:
            logger.debug(f"📚 All {len(books)} books retrieved from series:")
            for idx, book in enumerate(books, 1):
                logger.debug(f"   {idx}. '{book.get('title')}' (ID: {book.get('book_id')}, Position: {book.get('position')})")
                if book.get('subtitle'):
                    logger.debug(f"      Subtitle: {book.get('subtitle')}")

        # Apply deduplication if requested
        if deduplicate and len(books) > 0:
            books = self._deduplicate_books(books, debug=debug)

        result = {
            "series_id": series_data["id"],
            "series_name": series_name,
            "author_name": author_name,
            "books_count": books_count,
            "books": books
        }

        logger.info(f"✅ Returning {len(books)} books for series '{series_name}'")

        # Cache results
        await self._set_cache(
            cache_key,
            "books",
            result,
            {
                "series_id": series_id,
                "series_name": series_name,
                "series_author": author_name
            }
        )

        return result

    async def search_books_by_author(
        self,
        author_name: str,
        limit: int = 10,
        fields: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for books by a specific author using GraphQL query.

        Args:
            author_name: Author name to search for
            limit: Maximum number of results
            fields: List of fields to retrieve (default: title, description, series_names)

        Returns:
            List of book dictionaries with requested fields, or None on failure
        """
        if not self.is_configured:
            return None

        # Generate cache key
        fields_key = ",".join(sorted(fields)) if fields else "default"
        cache_key = self._get_cache_key("books_by_author", f"{author_name}|{limit}|{fields_key}")

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached.get("books", [])

        # Default fields if not specified
        if fields is None:
            fields = ["title", "description", "series_names"]

        # Build field selection string
        field_str = "\n            ".join(fields)

        # Build GraphQL query
        query = f"""
        query BooksByAuthor($authorName: String!, $limit: Int!) {{
            books(
                where: {{
                    contributions: {{
                        author: {{
                            name: {{_eq: $authorName}}
                        }}
                    }}
                }}
                limit: $limit
                order_by: {{users_count: desc}}
            ) {{
                id
                {field_str}
            }}
        }}
        """

        variables = {
            "authorName": author_name,
            "limit": limit
        }

        logger.info(f"🔍 Searching Hardcover for books by author: '{author_name}' (limit: {limit})")

        # Execute query
        data = await self._execute_graphql(query, variables)

        if data is None:
            return None

        if "books" not in data:
            logger.warning(f"⚠️  No books field in response for author '{author_name}'")
            return []

        books = data["books"]
        logger.info(f"✅ Found {len(books)} books by {author_name}")

        # Cache results
        await self._set_cache(
            cache_key,
            "books_by_author",
            {"books": books},
            {"author": author_name, "limit": limit}
        )

        return books

    async def search_book_by_title(
        self,
        title: str,
        author: str = "",
        limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for books by title using Hardcover search API.

        Args:
            title: Book title to search for
            author: Author name for filtering (optional)
            limit: Maximum number of results (default: 5)

        Returns:
            List of book dictionaries with keys:
            - book_id: Hardcover book ID
            - title: Book title
            - authors: List of author names
            - release_year: Publication year
            - description: Book description
            - cover_url: Cover image URL
            Returns None if API call fails, empty list [] if no results found.
        """
        if not self.is_configured:
            return None

        # Generate cache key
        cache_key = self._get_cache_key("book_search", f"{title}|{author}|limit{limit}")

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached.get("books", [])

        # Build GraphQL query using Hardcover's search function
        query = """
        query SearchBooks($query: String!, $queryType: String!, $perPage: Int!) {
          search(query: $query, query_type: $queryType, per_page: $perPage) {
            results
          }
        }
        """

        variables = {
            "query": title,
            "queryType": "Book",
            "perPage": limit
        }

        logger.info(f"🔍 Searching Hardcover for book: '{title}' (author: '{author}', limit: {limit})")

        # Execute query
        data = await self._execute_graphql(query, variables)

        if data is None:
            return None

        if "search" not in data:
            logger.warning(f"⚠️  No search results in response for '{title}'")
            return []

        search_data = data["search"]
        results = search_data.get("results")

        if results is None:
            logger.warning(f"⚠️  No results field in search response for '{title}'")
            return []

        # Handle string response (parse JSON)
        if isinstance(results, str):
            try:
                results = json.loads(results)
                logger.debug("📝 Parsed results from JSON string")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse results JSON: {e}")
                return []

        # Expected format: results is a dict with 'found' and 'hits' keys
        if isinstance(results, dict):
            found_count = results.get("found", 0)
            hits = results.get("hits", [])

            logger.debug(f"🔍 Results structure: found={found_count}, hits={len(hits)}")

            if not hits:
                logger.info(f"ℹ️  No books found matching '{title}' (found={found_count})")
                return []

            # Process hits array
            books_list = []
            for idx, hit in enumerate(hits):
                doc = hit.get("document", {})

                if idx == 0:
                    logger.debug(f"🔍 First book document keys: {list(doc.keys()) if isinstance(doc, dict) else 'Not a dict'}")

                # Extract book fields
                authors_field = doc.get("authors", [])
                # authors may be a list of strings or a list of dicts
                if isinstance(authors_field, list) and len(authors_field) > 0:
                    if isinstance(authors_field[0], dict):
                        authors = [a.get("name", "") for a in authors_field]
                    else:
                        authors = authors_field
                else:
                    authors = []

                # Apply author filter if provided
                if author and authors:
                    # Check if any author matches the filter
                    if not any(author.lower() in a.lower() for a in authors):
                        continue

                books_list.append({
                    "book_id": doc.get("id"),
                    "title": doc.get("title", ""),
                    "authors": authors,
                    "release_year": doc.get("release_year"),
                    "description": doc.get("description", ""),
                    "cover_url": doc.get("image", "")
                })

        # Fallback: if results is already a list
        elif isinstance(results, list):
            logger.debug(f"🔍 Results is a list (unexpected format), processing {len(results)} items")

            if len(results) == 0:
                logger.info(f"ℹ️  No books found matching '{title}'")
                return []

            books_list = []
            for idx, item in enumerate(results):
                doc = item.get("document", item) if isinstance(item, dict) else item

                if idx == 0:
                    logger.debug(f"🔍 First result keys: {list(doc.keys()) if isinstance(doc, dict) else 'Not a dict'}")

                # Extract authors
                authors_field = doc.get("authors", [])
                if isinstance(authors_field, list) and len(authors_field) > 0:
                    if isinstance(authors_field[0], dict):
                        authors = [a.get("name", "") for a in authors_field]
                    else:
                        authors = authors_field
                else:
                    authors = []

                # Apply author filter if provided
                if author and authors:
                    if not any(author.lower() in a.lower() for a in authors):
                        continue

                books_list.append({
                    "book_id": doc.get("id"),
                    "title": doc.get("title", ""),
                    "authors": authors,
                    "release_year": doc.get("release_year"),
                    "description": doc.get("description", ""),
                    "cover_url": doc.get("image", "")
                })

        else:
            logger.error(f"❌ Unexpected results type: {type(results)}")
            return []

        logger.info(f"✅ Found {len(books_list)} book matches")

        # Cache results
        await self._set_cache(
            cache_key,
            "book_search",
            {"books": books_list},
            {"title": title, "author": author, "normalized": title.lower()}
        )

        return books_list

    async def search_book_advanced(
        self,
        title: str,
        author: str = "",
        limit: int = 5,
        fields: Optional[str] = None,
        sort: Optional[str] = None,
        weights: Optional[str] = None,
        deduplicate: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Advanced book search with extended metadata fields.

        Uses Hardcover search API with custom fields, sorting, and weighting.
        Supports deduplication based on alternative titles.

        Args:
            title: Book title to search for
            author: Author name for filtering (optional)
            limit: Maximum number of results (default: 5)
            fields: Comma-separated field list (default: includes alternative_titles, isbns, audio metadata, rating)
            sort: Sort order (default: "users_count:desc,ratings_count:desc")
            weights: Field weights for relevance (default: "5,3,2,1,1,1,1")
            deduplicate: If True, keep only most popular version of duplicate books (default: False)

        Returns:
            List of book dictionaries with keys:
            - book_id: Hardcover book ID
            - title: Book title
            - authors: List of author names
            - author_names: Alternative format of authors (list of strings)
            - alternative_titles: List of alternative titles
            - isbns: List of ISBN numbers
            - audio_seconds: Audiobook duration in seconds
            - has_audiobook: Boolean indicating audiobook availability
            - rating: Hardcover average rating (float)
            - release_year: Publication year
            - description: Book description
            - cover_url: Cover image URL
            - users_count: Number of users (for popularity ranking)
            Returns None if API call fails, empty list [] if no results found.
        """
        if not self.is_configured:
            return None

        # Set defaults for advanced search
        if fields is None:
            fields = "title,alternative_titles,author_names,isbns,audio_seconds,has_audiobook,rating,description,image,release_year,users_count"
        if sort is None:
            sort = "users_count:desc,ratings_count:desc"
        if weights is None:
            weights = "5,3,2,1,1,1,1"

        # Generate cache key
        cache_key = self._get_cache_key("book_advanced", f"{title}|{author}|{limit}|{fields[:20]}|dedup:{deduplicate}")

        # Check cache
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached.get("books", [])

        # Build GraphQL query with advanced parameters
        query = """
        query SearchBooksAdvanced($query: String!, $queryType: String!, $perPage: Int!, $fields: String!, $sort: String!, $weights: String!) {
          search(query: $query, query_type: $queryType, per_page: $perPage, fields: $fields, sort: $sort, weights: $weights) {
            results
          }
        }
        """

        variables = {
            "query": title,
            "queryType": "Book",
            "perPage": limit,
            "fields": fields,
            "sort": sort,
            "weights": weights
        }

        logger.info(f"🔍 Advanced search for book: '{title}' (author: '{author}', limit: {limit}, dedup: {deduplicate})")
        logger.debug(f"   fields: {fields}")
        logger.debug(f"   sort: {sort}, weights: {weights}")

        # Execute query
        data = await self._execute_graphql(query, variables)

        # Check if we need to fall back to basic search
        need_fallback = False
        if data is None or "search" not in data:
            need_fallback = True
            logger.warning(f"⚠️  Advanced search failed for '{title}' (no data/search field)")
        else:
            # Check if results is None (advanced params not working)
            search_data = data.get("search", {})
            if isinstance(search_data, dict):
                results_check = search_data.get("results")
                if results_check is None:
                    need_fallback = True
                    logger.warning(f"⚠️  Advanced search returned None results for '{title}'")

        # Fall back to basic search if needed
        if need_fallback:
            logger.info(f"🔄 Falling back to basic search (no advanced params)")

            # Use basic search query (no advanced params)
            basic_query = """
            query SearchBooks($query: String!, $queryType: String!, $perPage: Int!) {
              search(query: $query, query_type: $queryType, per_page: $perPage) {
                results
              }
            }
            """

            basic_variables = {
                "query": title,
                "queryType": "Book",
                "perPage": limit
            }

            logger.debug(f"🔄 Executing basic search query")
            data = await self._execute_graphql(basic_query, basic_variables)

            if data is None:
                logger.error(f"❌ Basic search also failed for '{title}'")
                return None

        # Debug: log raw response structure
        logger.debug(f"🔍 Raw GraphQL response keys: {list(data.keys())}")

        if "search" not in data:
            logger.warning(f"⚠️  No 'search' field in response for '{title}'")
            logger.debug(f"   Available fields: {list(data.keys())}")
            return []

        search_data = data["search"]
        logger.debug(f"🔍 Search data type: {type(search_data)}")
        if isinstance(search_data, dict):
            logger.debug(f"   Search data keys: {list(search_data.keys())}")

        results = search_data.get("results") if isinstance(search_data, dict) else None

        if results is None:
            logger.warning(f"⚠️  No 'results' field in search response for '{title}'")
            logger.debug(f"   Search data content: {str(search_data)[:500]}")
            return []

        # Handle string response (parse JSON)
        if isinstance(results, str):
            try:
                results = json.loads(results)
                logger.debug("📝 Parsed results from JSON string")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse results JSON: {e}")
                return []

        # Expected format: results is a dict with 'found' and 'hits' keys
        books_list = []

        if isinstance(results, dict):
            found_count = results.get("found", 0)
            hits = results.get("hits", [])

            logger.debug(f"🔍 Results structure: found={found_count}, hits={len(hits)}")

            if not hits:
                logger.info(f"ℹ️  No books found matching '{title}' (found={found_count})")
                return []

            # Process hits array
            for idx, hit in enumerate(hits):
                doc = hit.get("document", {})

                if idx == 0:
                    logger.debug(f"🔍 First book document keys: {list(doc.keys()) if isinstance(doc, dict) else 'Not a dict'}")

                # Extract extended fields
                authors_field = doc.get("authors", [])
                author_names = doc.get("author_names", [])
                alternative_titles = doc.get("alternative_titles", [])
                isbns = doc.get("isbns", [])

                # Handle various author formats
                if isinstance(authors_field, list) and len(authors_field) > 0:
                    if isinstance(authors_field[0], dict):
                        authors = [a.get("name", "") for a in authors_field]
                    else:
                        authors = authors_field
                else:
                    authors = []

                # Ensure lists
                if not isinstance(alternative_titles, list):
                    alternative_titles = []
                if not isinstance(isbns, list):
                    isbns = []
                if not isinstance(author_names, list):
                    author_names = authors if not author_names else [author_names]

                # Apply author filter if provided
                if author:
                    author_match = False
                    for a in (authors + author_names):
                        if author.lower() in str(a).lower():
                            author_match = True
                            break
                    if not author_match:
                        continue

                books_list.append({
                    "book_id": doc.get("id"),
                    "title": doc.get("title", ""),
                    "authors": authors,
                    "author_names": author_names,
                    "alternative_titles": alternative_titles,
                    "isbns": isbns,
                    "audio_seconds": doc.get("audio_seconds"),
                    "has_audiobook": doc.get("has_audiobook", False),
                    "rating": doc.get("rating"),
                    "release_year": doc.get("release_year"),
                    "description": doc.get("description", ""),
                    "cover_url": doc.get("image", ""),
                    "users_count": doc.get("users_count", 0)
                })

        logger.info(f"✅ Found {len(books_list)} book matches (before dedup)")

        # Apply deduplication if requested
        if deduplicate and len(books_list) > 1:
            books_list = self._deduplicate_books_by_alt_titles(books_list)
            logger.info(f"✅ After deduplication: {len(books_list)} unique books")

        # Cache results
        await self._set_cache(
            cache_key,
            "book_advanced",
            {"books": books_list},
            {"title": title, "author": author, "normalized": title.lower()}
        )

        return books_list

    def _deduplicate_books_by_alt_titles(self, books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate books using alternative titles, keeping the most popular version.

        Args:
            books: List of book dictionaries with 'alternative_titles' and 'users_count' keys

        Returns:
            Deduplicated list of books
        """
        if not books:
            return books

        # Build a set of all titles (main + alternatives) for each book
        book_title_sets = []
        for book in books:
            title_set = {self._normalize_title(book.get("title", ""))}
            for alt in book.get("alternative_titles", []):
                title_set.add(self._normalize_title(alt))
            book_title_sets.append((book, title_set))

        # Find groups of overlapping books
        used = set()
        groups = []

        for i, (book1, titles1) in enumerate(book_title_sets):
            if i in used:
                continue

            group = [book1]
            used.add(i)

            # Find all books with overlapping titles
            for j, (book2, titles2) in enumerate(book_title_sets):
                if j <= i or j in used:
                    continue
                if titles1 & titles2:  # Set intersection
                    group.append(book2)
                    used.add(j)

            groups.append(group)

        # Keep most popular book from each group
        deduplicated = []
        for group in groups:
            # Sort by users_count (descending)
            sorted_group = sorted(
                group,
                key=lambda b: b.get("users_count", 0),
                reverse=True
            )
            deduplicated.append(sorted_group[0])

        logger.debug(f"📚 Alt-title deduplication: {len(books)} books → {len(deduplicated)} unique books ({len(groups)} groups)")

        return deduplicated

    async def get_books_by_ids(
        self,
        book_ids: List[int],
        fields: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Dict[int, Dict[str, Any]]:
        """
        Fetch book metadata by IDs using books(where: {id: {_eq: ...}}) GraphQL query.

        NOTE: The Hardcover API no longer supports book_by_pk, so this method queries
        books individually using the books(where:...) endpoint. To minimize API calls:
        - Results are cached in series.db book_metadata table
        - Requests are batched in chunks of 10 with 1s delays to respect rate limits

        ⚠️ IMPORTANT: This endpoint only provides basic book fields (id, title, users_count, rating).
        The has_audiobook and audio_seconds fields are NOT available in books(where:...) queries.
        Use search_book_advanced() instead if you need audiobook metadata.

        Args:
            book_ids: List of Hardcover book IDs to fetch
            fields: List of fields to fetch (default: ['id', 'title', 'users_count', 'rating'])
                   Note: 'id' is always included automatically
                   Available fields: id, title, users_count, rating
                   NOT available: has_audiobook, audio_seconds (use search_book_advanced())
            use_cache: If True, check series.db cache first (default: True)

        Returns:
            Dictionary mapping book_id to book metadata:
            {
                123: {"book_id": 123, "title": "...", "users_count": 5000, "rating": 4.5},
                456: {"book_id": 456, "title": "...", "users_count": 3000, "rating": 4.2}
            }
            Books not found in API will be omitted from result dict.
        """
        if not self.is_configured:
            logger.warning("⚠️  Hardcover API not configured, skipping book metadata fetch")
            return {}

        if not book_ids:
            return {}

        # Set default fields if not provided
        # NOTE: has_audiobook and audio_seconds are NOT available in this endpoint
        if fields is None:
            fields = ['id', 'title', 'users_count', 'rating']

        # Ensure 'id' is always included
        if 'id' not in fields:
            fields.insert(0, 'id')

        result = {}
        uncached_ids = []

        # Check cache first (if enabled)
        if use_cache:
            from db.db import get_series_engine
            engine = get_series_engine()

            with engine.begin() as conn:
                for book_id in book_ids:
                    cached_row = conn.execute(
                        text("SELECT * FROM book_metadata WHERE book_id = :book_id"),
                        {"book_id": book_id}
                    ).fetchone()

                    if cached_row:
                        # Reconstruct dict from cached row
                        # NOTE: Cache may contain has_audiobook/audio_seconds from advanced search queries
                        # but get_books_by_ids() only returns basic fields
                        result[book_id] = {
                            "book_id": cached_row.book_id,
                            "title": cached_row.title,
                            "users_count": cached_row.users_count,
                            "rating": cached_row.rating,
                        }
                        # Include audiobook fields if present in cache (for backward compatibility)
                        if hasattr(cached_row, 'has_audiobook') and cached_row.has_audiobook is not None:
                            result[book_id]["has_audiobook"] = bool(cached_row.has_audiobook)
                        if hasattr(cached_row, 'audio_seconds') and cached_row.audio_seconds is not None:
                            result[book_id]["audio_seconds"] = cached_row.audio_seconds
                        logger.debug(f"📦 Cache hit for book_id={book_id} (users_count={cached_row.users_count})")
                        HardcoverClient._cache_hit_count += 1
                    else:
                        uncached_ids.append(book_id)
        else:
            uncached_ids = book_ids

        # Fetch uncached books from API
        if uncached_ids:
            logger.info(f"🔍 Fetching metadata for {len(uncached_ids)} book(s) via books(where:...) query (cached: {len(result)})")

            # Process books individually with rate limiting (batching in chunks of 10)
            from db.db import get_series_engine
            engine = get_series_engine()

            # Chunk processing to respect rate limits
            chunk_size = 10
            for chunk_start in range(0, len(uncached_ids), chunk_size):
                chunk = uncached_ids[chunk_start:chunk_start + chunk_size]

                for book_id in chunk:
                    # Query books by ID using where clause (book_by_pk is broken in Hardcover API)
                    # NOTE: has_audiobook and audio_seconds are NOT available in books(where:...) endpoint
                    # These fields are only available via search_book_advanced() query
                    query = """
                    query GetBookById($bookId: Int!) {
                        books(where: {id: {_eq: $bookId}}) {
                            id
                            title
                            users_count
                            rating
                        }
                    }
                    """
                    variables = {"bookId": book_id}

                    data = await self._execute_graphql(query, variables)

                    if data and "books" in data:
                        books_list = data["books"]

                        if books_list:
                            # Take first result (should be only one for exact ID match)
                            book_data = books_list[0]

                            # Extract fields (only basic fields available in this endpoint)
                            book_dict = {
                                "book_id": book_data.get("id", book_id),
                                "title": book_data.get("title", ""),
                                "users_count": book_data.get("users_count", 0),
                                "rating": book_data.get("rating"),
                            }

                            result[book_id] = book_dict

                            # Cache in series.db
                            # NOTE: We only cache basic fields from this endpoint
                            # has_audiobook/audio_seconds are only available via search_book_advanced()
                            try:
                                with engine.begin() as conn:
                                    conn.execute(
                                        text("""
                                            INSERT OR REPLACE INTO book_metadata
                                            (book_id, title, users_count, rating, fetched_at)
                                            VALUES (:book_id, :title, :users_count, :rating, datetime('now'))
                                        """),
                                        {
                                            "book_id": book_id,
                                            "title": book_dict["title"],
                                            "users_count": book_dict["users_count"],
                                            "rating": book_dict["rating"],
                                        }
                                    )
                                logger.debug(f"💾 Cached book_id={book_id} to series.db (users_count={book_dict['users_count']})")
                            except Exception as e:
                                logger.warning(f"⚠️  Failed to cache book_id={book_id}: {e}")
                        else:
                            logger.warning(f"⚠️  Book ID {book_id} not found in Hardcover API")
                    else:
                        logger.warning(f"⚠️  Failed to fetch book_id={book_id} from API")

                # Rate limiting: pause between chunks
                if chunk_start + chunk_size < len(uncached_ids):
                    await asyncio.sleep(1)

            fetched_count = len([b for b in result.values() if b['book_id'] in uncached_ids])
            logger.info(f"✅ Fetched {fetched_count}/{len(uncached_ids)} book(s) from API")

        return result

    async def get_series_by_author(
        self,
        author_name: str,
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get series by author name with comprehensive field extraction.

        This method searches for series and attempts to extract:
        - series_names
        - book_series relationships
        - description
        - list_books

        Args:
            author_name: Author name to search for
            limit: Maximum number of results

        Returns:
            List of series dictionaries with comprehensive data
        """
        if not self.is_configured:
            return None

        # Use search_series with author filter
        logger.info(f"🔍 Getting series by author: '{author_name}'")
        results = await self.search_series(title="", author=author_name, limit=limit)

        if results is None:
            return None

        # Filter results to only those matching the author
        if author_name:
            filtered = [s for s in results if author_name.lower() in s.get('author_name', '').lower()]
            logger.info(f"✅ Found {len(filtered)} series by {author_name} (from {len(results)} results)")
            return filtered

        return results



# Global instance
hardcover_client = HardcoverClient()
