# Testing Guide - MAM Audiobook Finder

This document describes the testing infrastructure and workflows for both local and container-based testing.

## Overview

The project supports **three testing modes** that work together:

1. **Mock Mode** (default) - Deterministic tests using pre-recorded API fixtures (fast, CI-safe)
2. **Live Mode** - Tests hit real Hardcover API (slower, detects API changes)
3. **Container Testing** - Full integration with Docker networking (tests can reach ABS/qBittorrent)

All modes use the **same test suite** (223+ tests across 11+ files) without modification.

---

## Dual-Mode Testing (Mock vs Live)

The test suite supports **automatic dual-mode testing** for all external service API integration tests. The same tests can run in two modes controlled by the `LIVE_API_TESTS` environment variable:

**Supported Services (Phase 1 & 2):**
- ✅ **Hardcover API** - Series/book metadata
- ✅ **Audiobookshelf (ABS) API** - Library verification, cover fetching, metadata
- ✅ **qBittorrent API** - Torrent management
- ✅ **MAM Cache** - Search result caching

### Mock Mode (Default - Recommended for CI/CD)

**When:** `LIVE_API_TESTS` is not set or `!= "1"`

**Behavior:**
- Tests use pre-recorded API responses from `app/tests/fixtures/{service}/*.json`
- No real API calls are made
- Fast, deterministic execution (~200ms per test)
- No API tokens required
- Safe for GitHub Actions and parallel test runs
- All service clients are automatically patched with mock implementations:
  - HardcoverClient → MockHardcoverClient
  - AudiobookshelfClient → MockABSClient
  - qb_login functions → mock_qb_login functions
  - MAM cache functions → cache_mock functions

**Run mock mode:**
```bash
# Using Makefile (recommended)
make test-mock

# Using pytest directly
pytest app/tests/

# Explicit mock mode
LIVE_API_TESTS=0 pytest app/tests/
```

### Live Mode (For API Change Detection)

**When:** `LIVE_API_TESTS=1`

**Behavior:**
- Tests make real calls to Hardcover GraphQL API
- Requires `HARDCOVER_API_TOKEN` in environment
- Slower execution (~2-5s per test due to rate limiting)
- Detects API structure changes, field removals, response format updates
- Subject to rate limits (60 req/min by default)

**Run live mode:**
```bash
# Using Makefile (recommended)
make test-live

# Using pytest directly
LIVE_API_TESTS=1 pytest app/tests/

# With specific API token
HARDCOVER_API_TOKEN=your-token-here LIVE_API_TESTS=1 pytest app/tests/
```

### Marking Tests as Requires-Live

For tests that **must** run against the real API (e.g., testing rate limiting, caching behavior):

```python
@pytest.mark.requires_live
@pytest.mark.asyncio
async def test_rate_limiting(hardcover_client):
    """This test requires real API to verify rate limiting."""
    # Test implementation
```

**Behavior:**
- ✅ Runs in live mode (`LIVE_API_TESTS=1`)
- ⏭️ Skipped in mock mode with clear message

### How It Works

**Automatic Unified Patching (Phase 1 & 2):**
The `conftest.py` fixture `auto_mock_services()` runs once per test session:
- In **mock mode**: Patches all service clients with mock implementations
  - `hardcover_client.HardcoverClient` → `MockHardcoverClient`
  - `abs_client.AudiobookshelfClient` → `MockABSClient`
  - `qb_client.qb_login` → `mock_qb_login`
  - `qb_client.qb_login_sync` → `mock_qb_login_sync`
  - `mam_cache.*` functions → `cache_mock.*` functions
- In **live mode**: Does nothing (tests use real clients)

**No Test Modification Required:**
Tests simply use service client fixtures:
```python
@pytest.mark.asyncio
async def test_search_series(hardcover_client):
    result = await hardcover_client.search_series("Foundation")
    assert result is not None
    # Works in both modes!

@pytest.mark.asyncio
async def test_abs_verification(abs_client):
    result = await abs_client.verify_import("The Hobbit", "J.R.R. Tolkien")
    assert result["status"] == "verified"
    # Works in both modes!
```

**Test Isolation (Phase 2):**
- `reset_test_cache()` fixture clears mock cache before each test
- Ensures no test pollution from cached data
- Only active in mock mode

### Fixture Management

**Capturing New Fixtures:**

**Hardcover API:**
When you add new Hardcover API tests, capture fixtures from the live API:

```bash
# Activate virtual environment
source tmp/bin/activate

# Set API token
export HARDCOVER_API_TOKEN="your-token-here"

# Run capture script
python app/tests/scripts/capture_fixtures.py
```

