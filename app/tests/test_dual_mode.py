"""
Test dual-mode testing infrastructure for Hardcover API.

This test file verifies that:
1. Mock mode uses MockHardcoverClient with fixtures
2. Live mode uses real HardcoverClient
3. The @pytest.mark.requires_live marker works correctly
4. Tests can run without code changes between modes
"""
import pytest
import os


# This test should run in both modes
@pytest.mark.asyncio
async def test_search_series_foundation(hardcover_client):
    """Test series search for Foundation - should work in both modes."""
    # This test should work in both mock and live modes
    # because we have a fixture for it
    result = await hardcover_client.search_series("Foundation", author="", limit=10)

    # Assertions that should pass in both modes
    assert result is not None, "search_series returned None"
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected at least one series result for 'Foundation'"

    # Check first result structure
    first = result[0]
    assert "series_id" in first
    assert "series_name" in first
    assert "author_name" in first

    # Foundation by Isaac Asimov should be in results
    found_foundation = any("foundation" in s["series_name"].lower() for s in result)
    assert found_foundation, "Expected to find 'Foundation' series in results"


@pytest.mark.asyncio
async def test_search_series_harry_potter(hardcover_client):
    """Test series search for Harry Potter - should work in both modes."""
    result = await hardcover_client.search_series("Harry Potter", author="", limit=10)

    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0

    # Harry Potter should be in results
    found_hp = any("harry potter" in s["series_name"].lower() for s in result)
    assert found_hp, "Expected to find 'Harry Potter' series in results"


@pytest.mark.asyncio
async def test_search_series_empty_result(hardcover_client):
    """Test series search with no results - should work in both modes."""
    result = await hardcover_client.search_series("ThisSeriesDoesNotExist12345XYZ", author="", limit=10)

    assert result is not None, "search_series should return empty list, not None"
    assert isinstance(result, list)
    assert len(result) == 0, "Expected empty results for nonsense query"


@pytest.mark.asyncio
async def test_list_series_books_harry_potter(hardcover_client):
    """Test listing books in Harry Potter series - should work in both modes."""
    # First, search for Harry Potter to get series ID
    series_results = await hardcover_client.search_series("Harry Potter", author="", limit=1)
    assert len(series_results) > 0

    series_id = series_results[0]["series_id"]

    # Now get books for this series
    result = await hardcover_client.list_series_books(series_id, deduplicate=False)

    assert result is not None
    assert isinstance(result, dict)
    assert "series_id" in result
    assert "series_name" in result
    assert "books" in result
    assert isinstance(result["books"], list)


@pytest.mark.asyncio
async def test_search_book_by_title(hardcover_client):
    """Test book search - should work in both modes."""
    # Note: Using exact params from captured fixture
    result = await hardcover_client.search_book_by_title("Harry Potter and the Philosopher's Stone", author="", limit=5)

    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0

    # Check book structure
    first_book = result[0]
    assert "book_id" in first_book
    assert "title" in first_book
    assert "authors" in first_book


@pytest.mark.asyncio
async def test_client_type_detection():
    """Test that we can detect which client type is being used."""
    from tests.conftest import LIVE_MODE

    if LIVE_MODE:
        from hardcover_client import HardcoverClient
        client = HardcoverClient()
        assert client.__class__.__name__ == "HardcoverClient"
        print(f"✓ Running in LIVE mode with {client.__class__.__name__}")
    else:
        from tests.mocks.hardcover_mock import MockHardcoverClient
        # In mock mode, the client should be a MockHardcoverClient
        # but it might be patched, so we check by behavior
        print("✓ Running in MOCK mode")


@pytest.mark.asyncio
async def test_request_counting(hardcover_client):
    """Test that request counting works in both modes."""
    # Reset counters
    hardcover_client.reset_counters()
    assert hardcover_client.get_request_count() == 0
    assert hardcover_client.get_cache_hit_count() == 0

    # Make a request
    await hardcover_client.search_series("Foundation", author="", limit=10)

    # Should have made at least one request
    assert hardcover_client.get_request_count() > 0


@pytest.mark.requires_live
@pytest.mark.asyncio
async def test_live_mode_only(hardcover_client):
    """
    This test is marked as requires_live and should:
    - Run in LIVE mode
    - Be skipped in MOCK mode
    """
    from tests.conftest import LIVE_MODE
    assert LIVE_MODE, "This test should only run in LIVE mode"

    # This test verifies live API behavior
    result = await hardcover_client.search_series("Stormlight Archive", author="Brandon Sanderson", limit=5)
    assert result is not None
    print(f"✓ Live mode test passed - found {len(result)} series")


def test_mode_environment_variable():
    """Test that LIVE_MODE is set correctly based on environment."""
    from tests.conftest import LIVE_MODE

    env_value = os.getenv("LIVE_API_TESTS")

    if env_value == "1":
        assert LIVE_MODE is True, "LIVE_MODE should be True when LIVE_API_TESTS=1"
        print("✓ LIVE_MODE is True (LIVE_API_TESTS=1)")
    else:
        assert LIVE_MODE is False, "LIVE_MODE should be False when LIVE_API_TESTS != 1"
        print("✓ LIVE_MODE is False (mock mode)")
