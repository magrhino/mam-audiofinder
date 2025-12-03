"""ABS configuration from environment variables."""

from dataclasses import dataclass
from config import (
    ABS_BASE_URL,
    ABS_API_KEY,
    ABS_LIBRARY_ID,
    ABS_VERIFY_TIMEOUT,
    ABS_LIBRARY_CACHE_TTL,
)


@dataclass
class AbsConfig:
    """Configuration for Audiobookshelf client."""

    base_url: str
    api_key: str
    library_id: str
    verify_timeout: int = 10
    cache_ttl: int = 300

    @property
    def is_configured(self) -> bool:
        """Check if basic ABS connection is configured."""
        return bool(self.base_url and self.api_key)

    @property
    def is_fully_configured(self) -> bool:
        """Check if ABS is fully configured including library ID."""
        return bool(self.base_url and self.api_key and self.library_id)

    @classmethod
    def from_env(cls) -> "AbsConfig":
        """Create config from environment variables."""
        return cls(
            base_url=ABS_BASE_URL,
            api_key=ABS_API_KEY,
            library_id=ABS_LIBRARY_ID,
            verify_timeout=ABS_VERIFY_TIMEOUT,
            cache_ttl=ABS_LIBRARY_CACHE_TTL,
        )
