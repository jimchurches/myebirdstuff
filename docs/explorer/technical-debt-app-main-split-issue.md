## Summary

`explorer/app/streamlit/app.py` is a **thin** entrypoint; dashboard phases live in focused modules (GitHub #200, R13 hygiene 2026-05-23).

## Current layout (post R13)

| Module | Role |
|--------|------|
| `app.py` | `main()` — ordered bootstrap → data → map sidebar → dashboard shell |
| `app_bootstrap.py` | Page config, session defaults, settings YAML after CSV load, taxonomy assets |
| `app_dashboard_shell.py` | `st.tabs`, delegates prep + non-map fragments + Settings |
| `app_orchestration.py` | Re-exports public API for `app.py` |
| `app_landing_ui.py` | No-data landing + CSV load |
| `app_map_working_ui.py` | Map sidebar + working set |
| `app_prep_map_ui.py` | **Orchestrates** map prep spinner (~180 lines) |
| `app_prep_map_leaflet_modes.py` | Family vs All/Lifer/Species Leaflet payload builders |
| `app_prep_map_map_tab.py` | Map tab embed, export recipe, sidebar footer |
| `app_prep_map_leaflet_caches.py` | Session LRU + export HTML helpers |
| `app_prep_map_tab_prep.py` | Checklist / rankings / tab session sync spinner |
| `app_prep_map_blank_viewport.py` | Blank-map default viewport recipe |
| `app_settings_ui.py` | Settings tab body |

## Remaining optional splits

- Further split `app_prep_map_leaflet_modes.py` (~920 lines) into one file per map mode if edits become painful.
- `app_map_working_ui.py` (~490 lines) could gain a dedicated family-sidebar helper module later.

## Principles (unchanged)

1. **No behaviour change** on refactor-only PRs — same session keys, spinner order, tab fragments.
2. **Incremental** extractions with `pytest tests/explorer/` + manual map regression.
3. **Execution order** matters: sidebar widgets before main area, `st.tabs` before prep spinner nesting.

## Relationship to other work

Independent of HTML table SSOT and other tech-debt items. R5 phase 1 (caches + tab prep) and R13 (orchestration + prep modes) addressed the highest-churn paths before release.
