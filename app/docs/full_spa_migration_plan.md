# Full SPA Migration Plan

This document describes how to migrate ShelfArr from its hybrid Jinja + Vue UI to a pure Vue Single-Page Application (SPA) using Vue Router. It inventories current Jinja dependencies, backend routes, Vue coverage, required backend/frontend changes, and provides a step-by-step blueprint.

## A. Repository Audit

### Remaining Jinja Templates

| File | Purpose today | Reachable? | Vue equivalent? | Notes |
| --- | --- | --- | --- | --- |
| `app/templates/base.html` | Legacy layout with nav + CSS links for `main.css` and `legacy.css` | Not routed; only referenced by other templates | Yes (Vue `App.vue` + layout components) | Uses Jinja blocks for title/nav/content and loads legacy task bar styles. `{% extends %}` parent for all other templates. | 
| `app/templates/index.html` | Original multi-tab legacy page with search, history, logs, and showcase DOM | Not routed; superseded by SPA root | Yes (`SearchView`, `HistoryView`, `LogsView`, `ShowcaseView`) | Directly embeds nav, forms, and tables plus `legacy.css` reference. | 
| `app/templates/search.html` | Jinja wrapper rendering a Vue-powered search table | Not routed | Yes (`SearchView.vue`) | Extends `base.html`, sets title/nav blocks, loads `/static/pages/search.js`. | 
| `app/templates/history.html` | Legacy Vue-in-template history table/import form | Not routed | Yes (`HistoryView.vue`) | Extends `base.html`, sets nav block, loads `/static/pages/history.js`. | 
| `app/templates/logs.html` | Legacy logs page with native selects/buttons | Not routed | Yes (`LogsView.vue`) | Extends `base.html`, sets nav block, uses legacy controls. | 
| `app/templates/showcase.html` | Legacy showcase grid/detail viewer | Not routed | Yes (`ShowcaseView.vue`) | Extends `base.html`, sets nav block, uses legacy showcase classes. | 
| `app/templates/series.html` | Legacy series discovery table/detail | Not routed | Yes (`SeriesView.vue`) | Extends `base.html`, sets nav block, uses legacy showcase/series classes. | 

**Template inheritance:** All Jinja views extend `base.html` and override `{% block title %}`, navigation state blocks (`nav_*`), `{% block content %}`, and `{% block page_script %}`. Examples appear in every template listed above.【F:app/templates/base.html†L6-L46】【F:app/templates/search.html†L1-L50】

**Template-only CSS references:** `base.html` and `index.html` are the only places that pull in `legacy.css`, confirming the stylesheet is exclusively for Jinja pages.【F:app/templates/base.html†L13-L15】【F:app/templates/index.html†L14-L15】 The CSS refactor isolated these styles for safe removal once templates are deleted.【F:docs/css_refactoring_summary.md†L20-L33】【F:docs/css_refactoring_summary.md†L146-L166】

**render_template usage:** No `render_template()` calls remain in the codebase (search returned none).【b751b8†L1-L2】 With no backend entry points to the Jinja files, they are currently unreachable in normal operation.

### Backend Routes Still Using HTML Responses

The only HTML responses come from the SPA handoff routes below; they serve the built `static/dist/index.html` file rather than rendering Jinja:

| Path | Handler (file:line) | Behavior | Vue coverage |
| --- | --- | --- | --- |
| `/` | `app/routes/basic.py:17-20` | Returns SPA `index.html` (FileResponse) | `SearchView` | 
| `/history` | `app/routes/basic.py:23-26` | Returns SPA `index.html` | `HistoryView` | 
| `/showcase` | `app/routes/basic.py:29-32` | Returns SPA `index.html` | `ShowcaseView` | 
| `/logs` | `app/routes/basic.py:35-38` | Returns SPA `index.html` | `LogsView` | 
| `/series` | `app/routes/basic.py:41-44` | Returns SPA `index.html` | `SeriesView` | 

These routes are hardcoded; there is no history-mode catchall for additional SPA paths or nested routes.【F:app/routes/basic.py†L12-L44】

### API Routes (to keep)

All other routes under `app/routes/` are JSON/file APIs (search, history, imports, covers, series, qbittorrent, logs). None render HTML and can remain intact during migration.【68a2ff†L1-L17】

### Vulnerable Points if Templates Are Removed

- The only consumers of `legacy.css` are the Jinja templates; deleting templates allows deleting that stylesheet without impacting Vue, as documented in the CSS refactor report.【F:docs/css_refactoring_summary.md†L20-L33】 
- Favicon/meta tags currently live in both `base.html`/`index.html` and the Vite `index.html`; ensure SPA keeps these tags before removing templates.【F:app/templates/base.html†L6-L15】【F:build/frontend/index.html†L3-L15】
- SPA routes presently depend on `static/dist/index.html`; ensure the build pipeline always produces this file before dropping Jinja fallbacks.【F:app/routes/basic.py†L12-L20】

## B. Vue Audit

### Vue Router Coverage

Current Vue Router table (history mode) includes one route per legacy page: `/`, `/history`, `/showcase`, `/logs`, `/series`.【F:build/frontend/src/router/index.js†L9-L40】 Each route lazy-loads its matching view component and sets a document title.

### View Equivalents

- Search → `SearchView.vue`
- History → `HistoryView.vue`
- Showcase → `ShowcaseView.vue`
- Logs → `LogsView.vue`
- Series → `SeriesView.vue`