**Audiobookshelf (ABS) API (Phase 1):**
When you add new ABS API tests, capture fixtures from your live ABS instance:

```bash
# Activate virtual environment
source tmp/bin/activate

# Set ABS environment variables
export ABS_BASE_URL="http://your-abs-server:13378"
export ABS_API_KEY="your-api-key"
export ABS_LIBRARY_ID="your-library-id"

# Run ABS capture script
python app/tests/scripts/capture_abs_fixtures.py
```

**Fixture Storage:**
- Hardcover: `app/tests/fixtures/hardcover/`
- ABS: `app/tests/fixtures/abs/`
- qBittorrent: `app/tests/fixtures/qbittorrent/` (empty - no fixtures needed)
- Format: JSON files named by method and parameters
- Example: `search_series_title=Foundation.json`, `verify_import_title=The_Hobbit.json`

**Fixture Naming Convention:**
```
{method}_{param1}={value1}_{param2}={value2}.json

Examples:
search_series_title=Foundation.json
search_series_title=Discworld_author=Terry_Pratchett.json
list_series_books_series_id=1185.json
search_book_by_title_title=Harry_Potter_and_the_Philosoph.json
```

### Best Practices

1. **Default to Mock Mode:**
   - Run `make test-mock` or `pytest` without env vars for daily development
   - Fast feedback loop, no API dependency

2. **Periodic Live Mode Runs:**
   - Run `make test-live` weekly or before releases
   - Detects Hardcover API changes early

3. **CI/CD Uses Mock Mode:**
   - GitHub Actions should run in mock mode (no secrets needed)
   - Fast, deterministic, no rate limits

4. **Fixture Maintenance:**
   - Re-capture fixtures after Hardcover API updates
   - Keep fixtures in version control
   - Document any manual fixture edits

5. **Test Isolation:**
   - Each test should reset counters: `hardcover_client.reset_counters()`
   - Provided automatically by `hardcover_client` fixture

### Troubleshooting

**"Fixture not found" errors:**
```
FixtureNotFoundError: ❌ FIXTURE NOT FOUND: search_series_title=MyNewSeries.json
```

**Fix:** Capture the fixture in live mode:
```bash
export HARDCOVER_API_TOKEN="your-token"
python app/tests/scripts/capture_fixtures.py
# Or manually add test case to capture script
```

**Mock mode passes, live mode fails:**
- API response structure changed
- Field was removed/renamed
- Update fixtures to match new API
- Update test assertions if needed

**Live mode rate limiting:**
- Hardcover API: 60 requests/minute
- Tests include 1s delays between calls
- Reduce parallelism or use mock mode for bulk runs

---

## Test Suite Structure

```
app/tests/
├── conftest.py                          # Shared fixtures (in-memory DBs, mocks)
├── test_*.py                           # Backend unit tests (223 functions)
│   ├── test_verification.py           # ABS verification logic
│   ├── test_covers.py                  # Cover caching
│   ├── test_description_fetch.py       # Description fetching (manual integration test)
│   ├── test_search.py                  # MAM search
│   ├── test_helpers.py                 # Utility functions
│   ├── test_library_matching_intelligence.py  # Library matching
│   └── test_migration_syntax.py        # Migration validation
└── frontend/
    ├── conftest.py                     # Selenium fixtures
    └── test_*.py                       # Frontend E2E tests
        ├── test_search_page.py
        ├── test_history_page.py
        ├── test_showcase_page.py
        └── test_import_workflow.py
```

### Test Categories

**Backend Tests** - Pure Python unit tests:
- Use in-memory SQLite databases (via `conftest.py` fixtures)
- Mock all external HTTP calls (httpx, ABS API, qBittorrent)
- Fast execution (~5-10 seconds for full suite)
- No external dependencies required

**Frontend Tests** - Selenium browser automation:
- Require running application instance
- Use Chromium browser (integrated in container or via webdriver_manager locally)
- Test full user workflows (search, import, history)
- Slower execution (~30-60 seconds per test)

---

## Local Testing (Development)

### Initial Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests Locally

```bash
# Quick backend tests
make test-backend

# With coverage
make test-coverage

# Specific test file
pytest app/tests/test_verification.py -v

# Specific test function
pytest app/tests/test_verification.py::TestVerification::test_verify_import -v

# Watch mode (re-run on file changes)
make watch-tests
```

### Local Selenium Tests

Frontend tests require a running app instance + Selenium browser:

```bash
# Option 1: Use webdriver_manager (automatic Chrome download)
pytest app/tests/frontend/ -v --base-url=http://localhost:8080

# Option 2: Use separate Selenium Grid container (deprecated)
# Note: Selenium is now integrated into test container - use docker testing instead
```

