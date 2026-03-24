# Development guide: Personal eBird Explorer

Guidance for developers and contributors. For AI-assisted coding, see [AI_CONTEXT.md](AI_CONTEXT.md) and follow the **AI Coding Rules** there. (refs #48)

---

## Architecture overview

Data flow:

1. **CSV** — User’s eBird export (`MyEBirdData.csv` or custom path).
2. **data_loader** — Loads CSV, validates columns, adds canonical `datetime` column, and normalizes **`Protocol`** to short labels when present (e.g. `eBird - Traveling Count` → `Traveling`; same mapping as checklist stats). Missing/no-recorded times use synthetic **23:59** so same-day sorting is stable (user-facing explanation: [explorer README — Missing checklist times](explorer/README.md#missing-checklist-times-synthetic-2359); refs #44).
3. **working_set** — After load, optional date filter rebuild: working DataFrame, `location_data`, `records_by_loc`, species list, totals, Whoosh repopulation, map-cache clears. Called from the notebook; same API usable from Streamlit (refs #66).
4. **Statistics modules** — `stats`, `species_logic`, `duplicate_checks` provide rankings, species filtering, map-maintenance data. All operate on the DataFrame or derived structures.
5. **map_renderer** — Folium map factory, popups, banners, legend HTML helpers. Receives data; no notebook globals.
6. **map_controller** — Map pipeline: ``build_species_overlay_map(...)`` → :class:`MapOverlayResult` (all locations, selected species, or lifer-only mode; refs #67, #71). Framework-neutral; notebook handles widget display.
7. **Notebook (UI)** — Widgets (map view mode, search, checkbox, buttons), event handlers, map tab output (double-buffer), and `draw_map_with_species_overlay()` calling **map_controller** with session caches and options.
8. **Streamlit (prototype)** — `streamlit_app/app.py`: upload or disk discovery via **explorer_paths**, `load_dataset`, then **map_controller.build_species_overlay_map** (all-locations mode) + **streamlit_folium** for Folium popups matching the notebook. Prep helper: **streamlit_map_prep.prepare_all_locations_map_context**. Strategy: [issue #70](https://github.com/jimchurches/myebirdstuff/issues/70).

The notebook is a thin UI layer: it wires widgets to state and calls module APIs. Core logic lives in `personal_ebird_explorer/*.py`.

**Package `__init__`:** Whoosh- and Folium-backed symbols (`whoosh_common_name_suggestions`, `build_species_overlay_map`, `create_map`, …) are loaded **lazily** via `__getattr__` so lightweight imports (e.g. `data_loader`, `explorer_paths` for Streamlit) do not require those dependencies.

**Country tab / Streamlit:** Per-country numbers are computed in **stats** (`country_summary_stats`) and exposed on **checklist_stats_compute**’s payload; **checklist_stats_display** renders HTML (including optional **Country** accordion sort via `country_sort`). A Streamlit app can call the same `compute_checklist_stats_payload` + `format_checklist_stats_bundle(..., country_sort=...)` without duplicating logic.

---

## Module responsibilities

| Module | Role |
|--------|------|
| **data_loader** | Load CSV, validate columns, add `datetime` column (missing times → synthetic 23:59 for sort order; see explorer README). Single entry point: `load_dataset(path)`. |
| **path_resolution** | Low-level helper: ``find_data_file(filename, candidate_dirs)``. |
| **explorer_paths** | Builds the same candidate folder list as the notebook / Streamlit (hardcoded → ``config_secret`` → ``config_template`` → anchor folder), then resolves the CSV. Shared by ``notebooks/personal_ebird_explorer`` and ``streamlit_app/app.py``. |
| **streamlit_map_prep** | Builds kwargs for ``build_species_overlay_map`` in all-locations mode (Streamlit; refs #70). |
| **species_logic** | Species filtering (`filter_species`), countable-species logic, base-species for lifer/last-seen. |
| **stats** | Rankings, yearly summary, **country summary** (`country_summary_stats` / `checklist_country_keys`), streak calculation, safe count parsing. Pure functions on DataFrame. |
| **duplicate_checks** | Exact and near-duplicate location detection for the Map maintenance tab. |
| **ui_state** | Lightweight app state (e.g. `ExplorerState` dataclass: selection, suppress flags). |
| **map_renderer** | Folium map creation, popup/banner/legend HTML builders, lifer/last-seen resolution, location classification. No widget or notebook references. |
| **map_controller** | ``build_species_overlay_map`` / ``MapOverlayResult``: all-species, species overlay, or lifer-only pins; uses ``aggregate_lifer_sites`` for lifer mode (refs #67, #71). |
| **region_display** | Convert ISO country and subdivision (state/province) codes to human-readable names at display time. Used by rankings_display. |
| **rankings_display** | HTML builders for rankings tables (scroll wrapper, location 5-col, visited, seen-once, rank tables). Used by the notebook when rendering Checklist Statistics rankings. |
| **taxonomy** | eBird taxonomy lookup for species links (refs #56). Fetches taxonomy once from eBird API (no key); optional `locale` (e.g. `en_AU`) so common names match the user’s export. Provides `get_species_url(common_name)` and `get_species_lifelist_url(common_name)` for species only. Locale is set via notebook user variable **EBIRD_TAXONOMY_LOCALE**. On API failure, lookups return None and the notebook continues without links. |
| **working_set** | Rebuild filtered working DataFrame and derived structures after date-filter changes: `rebuild_working_set_from_date_filter(...)` returns a `WorkingSet` or `None` on invalid range. Handles Whoosh repopulation and map popup/location caches when passed in (refs #66). |
| **lifer_last_seen_prep** | Full-dataset lifer/last-seen prep: `prepare_lifer_last_seen(full_df)` → `LiferLastSeenPrep`; `aggregate_lifer_sites` groups lifer species by location for lifer-only map mode (refs #68, #71). |
| **checklist_stats_compute** | Structured checklist stats / yearly / country / rankings inputs: `compute_checklist_stats_payload(df, top_n_limit)` → `ChecklistStatsPayload` or `None` if empty (refs #68). |
| **checklist_stats_display** | HTML bundle for Checklist Statistics + Yearly + Country tabs and rankings sections: `format_checklist_stats_bundle(payload, ..., country_sort=...)` (`alphabetical` / `lifers_world` / `total_species`); Rankings tab shell: `format_rankings_tab_html(...)` (refs #68, #69). |
| **maintenance_display** | Maintenance tab HTML: map duplicates/close locations, incomplete checklists, sex-notation sections (`format_*_maintenance_html`, composable helpers + CSS constants for Streamlit; refs #69, #79). |
| **species_search** | Whoosh species autocomplete helper: `whoosh_common_name_suggestions(index, query, ...)` (refs #69). |

The notebook owns: widget creation, observers, initial Whoosh index creation (empty schema + first fill), session caches, and map tab display (double-buffered output); it calls **map_controller**’s `build_species_overlay_map()` for the Folium map. Filter-driven rebuild logic lives in **working_set**.

**Jupytext:** `notebooks/personal_ebird_explorer.ipynb` is paired with `notebooks/personal_ebird_explorer.py` (percent format; see notebook metadata). After editing the `.py`, run `jupytext --sync notebooks/personal_ebird_explorer.py` so the `.ipynb` stays aligned (`pip install jupytext`).

---

## Design principles

- **Dataset is static at runtime** — Load once; no live refresh. Caching (e.g. `records_by_loc`, popup HTML cache) is valid for the session.
- **Caching strategy** — In-memory, simple. Location groupbys and popup HTML are cached to avoid recomputation on redraw. Cache keys include enough context (e.g. location ID, species, date-filter view) to avoid stale data.
- **Separation of UI and logic** — Notebook: widgets, event handlers, and orchestration. Modules: data loading, statistics, map rendering. Do not move business logic into the notebook.
- **Jupytext** — The notebook is paired with `personal_ebird_explorer.py` (percent format). Use `jupytext --sync` to keep them in sync.
- **Streamlit UI (prototype)** — Use **native Streamlit** for layouts and simple tables. For **rankings / list tables** that mirror the notebook (linked species, locations, datetimes, styled cells), **`st.dataframe` is not sufficient** — use **`st.markdown(..., unsafe_allow_html=True)`** or **`st.html`** with HTML from **`checklist_stats_display`**, **`rankings_display`**, and related formatters in `personal_ebird_explorer/`; avoid parallel HTML in `streamlit_app/`. See [AI_CONTEXT.md — Streamlit UI](AI_CONTEXT.md#streamlit-ui) and `streamlit_app/README.md` — *UI guidelines*.
- **Streamlit defaults (single place)** — Behaviour defaults for the Streamlit explorer (persisted settings, slider min/max, map/basemap/session-only values, copy strings, theme-related literals, etc.) belong in **`streamlit_app/defaults.py`**. Import from there in **`streamlit_app/app.py`**, in **`personal_ebird_explorer/streamlit_settings_config.py`** for anything saved in embedded YAML, and in Streamlit HTML helpers when they need the same numbers. That keeps discovery easy and avoids silent drift; **`tests/explorer/test_streamlit_defaults.py`** checks the persisted payload against the Pydantic model. (refs #70)

---

## Testing workflow

- **Location:** Tests live under `tests/`, with `tests/explorer/` for explorer-specific tests and `tests/conftest.py` for shared fixtures.
- **Runner:** `pytest tests/ -v` (also used in CI).
- **Scope:** Unit tests for data_loader, path_resolution, species_logic, stats, duplicate_checks, ui_state, map_renderer, map_controller, region_display, rankings_display, taxonomy, working_set, lifer_last_seen_prep, checklist_stats_compute, checklist_stats_display (rankings tab shell), maintenance_display, species_search. No notebook execution in the test suite.
- **Adding tests:** Prefer testing logic in modules. For new behaviour, add tests in the appropriate `tests/explorer/test_*.py` file.
- **Integration fixture:** Tests in `tests/explorer/test_integration_fixture.py` use `tests/fixtures/ebird_integration_fixture.csv`; expected values are documented in `tests/fixtures/ebird_integration_fixture_notes.md`. If you change the fixture, update the notes and the test constants in the test file together.

---

## Refactor guidance

- **Incremental changes** — Prefer small, reviewable edits over large rewrites.
- **Preserve boundaries** — Keep data loading, stats, and map rendering in modules; keep the notebook thin.
- **Caching** — If you change what drives the map (e.g. date filter, new grouping), ensure cache keys and invalidation stay consistent. Document any new cache in comments.
- **Config and paths** — Path resolution and config (e.g. `config_secret.py`, `config_template.py`) are documented in the notebook and in docs/explorer; avoid duplicating logic.
- **Dependencies** — Avoid new dependencies unless clearly necessary. Current stack: pandas, folium, ipywidgets, Whoosh, scikit-learn (for TF–IDF in search, if used), pycountry (country/state names in rankings tables).

---

## AI guardrails

**Important:** AI coding assistants should read [docs/AI_CONTEXT.md](AI_CONTEXT.md) before suggesting architectural changes. That file includes a **roadmap toward Streamlit** (or similar): not every task is migration work yet, but new logic should still favour **modules with clear APIs** so a future app can reuse it.

- **Avoid architectural rewrites** — Do not propose large restructures of the data pipeline or map rendering unless the user has asked for it.
- **Prefer incremental changes** — Small, targeted edits over broad refactors.
- **Maintain separation** — Keep the notebook as UI only; do not move logic from modules into the notebook.
- **Avoid unnecessary dependencies** — Do not add libraries for something the current stack can do.
- **Document uncertainty** — If something is unclear (e.g. behaviour, intent), say so rather than inventing behaviour.
