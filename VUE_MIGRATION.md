# Vue 3 Migration Guide

## Overview

This branch migrates the MAM Audiobook Finder from Jinja2 templates + build-free Vue components to a full **Vue 3 Single File Component (SFC)** architecture with Vite build system.

## What Changed

### Frontend Architecture

**Before:**
- Jinja2 templates (`app/templates/*.html`)
- Build-free Vue components in JS files (`app/static/js/vue/components/*.js`)
- CDN-loaded Vue runtime
- Multi-page app with separate page scripts

**After:**
- Vue 3 SPA (Single Page Application)
- Single File Components (`.vue` files with `<template>/<script>/<style>` blocks)
- Vite build system for optimized production bundles
- Vue Router for client-side routing
- All pages rendered by Vue

### Directory Structure

```
mam-audiofinder/
├── src/                          # NEW: Vue source files
│   ├── main.js                   # Vue app entry point
│   ├── App.vue                   # Root component
│   ├── components/               # Reusable components
│   │   ├── NavBar.vue
│   │   ├── HealthIndicator.vue
│   │   ├── ActionButton.vue
│   │   ├── StatusBadge.vue
│   │   ├── ResultRow.vue
│   │   ├── HistoryRow.vue
│   │   ├── ShowcaseCard.vue
│   │   └── SeriesTable.vue
│   ├── views/                    # Page-level components
│   │   ├── SearchView.vue
│   │   ├── HistoryView.vue
│   │   ├── ShowcaseView.vue
│   │   ├── LogsView.vue
│   │   └── SeriesView.vue
│   ├── composables/              # Vue composables
│   │   ├── useApi.js
│   │   └── useCoverLoader.js
│   └── router/                   # Vue Router config
│       └── index.js
├── index.html                    # NEW: SPA entry HTML
├── vite.config.js                # NEW: Vite configuration
├── package.json                  # NEW: Node.js dependencies
├── app/
│   ├── static/
│   │   ├── dist/                 # NEW: Built Vue assets (gitignored)
│   │   ├── js/                   # KEPT: Shared utilities (api.js, utils.js, etc)
│   │   └── css/                  # KEPT: Global styles
│   └── templates/                # DEPRECATED: Can be removed after verification
```

### Backend Changes

**`app/routes/basic.py`:**
- All page routes now return `FileResponse(INDEX_HTML)` (the Vue SPA)
- Vue Router handles client-side routing

**`app/main.py`:**
- Updated static file mount to serve from `app/static` (includes `/static/dist`)

### Build Process

**Dockerfile:**
- Multi-stage build:
  1. **Stage 1 (`vue-builder`):** Node.js 20 Alpine builds Vue assets
  2. **Stage 2 (`production`):** Python slim + Vue dist output
- Vite bundles and optimizes all Vue code into `app/static/dist/`

## Development Workflow

### Local Development (with Vite dev server)

```bash
# Install Node.js dependencies
npm install

# Start Vite dev server (hot reload)
npm run dev
# Vite dev server runs on http://localhost:5173
# API proxied to http://localhost:8000 (FastAPI backend)
```

### Production Build

```bash
# Build Vue for production
npm run build
# Output: app/static/dist/

# Build and run Docker container
docker compose up -d --build
```

## API Integration

- **Reuses existing API:** All Vue components use `useApi()` composable
- **API endpoints unchanged:** `/search`, `/api/history`, `/qb/torrents`, etc.
- **Cover loader integration:** Uses existing `CoverLoader` class with ABS logic

## Key Features Preserved

✅ **All existing functionality maintained:**
- MAM search with sorting/pagination
- qBittorrent integration (add torrents)
- Audiobookshelf cover fetching and verification
- Multi-disc import flattening
- History tracking with verification status
- Showcase grouped view
- Series discovery (Hardcover API)
- Application logs viewer

✅ **Existing services reused:**
- `app/static/js/core/api.js` - API client
- `app/static/js/core/utils.js` - Utility functions
- `app/static/js/services/coverLoader.js` - Cover lazy loading
- `app/static/css/main.css` - Global styles

## Testing

```bash
# Backend tests (unchanged)
pytest app/tests/ -v

# Build verification
npm run build && docker compose up -d --build
```

## Migration Benefits

1. **Better Developer Experience:**
   - Hot module replacement (HMR) during development
   - TypeScript support ready (if needed)
   - Component-scoped styles
   - Better IDE support (Vue Language Features extension)

2. **Performance:**
   - Code splitting and lazy loading
   - Optimized production bundles
   - Tree-shaking of unused code

3. **Maintainability:**
   - Clear separation of concerns (template/script/style)
   - Reusable component library
   - Single source of truth for routing

4. **Future-Proof:**
   - Modern Vue 3 Composition API
   - Easy to add Vue ecosystem tools (Pinia, etc.)
   - Can incrementally add features without breaking changes

## Rollback Plan

If issues arise, the previous Jinja2 templates are still in `app/templates/`. To rollback:

1. Revert `app/routes/basic.py` to use `templates.TemplateResponse()`
2. Revert `app/main.py` static mount path
3. Remove Vue build stage from Dockerfile
4. Switch to previous branch/commit

## Next Steps

- [x] Migrate all templates to Vue SFCs
- [x] Set up Vite build system
- [x] Update Dockerfile for Vue build
- [x] Update backend routes to serve SPA
- [ ] Test all views and functionality
- [ ] Remove deprecated Jinja templates (after verification)
- [ ] Update documentation (README.md, FRONTEND.md)

## Notes

- **No breaking changes to API:** Backend endpoints remain unchanged
- **Docker-first deployment:** Vue build happens during Docker build
- **Zero authentication:** Same security model (use behind VPN/proxy)
- **Cover loading:** Still uses ABS integration via existing `api.fetchCover()`
