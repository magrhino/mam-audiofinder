# Documentation Update TODO

## Summary
ShelfArr now runs as a Vue 3 + Naive UI SPA served by a FastAPI backend, but customer-facing docs still describe the legacy mam-audiofinder/Jinja stack. `docs/jinja_migration_changes.md` and `docs/css_refactoring_summary.md` confirm the SPA fallback route, deleted templates, and the new CSS split (`main.css`, `legacy.css`, `global.css`, component-scoped styles, Naive UI theme overrides). The README and BACKEND docs must be rewritten so contributors stop following stale Flask/Jinja instructions and so we can introduce a brand-new FRONTEND guide.

## README.md Updates
### Additions
1. [ ] Replace the title/branding with “ShelfArr” everywhere, note that the repo lives at `magrhino/shelfarr`, and mention that the application target is modern Vue SPA + FastAPI APIs.
2. [ ] Insert an “Architecture Overview” section describing the SPA entrypoint (`static/dist/index.html`), FastAPI’s role (API surface + SPA fallback in `app/main.py`), and the CSS layering (`app/static/css/main.css`, `app/static/css/legacy.css`, `build/frontend/src/styles/global.css`, component-scoped `<style scoped>`, and Naive UI theme overrides from `build/frontend/src/theme/naive.js`).
3. [ ] Under “Repository Layout,” explicitly call out `build/frontend/` as the Vue workspace (Vite-based, scripts from `package.json`) and `app/routes/` modules for the API.
4. [ ] Add a short “Frontend build workflow” subsection in Quick Start explaining `npm install && npm run build` inside `build/frontend/` and that artifacts land in `app/static/dist/` (as enforced by vite.config.js).
5. [ ] Add links to the refreshed `docs/BACKEND.md` and new `docs/FRONTEND.md` inside the “Technical Documentation” section with one-line summaries.
### Rewrites
1. [ ] Update cloning instructions, env var notes, and Docker guidance to use the `shelfarr` repo path, image tags, and default container names (drop `mam-audiofinder`), ensuring terminology matches `.env` defaults.
2. [ ] Rewrite the “Features” list so UI-centric bullets explicitly reference the Vue SPA views (Search, History, Showcase, Logs, Series) and Naive UI interactions instead of “tabs” or Jinja template terminology.
3. [ ] Refresh the “How to Use” steps so each flow (Search, Add, Import, Showcase, Logs) references Vue navigation (Vue Router links, SPA refresh behavior) and remove legacy tab-switching language.
4. [ ] Replace any mention of Flask/Jinja templates with FastAPI + Vue wording, and note in “Logs”/“Troubleshooting” that `/logs` etc. are SPA views backed by API endpoints.
5. [ ] Update screenshot references or captions if needed to clarify they show the Vue SPA (optional if images already match, but mention Vue + Naive UI theme in text around them).
### Deletions
1. [ ] Delete the `git clone ... mam-audiofinder` instructions and any bullet that references “mam-audiofinder” categories or directories (update to ShelfArr defaults, e.g., `QB_CATEGORY=shelfarr` if applicable).
2. [ ] Remove references to `docs/documentation/` legacy pathing, Jinja templates (`app/templates/*.html`), or instructions about editing template files—replace with SPA directions.
3. [ ] Strip any mention that Flask serves HTML routes individually; state that non-API routes go through the SPA fallback described in `docs/jinja_migration_changes.md`.

## BACKEND.md Updates
### Architecture & Routing
1. [ ] Rewrite the intro to describe ShelfArr’s FastAPI service instead of the single service (“Unified Description Service”) focus—include a diagram or narrative showing: FastAPI app bootstrap (`app/main.py`), router aggregation (`routes/__init__.py`), static mount for `/static/dist`, and the SPA catch-all route.
2. [ ] Document that the backend now exposes **only API endpoints + SPA index**: `/health`, `/config`, `/search`, `/history`, `/logs`, `/import`, `/series`, `/covers`, `/qb`, etc., referencing modules inside `app/routes/`. Explicitly mention `app/routes/basic.py` no longer exports HTML responders.
3. [ ] Add a subsection for “SPA Fallback & Asset Serving” referencing the new `FileResponse("static/dist/index.html")` behavior in `app/main.py` so future changes keep SPA routing intact.
### API & Dependencies
4. [ ] Keep existing description-service details but nest them under a new “Auxiliary Services” heading so the file can also introduce other subsystems (history import pipeline, qBittorrent integration, ABS verification). Link to the relevant modules (`importer.py`, `qbittorrent.py`, etc.) so the doc reflects the complete backend architecture.
5. [ ] Document startup dependencies introduced by the migration (FastAPI, Vite-built assets, `app/static/dist` presence) and note that Jinja templates, `app/templates`, and `/app/static/pages` files were deleted per `docs/jinja_migration_changes.md`.
6. [ ] Add a section summarizing configuration relevant to backend behavior (`IMPORT_MODE`, `FLATTEN_DISCS`, ABS settings) and the new CSS pipeline (backend only serves the compiled `main.css` + `legacy.css` files—no template-specific overrides).
### Cleanup
7. [ ] Remove or rewrite any lingering Flask/Jinja references and ensure the doc no longer assumes a hybrid renderer; explicitly mention that Flask was replaced by FastAPI earlier and now only APIs remain.

