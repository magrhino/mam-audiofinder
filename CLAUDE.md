# CLAUDE.md - AI Assistant Guide for MAM Audiobook Finder

## Project Overview

**MAM Audiobook Finder** is a lightweight web application for searching MyAnonamouse audiobooks, adding them to qBittorrent, and importing completed downloads into Audiobookshelf. Personal use tool with zero authentication - Docker-first deployment, Vue 3 SPA with FastAPI backend.

**Repository Name:** shelfarr (historical name, project is MAM Audiobook Finder)

## Tech Stack

**Backend:** Python 3.12, FastAPI 0.4.0, Uvicorn, SQLite (SQLAlchemy), httpx (async HTTP)
**Frontend:** Vue 3.4.21 (Composition API), Vue Router 4.3.0, Vite 5.1.6, NaiveUI 2.43.2, @vueuse/core 14.0.0
**Infrastructure:** Docker (multi-stage builds), Docker Compose
**Testing:** pytest (223+ test functions), Selenium (integrated Chromium), dual-mode API testing (mock/live), Makefile automation

## Codebase Structure

```
shelfarr/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # FastAPI bootstrap, logging, DB init
│   ├── config.py                 # Environment configuration
│   ├── db/
│   │   ├── db.py                 # SQLAlchemy engines & migrations
│   │   └── migrations/           # SQL migration files (001-013)
│   ├── abs/                      # New ABS integration package
│   │   ├── __init__.py           # Exports AbsClient, AbsConfig, models
│   │   ├── client.py             # Async httpx client
│   │   ├── config.py             # Env-var config wrapper
│   │   ├── models.py             # Pydantic models for API responses
│   │   ├── library_cache.py      # SQLite-backed library cache with sync
│   │   └── matching.py           # Title/author/ASIN matching logic
│   ├── abs_client.py             # Compatibility shim (wraps app.abs.AbsClient)
│   ├── hardcover_client.py       # Hardcover GraphQL API client (~920 lines)
│   ├── covers.py                 # CoverService class (~350 lines)
│   ├── qb_client.py              # qBittorrent API helpers
│   ├── torrent_helpers.py        # Torrent state mapping & fuzzy matching
│   ├── mam_cache.py              # MAM search result caching (5-min TTL)
│   ├── utils.py                  # Filesystem utilities (sanitize, hardlink, etc.)
│   ├── routes/                   # API endpoints
│   │   ├── __init__.py
│   │   ├── basic.py              # Health, config, SPA serving
│   │   ├── search.py             # MAM search integration
│   │   ├── history.py            # History CRUD operations
│   │   ├── qbittorrent.py        # Torrent management
│   │   ├── import_route.py       # Import workflow with verification
│   │   ├── showcase.py           # Grouped search results
│   │   ├── series.py             # Hardcover series discovery
│   │   ├── covers_route.py       # Cover serving endpoint
│   │   ├── logs_route.py         # Application logs endpoint
│   │   └── abs_route.py          # ABS library sync management
│   ├── static/
│   │   ├── dist/                 # Vue build output (gitignored, generated)
│   │   └── js/                   # ⚠️ LEGACY - scheduled for removal
│   │       ├── core/             # api.js, utils.js (reused by Vue via aliases)
│   │       └── services/         # coverLoader.js
│   └── tests/                    # Test suite (24+ test files)
│       ├── conftest.py           # Shared fixtures + dual-mode auto-patching
│       ├── mocks/                # Mock implementations (hardcover_mock.py)
│       ├── fixtures/             # Test fixtures (JSON API responses)
│       ├── scripts/              # Test utilities (capture_fixtures.py)
│       ├── abs_providers_integration.py  # Standalone ABS provider testing tool
│       ├── test_*.py             # Backend tests (16+ files)
│       └── frontend/             # Selenium E2E tests (4 files)
├── build/                        # Build tooling & dependencies
│   ├── Dockerfile                # Multi-stage build (Node 20 + Python 3.12)
│   ├── Makefile                  # Test & build automation
│   ├── docker-compose.test.yml   # Test container configuration
│   ├── requirements.txt          # Python production dependencies
│   ├── requirements-dev.txt      # Python dev/test dependencies
│   ├── validate_env.py           # Environment validation script
│   └── frontend/                 # Vue 3 SPA source
│       ├── package.json          # Node dependencies
│       ├── vite.config.js        # Vite build configuration
│       ├── index.html            # SPA entry point
│       ├── src/
│       │   ├── main.js           # Vue app entry point
│       │   ├── App.vue           # Root component
│       │   ├── router/
│       │   │   └── index.js      # Vue Router config (5 routes)
│       │   ├── views/            # Page-level components
│       │   │   ├── SearchView.vue
│       │   │   ├── HistoryView.vue
│       │   │   ├── ShowcaseView.vue
│       │   │   ├── LogsView.vue
│       │   │   └── SeriesView.vue
│       │   ├── components/       # Reusable components (~17 files)
│       │   │   ├── NavBar.vue
│       │   │   ├── HealthIndicator.vue
│       │   │   ├── ResultRow.vue
│       │   │   ├── HistoryRow.vue
│       │   │   ├── ShowcaseCard.vue
│       │   │   ├── GlassSearchBar.vue
│       │   │   ├── CoverImage.vue
│       │   │   └── icons/        # SVG icon components
│       │   ├── composables/      # Vue composables
│       │   │   ├── useApi.js
│       │   │   ├── useCoverLoader.js
│       │   │   ├── useHistoryLiveUpdates.js
│       │   │   └── naive/        # NaiveUI table configs
│       │   ├── styles/           # Global styles
│       │   │   └── global.css    # CSS custom properties, resets
│       │   ├── theme/            # Theme configuration
│       │   │   └── naive.js      # NaiveUI theme overrides
│       │   └── uno.config.js     # UnoCSS configuration
│       └── static/               # Static assets (if any)
├── docs/                         # Documentation
│   ├── CLAUDE.md                 # AI assistant guide (this file)
│   ├── BACKEND.md                # Technical implementation details
│   ├── TESTING.md                # Testing guide & troubleshooting
│   ├── VUE_MIGRATION.md          # Vue 3 migration documentation
│   └── documentation/            # Screenshots & user guides
├── docker-compose.yml            # Production deployment
├── env.example                   # Configuration template
└── README.md                     # User-facing documentation
```

