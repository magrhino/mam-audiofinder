"""Regression tests for history verification with token auth.

These tests ensure the manual verify endpoint wires the ABS user token
through to the ABS client after the auth transition.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text

import abs_client as abs_client_module
import config
from routes import history as history_route
from utils import sanitize


@pytest.mark.asyncio
async def test_history_verify_uses_x_abs_token(monkeypatch, tmp_path: Path):
    # Arrange: in-memory history DB
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT,
                imported_at TEXT,
                abs_verify_status TEXT,
                abs_verify_note TEXT
            )
        """))
        conn.execute(
            text("INSERT INTO history (id, title, author, imported_at) VALUES (:id, :title, :author, :imported_at)"),
            {
                "id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "imported_at": "2025-01-01 00:00:00",
            },
        )

    # Arrange: mock library directory with metadata.json
    lib_root = tmp_path / "library"
    import_dir = lib_root / sanitize("Test Author") / sanitize("Test Book")
    import_dir.mkdir(parents=True)
    (import_dir / "metadata.json").write_text(json.dumps({"title": "Test Book", "authors": ["Test Author"]}))

    monkeypatch.setattr(config, "LIB_DIR", str(lib_root))
    monkeypatch.setattr(history_route, "engine", engine)

    captured: dict[str, str | None] = {"token": None}

    class SpyAbsClient:
        verify_import = AsyncMock(return_value={"status": "verified", "note": "ok", "abs_item_id": "abs-1"})

    spy_client = SpyAbsClient()

    def fake_get_abs_client(user_token=None):
        captured["token"] = user_token
        return spy_client

    monkeypatch.setattr(abs_client_module, "get_abs_client", fake_get_abs_client)

    # Act
    result = await history_route.verify_history_item(row_id=1, x_abs_token="token-123")

    # Assert: token propagated + DB updated
    assert result["ok"] is True
    assert captured["token"] == "token-123"
    spy_client.verify_import.assert_awaited()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT abs_verify_status, abs_verify_note FROM history WHERE id = 1")
        ).fetchone()
        assert row[0] == "verified"
        assert row[1] == "ok"