**Advantages of Local Testing:**
- ⚡ Fast iteration (no Docker rebuild)
- 🐛 Easy debugging (breakpoints, print statements)
- 💻 Works offline (after initial pip install)
- 🔍 IDE integration (PyCharm, VSCode test runners)

**Limitations:**
- ❌ Can't test ABS/qBittorrent integration (no docker networking)
- ❌ Requires local Python environment setup
- ❌ Frontend tests need manual app startup

---

## Container Testing (Integration)

### Architecture

Container testing uses a **multi-stage Dockerfile**:

```dockerfile
# Stage 1: production (lean, ~200MB)
FROM python:3.12-slim AS production
# ... production dependencies only ...

# Stage 2: testing (larger, ~400MB, includes test tools)
FROM production AS testing
# + pytest, selenium, make
# + chromium browser + chromedriver
# + test suite files
```

**Key Features:**
- Tests run inside container with same environment as production
- Has access to Docker networks (can reach ABS, qBittorrent by hostname)
- Integrated Chromium browser for Selenium tests (no separate container needed)
- Isolated test database (`/data/test-data/` volume)
- Live code mounting for rapid iteration

### Building Test Container

```bash
# Build test image (includes all test dependencies)
make docker-test-build

# Or manually:
docker compose -f docker-compose.yml -f docker-compose.test.yml build mam-audiofinder-test
```

This creates an image: `mam-audiofinder:test` (~400MB vs ~200MB for production)

### Running Container Tests

```bash
# Run full test suite
make docker-test-run

# Run only backend tests (fast)
make docker-test-backend

# Run only frontend tests (with integrated Selenium)
make docker-test-frontend

# Run specific test file
make docker-test-specific TEST=test_verification.py

# Run with coverage report
make docker-test-coverage

# Open shell for debugging
make docker-test-shell
# Inside container:
> pytest tests/test_verification.py -v
> pytest tests/ -k "test_verify" -v
> make test-backend
```

### Container Test Environment Variables

Configured in `docker-compose.test.yml`:

```yaml
environment:
  # Isolated test data (doesn't interfere with production)
  DATA_DIR: /data/test-data
  HISTORY_DB_PATH: /data/test-data/history.db
  COVERS_DB_PATH: /data/test-data/covers.db

  # Integrated Selenium
  SELENIUM_DRIVER_TYPE: local
  SELENIUM_BROWSER: chrome
  CHROME_BIN: /usr/bin/chromium
  CHROMEDRIVER_PATH: /usr/bin/chromedriver
```

### Docker Networking for Integration Tests

The test container joins the `nginx-network` (same as production):

```yaml
networks:
  - nginx-network  # Can reach ABS, qBittorrent by hostname
```

This enables **real integration testing**:

```python
# Example: Test can actually connect to ABS
@pytest.mark.integration
async def test_real_abs_connection():
    """Test actual ABS API connection via docker network"""
    from abs_client import abs_client

    # ABS_BASE_URL=http://audiobookshelf:13378 from .env
    is_configured, message = await abs_client.test_connection()
    assert is_configured, f"ABS not reachable: {message}"
```

**Advantages of Container Testing:**
- ✅ Full integration testing (ABS, qBittorrent via network)
- ✅ Production-like environment (same base image)
- ✅ Consistent across all developers
- ✅ CI/CD ready
- ✅ No local Python setup required

**Limitations:**
- 🐌 Slower build times (first build ~3-5 minutes)
- 💾 Larger image size (~400MB vs ~200MB)
- 🔄 Requires rebuild for dependency changes

---

## Selenium Integration

### Previous Architecture (Deprecated)

```yaml
# docker-compose.yml
services:
  selenium:
    image: selenium/standalone-chrome
    # Separate 2GB container just for browser
```

Problems:
- Extra 2GB container overhead
- Network configuration complexity
- Not available in test container

### New Architecture (Integrated)

```dockerfile
# Dockerfile - testing stage
RUN apt-get install chromium chromium-driver  # ~100MB
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
```

Benefits:
- ✅ No separate container needed
- ✅ Tests run in same environment
- ✅ Simpler network config
- ✅ Works in both local and container modes

The `conftest.py` automatically detects environment:

```python
def _create_local_driver(browser_name, headless):
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if chromedriver_path and os.path.exists(chromedriver_path):
        # Container mode: use system chromium
        return webdriver.Chrome(service=ChromeService(chromedriver_path))
    else:
        # Local mode: use webdriver_manager
        return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
```

---

## Configurable Database Paths

Database paths are now configurable via environment variables (defaults to `/data/`):