## FRONTEND.md Creation
### Required Structure
1. [ ] Create `docs/FRONTEND.md` with H1 “FRONTEND.md - ShelfArr Vue SPA”.
2. [ ] Include the following subheaders (in order): `## Overview`, `## Project Layout`, `## Core Technologies`, `## Routing & Views`, `## Components & Composables`, `## Styling Architecture`, `## Theme System`, `## Build & Deployment Workflow`, `## Migration Status & Legacy Interop`, `## Future Enhancements`.
### Content Requirements
3. [ ] In “Overview,” describe the SPA entrypoint (`App.vue` + Vue Router history mode) and the fact that FastAPI only serves `static/dist/index.html`. Reference the fallback logic from `docs/jinja_migration_changes.md`.
4. [ ] Under “Project Layout,” list key directories: `build/frontend/src/components`, `views`, `router`, `composables`, `styles/global.css`, `theme/naive.js`, and explain how `/app/static/dist/` is generated.
5. [ ] “Core Technologies” should cover Vue 3, Vite, Vue Router, Naive UI, and any custom composables (e.g., API helpers, cover loader) as noted in recent path alias changes.
6. [ ] “Routing & Views” must enumerate the Vue Router map (Search, History, Showcase, Logs, Series, catch-all redirect) and explain SPA navigation/404 handling.
7. [ ] “Components & Composables” should explain reusable components (StatusBadge, ActionButton, ResultRow, HistoryRow) and composables (`useApi`, `useCoverLoader`, Naive data table hooks) plus how import path aliases (`@core`, `@services`) are configured in `vite.config.js`.
8. [ ] “Styling Architecture” needs to explain the CSS split: `app/static/css/main.css` as shared base, `app/static/css/legacy.css` temporary, `build/frontend/src/styles/global.css` for Vue-specific globals, scoped component styles, and how these relate to Naive UI overrides.
9. [ ] “Theme System” should walk through `build/frontend/src/theme/naive.js` and how theme tokens map to CSS variables defined in `main.css`.
10. [ ] “Build & Deployment Workflow” must detail `npm install`, `npm run dev`, `npm run build`, artifact placement, and how Docker build copies the dist folder.
11. [ ] “Migration Status & Legacy Interop” needs to summarize which legacy assets remain (`legacy.css`, possibly dual-running pages) and note that Jinja templates are deleted per `docs/jinja_migration_changes.md`.
12. [ ] “Future Enhancements” should capture open cleanup tasks (e.g., deleting `legacy.css` once no legacy routes remain, additional Naive UI component conversions) as inferred from the migration + CSS summary docs.

## Files to Reference
1. [ ] `README.md` – base document to edit.
2. [ ] `docs/BACKEND.md` – rewrite target.
3. [ ] `docs/FRONTEND.md` – new file to create per requirements.
4. [ ] `docs/jinja_migration_changes.md` – authoritative SPA migration notes.
5. [ ] `docs/css_refactoring_summary.md` – CSS architecture reference.
6. [ ] `app/main.py` – SPA fallback and FastAPI bootstrap.
7. [ ] `app/routes/*.py` – API endpoints and module responsibilities.
8. [ ] `build/frontend/vite.config.js` – alias + build output paths.
9. [ ] `build/frontend/src/**/*` – components, views, styles, router, theme files.
10. [ ] `app/static/css/main.css` and `app/static/css/legacy.css`.
11. [ ] `build/frontend/src/styles/global.css` and `build/frontend/src/theme/naive.js`.

## Outdated Text Patterns to Remove
1. [ ] `mam-audiofinder` (repo name, container name, QB category, folder references).
2. [ ] `MAM Audiobook Finder` branding or mentions that imply the old name.
3. [ ] References to Flask or Jinja-rendered templates (e.g., “templates/index.html”, “Jinja tabs”, “Flask routes serve HTML”).
4. [ ] Instructions directing users to edit `app/templates/` or `app/static/pages/`.
5. [ ] Any mention of “multi-tab legacy page” UI elements that have been replaced by Vue Router views.

## QA Checklist
1. [ ] Verify README.md uses “ShelfArr” exclusively, links to the new FRONTEND doc, and accurately explains SPA + API responsibilities.
2. [ ] Confirm README.md and BACKEND.md both describe the CSS layering (main.css, legacy.css, global.css, component scopes, Naive UI theme) in alignment with `docs/css_refactoring_summary.md`.
3. [ ] Ensure BACKEND.md includes the SPA fallback explanation and no longer references Jinja or template-serving routes.
4. [ ] Confirm FRONTEND.md contains every required section and explicitly cites router structure, component layout, Naive UI theme, and build workflow.
5. [ ] Search updated docs for outlawed phrases listed above and ensure they’re removed or rewritten.
6. [ ] Check that all docs link to each other where relevant (README → FRONTEND/BACKEND, FRONTEND → CSS summary or theme files, BACKEND → migration doc).
7. [ ] Run markdown lint/preview locally if available to ensure headings, lists, and code blocks render correctly.
