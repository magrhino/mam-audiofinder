"""Security regression tests for backend auth enforcement."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import dependencies.abs as abs_dependencies


async def _fake_get_current_user(token: str):
    if token == "admin-token":
        return {"username": "admin", "type": "admin", "isActive": True, "token": token}
    if token == "user-token":
        return {"username": "member", "type": "user", "isActive": True, "token": token}
    raise HTTPException(status_code=401, detail="Invalid or expired token. Please login again.")


@pytest.fixture
def abs_auth_enabled(monkeypatch):
    monkeypatch.setattr(abs_dependencies.config, "ABS_BASE_URL", "http://abs.test")
    monkeypatch.setattr(abs_dependencies.config, "ABS_ADMIN_USER", "admin")
    monkeypatch.setattr(abs_dependencies, "get_current_user", _fake_get_current_user)


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/history", None),
        ("get", "/qb/torrents", None),
        ("get", "/api/showcase?limit=1", None),
        ("post", "/search", {}),
        ("post", "/api/covers/enrich", {"title": "Test Title"}),
        ("get", "/api/library/wishlist", None),
    ],
)
def test_sensitive_routes_require_auth_when_abs_configured(client, monkeypatch, abs_auth_enabled, method, path, payload):
    request = getattr(client, method)
    kwargs = {"json": payload} if payload is not None else {}
    response = request(path, **kwargs)
    assert response.status_code == 401


def test_settings_requires_admin_when_abs_configured(client, abs_auth_enabled):
    unauthenticated = client.get("/api/settings")
    assert unauthenticated.status_code == 401

    authenticated = client.get("/api/settings", headers={"X-ABS-Token": "user-token"})
    assert authenticated.status_code == 403

    admin = client.get("/api/settings", headers={"X-ABS-Token": "admin-token"})
    assert admin.status_code == 200


def test_logs_requires_admin_when_abs_configured(client, abs_auth_enabled):
    unauthenticated = client.get("/api/logs")
    assert unauthenticated.status_code == 401

    authenticated = client.get("/api/logs", headers={"X-ABS-Token": "user-token"})
    assert authenticated.status_code == 403

    admin = client.get("/api/logs", headers={"X-ABS-Token": "admin-token"})
    assert admin.status_code == 200


def test_admin_routes_fail_closed_without_admin_config(client, monkeypatch, abs_auth_enabled):
    monkeypatch.setattr(abs_dependencies.config, "ABS_ADMIN_USER", "")

    response = client.get("/api/settings", headers={"X-ABS-Token": "admin-token"})
    assert response.status_code == 503


def test_library_cover_rejects_query_string_token(client, abs_auth_enabled):
    response = client.get("/api/library/cover/item-1?token=admin-token")
    assert response.status_code == 401


def test_settings_and_logs_remain_open_without_abs(client, monkeypatch):
    monkeypatch.setattr(abs_dependencies.config, "ABS_BASE_URL", "")
    monkeypatch.setattr(abs_dependencies.config, "ABS_ADMIN_USER", "admin")

    settings_response = client.get("/api/settings")
    logs_response = client.get("/api/logs")

    assert settings_response.status_code == 200
    assert logs_response.status_code == 200
