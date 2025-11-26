"""
Pytest configuration and shared fixtures for MAM Audiobook Finder tests.

This module provides common test fixtures and configuration for all test modules.

DUAL-MODE TESTING:
    This test suite supports two modes controlled by the LIVE_API_TESTS environment variable:

    1. MOCK MODE (default, LIVE_API_TESTS not set or != "1"):
       - Tests use pre-recorded fixture data from app/tests/fixtures/hardcover/
       - No real API calls are made
       - Fast, deterministic, safe for CI/CD
       - HardcoverClient is automatically patched to use MockHardcoverClient

    2. LIVE MODE (LIVE_API_TESTS=1):
       - Tests make real calls to Hardcover API
       - Requires HARDCOVER_API_TOKEN in environment
       - Slower, may hit rate limits, detects API changes
       - HardcoverClient behaves normally

    Usage:
        # Run in mock mode (default)
        pytest

        # Run in live mode
        LIVE_API_TESTS=1 pytest

    Marking tests that require live mode:
        @pytest.mark.requires_live
        async def test_that_needs_real_api():
            # This test will be skipped in mock mode
            pass
"""
import os
import sys
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest
from sqlalchemy import create_engine, text

logger = logging.getLogger("mam-audiofinder")

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Determine testing mode
LIVE_MODE = os.getenv("LIVE_API_TESTS") == "1"

if LIVE_MODE:
    print("\n" + "="*80)
    print("🔴 LIVE API MODE ENABLED - Tests will hit real Hardcover API")
    print("="*80 + "\n")
else:
    print("\n" + "="*80)
    print("🟢 MOCK MODE ENABLED - Tests will use fixture data")
    print("="*80 + "\n")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_db_engine():
    """Create an in-memory SQLite database engine for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Create history table schema
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY,
                mam_id TEXT,
                title TEXT,
                author TEXT,
                narrator TEXT,
                dl TEXT,
                added_at TEXT DEFAULT (datetime('now')),
                qb_status TEXT,
                qb_hash TEXT,
                imported_at TEXT,
                abs_item_id TEXT,
                abs_cover_url TEXT,
                abs_cover_cached_at TEXT,
                abs_verify_status TEXT,
                abs_verify_note TEXT
            )
        """))

    yield engine
    engine.dispose()


@pytest.fixture
def mock_covers_db_engine():
    """Create an in-memory SQLite database engine for covers testing."""
    engine = create_engine("sqlite:///:memory:")

    # Create covers table schema
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE covers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mam_id TEXT UNIQUE NOT NULL,
                title TEXT,
                author TEXT,
                cover_url TEXT NOT NULL,
                abs_item_id TEXT,
                local_file TEXT,
                file_size INTEGER,
                fetched_at TEXT DEFAULT (datetime('now'))
            )
        """))

    yield engine
    engine.dispose()


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient for testing HTTP requests."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_config():
    """Provide mock configuration values for testing."""
    return {
        'MAM_COOKIE': 'mam_id=test123; session=abc456',
        'QB_URL': 'http://test-qbittorrent:8080',
        'QB_USER': 'admin',
        'QB_PASS': 'testpass',
        'DL_DIR': '/media/torrents',
        'LIB_DIR': '/media/Books/Audiobooks',
        'IMPORT_MODE': 'link',
        'FLATTEN_DISCS': True,
        'QB_CATEGORY': 'mam-audiofinder',
        'QB_POSTIMPORT_CATEGORY': '',
        'ABS_URL': 'http://test-abs:13378',
        'ABS_TOKEN': 'test-token-123',
        'ABS_VERIFY_TIMEOUT': 10,
        'COVERS_DIR': '/data/covers',
        'MAX_COVERS_SIZE_MB': 500,
    }


@pytest.fixture
def sample_mam_search_result():
    """Provide a sample MAM search result for testing."""
    return {
        'data': [
            {
                'id': '12345',
                'title': 'The Hobbit',
                'author_info': {
                    'author': 'J.R.R. Tolkien',
                    'narrator': 'Rob Inglis'
                },
                'torrent': {
                    'download_link': 'https://mam/download/12345'
                },
                'size': '536870912',  # 512 MB
                'seeders': 10,
                'leechers': 2,
                'format': 'M4B'
            },
            {
                'id': '67890',
                'title': 'The Fellowship of the Ring',
                'author_info': {
                    'author': 'J.R.R. Tolkien',
                    'narrator': 'Rob Inglis'
                },
                'torrent': {
                    'download_link': 'https://mam/download/67890'
                },
                'size': '1073741824',  # 1 GB
                'seeders': 15,
                'leechers': 3,
                'format': 'MP3'
            }
        ]
    }


@pytest.fixture
def sample_abs_cover_response():
    """Provide a sample Audiobookshelf cover fetch response."""
    return {
        'results': [
            {
                'title': 'The Hobbit',
                'author': 'J.R.R. Tolkien',
                'cover': 'https://abs-server/api/items/item123/cover',
                'id': 'item123'
            }
        ]
    }


@pytest.fixture
def sample_abs_library_items():
    """Provide a sample Audiobookshelf library items response."""
    return {
        'results': [
            {
                'id': 'lib-item-1',
                'media': {
                    'metadata': {
                        'title': 'The Hobbit',
                        'authorName': 'J.R.R. Tolkien',
                        'narratorName': 'Rob Inglis'
                    }
                },
                'path': '/audiobooks/Tolkien, J.R.R/The Hobbit'
            },
            {
                'id': 'lib-item-2',
                'media': {
                    'metadata': {
                        'title': 'The Fellowship of the Ring',
                        'authorName': 'J.R.R. Tolkien',
                        'narratorName': 'Rob Inglis'
                    }
                },
                'path': '/audiobooks/Tolkien, J.R.R/The Fellowship of the Ring'
            }
        ],
        'total': 2
    }


@pytest.fixture
def sample_qb_torrent_info():
    """Provide a sample qBittorrent torrent info response."""
    return {
        'hash': 'abc123def456',
        'name': 'The Hobbit',
        'state': 'pausedUP',
        'progress': 1.0,
        'dlspeed': 0,
        'upspeed': 1024,
        'downloaded': 536870912,
        'uploaded': 1073741824,
        'size': 536870912,
        'save_path': '/downloads/The Hobbit',
        'content_path': '/downloads/The Hobbit',
        'category': 'mam-audiofinder',
        'tags': 'mam-12345'
    }


@pytest.fixture
def sample_file_tree():
    """Provide a sample multi-disc file tree structure."""
    return {
        'Disc 01': [
            'Track 01.mp3',
            'Track 02.mp3',
            'Track 03.mp3'
        ],
        'Disc 02': [
            'Track 01.mp3',
            'Track 02.mp3'
        ],
        'cover.jpg': None
    }


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables before each test."""
    # Store original env
    original_env = os.environ.copy()

    yield

    # Restore original env after test
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def reset_test_cache():
    """Reset mock cache before each test for isolation (Phase 2)."""
    if not LIVE_MODE:
        from tests.mocks import cache_mock
        cache_mock.reset_test_cache()
    yield


