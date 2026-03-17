"""Tests for token-aware cover metadata routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import dependencies.abs as abs_dependencies
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


def test_covers_enrich_uses_token_scoped_abs_client(client, monkeypatch):
    captured = {}

    async def fake_get_current_user(token: str):
        return {"username": "tester", "type": "user", "isActive": True, "token": token}

    provider_client = Mock()
    provider_client._fetch_from_provider = AsyncMock(return_value={
        "title": "Fourth Wing",
        "author": "Rebecca Yarros",
        "description": "Dragon riders."
    })

    def fake_get_abs_client(user_token=None):
        captured["token"] = user_token
        return provider_client

    monkeypatch.setattr(abs_dependencies.config, "ABS_BASE_URL", "http://abs.test")
    monkeypatch.setattr(abs_dependencies.config, "ABS_ADMIN_USER", "admin")
    monkeypatch.setattr(abs_dependencies, "get_current_user", fake_get_current_user)
    monkeypatch.setattr("routes.covers_route.get_abs_client", fake_get_abs_client)

    response = client.post(
        "/api/covers/enrich",
        json={"title": "Fourth Wing", "author": "Rebecca Yarros"},
        headers={"X-ABS-Token": "user-token"},
    )

    assert response.status_code == 200
    assert captured["token"] == "user-token"
    assert response.json()["description"] == "Dragon riders."


def test_refresh_cover_uses_token_scoped_abs_client(client, monkeypatch):
    captured = {}

    async def fake_get_current_user(token: str):
        return {"username": "tester", "type": "user", "isActive": True, "token": token}

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY,
                mam_id TEXT,
                title TEXT,
                author TEXT
            )
        """))
        conn.execute(text(
            "INSERT INTO history (mam_id, title, author) VALUES ('12345', 'Fourth Wing', 'Rebecca Yarros')"
        ))

    refresh_client = Mock()
    refresh_client.fetch_cover = AsyncMock(return_value={"cover_url": "/covers/12345.webp", "item_id": "item-1"})

    def fake_get_abs_client(user_token=None):
        captured["token"] = user_token
        return refresh_client

    monkeypatch.setattr(abs_dependencies.config, "ABS_BASE_URL", "http://abs.test")
    monkeypatch.setattr(abs_dependencies.config, "ABS_ADMIN_USER", "admin")
    monkeypatch.setattr(abs_dependencies, "get_current_user", fake_get_current_user)
    monkeypatch.setattr("routes.covers_route.get_abs_client", fake_get_abs_client)
    monkeypatch.setattr("routes.covers_route.engine", engine)
    monkeypatch.setattr("routes.covers_route.get_cover_service", lambda: Mock(invalidate_cover=Mock(return_value=True)))

    response = client.post(
        "/covers/refresh/12345",
        headers={"X-ABS-Token": "user-token"},
    )

    assert response.status_code == 200
    assert captured["token"] == "user-token"
    refresh_client.fetch_cover.assert_awaited_once()
