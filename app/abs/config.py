"""ABS configuration from environment variables."""

from dataclasses import dataclass
from config import (
    ABS_BASE_URL,
    ABS_VERIFY_TIMEOUT,
    ABS_LIBRARY_CACHE_TTL,
)


@dataclass
class AbsConfig:
    """Configuration for Audiobookshelf client.

    Note: api_key is no longer stored in config. User tokens are passed
    at runtime via the user_token parameter in AbsClient methods.
    Library IDs are stored in app_settings and managed dynamically.
    """

    base_url: str
    verify_timeout: int = 10
    cache_ttl: int = 300

    @property
    def is_configured(self) -> bool:
        """Check if ABS connection is configured (base URL set)."""
        return bool(self.base_url)

    @classmethod
    def from_env(cls) -> "AbsConfig":
        """Create config from environment variables."""
        return cls(
            base_url=ABS_BASE_URL,
            verify_timeout=ABS_VERIFY_TIMEOUT,
            cache_ttl=ABS_LIBRARY_CACHE_TTL,
        )
