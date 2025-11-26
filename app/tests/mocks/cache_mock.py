"""
Mock MAM cache for deterministic testing.

This mock implementation provides the same interface as mam_cache.py
but uses separate storage to ensure test isolation.

Usage:
    In mock mode (LIVE_API_TESTS != "1"), these functions are automatically used
    instead of the real cache functions via monkey-patching in conftest.py.
"""
import time
import hashlib
from typing import Optional, Dict, Any

# Separate cache storage for tests (not shared with real cache)
_test_cache: Dict[str, tuple[Any, float]] = {}
TEST_CACHE_TTL = 300  # 5 minutes (same as real cache)


def _get_cache_key(query: str, limit: int, sort_type: str = "default") -> str:
    """Generate cache key (same logic as real cache)."""
    cache_data = f"{query}|{limit}|{sort_type}"
    return hashlib.md5(cache_data.encode()).hexdigest()


def get_cached_mam_search(query: str, limit: int, sort_type: str = "default") -> Optional[Dict[str, Any]]:
    """
    Get cached search result (mock implementation).

    Args:
        query: Search query text
        limit: Results limit
        sort_type: Sort type (default, seeders, added, etc.)

    Returns:
        Cached result dict if found and not expired, None otherwise
    """
    cache_key = _get_cache_key(query, limit, sort_type)

    if cache_key not in _test_cache:
        return None

    result, timestamp = _test_cache[cache_key]
    age = time.time() - timestamp

    if age > TEST_CACHE_TTL:
        # Expired - remove from cache
        del _test_cache[cache_key]
        return None

    return result


def cache_mam_search(query: str, limit: int, result: Dict[str, Any], sort_type: str = "default") -> None:
    """
    Cache search result (mock implementation).

    Args:
        query: Search query text
        limit: Results limit
        result: Search result to cache
        sort_type: Sort type (default, seeders, added, etc.)
    """
    cache_key = _get_cache_key(query, limit, sort_type)
    _test_cache[cache_key] = (result, time.time())


def clear_expired_cache() -> int:
    """
    Clear expired entries (mock implementation).

    Returns:
        Number of entries cleared
    """
    now = time.time()
    to_delete = [
        key for key, (_, ts) in _test_cache.items()
        if now - ts > TEST_CACHE_TTL
    ]

    for key in to_delete:
        del _test_cache[key]

    return len(to_delete)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics (mock implementation).

    Returns:
        Dict with cache_size, oldest_entry_age, newest_entry_age
    """
    if not _test_cache:
        return {
            "cache_size": 0,
            "oldest_entry_age": 0,
            "newest_entry_age": 0
        }

    now = time.time()
    timestamps = [ts for _, ts in _test_cache.values()]

    return {
        "cache_size": len(_test_cache),
        "oldest_entry_age": int(now - min(timestamps)),
        "newest_entry_age": int(now - max(timestamps))
    }


def reset_test_cache():
    """
    Reset test cache (for test isolation).

    This is only available in the mock implementation, not in the real cache.
    Call this between tests to ensure no cache pollution.
    """
    _test_cache.clear()
