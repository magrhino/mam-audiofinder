"""
Mock qBittorrent client functions for testing.

This module provides mock implementations of qBittorrent login functions that
always succeed without making real network calls.

Usage:
    In mock mode (LIVE_API_TESTS != "1"), these functions are automatically used
    instead of the real qb_login/qb_login_sync via monkey-patching in conftest.py.
"""
import logging
from typing import Optional

logger = logging.getLogger("mam-audiofinder")


async def mock_qb_login(client):
    """
    Mock async qBittorrent login (always succeeds in tests).

    Args:
        client: httpx.AsyncClient instance (ignored in mock, just for signature compatibility)

    Note:
        In mock mode, this function does nothing - it just succeeds silently.
        The real function would POST to /api/v2/auth/login and raise HTTPException on failure.
    """
    logger.debug(f"🔧 MOCK qb_login called (async) - success")
    # In mock mode, we don't need to do anything - just succeed silently
    pass


def mock_qb_login_sync(client):
    """
    Mock sync qBittorrent login (always succeeds in tests).

    Args:
        client: httpx.Client instance (ignored in mock, just for signature compatibility)

    Note:
        In mock mode, this function does nothing - it just succeeds silently.
        The real function would POST to /api/v2/auth/login and raise HTTPException on failure.
    """
    logger.debug(f"🔧 MOCK qb_login_sync called (sync) - success")
    # In mock mode, we don't need to do anything - just succeed silently
    pass