# ============================================================================
# DUAL-MODE TESTING INFRASTRUCTURE
# ============================================================================

def pytest_configure(config):
    """Register custom markers for dual-mode testing."""
    config.addinivalue_line(
        "markers",
        "requires_live: mark test as requiring live API access (will be skipped in mock mode)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests marked as requires_live when in mock mode."""
    if not LIVE_MODE:
        skip_live = pytest.mark.skip(reason="Test requires live API (LIVE_API_TESTS=1 to run)")
        for item in items:
            if "requires_live" in item.keywords:
                item.add_marker(skip_live)


@pytest.fixture(scope="session", autouse=True)
def auto_mock_services():
    """
    Automatically patch all external service clients in mock mode.

    Patches:
    - HardcoverClient → MockHardcoverClient
    - AudiobookshelfClient → MockABSClient
    - qb_login/qb_login_sync → mock_qb_login/mock_qb_login_sync

    This fixture runs once per test session and patches all service clients
    at the module level before any tests import them.

    In LIVE mode: Does nothing (tests use real clients)
    In MOCK mode: Patches all clients with mock implementations
    """
    if LIVE_MODE:
        # Live mode: no patching needed
        yield
        return

    # Mock mode: patch all external service clients
    from tests.mocks.hardcover_mock import MockHardcoverClient
    from tests.mocks.abs_mock import MockABSClient
    from tests.mocks import qb_mock
    from tests.mocks import cache_mock

    # Create nested context managers for all patches
    with patch('hardcover_client.HardcoverClient', MockHardcoverClient), \
         patch('abs_client.AudiobookshelfClient', MockABSClient), \
         patch('qb_client.qb_login', qb_mock.mock_qb_login), \
         patch('qb_client.qb_login_sync', qb_mock.mock_qb_login_sync), \
         patch('mam_cache.get_cached_mam_search', cache_mock.get_cached_mam_search), \
         patch('mam_cache.cache_mam_search', cache_mock.cache_mam_search), \
         patch('mam_cache.clear_expired_cache', cache_mock.clear_expired_cache), \
         patch('mam_cache.get_cache_stats', cache_mock.get_cache_stats):

        # Patch already-imported module references
        import hardcover_client
        import abs_client
        import qb_client

        # Store originals
        orig_hc = hardcover_client.HardcoverClient
        orig_abs = abs_client.AudiobookshelfClient
        orig_qb_async = qb_client.qb_login
        orig_qb_sync = qb_client.qb_login_sync

        # Apply patches
        hardcover_client.HardcoverClient = MockHardcoverClient
        abs_client.AudiobookshelfClient = MockABSClient
        qb_client.qb_login = qb_mock.mock_qb_login
        qb_client.qb_login_sync = qb_mock.mock_qb_login_sync

        # Patch global instances if they exist
        if hasattr(hardcover_client, 'hardcover_client'):
            hardcover_client.hardcover_client = MockHardcoverClient()

        if hasattr(abs_client, 'abs_client'):
            abs_client.abs_client = MockABSClient()

        logger.info("🔧 MOCK MODE: All services patched (Hardcover, ABS, qBittorrent, MAM Cache)")

        yield

        # Restore originals (though typically tests end after this)
        hardcover_client.HardcoverClient = orig_hc
        abs_client.AudiobookshelfClient = orig_abs
        qb_client.qb_login = orig_qb_async
        qb_client.qb_login_sync = orig_qb_sync


@pytest.fixture
def hardcover_client():
    """
    Provide appropriate HardcoverClient instance based on test mode.

    Returns:
        HardcoverClient in live mode, MockHardcoverClient in mock mode
    """
    if LIVE_MODE:
        from hardcover_client import HardcoverClient
        client = HardcoverClient()
    else:
        from tests.mocks.hardcover_mock import MockHardcoverClient
        client = MockHardcoverClient()

    # Reset counters before each test
    client.reset_counters()

    yield client


@pytest.fixture
def abs_client():
    """
    Provide appropriate ABS client instance based on test mode.

    Returns:
        AudiobookshelfClient in live mode, MockABSClient in mock mode
    """
    if LIVE_MODE:
        from abs_client import AudiobookshelfClient
        client = AudiobookshelfClient()
    else:
        from tests.mocks.abs_mock import MockABSClient
        client = MockABSClient()

    # Reset counters if method exists
    if hasattr(client, 'reset_counters'):
        client.reset_counters()

    yield client
