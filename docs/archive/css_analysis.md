# CSS Usage and Duplication Report

## How `main.css` is loaded
- Legacy Jinja templates load `/static/css/main.css` via `app/templates/base.html`, so History (`history.html`) and Logs (`logs.html`) inherit it automatically. No other stylesheets are referenced on those pages. The templates only include minimal inline column widths. 
- The legacy single-page `app/templates/index.html` (search/history/logs/showcase) also links to `/static/css/main.css`.
- The Vue SPA entry `build/frontend/index.html` loads the same `/static/css/main.css` so the SFCs can rely on legacy class names while Naive UI provides component styling.

## Legacy History & Logs CSS sources
- Both legacy pages rely solely on `/static/css/main.css`; neither page imports additional CSS or inline style blocks beyond per-column widths in the table headers.
- Logs page markup uses `.card`, `.logs-header`, `.logs-controls`, `.logs-container`, and `.primary` button classes defined in `main.css`.
- History page uses `.card`, default table styling, `.center`, `.muted`, and import-related classes provided by `main.css`.

## Mapping `main.css` blocks to usage
The stylesheet is organized into commented sections. Each block below lists where it is consumed:

| Section / selectors | Logs page | History page | Vue components | Notes |
| --- | --- | --- | --- | --- |
| Variables & base (`:root`, `body`, typography)【F:app/static/css/main.css†L6-L122】 | Yes | Yes | Yes (global) | Needed for color tokens shared across legacy and Vue.
| Card/panel layout (`.card`, `.panel`)【F:app/static/css/main.css†L105-L121】 | Yes | Yes | Yes (HistoryView/LogsView wrapper)【F:build/frontend/src/views/HistoryView.vue†L2-L24】【F:build/frontend/src/views/LogsView.vue†L2-L27】 | Keep globally until legacy removed.
| Legacy form controls (`.search-view`/`.logs-view` inputs, selects, buttons)【F:app/static/css/main.css†L131-L250】 | Logs uses selects/buttons【F:app/templates/logs.html†L9-L33】; Search index uses all | History uses button styles only in inline? (none) | Vue SearchView uses Naive UI (`GlassSearchBar`, `NButton`), so these selectors are unused by Vue; Vue LogsView still uses native `<select>` and `<button>` so the block still applies.【F:build/frontend/src/views/LogsView.vue†L2-L27】 | Move to `legacy.css` once Vue Logs stops using native controls.
| Table styles (`table`, `th`, `td`, hover, alignment)【F:app/static/css/main.css†L252-L292】 | Yes (logs container not table) | Yes | Yes (HistoryView table)【F:build/frontend/src/views/HistoryView.vue†L2-L24】 | Shared baseline; could be split into legacy + shared minimal.
| Text/link utilities (`.muted`, `.text-subtle`, `a`)【F:app/static/css/main.css†L293-L314】 | Used in status text | Yes | Yes (History empty row)【F:build/frontend/src/views/HistoryView.vue†L17-L23】 | Keep minimal.
| Import form (legacy compact) `.import-form` block【F:app/static/css/main.css†L321-L355】 | No | Legacy index import | Vue HistoryRow uses enhanced import form classes later in file; this early block can move to legacy-only.
| Responsive base (@media 768px)【F:app/static/css/main.css†L357-L384】 | Yes | Yes | Partially (table width) | Can keep minimal or scope per page.
| Loading/skeleton (`.loading`, `@keyframes pulse/shimmer`, `.cover-skeleton`, `.cover-image`, `.cover-placeholder`)【F:app/static/css/main.css†L386-L458】【F:app/static/css/main.css†L400-L458】 | No | No | Yes (ShowcaseView uses `.cover-skeleton`)【F:build/frontend/src/views/ShowcaseView.vue†L82-L94】【F:build/frontend/src/views/ShowcaseView.vue†L100-L113】 | Keep or move to component-scoped replacements.
| Deprecated task bar (`.task-bar`, `.nav-btn`, `.health-indicator`) commented out【F:app/static/css/main.css†L484-L567】 | Legacy index only | Legacy index only | Replaced by NavBar scoped glass styles【F:build/frontend/src/components/NavBar.vue†L133-L469】 | Safe to delete once legacy index retired.
| Logs view (`.logs-header`, `.logs-controls`, `.logs-container`, log level colors)【F:app/static/css/main.css†L569-L639】 | Yes | No | Yes (Vue LogsView reuses classes)【F:build/frontend/src/views/LogsView.vue†L2-L27】 | Keep shared until Vue logs migrates to Naive UI components.
| Showcase grid/detail styles (`.showcase-*`, `.series-search-btn`)【F:app/static/css/main.css†L641-L1149】 | Legacy index showcase | No | Partially: Vue ShowcaseView defines scoped replacements for grid/layout, covers, and shimmer【F:build/frontend/src/views/ShowcaseView.vue†L513-L620】 | Move unused legacy rules to `legacy.css`; rely on scoped Vue styles.
| Toast styles (`.toast*`)【F:app/static/css/main.css†L1153-L1255】 | No | No | No (Vue uses Naive notifications) | Candidate for deletion.
| Action buttons/status badges/import form (enhanced)【F:app/static/css/main.css†L1264-L1348】 | No | Yes (HistoryRow import form) | Yes (HistoryRow, ActionButton, StatusBadge use these classes)【F:build/frontend/src/components/ActionButton.vue†L1-L35】【F:build/frontend/src/components/StatusBadge.vue†L1-L18】【F:build/frontend/src/components/HistoryRow.vue†L95-L149】 | Keep but consider moving into component-scoped styles.
| Glass utility classes (`.glass-*`)【F:app/static/css/main.css†L1353-L1504】 | No | No | Overlaps with NavBar/Glass* component scoped styles【F:build/frontend/src/components/NavBar.vue†L133-L469】【F:build/frontend/src/components/GlassSearchBar.vue†L58-L120】 | Duplicate; prefer scoped versions or Naive theme overrides.
| Glass button/card variations & shimmering (`.glass-button*`, `.glass-card`, `.glass-tag`, `.glass-overlay`, `.glass-shimmer`)【F:app/static/css/main.css†L1427-L1605】 | No | No | Partially referenced via Naive DataTable columns (`glass-button`, `glass-tag`)【F:build/frontend/src/composables/naive/useMAMSearchDataTable.js†L208-L299】 but components also have scoped glass styles. | Move only the selectors still referenced by JS composables into scoped/global Vue styles; remove unused variants.
| Naive UI data table shimmer overrides (`:deep(.n-data-table-tr)` etc.)【F:app/static/css/main.css†L1620-L1655】 | No | No | Yes (SearchView uses Naive DataTable)【F:build/frontend/src/views/SearchView.vue†L23-L60】 | Could live in a Vue global styles file instead of legacy `main.css`.