```python
# config.py
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
HISTORY_DB_PATH = os.getenv("HISTORY_DB_PATH", str(DATA_DIR / "history.db"))
COVERS_DB_PATH = os.getenv("COVERS_DB_PATH", str(DATA_DIR / "covers.db"))
```

This enables:
- Container tests use `/data/test-data/` (isolated from production)
- Local tests can use `/tmp/test-db/` or in-memory (`:memory:`)
- Fixtures use in-memory SQLite for speed

---

## Workflow Comparison

| Task | Local | Container |
|------|-------|-----------|
| **Initial Setup** | `make venv && make install-dev` | `make docker-test-build` |
| **Run All Tests** | `make test-backend` | `make docker-test-run` |
| **Run One Test** | `pytest tests/test_X.py -v` | `make docker-test-specific TEST=test_X.py` |
| **With Coverage** | `make test-coverage` | `make docker-test-coverage` |
| **Debug Tests** | `pytest tests/test_X.py -vv --pdb` | `make docker-test-shell` then `pytest ...` |
| **Frontend Tests** | `pytest tests/frontend/ -v` (needs app running) | `make docker-test-frontend` |
| **Integration Tests** | ❌ No ABS/qB networking | ✅ Full docker networking |
| **Speed** | ⚡⚡⚡ Instant | 🐌 Container startup overhead |
| **Iteration** | ⚡⚡⚡ Edit + run | ⚡⚡ Live mounted (no rebuild) |

---

## Best Practices

### Daily Development

```bash
# Fast local testing while coding
pytest app/tests/test_verification.py -v

# Before commit: run full suite locally
make test-backend

# Before PR: run container tests to verify integration
make docker-test-run
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Build test image
  run: make docker-test-build

- name: Run tests in container
  run: make docker-test-run

- name: Generate coverage report
  run: make docker-test-coverage
```

### Writing New Tests

**Unit Tests** (fast, no external deps):
```python
# tests/test_my_feature.py
def test_my_function(mock_db_engine):  # Use fixtures from conftest.py
    result = my_function()
    assert result == expected
```

**Integration Tests** (need docker networking):
```python
# tests/test_abs_integration.py
@pytest.mark.integration
async def test_abs_verify_import():
    # Requires: make docker-test-run (can reach ABS via network)
    result = await abs_client.verify_import("Book Title", "Author")
    assert result['status'] == 'verified'
```

**Frontend Tests** (Selenium):
```python
# tests/frontend/test_search_page.py
def test_search_workflow(navigate_to, wait_for_element):
    navigate_to("/search")
    search_input = wait_for_element(By.ID, "search-query")
    search_input.send_keys("Hobbit")
    # ... test continues
```

### Cleanup

```bash
# Remove test containers and volumes
make docker-test-clean

# Remove test artifacts
make clean-test

# Full cleanup
make clean
```

---

## Troubleshooting

### Local Testing Issues

**Import errors:**
```bash
# Make sure you're in venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

**Tests can't find modules:**
```bash
# Run pytest from project root
cd /path/to/mam-audiofinder
pytest app/tests/ -v
```

### Container Testing Issues

**Build fails:**
```bash
# Check Docker is running
docker ps

# Try clean build
make docker-test-clean
make docker-test-build
```

**Tests can't reach ABS:**
```bash
# Check ABS is running and on same network
docker network inspect nginx-network

# Check .env has correct ABS_BASE_URL
grep ABS_BASE_URL .env
# Should be: ABS_BASE_URL=http://audiobookshelf:13378 (hostname, not localhost)
```

**Selenium errors in container:**
```bash
# Check chromium installed
make docker-test-shell
> which chromium
> chromium --version

# Check environment variables
> echo $CHROME_BIN
> echo $CHROMEDRIVER_PATH
```

**Database permission errors:**
```bash
# Check PUID/PGID in .env match your user
id -u  # Your UID
id -g  # Your GID

# Update .env
PUID=1000
PGID=1000
```

---

## Migration Guide

If you have existing local test setup:

```bash
# 1. Pull latest changes (includes new docker-compose.test.yml)
git pull

# 2. Your local testing still works unchanged
make test-backend

# 3. Build new test container
make docker-test-build

# 4. Try container testing
make docker-test-run

# 5. Update CI/CD to use new targets
# Replace: docker compose exec mam-audiofinder pytest ...
# With:    make docker-test-run
```

No changes to test code required - everything is backward compatible!

---

## Summary

**Use Local Testing When:**
- Writing/debugging new features
- Quick iteration needed
- Testing pure Python logic
- No external services needed

**Use Container Testing When:**
- Testing ABS/qBittorrent integration
- Verifying production-like behavior
- Running CI/CD pipeline
- Need consistent environment across team

**Both modes use the same test suite** - pick the right tool for the task!
