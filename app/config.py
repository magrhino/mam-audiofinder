"""
Configuration module for MAM Audiobook Finder.
Handles environment variable parsing and validation.
"""
import os
from pathlib import Path


# ---------------------------- Paths Configuration ----------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
COVERS_DIR = DATA_DIR / "covers"
HISTORY_DB_PATH = os.getenv("HISTORY_DB_PATH", str(DATA_DIR / "history.db"))
COVERS_DB_PATH = os.getenv("COVERS_DB_PATH", str(DATA_DIR / "covers.db"))
SERIES_DB_PATH = os.getenv("SERIES_DB_PATH", str(DATA_DIR / "series.db"))

# ---------------------------- Logging Configuration ----------------------------
LOG_MAX_MB = int(os.getenv("LOG_MAX_MB", "5"))
LOG_MAX_FILES = int(os.getenv("LOG_MAX_FILES", "5"))
LOG_DIR = DATA_DIR / "logs"

# ---------------------------- MAM Configuration ----------------------------
MAM_BASE = "https://www.myanonamouse.net"

def build_mam_cookie():
    """Build MAM cookie from environment variable."""
    raw = os.getenv("MAM_COOKIE", "").strip()
    # If user pasted full cookie header, use it as-is
    if "mam_id=" in raw or "mam_session=" in raw:
        return raw
    # If ASN single-token was pasted, wrap it
    if raw and "=" not in raw and ";" not in raw:
        return f"mam_id={raw}"
    return raw

MAM_COOKIE = build_mam_cookie()

# ---------------------------- qBittorrent Configuration ----------------------------
QB_URL = os.getenv("QB_URL", "http://qbittorrent:8080").rstrip("/")
QB_USER = os.getenv("QB_USER", "admin")
QB_PASS = os.getenv("QB_PASS", "adminadmin")
QB_SAVEPATH = os.getenv("QB_SAVEPATH", "")  # optional
QB_TAGS = os.getenv("QB_TAGS", "MAM,audiobook")  # optional
QB_CATEGORY = os.getenv("QB_CATEGORY", "mam-audiofinder")
QB_POSTIMPORT_CATEGORY = os.getenv("QB_POSTIMPORT_CATEGORY", "")  # "" = clear; or set e.g. "imported"
QB_INNER_DL_PREFIX = os.getenv("QB_INNER_DL_PREFIX", "/downloads")  # qB container's mount point

# ---------------------------- Audiobookshelf Configuration ----------------------------
ABS_BASE_URL = os.getenv("ABS_BASE_URL", "").rstrip("/")
ABS_API_KEY = os.getenv("ABS_API_KEY", "")
ABS_LIBRARY_ID = os.getenv("ABS_LIBRARY_ID", "")
MAX_COVERS_SIZE_MB = int(os.getenv("MAX_COVERS_SIZE_MB", "500"))  # 0 = direct fetch only (not recommended)
ABS_VERIFY_TIMEOUT = int(os.getenv("ABS_VERIFY_TIMEOUT", "10"))  # Timeout in seconds for import verification

# Library visibility feature - check if search results exist in ABS library
# Default to True if ABS is fully configured, False otherwise
_abs_fully_configured = bool(ABS_BASE_URL and ABS_API_KEY and ABS_LIBRARY_ID)
ABS_CHECK_LIBRARY = os.getenv("ABS_CHECK_LIBRARY", str(_abs_fully_configured)).lower() in ("true", "1", "yes")
ABS_LIBRARY_CACHE_TTL = int(os.getenv("ABS_LIBRARY_CACHE_TTL", "300"))  # Cache duration in seconds (default: 5 minutes)

# ---------------------------- Debug Configuration ----------------------------
DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"  # Enable debug logging globally
DEBUG_MATCHING = os.getenv("DEBUG_MATCHING", "0") == "1"  # Enable verbose matching debug logs

# ---------------------------- Hardcover API Configuration ----------------------------
HARDCOVER_API_TOKEN = os.getenv("HARDCOVER_API_TOKEN", "")
HARDCOVER_BASE_URL = "https://api.hardcover.app/v1/graphql"
HARDCOVER_CACHE_TTL = int(os.getenv("HARDCOVER_CACHE_TTL", "300"))  # Cache duration in seconds (default: 5 minutes)
HARDCOVER_RATE_LIMIT = int(os.getenv("HARDCOVER_RATE_LIMIT", "60"))  # Requests per minute (API limit: 60/min)
HARDCOVER_SERIES_LIMIT = int(os.getenv("HARDCOVER_SERIES_LIMIT", "20"))  # Default number of series results to fetch

# ---------------------------- Import Configuration ----------------------------
DL_DIR = os.getenv("DL_DIR", "/media/torrents")
LIB_DIR = os.getenv("LIB_DIR", "/media/Books/Audiobooks")
IMPORT_MODE = os.getenv("IMPORT_MODE", "link")  # link|copy|move
FLATTEN_DISCS = os.getenv("FLATTEN_DISCS", "true").lower() in ("true", "1", "yes")  # flatten multi-disc to sequential files
AUDIO_EXTS = None  # copy everything except .cue
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}  # Image file extensions (preserved, not renamed)
# Cover source priority: "shelfarr" (use Shelfarr cache first) or "torrent" (use torrent image first)
# Falls back to the other source if preferred is unavailable
COVER_SOURCE_PRIORITY = os.getenv("COVER_SOURCE_PRIORITY", "torrent").lower()  # shelfarr|torrent

# ---------------------------- Auto-Import Configuration ----------------------------
# These are default values that can be overridden at runtime via the Settings page
AUTO_IMPORT_ENABLED = os.getenv("AUTO_IMPORT_ENABLED", "false").lower() in ("true", "1", "yes")
AUTO_IMPORT_POLL_INTERVAL = int(os.getenv("AUTO_IMPORT_POLL_INTERVAL", "30"))  # Polling interval in seconds (15-300)
AUTO_IMPORT_FLATTEN = os.getenv("AUTO_IMPORT_FLATTEN", "true").lower() in ("true", "1", "yes")  # Flatten multi-disc during auto-import

# ---------------------------- Apply UMASK ----------------------------
def apply_umask():
    """Apply UMASK if specified in environment."""
    _um = os.getenv("UMASK")
    if _um:
        try:
            os.umask(int(_um, 8))
        except Exception:
            pass

apply_umask()
