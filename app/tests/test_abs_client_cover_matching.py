"""Tests for secure ABS cover fetching behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from abs.client import AbsClient
from abs.config import AbsConfig
from abs.matching import MatchResult
from abs.models import LibraryItem


class _FakeCache:
    def __init__(self, item, result):
        self.item = item
        self.result = result

    async def ensure_fresh(self, _fetch_func):
        return None

    def find_best_match(self, *_args, **_kwargs):
        return self.item, self.result


@pytest.fixture
def abs_client(monkeypatch):
    client = AbsClient(AbsConfig(base_url="http://abs.test"), user_token="token")
    client._shared_client = Mock()
    client._shared_client.get = AsyncMock(return_value=Mock(status_code=200, json=lambda: {"results": []}))
    client._semaphore = asyncio.Semaphore(1)

    cover_service = Mock()
    cover_service.get_cached_cover.return_value = {}
    cover_service.get_cover_record.return_value = {}
    cover_service.save_cover_to_cache = AsyncMock()
    monkeypatch.setattr("abs.client._get_cover_service", lambda: cover_service)

    return client, cover_service


@pytest.mark.asyncio
async def test_fetch_cover_uses_first_search_cover_result(abs_client):
    client, cover_service = abs_client
    client._shared_client.get = AsyncMock(return_value=Mock(status_code=200, json=lambda: {
        "results": [
            {"cover": "https://example.com/first.jpg"},
            {"cover": "https://example.com/second.jpg"},
        ]
    }))
    cover_service.get_cached_cover.side_effect = [{}, {"cover_url": "/covers/94481.jpg", "item_id": None, "is_local": True}]

    result = await client.fetch_cover("Red Mist", "Patricia Cornwell", "94481", library_ids=["lib-1"])

    assert result.cover_url == "/covers/94481.jpg"
    cover_service.save_cover_to_cache.assert_awaited_once_with(
        "94481",
        "https://example.com/first.jpg",
        "Red Mist",
        "Patricia Cornwell",
        auth_headers={"Authorization": "Bearer token"},
    )


@pytest.mark.asyncio
async def test_fetch_cover_heals_stale_cached_cover_before_new_lookup(abs_client):
    client, cover_service = abs_client
    cover_service.get_cached_cover.side_effect = [
        {"item_id": "item-1", "needs_heal": True, "source_cover_url": "http://abs.test/api/items/item-1/cover"},
        {"cover_url": "/covers/94481.jpg", "item_id": "item-1", "is_local": True},
    ]
    cover_service.get_cover_record.return_value = {
        "cover_url": "http://abs.test/api/items/item-1/cover",
        "item_id": "item-1",
        "title": "Red Mist",
        "author": "Patricia Cornwell",
        "local_file": None,
        "description": None,
        "metadata": None,
    }

    result = await client.fetch_cover("Red Mist", "Patricia Cornwell", "94481", library_ids=["lib-1"])

    assert result.cover_url == "/covers/94481.jpg"
    cover_service.save_cover_to_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_cover_uses_legacy_best_match_fallback(abs_client, monkeypatch):
    client, cover_service = abs_client
    match = LibraryItem(
        id="item-strong",
        library_id="lib-1",
        title="Red Mist",
        author="Patricia Cornwell",
        cover_path="/api/items/item-strong/cover",
    )
    result = MatchResult(confidence=40.0, method="NO_MATCH", title_score=20.0, author_score=20.0)
    cover_service.get_cached_cover.side_effect = [{}, {"cover_url": "/covers/94481.jpg", "item_id": "item-strong", "is_local": True}]

    monkeypatch.setattr(client, "_get_library_cache", lambda _lib_id: _FakeCache(match, result))

    response = await client.fetch_cover("Red Mist", "Patricia Cornwell", "94481", library_ids=["lib-1"])

    assert response.cover_url == "/covers/94481.jpg"
    cover_service.save_cover_to_cache.assert_awaited_once_with(
        "94481",
        "http://abs.test/api/items/item-strong/cover",
        "Red Mist",
        "Patricia Cornwell",
        "item-strong",
        auth_headers={"Authorization": "Bearer token"},
    )