**Important Notes:**
- Frontend source is in `build/frontend/src/`, not at root level
- Built Vue assets are output to `app/static/dist/` during Docker build
- ⚠️ **Legacy JS in `app/static/js/` is deprecated** - Do not extend. Migrate to Vue composables before removal.
- UnoCSS is the primary styling system - no legacy CSS files remain

## Architecture & Data Flow

### Request Flow

1. **Frontend:** Vue 3 SPA (build/frontend/src/) → Vue Router (client-side)
2. **Backend:** FastAPI routes (app/routes/) → Python services
3. **External Services:** MAM API, qBittorrent WebUI, Audiobookshelf API, Hardcover GraphQL API
4. **Storage:** SQLite (history.db, covers.db), filesystem (imports, covers)

### Key Workflows

**Search:**
User Input → POST /search → MAM API (5-min cache) → ABS Cover Fetch → Library Check → Display Results

**Add to qBittorrent:**
User Click → POST /add → Fetch .torrent file → qBittorrent API → Tag with MAM ID → Save to history.db

**Import:**
POST /import → Validate Paths → Analyze Structure → Copy/Link/Move Files → Wait for metadata.json → **Verify (3 retries)** → Update DB with verification status

**Verification:**
Check ABS library → Score match (ASIN/ISBN=200pts, Title=100pts, Author=50pts) → Return verified/mismatch/not_found/unreachable

**Cover Cache:**
Check covers.db → If miss: ABS API → Download image → Save to /data/covers/ → Auto-cleanup/healing when exceeding size limit

**Series Discovery:**
POST /api/series/search → Hardcover GraphQL API → Cache results (5-min) → Display with metadata

**Series Books Load (Fast Path):**
GET /api/series/{id}/books (enrich_mode=immediate) → Fetch basic book list → Return immediately → Background: Fetch covers + library check (no audiobook metadata)

**Series Audiobook Metadata (On-Demand):**
User clicks "🎧 Fetch Audiobook Info" → POST /api/series/{id}/books/fetch-audio → Hardcover advanced search (all books) → Extract has_audiobook/audio_seconds → Save to covers.db → Update UI with badges

For detailed backend architecture, see [BACKEND.md](BACKEND.md).

## Key Modules

### Backend Core

**`main.py` (73 lines):**
Logging setup, DB init, FastAPI app creation, route registration, static file serving

**`config.py` (84 lines):**
Environment variable parsing with defaults, validation

**`db/db.py` (200 lines):**
SQLAlchemy engines (history.db, covers.db), smart migration system with per-statement error handling

**`abs/` package:**
New modular ABS integration architecture (replaces monolithic abs_client_legacy.py):
- `abs/client.py` - Async AbsClient with connection pooling, semaphore limiting (10 concurrent)
- `abs/config.py` - AbsConfig dataclass for environment configuration
- `abs/models.py` - Pydantic models (LibraryItem, VerificationResult, CoverResult, LibrarySyncStatus)
- `abs/library_cache.py` - SQLite-backed LibraryCache with TTL-aware sync (replaces in-memory cache)
- `abs/matching.py` - Scoring logic for title/author/ASIN matching (ASIN/ISBN=200pts, Title=100pts, Author=50pts)

