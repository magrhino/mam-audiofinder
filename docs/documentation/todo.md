# Series Tab Integration Roadmap

This roadmap enumerates the concurrent-ready tasks AI assistants can execute to ship the Series tab, richer card-driven discovery, Hardcover API integration, and safe multi-book imports.

## Legend
- `[SEQ]` — Must be completed in presented order within the phase.
- `[CON]` — Can run concurrently with other `[CON]` tasks in the same phase.

## Phase 0 — Research & Guardrails
1. `[SEQ]` Review `docs/documentation/hardcover-api-ref.md` and confirm current request/response schemas, auth headers, and rate-limit notes (target: summary + open questions).
2. `[CON]` Capture explicit Hardcover API rate limits (per key, per endpoint) and document throttle strategy (retry/backoff policy doc stub in `docs/documentation/hardcover-api-ref.md`).
3. `[CON]` Inventory data the Series tab must display (series title, position, release data, cover URL) and map to existing UI helpers (esp. `card_helper`).

## Phase 1 — Unified Title Search Controls
1. `[SEQ]` Extend the card helper context so every rendered search/history card includes the normalized "unified title" and card GUID.
2. `[CON]` Add a "Series Search" icon/button on each card; clicking dispatches a frontend event carrying the unified title.
3. `[SEQ]` Build a backend endpoint `/api/series/search` that accepts `title`, `author`, falls back to normalized card title, and fans out to MAM + Hardcover queries.
4. `[CON]` Update the search results reducer so Series-search-triggered payloads render adjacent to the original card stack without clobbering pagination caches.

## Phase 2 — Hardcover API Series Data
1. `[SEQ]` Add a dedicated Hardcover client module encapsulating base URL, auth token, and shared headers; reuse rate-limit values from Phase 0.
2. `[CON]` Implement a `search_series(title, author)` call returning normalized series metadata (id, name, match confidence, book counts).
3. `[CON]` Implement `list_series_books(series_id)` that returns book records ready for `card_helper` consumption (title, narrators, cover, torrent refs when present).
4. `[SEQ]` Define cache + persistence strategy (SQLite table or in-memory TTL store) so repeated UI clicks avoid exceeding rate limits.

## Phase 3 — Series Tab & ABS/MAM Integration

### Task 12: Table-First Layout `[SEQ]`
1. Keep `/series` as the entry point but remove the broken `cardHelper` grid entirely; Hardcover is only trusted for hierarchy metadata, so the UI should stay in tables.
2. Series list remains a table (title, author, readers, book count). When a series is selected, swap in a **book table** (position, title, optional year, action column) instead of card tiles. Maintain router/back-state so `q`, `author`, `limit`, and the selected series/book can be restored.

### Task 13: Book → Grouped MAM Results `[CON]`
1. Each book row gets a “View torrents” button. Clicking it issues a MAM search (`/search`) for `"{bookTitle} {seriesAuthor}"` using the “Search #” selector (allowed values `5,10,20,30,40,50`) for `perpage`.
2. Immediately group that payload the same way Showcase does (reuse the existing helper or `/api/showcase`). Render the result **inside the Series tab** with the exact markup Showcase detail uses: ABS cover fetched via `/api/covers/fetch`, metadata chips, torrent table with Add buttons, and ABS availability badges.
3. Provide breadcrumbs/back buttons so users can jump:
   - Series list → Book list → Grouped MAM view.
   Persist identifiers in router state so reloading restores whatever panel was open.

### Task 14: Drawer & Feedback `[SEQ]`
1. Ensure the search-page drawer that responds to `series-search` events now embeds the same table/grouped components (no cards). When a card triggers the drawer, auto-run the corresponding series search, focus the matching book row, and optionally auto-open the grouped view for the best match.
2. Reuse the existing toast helper for every async stage (Hardcover search, book fetch, MAM grouped fetch). Surface distinct errors (rate limit vs. “no torrents”) and reset the triggering `series-search` button via `setSeriesSearchButtonSuccess/Error`.
3. When a grouped detail is shown via the drawer, keep the ABS cover + Add torrent functionality identical to Showcase so behavior stays predictable.

### Task 15: Limit Coupling `[CON]`
1. Validate both `perpage` (MAM) and `limit` (Hardcover) against the shared whitelist `5,10,20,30,40,50` server-side; coerce invalid requests back to the nearest supported value to protect caches and rate limits.
2. Drive every selector (search page, series tab, drawer) from that single constant, and log the applied value so debugging mismatches is easy.
3. When book rows trigger grouped searches, reuse the same selected value to keep ABS cover caching and MAM limit behavior aligned with the rest of the app.

## Phase 4 — Multi-Book Download & Import Pipeline
1. `[SEQ]` Extend import planning logic to accept multiple book payloads per torrent without altering the disk-flattening helper contracts.
2. `[CON]` Update database schema/migrations if additional linkage tables (torrent -> multiple books) are required; keep migrations idempotent.
3. `[SEQ]` Modify the worker/import route to enqueue per-book ABS verification while ensuring a single torrent download fan-outs into multiple library imports safely.
4. `[CON]` Add regression tests that simulate multi-book torrents and verify flattening rules remain untouched (see `tests/` import suites).

## Phase 5 — Validation & Telemetry
1. `[SEQ]` Create integration tests (pytest + httpx mocks) covering the new `/api/series/search` and Hardcover client methods, including rate-limit fallbacks.
2. `[CON]` Instrument logging/tracing (structured logs) around Hardcover requests to surface latency, retries, and throttled calls.
3. `[SEQ]` Update `README.md`/`FRONTEND.md` with Series tab usage instructions, new env vars (Hardcover API key/URL), and deployment notes.
4. `[CON]` Run manual UX verification: card buttons, Series tab flows, multi-book download scenarios, and ensure Audiobookshelf imports complete without flattening regressions.
