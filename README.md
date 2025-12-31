<p align="center">
  <img src="app/static/icon.png" width="180" alt="ShelfArr logo" />
</p>

<h1 align="center">ShelfArr</h1>

<p align="center">
  Audiobook-first automation for MyAnonamouse → qBittorrent → Audiobookshelf.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#how-to-use">How to Use</a> •
  <a href="#troubleshooting">Troubleshooting</a> •
  <a href="docs/">Docs</a>
</p>

ShelfArr is an audiobook-first management app for searching MyAnonamouse (MAM), sending torrents to qBittorrent, and importing completed downloads into Audiobookshelf.

Originally forked from `raygan/mam-audiofinder` and intended to remain upgrade-compatible where practical.

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [How to Use](#how-to-use)
- [Architecture Overview](#architecture-overview)
- [Troubleshooting](#troubleshooting)
- [Logs](#logs)
- [Technical Documentation](#technical-documentation)
- [Requirements](#requirements)
- [License](#license)

## Features
- **Vue 3 SPA:** Search, History (imports + verification), Showcase, Logs, and Series.
- **Search MAM:** Find audiobooks by title/author/narrator with rich results.
- **Add to qBittorrent:** One-click torrent submissions with category support.
- **Import to Audiobookshelf:** Link/copy/move downloads, optional disc flattening, and verification.
- **Series discovery:** Explore series metadata via Hardcover.

## Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/magrhino/shelfarr.git
cd shelfarr
cp env.example .env
```

### 2. Edit `.env`

At minimum, set your port, user/permissions, MAM + qBittorrent details, and host mount paths:

```bash
APP_PORT=8008

PUID=1000
PGID=1000
UMASK=0002

# --- MAM and qBittorrent credentials ---
MAM_COOKIE=mam_id=your_cookie_here
QB_URL=http://qbittorrent:8080
QB_USER=youruser
QB_PASS=yourpass

# Recommended
QB_CATEGORY=shelfarr

# --- host mounts (adjust to your system) ---
MEDIA_ROOT=/path/to/media
DATA_DIR=/path/to/appdata/shelfarr/data
```

Tip: you can paste the full Cookie header, a `mam_id=...` cookie, or a single token; ShelfArr normalizes it.

### 3. Create the Docker Network (if needed)

`docker-compose.yml` references an external network named `nginx-network`. If you don’t use it, either create it:

```bash
docker network create nginx-network
```

…or edit `docker-compose.yml` to remove the `networks:` section.

### 4. Start the Container
```bash
docker compose up -d --build
```

### 5. Open the Web UI
Visit `http://127.0.0.1:8008` (or whatever you set in `APP_PORT`).

If you set `ABS_BASE_URL`, ShelfArr will prompt you to log in with your Audiobookshelf credentials to enable covers, library checks, and verification.

## Configuration

All configuration is done via environment variables (see `env.example`). Common ones are listed here.

### Required

| Variable | Description |
|----------|-------------|
| `APP_PORT` | Host port to expose the web UI on (maps to container port 8080) |
| `PUID` | Host user ID to run the container as |
| `PGID` | Host group ID to run the container as |
| `UMASK` | File creation mask (octal string, e.g. `0002`) |
| `MEDIA_ROOT` | Host path mounted to `/media` in the container (should include your downloads + library paths or hardlinks will not work)|
| `DATA_DIR` | Host path mounted to `/data` (databases, logs, cover cache) |
| `QB_URL` | qBittorrent WebUI URL |
| `QB_USER` | qBittorrent username |
| `QB_PASS` | qBittorrent password |
| `MAM_COOKIE` | MAM cookie/token used for searching (`mam_id=...` or full cookie header) |

### Audiobookshelf (Optional)
While optional it is recommended to configure ABS_BASE_URL and ABS_ADMIN_USER for full functionality.

| Variable | Default | Description |
|----------|---------|-------------|
| `ABS_BASE_URL` | *(none)* | Base URL for Audiobookshelf (enables login + covers + verification) |
| `ABS_ADMIN_USER` | *(none)* | ABS username treated as “admin” for library-management actions |
| `MAX_COVERS_SIZE_MB` | `500` | Max disk space for cached covers (0 = no limit; direct-fetch-only is not recommended) |
| `ABS_VERIFY_TIMEOUT` | `10` | Timeout (seconds) for import verification |
| `ABS_CHECK_LIBRARY` | `true` when ABS configured | Show “already in library” indicators |
| `ABS_LIBRARY_CACHE_TTL` | `300` | Cache TTL (seconds) for library presence checks |

### Import Behavior (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `IMPORT_MODE` | `link` | `link` (hardlink), `copy`, or `move` |
| `FLATTEN_DISCS` | `true` | Flatten multi-disc audiobooks into a single sequence |
| `DL_DIR` | `/media/torrents` | In-container downloads path |
| `LIB_DIR` | `/media/Books/Audiobooks` | In-container library path |
| `QB_CATEGORY` | `shelfarr` | Category assigned to new torrents |
| `QB_POSTIMPORT_CATEGORY` | *(empty)* | Category to set after import (empty = none/clear) |


### Hardcover (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `HARDCOVER_API_TOKEN` | *(none)* | Hardcover GraphQL token for series discovery |
| `HARDCOVER_CACHE_TTL` | `300` | Cache TTL (seconds) for series lookups |
| `HARDCOVER_RATE_LIMIT` | `60` | Requests per minute (Hardcover API limit: 60/min) |
| `HARDCOVER_SERIES_LIMIT` | `20` | Default number of series results to fetch |
A hardcover api key can be obtained by creating a [free hardcover account](https://hardcover.app/account/api).
## How to Use

### Search for Audiobooks
1. Open the **Discover** view.
2. Enter title, author, or narrator.
3. Add results to qBittorrent or open details.

### Import to Audiobookshelf
#### You can either anually import or auto import
a) Auto import
1. Go to Gear Icon and toggle auto import feature on.

b) Manual Import
1. Open the **History** view.
2. Wait for qBittorrent to finish the download.
3. Click **Import** and confirm.
4. If ABS is configured and you’re logged in, ShelfArr verifies the import automatically and when you click verify.

## Architecture Overview
- **SPA entrypoint:** Vite builds land in `app/static/dist/` with `index.html` served for all non-API routes. FastAPI mounts `/static` and provides the SPA fallback in `app/main.py`.
- **Backend role:** FastAPI exposes API routes under `app/routes/` (`/search`, `/history`, `/import`, `/qb`, `/logs`, `/series`, `/covers`, `/config`, `/health`) and defers HTML to the SPA index.
- **Routing:** Vue Router runs in history mode with a catch-all redirect for unknown paths. Deep links and refreshes resolve through the FastAPI fallback.
- **Styling system:** UnoCSS atomic utilities with custom shortcuts (`build/frontend/uno.config.js`), global CSS variables in `build/frontend/src/styles/global.css`, and Naive UI theme overrides in `build/frontend/src/theme/naive.js`.

## Troubleshooting
- **Docker compose fails with “network nginx-network declared as external, but could not be found”:** Run `docker network create nginx-network` or remove the external network from `docker-compose.yml`.
- **Import fails with “path not found”:** Confirm your `/media` mount contains both the downloads and library directories and that `DL_DIR`/`LIB_DIR` match your structure.
- **Permission errors:** Set `PUID`, `PGID`, and `UMASK` to match your host and rebuild the container.
- **MAM searches fail:** Refresh your MAM cookie and restart the container.
- **ABS features disabled:** Set `ABS_BASE_URL`, restart, then log in via the UI.

## Logs
- In-app: open the SPA **Logs** view at `/logs` (rendered by Vue, fed by API).
- CLI: `docker compose logs -f` or view log files inside the mounted `DATA_DIR`.

## Technical Documentation
- `docs/BACKEND.md` – FastAPI architecture, routing, dependencies, and SPA fallback behavior.
- `docs/FRONTEND.md` – Vue SPA architecture, routing map, components, styling, and Naive UI theme.
- `docs/TESTING.md` – Testing guide: local and container-based testing, Selenium integration.

## Requirements
- Docker & Docker Compose
- qBittorrent with WebUI enabled
- Valid MAM session cookie
- (Optional) Audiobookshelf instance for covers and verification

## License
MIT - Provided as-is, no warranty. Personal-use tooling only.
