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
# Using run-tests.sh script (recommended) - LOCAL TESTS
cd build/
./run-tests.sh                             # Mock by default (local)
./run-tests.sh backend                     # Backend only (mock)

# Docker tests - use --mock to override live default
./run-tests.sh --docker --mock             # Force mock in Docker

# Using pytest directly
pytest app/tests/                          # Mock mode (local Python)

# Explicit mock mode
LIVE_API_TESTS=0 pytest app/tests/
```

### Live Mode (For API Change Detection & Docker Integration)

**When:** `LIVE_API_TESTS=1`

**Behavior:**
- Tests make real calls to Hardcover GraphQL API and ABS
- Requires `HARDCOVER_API_TOKEN` and other API credentials in .env
- Slower execution (~2-5s per test due to rate limiting)
- Detects API structure changes, field removals, response format updates
- Subject to rate limits (60 req/min by default)

**Run live mode:**
```bash
# Using run-tests.sh script (recommended)
# DOCKER TESTS: Live by default
cd build/
./run-tests.sh --docker                    # Live mode (default for Docker)
./run-tests.sh --docker backend            # Backend only (live)

# LOCAL TESTS: Use --live flag
./run-tests.sh --live                      # Force live mode (local)
./run-tests.sh --live -- -k hardcover      # Specific tests (live)

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

1. **Local Development (Mock Mode):**
   - Run `./run-tests.sh` for fast daily development
   - Fast feedback loop, no API dependency
   - No API tokens needed

2. **Integration Testing (Docker Live Mode):**
   - Run `./run-tests.sh --docker` for full integration tests
   - Tests hit real APIs (Hardcover, ABS, qBittorrent)
   - Requires .env with valid API tokens
   - Run before releases or after major changes

3. **Periodic Live Mode Checks:**
   - Run `./run-tests.sh --live` locally weekly
   - Detects Hardcover API changes early without Docker

4. **CI/CD Uses Mock Mode:**
   - GitHub Actions should run in mock mode (no secrets needed)
   - Fast, deterministic, no rate limits

5. **Fixture Maintenance:**
   - Re-capture fixtures after Hardcover API updates
   - Keep fixtures in version control
   - Document any manual fixture edits

6. **Test Isolation:**
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
cd build/
./run-tests.sh backend

# With coverage
./run-tests.sh coverage

# Specific test file
./run-tests.sh backend -- tests/test_verification.py -v

# Specific test function
./run-tests.sh backend -- tests/test_verification.py::TestVerification::test_verify_import -v

# Using pytest directly (if in app/ directory)
pytest tests/test_verification.py -v
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
cd build/
./run-tests.sh build

# Or manually:
docker compose -f build/docker-compose.test.yml build test
```

This creates an image: `mam-audiofinder-test:latest` (~400MB vs ~200MB for production)

### Running Container Tests

```bash
# Run full test suite
cd build/
./run-tests.sh --docker

# Run only backend tests (fast)
./run-tests.sh --docker backend

# Run only frontend tests (with integrated Selenium)
./run-tests.sh frontend

# Run specific test file
./run-tests.sh --docker backend -- tests/test_verification.py -v

# Run with coverage report
./run-tests.sh --docker coverage

# Open shell for debugging
./run-tests.sh shell
# Inside container:
> pytest tests/test_verification.py -v
> pytest tests/ -k "test_verify" -v
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
| **Initial Setup** | `python3 -m venv venv && pip install -r requirements-dev.txt` | `./run-tests.sh build` |
| **Run All Tests** | `./run-tests.sh backend` | `./run-tests.sh --docker` |
| **Run One Test** | `pytest tests/test_X.py -v` | `./run-tests.sh --docker backend -- tests/test_X.py -v` |
| **With Coverage** | `./run-tests.sh coverage` | `./run-tests.sh --docker coverage` |
| **Debug Tests** | `pytest tests/test_X.py -vv --pdb` | `./run-tests.sh shell` then `pytest ...` |
| **Frontend Tests** | `pytest tests/frontend/ -v` (needs app running) | `./run-tests.sh frontend` |
| **Integration Tests** | ❌ No ABS/qB networking | ✅ Full docker networking |
| **Speed** | ⚡⚡⚡ Instant | 🐌 Container startup overhead |
| **Iteration** | ⚡⚡⚡ Edit + run | ⚡⚡ Live mounted (no rebuild) |

---

## Best Practices

### Daily Development

