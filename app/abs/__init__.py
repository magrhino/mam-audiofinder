"""
ABS (Audiobookshelf) integration package.

This package provides async HTTP client, library caching, and verification
logic for Audiobookshelf API integration.
"""

from abs.client import AbsClient
from abs.config import AbsConfig
from abs.models import (
    Library,
    LibraryItem,
    VerificationResult,
    CoverResult,
    LibrarySyncStatus,
)

__all__ = [
    "AbsClient",
    "AbsConfig",
    "Library",
    "LibraryItem",
    "VerificationResult",
    "CoverResult",
    "LibrarySyncStatus",
]
