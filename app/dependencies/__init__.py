"""
FastAPI dependencies for shared logic across routes.

This module provides reusable dependencies for:
- qBittorrent session management and torrent operations
- MAM search client and response normalization
- ABS verification, config guards, and library checks
- Database session providers
"""

from .qb import (
    get_qb_sync_client,
    get_qb_async_client,
    require_torrent_info,
    map_qb_content_path,
)
from .mam import (
    flatten,
    detect_format,
    mam_search_client,
    normalize_mam_result,
)
from .abs import (
    require_abs_config,
    abs_library_check,
    abs_import_verifier,
    load_metadata_with_retry,
    ensure_library_destination,
)
from .db import (
    db_session,
    covers_db_session,
)

__all__ = [
    # qBittorrent
    "get_qb_sync_client",
    "get_qb_async_client",
    "require_torrent_info",
    "map_qb_content_path",
    # MAM
    "flatten",
    "detect_format",
    "mam_search_client",
    "normalize_mam_result",
    # ABS
    "require_abs_config",
    "abs_library_check",
    "abs_import_verifier",
    "load_metadata_with_retry",
    "ensure_library_destination",
    # DB
    "db_session",
    "covers_db_session",
]
