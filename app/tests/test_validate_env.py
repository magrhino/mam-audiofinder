"""Tests for startup environment validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / 'build' / 'validate_env.py'
SPEC = importlib.util.spec_from_file_location('validate_env_module', MODULE_PATH)
assert SPEC is not None
validate_env_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_env_module)


def test_validate_env_rejects_insecure_qb_defaults(monkeypatch, capsys):
    monkeypatch.delenv('GUID', raising=False)
    monkeypatch.delenv('PUID', raising=False)
    monkeypatch.delenv('PGID', raising=False)
    monkeypatch.setenv('QB_USER', 'admin')
    monkeypatch.setenv('QB_PASS', 'adminadmin')

    with pytest.raises(SystemExit, match='1'):
        validate_env_module.validate_env()

    captured = capsys.readouterr()
    assert 'insecure default admin/adminadmin' in captured.err


def test_validate_env_accepts_explicit_qb_credentials(monkeypatch, capsys):
    monkeypatch.delenv('GUID', raising=False)
    monkeypatch.delenv('PUID', raising=False)
    monkeypatch.delenv('PGID', raising=False)
    monkeypatch.setenv('QB_USER', 'qbuser')
    monkeypatch.setenv('QB_PASS', 'secret-pass')

    validate_env_module.validate_env()

    captured = capsys.readouterr()
    assert 'validated successfully' in captured.out
