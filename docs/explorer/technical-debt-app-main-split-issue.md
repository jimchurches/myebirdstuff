## Summary

`explorer/app/streamlit/app.py` defines `main()` as a **very long** linear script: data loading, settings, sidebar, working set, prep spinner (checklist + rankings + syncs), main tabs (Map through Settings), and footer. This predates recent features; growth is incremental.

## Justification

- **Maintainability:** A single huge function is hard to navigate, review, and test in isolation. Boundaries between “load + prep”, “render tabs”, and “settings panel” are implicit.
- **Not correctness:** The app behaves correctly today; this is **structural** hygiene, not a bugfix.

## Desired outcomes (when addressed)

1. **Clear modules or functions** with stable names, e.g.:
   - data load + session bootstrap (or reuse existing `app_data_loading` patterns);
   - map sidebar + working set (already partially separated);
   - **prep pass** (spinner block: caches, bundles, sync helpers);
   - **main tab bodies** delegated to existing `*_fragment` / tab modules where possible;
   - **Settings** tab content in a dedicated function or `app_settings_ui.py`-style module.
2. **`main()` as orchestration** — short, ordered calls, minimal logic.
3. **Easier testing** — optional: pure helpers or smoke tests for prep without full Streamlit, where feasible without heavy mocking.
4. **No behaviour change** — refactor-only PRs; same user-visible flows and session keys.

## Scope / risks

- **Large diff** if done in one go; prefer **incremental** extractions (one phase per PR) with regression checks (`pytest tests/explorer/`, manual Streamlit smoke).
- Watch **execution order** (sidebar widgets before main area, pending cluster key, spinner placement).

## Relationship to other work

Independent of HTML table SSOT and other tech-debt items; schedule when a dedicated refactor window is available.