**`abs_client.py`:**
Compatibility shim wrapping `app.abs.AbsClient` for backward compatibility.
All existing routes use this shim transparently.
Key methods (mapped to new client):
- `test_connection()` → `AbsClient.ping()`
- `check_library_items()` → `AbsClient.check_library_presence()`
- `verify_import()` → `AbsClient.verify_import()`
- `fetch_cover()` → `AbsClient.fetch_cover()`
- `fetch_item_details()` → `AbsClient.fetch_item_details()`

**`hardcover_client.py` (~920 lines):**
GraphQL API client for series discovery:
- `search_series()` - Series search with caching (5-min TTL)
- `list_series_books()` - Get books in a series
- `search_book_by_title()` - Book search for metadata
- Rate limiting (60 req/min), retry logic

**`covers.py` (~350 lines):**
CoverService class: Local caching in /data/covers/, auto-cleanup when exceeding MAX_COVERS_SIZE_MB, auto-healing for missing files

**`torrent_helpers.py`:**
State mapping (qBittorrent status → app status), path validation, MAM ID extraction, fuzzy title/author matching

**`utils.py` (206 lines):**
`sanitize()`, `next_available()`, `extract_disc_track()`, `try_hardlink()`, filesystem utilities

**`mam_cache.py`:**
In-memory MAM search result caching with 5-minute TTL

### Backend Routes (FastAPI)

All routes are `async def` endpoints:

- `basic.py` - GET / (serves Vue SPA index.html), /health, /config
- `search.py` - POST /search (MAM API integration with caching)
- `history.py` - GET /api/history, DELETE /api/history/{id}, POST /api/history/{id}/verify
- `qbittorrent.py` - GET /qb/torrents, GET /qb/torrent/{hash}/tree, POST /add
- `import_route.py` - POST /import (with verification workflow)
- `showcase.py` - GET /api/showcase (grouped search results by normalized title)
- `series.py` - POST /api/series/search, GET /api/series/{id}/books (Hardcover integration, default `enrich_mode=immediate`, optional `include_audio_meta`), POST /api/series/{id}/books/fetch-audio (on-demand audiobook metadata)
- `covers_route.py` - GET /covers/{filename} (serve cached covers)
- `logs_route.py` - GET /api/logs (application logs)
- `abs_route.py` - POST /api/abs/sync (force library sync), GET /api/abs/status (sync status)

### Frontend Architecture (Vue 3)

**Single-Page Application (SPA):**
Built with Vite, all routing handled client-side by Vue Router

**Build Process:**
Vite dev server (:5173) with HMR → `npm run build` → outputs to `app/static/dist/`

**Composition API:**
All components use `<script setup>` syntax with reactive refs

**Router (5 routes):**
/, /history, /showcase, /logs, /series (lazy-loaded views)

**Views:**
SearchView, HistoryView, ShowcaseView, LogsView, SeriesView

**Components:**
NavBar, HealthIndicator, ResultRow, HistoryRow, ShowcaseCard, SeriesTable, GlassSearchBar, CoverImage, ActionButton, StatusBadge, icon components

**Composables:**
- `useApi()` - API wrapper (reuses legacy `app/static/js/core/api.js`)
- `useCoverLoader()` - Lazy image loading with IntersectionObserver
- `useHistoryLiveUpdates()` - Real-time history updates (auto-refresh)
- `useMAMSearchDataTable()` - NaiveUI table configuration with responsive 3-column-set strategy, native expansion for mobile, no scroll-x
- `useSeriesDataTable()` - NaiveUI table configuration for Hardcover series results with responsive column filtering
- `useCover()` - Cover URL fetching with in-memory caching (5-min TTL, LRU eviction)
- `useBreakpoints()` - **Centralized responsive breakpoints** (mobile: 0-767px, tablet: 768-1023px, desktop: 1024px+) - Single source of truth for all breakpoint logic

**Utilities:**
- `sanitizeDescription()` - DOMPurify-based HTML sanitization for descriptions (strips `<p>` tags, allows safe inline formatting)

