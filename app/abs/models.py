"""Pydantic models for ABS API responses."""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class LibraryItem(BaseModel):
    """ABS library item with flattened metadata."""

    id: str
    library_id: str
    title: str
    author: Optional[str] = None
    narrator: Optional[str] = None
    series_name: Optional[str] = None
    series_index: Optional[float] = None
    asin: Optional[str] = None
    isbn: Optional[str] = None
    cover_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    path: Optional[str] = None
    title_normalized: Optional[str] = None
    author_normalized: Optional[str] = None


class VerificationResult(BaseModel):
    """Import verification result."""

    status: Literal["verified", "mismatch", "not_found", "unreachable", "not_configured"]
    note: str
    abs_item_id: Optional[str] = None
    matched_title: Optional[str] = None
    score: int = 0


class CoverResult(BaseModel):
    """Cover fetch result."""

    cover_url: Optional[str] = None
    item_id: Optional[str] = None
    is_local: bool = False
    needs_heal: bool = False
    description: Optional[str] = None
    metadata: Optional[dict] = None


class LibrarySyncStatus(BaseModel):
    """Library sync status."""

    library_id: str
    last_full_sync: Optional[str] = None
    last_item_count: int = 0
    sync_in_progress: bool = False
    cache_age_seconds: float = 0
