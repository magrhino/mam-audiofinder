## Summary
- qBittorrent flows repeat across `import_route.py`, `history.py`, and `qbittorrent.py` (login setup, content_path→container mapping, torrent info retrieval, and path validation). Converting these blocks into shared dependencies keeps auth/session handling and path checks consistent while reducing error-prone copy/paste.
- Search-related routes (`search.py`, `showcase.py`) duplicate MAM request construction, response normalization (`flatten`, `detect_format`), caching, and ABS library checks. A reusable MAM dependency can centralize headers, validation, and caching, improving maintainability and cache hit parity.
- ABS verification/metadata handling is scattered across imports and history verification (metadata.json polling, library path resolution, verify_import calls, DB updates). Dependencies that encapsulate metadata loading and ABS verification will standardize retries and error mapping without changing behavior.
- Configuration guards (ABS/MAM availability) and DB lookups (history rows, cover invalidation) are implemented ad hoc; moving them into dependencies reduces boilerplate and keeps HTTPException semantics aligned.

## Inventory of All Routes
| Route | File path | Repeated logic discovered | Proposed dependencies |
| --- | --- | --- | --- |
| GET /health, /config | app/routes/basic.py | None beyond config reads | n/a |
| GET /api/history, DELETE /api/history/{id}, POST /api/history/{id}/verify | app/routes/history.py | qB login + torrent fetch, path validation, cover resolution, metadata.json reading, ABS verify_import, DB session boilerplate | `get_qb_sync_client`, `map_qb_content_path`, `load_metadata_with_retry`, `abs_import_verifier`, `db_session` |
| POST /import, POST /import/multi-book | app/routes/import_route.py | qB login + torrent info, content_path mapping (duplicated function), filesystem validation, metadata.json polling, ABS verify_import, history updates | `get_qb_sync_client`, `require_torrent_info`, `map_qb_content_path`, `ensure_library_destination`, `load_metadata_with_retry`, `abs_import_verifier`, `db_session` |
| GET /qb/torrents, POST /add, GET /qb/torrent/{hash}/tree | app/routes/qbittorrent.py | qB login/auth, torrent info fetching, multi-disc detection uses utils, content_path mapping (filesystem fallback) | `get_qb_async_client`, `require_torrent_info`, `map_qb_content_path`, `torrent_files_tree` |
| POST /search, GET /api/covers/fetch | app/routes/search.py | MAM request building, response normalization (flatten/detect_format), cache integration, ABS library check shape, cover fetch error handling | `mam_search_client`, `normalize_mam_result`, `abs_library_check`, `cover_fetcher` |
| GET /api/showcase | app/routes/showcase.py | Same MAM request/caching/normalize path as search (dup flatten/detect_format), ABS library check | `mam_search_client`, `normalize_mam_result`, `abs_library_check` |
| GET /api/series/* | app/routes/series.py | ABS client presence checks, ABS library lookups similar to search/showcase, shared enrichment concurrency patterns | `require_abs_config`, `abs_library_check`, `abs_enrichment_guard` |
| GET /covers/{filename}, POST /covers/refresh/{mam_id} | app/routes/covers_route.py | ABS config guard, history lookup for title/author, cover refresh/error handling | `require_abs_config`, `history_item_provider`, `cover_fetcher` |
| GET /api/logs | app/routes/logs_route.py | None (self-contained file read) | n/a |

## Proposed Dependency Modules
- **qBittorrent session**
  - `get_qb_async_client` / `get_qb_sync_client`: yield logged-in httpx clients; handle auth errors uniformly. Routes: history, import_route, qbittorrent.
  - Notes: keep per-request lifetime to avoid leaking cookies; reuse timeout settings already in qb_client.
- **Torrent lookup & path mapping**
  - `require_torrent_info`: fetch properties/files/content_path and raise mapped HTTPExceptions for 502/404 cases; hides repeat code in import and qb tree.
  - `map_qb_content_path`: shared mapper from qB paths to container paths with existence check + DL_DIR awareness; routes: import_route (both endpoints), qbittorrent tree fallback, history verification.
- **Library destination & metadata**
  - `ensure_library_destination`: create author/title folders with sanitized names and next_available semantics; returns dest path and safe error responses. Routes: import_route, history.verify_history_item.
  - `load_metadata_with_retry`: async dependency that polls metadata.json with configured attempts/sleep and logs; routes: import_route (single/multi), history verification.
- **ABS verification & config guards**
  - `require_abs_config`: fail fast with consistent HTTPException when ABS is not configured; used by search.cover fetch, covers_route refresh, series endpoints, import verification hooks.
  - `abs_import_verifier`: wraps abs_client.verify_import with metadata/title fallback, exception handling, and optional DB status update hook; routes: import_route (single/multi), history.verify_history_item.
  - `abs_library_check`: shared helper to batch check library presence with cache keys; routes: search, showcase, series enrichment.
- **MAM search client**
  - `mam_search_client`: builds headers/payloads, validates perpage/limit, invokes HTTP call, handles HTTP errors; returns raw data + cache metadata. Routes: search, showcase.
  - `normalize_mam_result`: reusable transformer for `flatten` + `detect_format` + id/title extraction to keep response shape in sync across search/showcase.
  - Notes: preserve existing cache plumbing by injecting `cache_mam_search`/`get_cached_mam_search`.
- **Cover fetch**
  - `cover_fetcher`: encapsulate abs_client.fetch_cover with retry/backoff and optional history lookup for title/author; used by search.fetch_cover and covers_route.refresh.
- **DB session provider**
  - `db_session` / `covers_db_session`: context-managed dependency around `engine` / `covers_engine`; used where raw connections are opened directly (history, import_route, qbittorrent, covers_route).

## Migration Plan (Actionable Checklist)
1. Create `app/dependencies/qb.py`, `app/dependencies/mam.py`, and `app/dependencies/abs.py` modules with the dependency signatures above, reusing existing helpers (qb_client, torrent_helpers, utils).
2. Refactor `search.py` and `showcase.py` to consume `mam_search_client` + `normalize_mam_result` + `abs_library_check`; delete duplicated `flatten`/`detect_format` blocks while keeping cache contract unchanged.
3. Introduce `get_qb_sync_client`, `require_torrent_info`, and `map_qb_content_path` into `import_route.py` (both endpoints) and `qbittorrent.py` (tree + list), removing local path-mapping functions and repeated login code.
4. Extract `ensure_library_destination` + `load_metadata_with_retry` and wire them into import + history verification flows; replace inline metadata polling and directory creation logic.
5. Add `abs_import_verifier` + `require_abs_config` to import flows and history verification; standardize ABS error handling and DB status updates via dependency outputs.
6. Move cover refresh/fetch to `cover_fetcher` and `history_item_provider` (for title/author lookup); apply in `covers_route` and `search.fetch_cover`.
7. Adopt `abs_library_check` in `series.py` enrichment path to align with search/showcase logic and caching.
8. Run existing tests/linters; add smoke tests for dependency wiring (qB auth failure, ABS not configured, MAM cookie missing) to ensure HTTPException parity before removing old helpers.

## Lines of Code Saved
- Estimated 180–230 LOC reduction (duplicated MAM normalization ~70, qB path/login handling ~60, metadata/ABS verification loops ~60) plus fewer ad-hoc config/error blocks. Maintenance improves via single points for auth, path mapping, and ABS/MAM behavior.