All legacy pages have Vue counterparts (also confirmed in the CSS refactor status table).【F:docs/css_refactoring_summary.md†L133-L145】 Dynamic series detail is handled via in-view state rather than a dedicated `/series/:id` route; adding a dynamic route will be part of the migration blueprint if deep-linking is required.

### Missing/Mismatched Paths

- No catchall (`/:pathMatch(.*)*`) exists to support history mode for future nested routes (e.g., deep-linked series detail).【F:build/frontend/src/router/index.js†L15-L40】
- Backend only serves `index.html` for five hardcoded paths; direct hits to any other SPA path would 404 once added unless a wildcard fallback is implemented.【F:app/routes/basic.py†L17-L44】

## C. Migration Blueprint

1. **Remove Jinja templates** – Delete `app/templates/*` after verifying SPA parity and update any documentation that points to template rendering.【F:app/templates/base.html†L1-L46】【F:docs/css_refactoring_summary.md†L146-L166】
2. **Remove `legacy.css`** – Delete `app/static/css/legacy.css` and its references once templates are gone; keep `main.css` for shared tokens only.【F:app/templates/base.html†L13-L15】【F:docs/css_refactoring_summary.md†L20-L33】
3. **Replace backend HTML routes with SPA index fallback** – Consolidate the five FileResponse routes into a single wildcard handler that serves `static/dist/index.html` for any non-API GET path, preserving API routes untouched.【F:app/routes/basic.py†L12-L44】
4. **Add full Vue Router routing table** – Extend `src/router/index.js` with any needed dynamic routes (e.g., `/series/:id`) and a 404/redirect catchall while keeping document titles updated.【F:build/frontend/src/router/index.js†L9-L43】
5. **Update backend to serve Vue’s `dist/` folder** – Ensure `StaticFiles` mounts `/static` (already present) and add a fallback route that responds with `/static/dist/index.html` for unknown frontend paths.【F:app/main.py†L27-L37】【F:app/routes/basic.py†L12-L20】
6. **Update Dockerfile/build process** – Build the Vue app during image creation, placing assets in `app/static/dist`; remove any template copy steps and ensure `index.html` is bundled. Base path `/static/dist/` must align with reverse proxies.【F:build/frontend/vite.config.js†L7-L31】
7. **Remove unused CSS/HTML assets** – Delete template-only JS bundles (`/static/pages/*.js`), images, and toast styles once templates are removed; rely on scoped Vue styles and `global.css`.【F:docs/css_refactoring_summary.md†L53-L96】

## D. Backend Code Changes (with line references)

- **`app/main.py`** – Keep `app.mount('/static', ...)`; add an app-wide fallback route (e.g., `@app.get('/{full_path:path}')`) that returns `static/dist/index.html` for GET requests not matching API prefixes. Ensure logging remains unchanged.【F:app/main.py†L27-L37】
- **`app/routes/basic.py`** – Replace discrete SPA FileResponse routes (`/`, `/history`, `/showcase`, `/logs`, `/series`) with a single router handler for any non-API path, and drop unused health/config routes from SPA routing to avoid conflicts with API paths.【F:app/routes/basic.py†L12-L60】
- **Route preservation** – Leave API routers (`search`, `history`, `import`, `qbittorrent`, `covers`, `series`, `logs`) unchanged as JSON/file endpoints; ensure the fallback excludes paths starting with `/api`, `/qb`, `/covers`, `/health`, `/config`, etc., to prevent HTML responses from shadowing APIs.【68a2ff†L1-L17】
- **Template removal** – Delete `app/templates` directory references from any configuration or deployment scripts (none exist today) and remove `StaticFiles` exposure of `/templates` if ever added (not present).【F:app/main.py†L27-L37】

## E. Frontend Changes

- **Router (`build/frontend/src/router/index.js`)** – Add catchall route redirecting to `/` or a Vue 404 component; optionally introduce dynamic routes such as `/series/:id` for deep links. Confirm meta titles for any new routes.【F:build/frontend/src/router/index.js†L9-L43】
- **SPA entry (`build/frontend/index.html`)** – Ensure favicon/meta tags mirror what Jinja provided (already present) and keep `main.css` link for shared tokens. Remove any legacy script includes when `legacy.css` is deleted.【F:build/frontend/index.html†L3-L19】【F:app/templates/base.html†L6-L15】
- **Vite config** – Verify `base: '/static/dist/'` aligns with backend static mount; adjust if deployment path changes. Confirm `outDir: '../app/static/dist'` so backend can serve built assets. Preserve proxy rules for local dev against FastAPI.【F:build/frontend/vite.config.js†L7-L68】
- **CSS cleanup** – Remove `legacy.css` import from `index.html` once backend templates are gone; rely on scoped component styles and `global.css` per the CSS refactor summary.【F:build/frontend/index.html†L14-L15】【F:docs/css_refactoring_summary.md†L53-L96】
- **Component parity** – Validate that each legacy feature has a Vue component (confirmed in refactor table) and backfill any missing functionality before deleting templates.【F:docs/css_refactoring_summary.md†L133-L145】

## F. Final Deliverable

Following this plan will remove Jinja dependencies, retire `legacy.css`, and run ShelfArr as a pure Vue SPA with Vue Router handling all navigation. Implement the backend fallback to serve `/static/dist/index.html`, ensure Vite builds output to that path with correct base URL, and delete legacy templates/assets once parity checks pass.