```bash
# Fast local testing while coding
cd build/
./run-tests.sh backend -- tests/test_verification.py -v

# Before commit: run full suite locally
./run-tests.sh backend

# Before PR: run container tests to verify integration
./run-tests.sh --docker
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Build test image
  run: cd build && ./run-tests.sh build

- name: Run tests in container
  run: cd build && ./run-tests.sh --docker

- name: Generate coverage report
  run: cd build && ./run-tests.sh --docker coverage
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
    # Requires: ./run-tests.sh --docker (can reach ABS via network)
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
docker compose -f build/docker-compose.test.yml down -v

# Remove test image
docker rmi mam-audiofinder-test:latest

# Remove coverage reports
rm -rf htmlcov/ .coverage
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
docker compose -f build/docker-compose.test.yml down -v
cd build && ./run-tests.sh build
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
cd build && ./run-tests.sh shell
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
# 1. Pull latest changes (includes new run-tests.sh script)
git pull

# 2. Your local testing still works unchanged
cd build && ./run-tests.sh backend

# 3. Build new test container
./run-tests.sh build

# 4. Try container testing
./run-tests.sh --docker

# 5. Update CI/CD to use new script
# Replace: make docker-test-run
# With:    cd build && ./run-tests.sh --docker
```

No changes to test code required - everything is backward compatible!

### What Changed

- **Old:** Makefile with `make test-backend`, `make docker-test-run`, etc.
- **New:** Shell script with `./run-tests.sh backend`, `./run-tests.sh --docker`, etc.
- **Benefit:** Better help (`--help`), auto-detection, pytest passthrough, clearer errors

---

## Branch Strategy & CI/CD

### GitHub Actions Test Triggers

Tests run automatically on:
- **Push to `master`** - Production branch (all tests must pass)
- **Push to `dev`** - Development branch (catch bugs before master)
- **Pull requests to `master` or `dev`** - PR validation

**Branch Workflow:**
```
feature/* → dev (PR + tests) → master (PR + tests)
```

**Why dev branch:**
- Catch integration issues before master
- Safe experimentation without breaking production
- Parallel feature development

**Workflow file:** `.github/workflows/test.yml`

### CI Test Configuration

```yaml
# Backend tests only (frontend tests via Vitest/Playwright in future)
run: pytest app/tests/ -v --tb=short --ignore=app/tests/frontend/

# Mock mode by default (fast, no API tokens needed)
env:
  LIVE_API_TESTS: 0
```

---

## Ephemeral Test Environments

### tmpfs Volumes for Test Isolation

**What:** Test data stored in RAM (in-memory filesystem), auto-cleanup on exit

**Configuration:** `build/docker-compose.test.yml`

```yaml
volumes:
  test-data:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=500m,mode=1777  # 500MB limit, world-writable
```

**Benefits:**
- ✅ **Automatic cleanup** - No manual `docker volume rm` needed
- ✅ **Fastest I/O** - RAM-based storage (~10x faster than disk)
- ✅ **No disk accumulation** - Prevents test data filling disk over time
- ✅ **True ephemeral** - Lost on container exit (acceptable for tests)

**Limitations:**
- 500MB size limit (sufficient for test DBs, covers, logs)
- Data lost on system crash (not a problem for ephemeral tests)

**Usage:**
```bash
# Run tests - tmpfs volume created automatically
cd build && ./run-tests.sh --docker

# Container exits, tmpfs volume destroyed automatically
# No cleanup needed!
```

**Why not persistent volumes:**
- Test data should not persist between runs
- Prevents "dirty" test environments
- Faster test execution
- No manual cleanup required

---

## Future Frontend Testing

### Current State (Backend Only)

Frontend E2E tests exist but are **not run in CI**:
- `app/tests/frontend/` - 4 Selenium test files
- Skipped in GitHub Actions via `--ignore=app/tests/frontend/`
- Can run locally: `cd build && ./run-tests.sh frontend`

### Planned Migration: Vitest + Playwright

**Why migrate:**
- Selenium tests slow (~30s+ per test)
- Chromium integration complex (100MB+ in Docker)
- Modern frontend needs modern testing tools

**Future stack:**
- **Vitest** - Unit/component tests for Vue 3 SPA
- **Playwright** - E2E browser automation (faster than Selenium)
- **@testing-library/vue** - Component testing best practices

**When to implement:**
- After Vue 3 migration complete
- When frontend features stabilize
- When team bandwidth allows

**Preparation:**
- Workflow structured for easy frontend test addition
- Can add matrix job for frontend tests later
- Documentation in place for future contributors

---

## Standalone Test Scripts

### abs_providers_integration.py

**What:** Standalone CLI tool for testing ABS metadata providers

**Location:** `app/tests/abs_providers_integration.py` (not collected by pytest)

**Usage:**
```bash
# Run directly (not via pytest)
python app/tests/abs_providers_integration.py --help

# Example: Test all providers
python app/tests/abs_providers_integration.py --test-all
```

**Why not a pytest test:**
- Has CLI argument parsing (argparse)
- Designed for manual interactive testing
- Has `if __name__ == '__main__'` entry point
- Would fail pytest collection with ERROR status

**Note:** Renamed from `test_abs_providers.py` to prevent pytest collection

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

**Use Ephemeral Environments (tmpfs) For:**
- CI/CD pipelines (GitHub Actions)
- Ensuring clean test state
- Preventing disk accumulation
- Maximum test performance

**Both modes use the same test suite** - pick the right tool for the task!
