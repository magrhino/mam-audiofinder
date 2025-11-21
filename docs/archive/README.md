# Documentation Archive

This directory contains historical documentation that is no longer relevant to the current codebase architecture.

## Archived Documents

### css_refactoring_summary.md
**Archived:** 2025-11-21
**Reason:** Describes legacy CSS architecture (`app/static/css/main.css`, `app/static/css/legacy.css`) that has been completely removed. ShelfArr now uses UnoCSS as the primary styling system with global styles in `build/frontend/src/styles/global.css`.

### jinja_migration_changes.md
**Archived:** 2025-11-21
**Reason:** Historical documentation of Jinja template removal. Migration is complete - ShelfArr is now a pure Vue 3 SPA with FastAPI backend.

### update_documentation_todo.md
**Archived:** 2025-11-21
**Reason:** Temporary planning document for documentation updates. Tasks completed.

### create_documentation_updates.md
**Archived:** 2025-11-21
**Reason:** Temporary prompt/guide for documentation generation. No longer needed.

### css_analysis.md
**Archived:** 2025-11-21
**Reason:** Analysis document from CSS refactoring phase. Refactoring complete.

## Current Documentation

For up-to-date documentation, see:
- `/CLAUDE.md` - AI assistant guide with architecture overview
- `/docs/FRONTEND.md` - Vue 3 SPA architecture and UnoCSS styling
- `/docs/BACKEND.md` - FastAPI backend implementation details
- `/docs/TESTING.md` - Testing guide
- `/docs/VUE_MIGRATION.md` - Vue migration notes
- `/README.md` - User-facing documentation
