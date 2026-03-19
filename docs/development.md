# Development guide: Personal eBird Explorer

Guidance for developers and contributors. For AI-assisted coding, see [AI_CONTEXT.md](AI_CONTEXT.md) and follow the **AI Coding Rules** there. (refs #48)

---

## Architecture overview

Data flow:

1. **CSV** — User’s eBird export (`MyEBirdData.csv` or custom path).
2. **data_loader** — Loads CSV, validates columns, adds canonical `datetime` column. Returns a single DataFrame.
3. **Notebook (data prep)** — Applies optional date filter, builds `location_data`, `records_by_loc`, Whoosh index, lifer/last-seen lookups. Dataset is static for the session.
4. **Statistics modules** — `stats`, `species_logic`, `duplicate_checks` provide rankings, species filtering, map-maintenance data. All operate on the DataFrame or derived structures.
5. **map_renderer** — Builds Folium map, popups, banners, legend HTML. Receives data; no notebook globals.
6. **Notebook (UI)** — Widgets (search, dropdown, checkbox, buttons), event handlers, and a single `draw_map_with_species_overlay()` that uses the precomputed structures and calls into `map_renderer`.

The notebook is a thin UI layer: it wires widgets to state and calls module APIs. Core logic lives in `personal_ebird_explorer/*.py`.

---

## Module responsibilities

| Module | Role |
|--------|------|
| **data_loader** | Load CSV, validate columns, add `datetime` column. Single entry point: `load_dataset(path)`. |
| **path_resolution** | Resolve data file path (hardcoded, config, or fallbacks). Used by the notebook to find the CSV. |
| **species_logic** | Species filtering (`filter_species`), countable-species logic, base-species for lifer/last-seen. |
| **stats** | Rankings, yearly summary, streak calculation, safe count parsing. Pure functions on DataFrame. |
| **duplicate_checks** | Exact and near-duplicate location detection for the Map maintenance tab. |
| **ui_state** | Lightweight app state (e.g. `ExplorerState` dataclass: selection, suppress flags). |
| **map_renderer** | Folium map creation, popup/banner/legend HTML builders, lifer/last-seen resolution, location classification. No widget or notebook references. |
| **region_display** | Convert ISO country and subdivision (state/province) codes to human-readable names at display time. Used by rankings_display. |
| **rankings_display** | HTML builders for rankings tables (scroll wrapper, location 5-col, visited, seen-once, rank tables). Used by the notebook when rendering Checklist Statistics rankings. |
| **taxonomy** | eBird taxonomy lookup for species links (refs #56). Fetches taxonomy once from eBird API (no key); optional `locale` (e.g. `en_AU`) so common names match the user’s export. Provides `get_species_url(common_name)` and `get_species_lifelist_url(common_name)` for species only. Locale is set via notebook user variable **EBIRD_TAXONOMY_LOCALE**. On API failure, lookups return None and the notebook continues without links. |

The notebook owns: widget creation, observers, Whoosh index creation, data-prep groupbys and caches, and the single `draw_map_with_species_overlay()` that orchestrates the map.

---

## Design principles

- **Dataset is static at runtime** — Load once; no live refresh. Caching (e.g. `records_by_loc`, popup HTML cache) is valid for the session.
- **Caching strategy** — In-memory, simple. Location groupbys and popup HTML are cached to avoid recomputation on redraw. Cache keys include enough context (e.g. location ID, species, date-filter view) to avoid stale data.
- **Separation of UI and logic** — Notebook: widgets, event handlers, and orchestration. Modules: data loading, statistics, map rendering. Do not move business logic into the notebook.
- **Jupytext** — The notebook is paired with `personal_ebird_explorer.py` (percent format). Use `jupytext --sync` to keep them in sync.

---

## Testing workflow

- **Location:** Tests live under `tests/`, with `tests/explorer/` for explorer-specific tests and `tests/conftest.py` for shared fixtures.
- **Runner:** `pytest tests/ -v` (also used in CI).
- **Scope:** Unit tests for data_loader, path_resolution, species_logic, stats, duplicate_checks, ui_state, map_renderer, region_display, rankings_display, taxonomy. No notebook execution in the test suite.
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