## Duplication and overlaps
- Navigation/task bar styles in `main.css` are superseded by `NavBar.vue` scoped glass styles; legacy rules are commented out and only needed for the old multi-panel `index.html`.
- Showcase grid/card/description styles are reimplemented with scoped CSS inside `ShowcaseView.vue`; main.css versions are only necessary for the legacy showcase embedded in `index.html`.
- Glass effect utilities (`.glass-*`) exist both in `main.css` and as scoped styles within `NavBar.vue`, `GlassSearchBar.vue`, `GlassSelect.vue`, and other components. Prefer the component-scoped implementations to avoid global bleed.
- Toast styling appears unused across legacy and Vue (Naive UI provides notifications instead).
- Form control styling for `.search-view`/`.logs-view` is redundant for Vue Search/Series/Showcase views because they rely on Naive UI inputs; only Vue Logs still uses native controls.

## Cleanup recommendations
- **Move legacy-only selectors** (commented task bar, legacy search form controls, legacy import form block at lines 321-355, legacy showcase grid) into a small `legacy.css` referenced only by the Jinja templates once Vue pages replace them fully.
- **Component-scope reusable pieces**: migrate `.action-btn`, `.status-badge`, `.import-form__*`, `.glass-button`, `.glass-tag`, and cover skeleton styles into the Vue SFCs or shared Vue style module so they follow component lifecycles.
- **Naive UI theme overrides**: port color tokens and table hover shimmer (`:deep(.n-data-table-tr)` block) into `build/frontend/src/theme/naive.js` or a global Vue style entry to align with Naive’s CSS-in-JS approach.
- **Delete dead code**: toast styles, unused glass variants, and the deprecated task bar block can be removed after confirming no legacy template references remain.

## Step-by-step migration plan
**Logs**
1. Replace native `<select>`/`<button>` in `build/frontend/src/views/LogsView.vue` with Naive UI components, then move `.logs-*` styles into scoped `<style>` or Naive theme. Drop the `.logs-view` form-control block from `main.css` once done.
2. If legacy `logs.html` is retired, remove the `.logs-*` section from `main.css` or move it to `legacy.css` used only by Jinja templates.

**History**
1. Move `.action-btn`, `.status-badge`, `.import-form__*`, and related blocks from `main.css` into `HistoryRow.vue` scoped styles. Ensure Naive buttons replace any remaining native buttons.
2. After migration, leave only shared table/base styles in `main.css` or a new `shared.css` for Vue.

**Showcase**
1. Confirm the legacy showcase in `app/templates/index.html` is unused; if so, delete `.showcase-*` rules from `main.css` because `ShowcaseView.vue` already defines scoped equivalents.
2. Keep cover skeleton animation either in `ShowcaseView.vue` scoped CSS or a small shared Vue style.

**Import**
1. The legacy import form styles (lines 321-355) can move to `legacy.css`; Vue import UI uses the newer `.import-form__*` block later in the file and should be scoped into `HistoryRow.vue`.

**Search**
1. Remove `.search-view` input/select/button styles from `main.css` once legacy search is gone; Vue Search uses Naive UI and Glass components with scoped styles. Keep only table utility styles used by results if necessary.

## Proposed new structure
- `static/css/main.css` (minimal): keep variables, base typography, table defaults, and any truly shared utilities (`.card`, `.panel`, `.muted`, `.center`).
- `static/css/legacy.css`: store legacy nav bar, legacy search/logs form controls, legacy showcase grid, and import styles for Jinja templates until they are removed.
- Component-scoped styles: move action/import/status/glass utility classes into their respective Vue SFCs (`HistoryRow.vue`, `ActionButton.vue`, `Glass*` components, `NavBar.vue`).
- Naive UI theme overrides: shift table shimmer and color tokens into `build/frontend/src/theme/naive.js` and rely on Naive’s styling for buttons/inputs instead of global CSS.