**Styling System:**
- **UnoCSS** - Atomic CSS engine with preset utilities and custom shortcuts (uno.config.js)
- **Global CSS** - CSS custom properties and resets in `build/frontend/src/styles/global.css`
- **Component-scoped styles** - `<style scoped>` blocks in Vue components
- **NaiveUI theme** - Theme overrides in `build/frontend/src/theme/naive.js`
- **Design tokens** - Dark theme with maroon accents (#500000), glassmorphism effects, system fonts
- **No legacy CSS** - `app/static/css/` has been removed entirely

**Legacy Integration (Temporary):**
⚠️ Vue components currently import `app/static/js/core/api.js` for backend communication. Vite configured with aliases (@core, @services) to access these legacy modules. **Do not extend** - migrate logic to Vue composables instead.

## Database Schemas

### history.db

```sql
CREATE TABLE history (
  id INTEGER PRIMARY KEY,
  mam_id TEXT, title TEXT, author TEXT, narrator TEXT, dl TEXT,
  added_at TEXT DEFAULT (datetime('now')),

  -- qBittorrent tracking
  qb_status TEXT, qb_hash TEXT,

  -- Import tracking
  imported_at TEXT,

  -- Audiobookshelf integration (Migration 004)
  abs_item_id TEXT,
  abs_cover_url TEXT,
  abs_cover_cached_at TEXT,

  -- Verification system (Migration 006)
  abs_verify_status TEXT,  -- 'verified', 'mismatch', 'not_found', 'unreachable', 'not_configured'
  abs_verify_note TEXT,

  -- Descriptions (Migration 007)
  abs_description TEXT,
  abs_metadata TEXT,       -- JSON blob
  abs_description_source TEXT  -- 'abs', 'hardcover', 'none'
);

CREATE TABLE torrent_books (
  qb_hash TEXT PRIMARY KEY,
  history_id INTEGER,
  mam_id TEXT,
  title TEXT,
  -- Multi-book torrent support (Migration 010)
  FOREIGN KEY (history_id) REFERENCES history(id)
);
```

**Migrations:** 001 (initial), 002 (author/narrator), 003 (imported_at), 004 (ABS columns), 006 (verification), 007 (descriptions), 010 (multi-book support)

### covers.db

```sql
CREATE TABLE covers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mam_id TEXT UNIQUE NOT NULL,
  title TEXT, author TEXT,
  cover_url TEXT NOT NULL,
  abs_item_id TEXT,
  local_file TEXT,
  file_size INTEGER,
  fetched_at TEXT DEFAULT (datetime('now')),

  -- Metadata integration (Migration 008)
  abs_description TEXT,
  abs_metadata TEXT,
  abs_metadata_fetched_at TEXT,
  description_source TEXT  -- 'abs', 'hardcover', 'none'
);

CREATE TABLE series_cache (
  series_id TEXT PRIMARY KEY,
  title TEXT,
  author TEXT,
  metadata TEXT,  -- JSON blob (Hardcover series data)
  cached_at TEXT
);
```

**Migrations:** 005 (initial schema), 008 (descriptions), 009 (series_cache)

**Migration System:**
- Smart routing: history table → history.db, covers/series → covers.db
- Idempotent SQL (IF NOT EXISTS patterns)
- Runs automatically on startup
- Per-statement error handling for resilience

## Key Features

### Import Verification
- Automatic verification after import (if ABS configured)
- ASIN/ISBN priority matching (200 points), fuzzy title/author fallback
- 3 retry attempts with exponential backoff (1s, 2s, 4s)
- Status badges in UI: ✓ verified, ⚠ mismatch, ✗ not_found, ? unreachable
- Manual re-verification via "🔄 Verify" button

### Library Visibility
- Green checkmark badges on search/showcase for items already in library
- Batch checking with 5-minute cache (configurable via ABS_LIBRARY_CACHE_TTL)
- Auto-enabled when ABS is configured (or set ABS_CHECK_LIBRARY explicitly)

### Description Fetching
- Fetched from Audiobookshelf during verification (if match score ≥100)
- Fallback to Hardcover API for additional metadata (optional)
- Updates both history.db and covers.db
- Displayed in showcase view with expand/collapse
- Source tracking: 'abs', 'hardcover', or 'none'

### Showcase View
- Groups search results by normalized title (removes articles "The", "A", "An" and punctuation)
- Card-based grid layout with covers and descriptions
- Detail view shows all versions/editions per title
- URL state management (?detail=title-slug)
- Responsive layout with @vueuse/core breakpoints

### Multi-Disc Flattening
- Auto-detects Disc/Disk/CD/Part patterns in folder structure
- Flattens to sequential files (Part 001.mp3, Part 002.mp3, ...)
- Frontend shows before/after preview in import modal
- Controlled by FLATTEN_DISCS env var (default: true)

### Cover Caching
- Separate covers.db database for performance
- Local storage in /data/covers/
- Auto-cleanup when exceeding MAX_COVERS_SIZE_MB (default: 500MB)
- Auto-healing for missing files
- Progressive loading with lazy loading (IntersectionObserver)

### Hardcover Series Discovery
- Optional integration with Hardcover API for series metadata
- GraphQL API with rate limiting (60 req/min) and caching (5-min TTL)
- Limit parameter controls result count (configurable via HARDCOVER_SERIES_LIMIT, default: 20)
- **Note:** Pagination removed (non-functional in Hardcover API)
- **Audiobook Metadata:** Fetching audiobook metadata (has_audiobook, audio_seconds) is opt-in via explicit user action
  - Default series load is fast (covers + library check only, no advanced Hardcover lookups)
  - Users can fetch audiobook metadata on-demand via "🎧 Fetch Audiobook Info" button in SeriesView
  - Metadata persists to covers.db once fetched (duration stored in minutes, audio_seconds in JSON)
  - Green badge (🎧 duration) shown for available audiobooks, red badge (🚫 Audio) for unavailable

## Environment Configuration

See `env.example` for full list with detailed comments.

**Required:**
MAM_COOKIE, QB_URL, QB_USER, QB_PASS, MEDIA_ROOT, DATA_DIR

**Optional (Audiobookshelf):**
ABS_BASE_URL, ABS_API_KEY, ABS_LIBRARY_ID, ABS_VERIFY_TIMEOUT, ABS_CHECK_LIBRARY, ABS_LIBRARY_CACHE_TTL, MAX_COVERS_SIZE_MB

**Optional (Hardcover):**
HARDCOVER_API_TOKEN, HARDCOVER_CACHE_TTL, HARDCOVER_RATE_LIMIT, HARDCOVER_SERIES_LIMIT

**Optional (Behavior):**
IMPORT_MODE (link/copy/move, default: link), FLATTEN_DISCS (default: true), QB_CATEGORY (default: mam-audiofinder), QB_POSTIMPORT_CATEGORY

**Optional (Container):**
APP_PORT (default: 8008), DL_DIR, LIB_DIR, PUID, PGID, UMASK, LOG_MAX_MB, LOG_MAX_FILES

**Critical Path Mapping:**
`MEDIA_ROOT` must be mounted to BOTH this app and qBittorrent containers at consistent paths. Misalignment causes "path not found" import errors.

## Development

### Setup

```bash
# Configure environment
cp env.example .env
# Edit .env with your settings

# Build and run
docker compose up -d --build

# View logs
docker compose logs -f
```

### Making Changes

**Backend:**
Edit Python files → `docker compose up -d --build` → Check logs

**Frontend (Development with HMR):**
```bash
cd build/frontend
npm install
npm run dev  # Vite dev server on :5173 with hot reload
# Edit .vue files → auto-reload
```

**Frontend (Production):**
```bash
cd build/frontend
npm run build  # Build to app/static/dist/
docker compose up -d --build
```

**Environment:**
Edit .env → `docker compose up -d --force-recreate`

### Testing

**Three testing modes - same test suite (223+ tests), different execution strategies:**

#### Dual-Mode Testing (Mock vs Live API)

Hardcover API tests support automatic dual-mode execution:

**Local Tests (Mock by default):**
```bash
cd build/
./run-tests.sh                             # Mock mode - uses JSON fixtures
./run-tests.sh backend                     # Backend only (mock)
./run-tests.sh --live                      # Override to live API mode
```

**Docker Tests (Live by default):**
```bash
cd build/
./run-tests.sh --docker                    # Live mode - hits real APIs
./run-tests.sh --docker backend            # Backend only (live)
./run-tests.sh --docker --mock             # Override to mock mode
```

**Key Features:**
- Same tests run in both modes without code changes
- Mock mode uses pre-recorded JSON fixtures (~200ms per test)
- Live mode validates against real API (~2-5s per test)
- Docker tests use production .env for integration testing
- `@pytest.mark.requires_live` for API-dependent tests
- Automatic client patching via `conftest.py`

#### Local Testing (Development)

Fast iteration with virtual environment:
```bash
cd build/
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
./run-tests.sh backend                     # All backend tests (mock mode)
./run-tests.sh coverage                    # With HTML coverage report
./run-tests.sh backend -- tests/test_verification.py -v   # Specific file
```

#### Container Testing (Integration)

Full Docker integration with ABS/qBittorrent networking (uses production .env, defaults to LIVE API):
```bash
cd build/
./run-tests.sh build                       # Build test container (first time)
./run-tests.sh --docker                    # Full test suite (LIVE mode)
./run-tests.sh --docker backend            # Backend tests only (LIVE)
./run-tests.sh --docker --mock             # Use mock mode in Docker
./run-tests.sh frontend                    # Frontend tests (Selenium, LIVE)
./run-tests.sh shell                       # Debug shell in container
```

**Test Infrastructure:**
- 17 JSON fixtures for Hardcover API (Foundation, Harry Potter, LOTR, etc.)
- Fixture capture scripts:
  - `app/tests/scripts/capture_fixtures.py` (Hardcover)
  - `app/tests/scripts/capture_abs_fixtures.py` (ABS - with automatic sanitization)
- MockHardcoverClient mirrors real client (600+ lines)
- MockABSClient with sanitized test fixtures
- Multi-stage Dockerfile with integrated Chromium for Selenium
- Isolated test data, configurable database paths
- **Automatic fixture sanitization:** ABS fixtures automatically redact URLs, library IDs, item IDs, file paths, and usernames

**Test Coverage:**
Verification, cover caching, descriptions, search, MAM cache, helpers, migrations, multi-book imports, Hardcover series, frontend E2E workflows

See [TESTING.md](TESTING.md) for comprehensive dual-mode guide, troubleshooting, and fixture management.

## Important Patterns

### Error Handling

**Validate early, fail fast for critical operations:**
```python
if not src_root.exists():
    raise HTTPException(status_code=404, detail=f"Source path not found: {src_root}")
```

**Best-effort for non-critical operations:**
```python
try:
    # ... category change ...
except Exception:
    pass  # Don't fail import
```

### Async/Await

- All FastAPI endpoints are `async def` with httpx for HTTP calls
- Database operations use sync SQLAlchemy (no asyncpg)
- Connection pooling and semaphore limiting for external APIs

### Data Sanitization

**Backend:** Always use `sanitize()` from utils.py before filesystem operations
**Frontend:** Always use `escapeHtml()` for user input display

### Responsive Design

**Centralized Breakpoint System (Single Source of Truth):**

All components must use the centralized `useBreakpoints` composable from `build/frontend/src/composables/useBreakpoints.js`:

```javascript
import { useBreakpoints } from '@/composables/useBreakpoints'

// Get reactive breakpoint state
const { isMobile, isTablet, isDesktop } = useBreakpoints()

// Use in computed properties or directly in templates
const showFullDetails = computed(() => isDesktop.value)
```

**Standard Breakpoints (3-tier system):**
- **Mobile:** 0-767px (phones, small tablets)
- **Tablet:** 768-1023px (tablets, small laptops)
- **Desktop:** 1024px+ (laptops, desktops)

**Table Responsive Strategy:**
Tables use a 3-column-set approach with native Naive UI expansion for mobile:
- **Mobile:** Minimal columns (expand + cover + title + action) - users tap expand for details
- **Tablet:** Moderate columns (+ author + narrator + size)
- **Desktop:** Full columns (all fields visible, expand column hidden)

**Key Principles:**
- ❌ **NEVER** use fixed `minWidth` on table columns - let Naive UI auto-size
- ❌ **NEVER** use `scroll-x` prop - tables adapt to container width naturally
- ❌ **NEVER** create local breakpoint definitions - use centralized composable
- ✅ **ALWAYS** use `single-line="false"` on `n-data-table` to allow multi-line cells
- ✅ **ALWAYS** add `w-full max-w-full overflow-x-hidden` to view wrapper divs
- ✅ **ALWAYS** use CSS `clamp()` for responsive font sizing (e.g., `clamp(0.85rem, 1.5vw, 1rem)`)
- Mobile-first approach with progressive column enhancement
- Use CSS media queries for styling, centralized breakpoints for behavior

### Database Migrations

1. Create `app/db/migrations/011_my_change.sql` (next available number)
2. Write idempotent SQL (use IF NOT EXISTS, IF column NOT EXISTS patterns)
3. Runs automatically on next startup
4. Smart routing: history table → history.db, covers/series tables → covers.db
5. Current: 001-010 (10 migrations total)

### Styling & Design

**UnoCSS Approach:**
ShelfArr uses UnoCSS as the primary styling system. UnoCSS is an atomic CSS engine that generates utility classes on-demand.

**Configuration:**
- `build/frontend/uno.config.js` - Defines presets, shortcuts, and custom rules
- `build/frontend/src/styles/global.css` - CSS custom properties, resets, and base styles
- `build/frontend/src/theme/naive.js` - NaiveUI component theme overrides

**Key UnoCSS Shortcuts:**
- `glass-panel` - Premium glassmorphism panel with backdrop blur and border
- `glass-panel-hover` - Hover state with maroon border and enhanced shadow
- `glass-overlay` - Glass overlay with pseudo-element shine effect
- `responsive-title` - Responsive title with word-aware truncation using clamp() (120px-30vw-400px)
- `card` - Glass card container with rounded corners and padding
- `panel` - Simple panel with backdrop blur
- `muted` - Muted text color (#b8b8b8) at 0.9rem
- `heading-1`, `heading-3` - Typography presets

**Styling Priority:**
1. **UnoCSS utilities** - Use for spacing, layout, colors (e.g., `flex`, `p-4`, `bg-gray-900`)
2. **UnoCSS shortcuts** - Custom shortcuts defined in uno.config.js (e.g., `glass-panel`)
3. **Component-scoped styles** - Use `<style scoped>` for component-specific CSS
4. **Global CSS** - Only for CSS custom properties and truly global styles

**Example Component Styling:**
```vue
<template>
  <div class="glass-panel flex flex-col gap-4 p-6">
    <h2 class="text-xl font-semibold">Title</h2>
    <p class="text-gray-400">Description</p>
  </div>
</template>

<style scoped>
/* Only for styles that can't be expressed with UnoCSS utilities */
.custom-gradient {
  background: linear-gradient(to bottom, var(--maroon-dark), transparent);
}
</style>
```

**Design Tokens (CSS Custom Properties in global.css):**
- `--maroon-primary: #500000` - Primary brand color
- `--maroon-light: #800000` - Lighter maroon variant
- `--maroon-dark: #300000` - Darker maroon variant

**⚠️ DO NOT:**
- Reference `app/static/css/main.css` or `app/static/css/legacy.css` (removed)
- Create new CSS files outside of `build/frontend/src/styles/`
- Use inline styles when UnoCSS utilities suffice
- Extend legacy CSS patterns

**Adding New Styles:**
1. Check if UnoCSS preset utilities cover your need
2. Add custom shortcut to uno.config.js if pattern repeats
3. Use scoped styles for component-specific CSS
4. Add to global.css only for CSS custom properties or true globals

## Common Tasks

### Add Backend Endpoint

1. Create route in `app/routes/my_feature.py`
2. Register in `app/routes/__init__.py`
3. Add method to `app/static/js/core/api.js` (legacy, still used by Vue via aliases)
4. Call from Vue composable or component using `useApi()`
5. Test with pytest and manual verification

### Add Vue View/Component

1. Create `.vue` file in `build/frontend/src/views/` or `build/frontend/src/components/`
2. Use `<script setup>` with Composition API
3. Add route to `build/frontend/src/router/index.js` (if view)
4. Import and use in parent component (if component)
5. Test with `npm run dev` in build/frontend/

### Add Environment Variable

1. Add to `env.example` with descriptive comment
2. Add to `app/config.py` with default value
3. Add validation in `build/validate_env.py` if required
4. Document in README.md if user-facing
5. Update this file if it affects AI assistant behavior

### Add Database Column

Create `app/db/migrations/011_add_field.sql`:
```sql
ALTER TABLE history ADD COLUMN new_field TEXT;
```

Restart container - migration runs automatically. Verify in logs.

### Debug Import Issues

**Path not found:**
Check MEDIA_ROOT mapping in docker-compose.yml, verify qBittorrent save_path matches DL_DIR

**Permission denied:**
Check PUID/PGID match host user (`id -u` and `id -g`), verify UMASK=0002

**Files not copied:**
Check AUDIO_EXTS filter in utils.py, add debug logging

**Verification fails:**
Check ABS_BASE_URL reachable from container, verify API key valid, check metadata.json was created

## Debugging

```bash
# Real-time logs
docker compose logs -f

# Container shell access
docker exec -it mam-audiofinder bash

# Check permissions
docker exec -it mam-audiofinder ls -la /media /data

# Database inspection
docker exec -it mam-audiofinder sqlite3 /data/history.db
sqlite> .schema history
sqlite> SELECT * FROM history ORDER BY added_at DESC LIMIT 5;
sqlite> .exit

# Check ABS connectivity
docker exec -it mam-audiofinder curl http://audiobookshelf:13378/ping
```

**Frontend Debugging:**
DevTools (F12) → Console for errors, Network tab for API calls, Vue DevTools extension for component inspection

## Security

**⚠️ WARNING: ZERO AUTHENTICATION**

**Safe Usage Only:**
- Behind VPN (Tailscale, WireGuard, Headscale)
- Behind authenticated reverse proxy (Authelia, Authentik, Caddy with auth)
- Trusted local network only (with firewall rules)
- **NEVER exposed to public internet**

**Credentials:** MAM_COOKIE, qBittorrent credentials, API keys stored in env vars only (never committed to git)

## Code Style

**Python:**
PEP 8 compliance, async endpoints, HTTPException for user errors, minimal inline docstrings (prefer self-documenting code), type hints encouraged but not enforced

**Vue:**
Composition API with `<script setup>`, camelCase for variables/functions, PascalCase for components, reactive refs, composables for reusable logic

**JavaScript:**
ES6+ modules, async/await, camelCase for functions/variables, UPPER_SNAKE_CASE for constants

**CSS/Styling:**
UnoCSS atomic utilities preferred, kebab-case for custom classes, CSS custom properties in global.css, component-scoped styles, dark theme with maroon accents

**Logging:**
Emoji prefixes (✅ success, ❌ error, ⚠️ warning, 🔍 debug, 📚 library, 🔄 retry, 📦 cache)

## AI Assistant Guidelines

### Legacy Asset Policy

**⚠️ CRITICAL: `app/static/js/` is DEPRECATED**

The legacy JavaScript modules in `app/static/js/` are scheduled for removal. They represent the pre-Vue architecture.

**DO NOT:**
- Add new files to `app/static/js/`
- Extend existing legacy modules
- Import legacy modules in new Vue components
- Reference these modules in documentation

**DO:**
- Migrate logic from legacy modules to Vue composables in `build/frontend/src/composables/`
- Use `useApi()` composable for API calls (eventual replacement for api.js)
- Document migration path when working with legacy code
- Plan incremental migration to avoid breaking changes

**Current Legacy Dependencies:**
- `app/static/js/core/api.js` - API wrapper (used via useApi composable)
- `app/static/js/core/utils.js` - Utilities (migrate to composables)
- `app/static/js/services/coverLoader.js` - Cover loading (partially migrated to useCoverLoader)

**Migration Strategy:**
1. Identify legacy import in Vue component
2. Create equivalent composable in `build/frontend/src/composables/`
3. Update component to use new composable
4. Remove legacy import
5. Mark legacy file for deletion once all references removed

### Making Changes

1. **Read existing code first** to understand patterns and conventions
2. **Follow existing patterns** (don't introduce new architectures without discussion)
3. **Test thoroughly** (automated tests + manual verification in Docker)
4. **Write descriptive commits** ("why" not "what") - see recent commits for style
5. **Update documentation** if architecture or significant functionality changes
6. **Respect the legacy policy** - migrate, don't extend

### Adding Features

1. Check if new environment variables needed → update env.example and config.py
2. Update README.md for user-facing features
3. **Always sanitize user input** (filesystem operations, SQL queries, HTML output)
4. Provide clear, actionable error messages (not generic "something went wrong")
5. Test edge cases (missing ABS, expired cookie, permission errors, network timeouts)
6. Consider mobile responsiveness for frontend features

### Debugging Approach

1. **Check logs first** (`docker compose logs -f`)
2. Verify path mappings (MEDIA_ROOT alignment between containers)
3. Check PUID/PGID permissions (`docker exec ... ls -la /media`)
4. Test API directly with curl before debugging frontend
5. Inspect SQLite database for data consistency
6. Enable debug logging if needed (modify logging level in main.py)

### Refactoring

1. Keep changes small and focused (one logical change per commit)
2. Preserve existing behavior (regression testing critical)
3. Verify no test failures after refactoring
4. Document architecture changes in this file and BACKEND.md
5. Consider backwards compatibility for database migrations

### Testing Requirements

1. Add unit tests for new backend logic (pytest)
2. Add integration tests for API endpoints if they interact with external services
3. **For Hardcover API tests:** Capture fixtures in live mode, verify in both modes
   - Add test using `hardcover_client` fixture (works in both modes automatically)
   - Capture fixture: `HARDCOVER_API_TOKEN=xxx python app/tests/scripts/capture_fixtures.py`
   - Verify mock mode: `pytest app/tests/test_yourfeature.py -v`
   - Verify live mode: `LIVE_API_TESTS=1 pytest app/tests/test_yourfeature.py -v`
4. **For ABS API tests:** Capture fixtures with automatic sanitization
   - Capture fixture: `ABS_BASE_URL=xxx ABS_API_KEY=xxx ABS_LIBRARY_ID=xxx python app/tests/scripts/capture_abs_fixtures.py`
   - All sensitive data (URLs, IDs, paths, usernames) automatically sanitized with placeholders
   - Safe to commit fixtures to version control
5. Manual E2E testing for frontend features
6. Run full test suite before pushing (`make test-mock` or `make docker-test-run`)
7. Aim for 70%+ code coverage on new code

## Project Philosophy

**Design Principles:**
- **Simplicity over features** - Don't add complexity without clear user benefit
- **Personal use over production** - Optimize for single-user, trusted network usage
- **Clear errors over silent failures** - User should know what went wrong and how to fix it
- **Pragmatic over perfect** - Working solution beats theoretical ideal

**Non-Goals:**
- Enterprise deployment (no multi-tenancy, high availability, load balancing)
- Advanced authentication/authorization (use network-level security instead)
- Public API exposure (no rate limiting, API versioning, etc.)
- Mobile native apps (responsive web UI sufficient)
- Real-time collaboration (single-user focus)

**Maintenance Focus:**
- Bug fixes over new features
- Preserve existing functionality
- Avoid over-engineering
- Keep dependencies minimal and updated
- Docker-first deployment (no native installation support)

---

**For Technical Implementation Details:** See [BACKEND.md](BACKEND.md)
**For Testing Guide:** See [TESTING.md](TESTING.md)
**For Vue Migration Notes:** See [VUE_MIGRATION.md](VUE_MIGRATION.md)

*Update this document when making significant architecture or functionality changes. Keep it accurate and remove outdated information.*
