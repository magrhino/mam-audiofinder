"""
Settings service for MAM Audiobook Finder.
Manages runtime-configurable application settings with database persistence.
"""
import json
import logging
from typing import Any, List
from sqlalchemy import text

from db import engine
from config import AUTO_IMPORT_ENABLED, AUTO_IMPORT_POLL_INTERVAL, AUTO_IMPORT_FLATTEN, COVER_SOURCE_PRIORITY

logger = logging.getLogger("mam-audiofinder")


# Default settings (used if not set in database)
DEFAULT_SETTINGS = {
    "auto_import_enabled": str(AUTO_IMPORT_ENABLED).lower(),
    "auto_import_flatten": str(AUTO_IMPORT_FLATTEN).lower(),
    "auto_import_poll_interval": str(AUTO_IMPORT_POLL_INTERVAL),
    "cover_source_priority": COVER_SOURCE_PRIORITY,  # "shelfarr" or "torrent"
}

# Settings type definitions for proper casting
SETTINGS_TYPES = {
    "auto_import_enabled": bool,
    "auto_import_flatten": bool,
    "auto_import_poll_interval": int,
    "cover_source_priority": str,  # "shelfarr" or "torrent"
}


def _cast_value(key: str, value: str) -> Any:
    """Cast a string value to its proper type based on key."""
    if key not in SETTINGS_TYPES:
        return value

    target_type = SETTINGS_TYPES[key]
    if target_type == bool:
        return value.lower() in ("true", "1", "yes")
    elif target_type == int:
        try:
            return int(value)
        except ValueError:
            return int(DEFAULT_SETTINGS.get(key, "0"))
    return value


def _serialize_value(value: Any) -> str:
    """Serialize a value to string for storage."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class SettingsService:
    """
    Manages application settings with database persistence.

    Settings are stored in the app_settings table in history.db.
    Environment variables provide defaults that can be overridden at runtime.
    """

    def get_all(self) -> dict[str, Any]:
        """
        Get all application settings with proper type casting.

        Returns:
            dict: All settings with their current values
        """
        settings = dict(DEFAULT_SETTINGS)

        try:
            with engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT key, value FROM app_settings")
                ).fetchall()

                for row in rows:
                    settings[row[0]] = row[1]

        except Exception as e:
            logger.warning(f"Failed to read settings from database: {e}")

        # Cast values to proper types
        return {key: _cast_value(key, value) for key, value in settings.items()}

    def get(self, key: str) -> Any:
        """
        Get a single setting value.

        Args:
            key: The setting key

        Returns:
            The setting value (properly typed) or None if not found
        """
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT value FROM app_settings WHERE key = :key"),
                    {"key": key}
                ).fetchone()

                if row:
                    return _cast_value(key, row[0])

        except Exception as e:
            logger.warning(f"Failed to read setting '{key}' from database: {e}")

        # Fall back to default
        if key in DEFAULT_SETTINGS:
            return _cast_value(key, DEFAULT_SETTINGS[key])

        return None

    def set(self, key: str, value: Any) -> bool:
        """
        Set a single setting value.

        Args:
            key: The setting key
            value: The value to set

        Returns:
            True if successful, False otherwise
        """
        serialized = _serialize_value(value)

        try:
            with engine.begin() as conn:
                # Use INSERT OR REPLACE (upsert)
                conn.execute(
                    text("""
                        INSERT INTO app_settings (key, value, updated_at)
                        VALUES (:key, :value, datetime('now'))
                        ON CONFLICT(key) DO UPDATE SET
                            value = excluded.value,
                            updated_at = datetime('now')
                    """),
                    {"key": key, "value": serialized}
                )

            logger.info(f"Setting '{key}' updated to '{serialized}'")
            return True

        except Exception as e:
            logger.error(f"Failed to update setting '{key}': {e}")
            return False

    def set_many(self, settings: dict[str, Any]) -> bool:
        """
        Set multiple settings at once.

        Args:
            settings: Dictionary of key-value pairs to set

        Returns:
            True if all successful, False if any failed
        """
        success = True
        for key, value in settings.items():
            if not self.set(key, value):
                success = False
        return success

    def get_auto_import_config(self) -> dict[str, Any]:
        """
        Get auto-import specific configuration.

        Returns:
            dict with enabled, flatten, and poll_interval keys
        """
        all_settings = self.get_all()
        return {
            "enabled": all_settings.get("auto_import_enabled", False),
            "flatten": all_settings.get("auto_import_flatten", True),
            "poll_interval": all_settings.get("auto_import_poll_interval", 30),
        }

    def reset_to_defaults(self) -> bool:
        """
        Reset all settings to their default values.

        Returns:
            True if successful, False otherwise
        """
        try:
            with engine.begin() as conn:
                for key, value in DEFAULT_SETTINGS.items():
                    conn.execute(
                        text("""
                            INSERT INTO app_settings (key, value, updated_at)
                            VALUES (:key, :value, datetime('now'))
                            ON CONFLICT(key) DO UPDATE SET
                                value = excluded.value,
                                updated_at = datetime('now')
                        """),
                        {"key": key, "value": value}
                    )

            logger.info("All settings reset to defaults")
            return True

        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            return False

    # --- Library Settings ---

    def get_enabled_libraries(self) -> List[str]:
        """
        Get list of enabled library IDs.

        Returns:
            List of library ID strings
        """
        try:
            value = self.get("enabled_library_ids")
            if value and isinstance(value, str):
                return json.loads(value)
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_enabled_libraries(self, library_ids: List[str]) -> bool:
        """
        Set the list of enabled library IDs.

        Args:
            library_ids: List of library ID strings

        Returns:
            True if successful, False otherwise
        """
        return self.set("enabled_library_ids", json.dumps(library_ids))

    def get_cached_libraries(self) -> List[dict]:
        """
        Get cached library metadata for display.

        Returns:
            List of library dicts with id, name, media_type, etc.
        """
        try:
            value = self.get("cached_libraries")
            if value and isinstance(value, str):
                return json.loads(value)
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_cached_libraries(self, libraries: List[dict]) -> bool:
        """
        Cache library metadata from ABS.

        Args:
            libraries: List of library dicts

        Returns:
            True if successful, False otherwise
        """
        return self.set("cached_libraries", json.dumps(libraries))

    def is_libraries_initialized(self) -> bool:
        """
        Check if libraries have been initialized from ABS.

        Returns:
            True if initialized, False otherwise
        """
        value = self.get("libraries_initialized")
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    def set_libraries_initialized(self, initialized: bool) -> bool:
        """
        Set the libraries initialized flag.

        Args:
            initialized: Whether libraries are initialized

        Returns:
            True if successful, False otherwise
        """
        return self.set("libraries_initialized", "true" if initialized else "false")

    def initialize_libraries(self, libraries: List[dict]) -> bool:
        """
        Initialize library settings from ABS library list.

        Auto-enables libraries with mediaType='book'.

        Args:
            libraries: List of library dicts from ABS API

        Returns:
            True if successful, False otherwise
        """
        try:
            # Cache the full library list
            self.set_cached_libraries(libraries)

            # Auto-enable audiobook libraries (mediaType='book')
            audiobook_ids = [
                lib.get("id") for lib in libraries
                if lib.get("media_type") == "book" or lib.get("mediaType") == "book"
            ]

            self.set_enabled_libraries(audiobook_ids)
            self.set_libraries_initialized(True)

            logger.info(f"📚 Initialized {len(audiobook_ids)} audiobook libraries out of {len(libraries)} total")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize libraries: {e}")
            return False


# Global singleton instance
settings_service = SettingsService()
