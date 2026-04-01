# Streamlit v3 move order (end-state prep)

**Document status — complete.** Target layout is implemented: **`explorer.core`** (domain, paths, settings schema, map pipeline), **`explorer.presentation`** (HTML + Folium chrome), **`explorer.app.streamlit`** (UI). The old top-level `personal_ebird_explorer` and `streamlit_app` packages are gone; imports use `explorer.core.*` and `explorer.presentation.*`.

You can **delete this file** when you no longer need the historical checklist; Git keeps prior versions.

---

## Target structure (as implemented)

```text
explorer/
  core/                  # data, stats, taxonomy, paths, settings_config, map_prep, map_controller, …
  presentation/          # checklist_stats_display, rankings_display, map_renderer, …
  app/
    streamlit/           # Streamlit orchestration and tab modules
```

## Current status

- **Run:** `streamlit run explorer/app/streamlit/app.py` from repo root (`app.py` prepends repo root to `sys.path`).
- **Tests:** `pytest.ini` uses `pythonpath = .` only.
- **Optional later:** Editorial doc pass (Jupyter legacy wording, etc.).

## Former phased checklist (all addressed)

- Phase 1–2 boundary and Streamlit migration — done (see issue #70).
- Phase 3 — `streamlit_app` shims removed; library split into `core` / `presentation`; `map_prep` / `settings_config` naming in core.
