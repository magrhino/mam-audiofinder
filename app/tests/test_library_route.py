"""Tests for library API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_abs_client():
    """Mock ABS client for testing."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.config = MagicMock()
    mock_client.config.library_id = "test_library"
    mock_client.config.base_url = "http://abs.test"
    mock_client.config.api_key = "test_key"
    mock_client.get_series_list = AsyncMock(return_value=[])
    mock_client.get_books_in_series = AsyncMock(return_value=[])
    mock_client._library_cache = MagicMock()
    mock_client._library_cache.ensure_fresh = AsyncMock()

    with patch('routes.library_route.abs_client', mock_client):
        yield mock_client


@pytest.fixture
def mock_hardcover_client():
    """Mock Hardcover client for testing."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.search_series = AsyncMock(return_value=[])
    mock_client.list_series_books = AsyncMock(return_value=None)

    with patch('routes.library_route.hardcover_client', mock_client):
        yield mock_client


class TestSeriesEndpoint:
    def test_list_series_abs(self, client, mock_abs_client):
        """GET /api/library/series returns ABS series."""
        mock_abs_client.get_series_list.return_value = [
            {"id": "s1", "name": "Test Series", "books": [{"id": "b1"}]}
        ]

        response = client.get("/api/library/series?source=abs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["series"][0]["name"] == "Test Series"

    def test_series_diff(self, client, mock_abs_client, mock_hardcover_client):
        """GET /api/library/series/{name}/diff returns diff result."""
        from abs.models import LibraryItem
        from series_resolver import SeriesSource

        # Mock ABS books
        mock_abs_client.get_books_in_series.return_value = []

        # Mock Hardcover series search
        mock_hardcover_client.search_series.return_value = [
            {"series_id": 123, "series_name": "Test"}
        ]
        mock_hardcover_client.list_series_books.return_value = {
            "books": [{"book_id": 1, "title": "Book One"}]
        }

        response = client.get("/api/library/series/Test/diff")

        assert response.status_code == 200
        data = response.json()
        assert len(data["missing"]) == 1


class TestWishlistEndpoint:
    def test_add_to_wishlist(self, client):
        """POST /api/library/wishlist creates entry."""
        response = client.post("/api/library/wishlist", json={
            "title": "Test Book",
            "author": "Test Author",
            "series_name": "Test Series",
        })

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_list_wishlist(self, client):
        """GET /api/library/wishlist returns items."""
        # First add an item
        client.post("/api/library/wishlist", json={
            "title": "Test Book",
            "author": "Test Author",
        })

        # Then list
        response = client.get("/api/library/wishlist")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
