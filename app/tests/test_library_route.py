"""Tests for library API endpoints."""

import pytest
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

import dependencies.abs as abs_dependencies
import db.db as db_module


@pytest.fixture
def mock_abs_client():
    """Mock ABS client for testing."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.has_token = True
    mock_client.config = MagicMock()
    mock_client.config.base_url = "http://abs.test"
    mock_client.get_series_list = AsyncMock(return_value=[])
    mock_client.get_books_in_series = AsyncMock(return_value=[])

    # Mock inner client for cache access
    mock_inner_client = MagicMock()
    mock_inner_client._library_caches = {}
    mock_inner_client._get_library_cache = MagicMock()
    mock_client._client = mock_inner_client

    # Patch all ABS-related imports at the route level
    async def fake_get_current_user(token: str):
        return {"username": "tester", "type": "user", "isActive": True, "token": token}

    with patch('routes.library_route.get_abs_client', return_value=mock_client), \
         patch('routes.library_route.ABS_BASE_URL', 'http://abs.test'), \
         patch.object(abs_dependencies.config, 'ABS_BASE_URL', 'http://abs.test'), \
         patch.object(abs_dependencies, 'get_current_user', fake_get_current_user), \
         patch('routes.library_route.settings_service') as mock_settings:
        mock_settings.get_enabled_libraries.return_value = ['test_library']
        yield mock_client


@pytest.fixture
def abs_auth_disabled(monkeypatch):
    monkeypatch.setattr(abs_dependencies.config, 'ABS_BASE_URL', '')


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

        # Include X-ABS-Token header for authentication
        response = client.get("/api/library/series?source=abs", headers={"X-ABS-Token": "test-token"})

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
            "books": [
                {"book_id": 1, "title": "Book One", "position": 1.0}
            ]
        }

        # Include X-ABS-Token header for authentication
        response = client.get("/api/library/series/Test/diff", headers={"X-ABS-Token": "test-token"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["missing"]) == 1

    def test_list_series_treats_library_id_as_data(self, client, mock_abs_client, monkeypatch):
        """GET /api/library/series binds library_id instead of interpolating SQL."""
        mock_abs_client.get_series_list.return_value = [
            {"id": "s1", "name": "Test Series", "author": "Author One", "book_count": 1}
        ]

        covers_engine = create_engine("sqlite:///:memory:")
        with covers_engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE series_hardcover_link (
                    series_name TEXT,
                    series_name_normalized TEXT,
                    library_id TEXT,
                    hardcover_series_id INTEGER,
                    hardcover_series_name TEXT,
                    hardcover_author_name TEXT,
                    hardcover_book_count INTEGER,
                    link_confidence REAL,
                    linked_by TEXT,
                    linked_at TEXT
                )
            """))
            conn.execute(text("""
                INSERT INTO series_hardcover_link (
                    series_name, series_name_normalized, library_id,
                    hardcover_series_id, hardcover_series_name, hardcover_author_name,
                    hardcover_book_count, link_confidence, linked_by
                ) VALUES (
                    'Test Series', 'test series', 'secret-lib',
                    999, 'Secret Link', 'Author One',
                    4, 1.0, 'manual'
                )
            """))

        monkeypatch.setattr(db_module, 'covers_engine', covers_engine)
        monkeypatch.setattr(abs_dependencies.config, 'ABS_BASE_URL', 'http://abs.test')

        async def fake_get_current_user(token: str):
            return {"username": "tester", "type": "user", "isActive": True, "token": token}

        monkeypatch.setattr(abs_dependencies, 'get_current_user', fake_get_current_user)

        response = client.get(
            "/api/library/series",
            params={"library_id": "test_library') OR 1=1 --"},
            headers={"X-ABS-Token": "test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["series"][0]["hardcover_series_id"] is None


class TestWishlistEndpoint:
    def test_add_to_wishlist(self, client, abs_auth_disabled):
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

    def test_list_wishlist(self, client, abs_auth_disabled):
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
