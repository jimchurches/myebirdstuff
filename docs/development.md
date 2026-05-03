# Development Guide — Personal eBird Explorer

Guidance for developers and contributors.

For AI-assisted coding, see **[AI_CONTEXT.md](AI_CONTEXT.md)** and follow those rules first.

**Detailed Streamlit UI notes** (guidelines, run behaviour, HTML/table patterns): [explorer/app/streamlit/README.md](../explorer/app/streamlit/README.md)

---

# Overview

This repository contains:

| Component | Purpose |
|----------|--------|
| Streamlit app | Primary UI for exploring personal eBird data |
| Core modules (`explorer/core`) | Data loading, stats, filtering, map logic |
| Presentation (`explorer/presentation`) | HTML + Folium rendering helpers |
| GPS script | Converts coordinates → location names (used by automation) |
| UI.Vision macros | Browser automation for eBird workflows |
| Tests | Validation of logic and data handling |

---

# Python version

CI runs **Python 3.12** (see `.github/workflows/tests.yml`). Contributors should use **3.12** locally so behaviour matches automated tests.

We **do not** bump the documented interpreter just to stay on the newest Python release. Reasons:

- **Stack compatibility** — Scientific and UI dependencies (pandas, Streamlit, Folium, binary wheels) often trail the latest Python; upgrading adds churn and risk for limited benefit if the project already runs cleanly on 3.12.
- **Alignment** — Local installs, CI, and docs should stay in step. Changing the version is a deliberate, coordinated update (CI workflow, install docs, and smoke-testing the app), not a silent assumption.

**When upgrading** (for example to 3.13 or later) makes sense: a dependency requires it, you need a language or standard-library feature not available on 3.12, or you have time to run the full test suite and verify Streamlit on a branch before merging.

Patch releases within the same minor line (for example 3.12.3 vs 3.12.7) are fine and do not require doc changes.

---

# Architecture Overview (Streamlit App)

```
CSV (eBird export)
    ↓
data_loader
    ↓
canonical dataframe
    ↓
core modules
    ↓
map rendering
    ↓
Streamlit UI
```

**Key rule:** UI is thin. Logic lives in modules.

---

# Data Flow (Simplified)

| Step | Description |
|------|------------|
| Load | CSV loaded via `data_loader` |
| Normalise | Datetime + protocol normalisation |
| Working set | Optional filtered dataset rebuild |
| Compute | Stats, rankings, species logic |
| Render | Map + HTML tables |
| Display | Streamlit UI |

---

# Core Modules (Responsibilities)

| Module | Responsibility |
|--------|---------------|
| data_loader | Load CSV, validate, normalise datetime |
| species_logic | Filtering + countable species rules |
| stats | Rankings, summaries, country stats |
| working_set | Rebuild filtered dataset |
| map_controller | Map orchestration (entry point; see `map_overlay_*` under `explorer/core/`) |
| map_renderer | Folium + popup rendering |
| taxonomy | eBird taxonomy lookup |
| duplicate_checks | Maintenance checks |
| checklist_stats_* | Stats + display formatting |
| maintenance_display | Maintenance UI output |
| species_search | Whoosh-based autocomplete |

---

# Supporting Components

## GPS Script

- Converts GPS → readable names
- Uses Google **Geocoding** API (reverse geocode)
- Has:
  - internal test function
  - standalone test file
- Used by UI.Vision macros

⚠️ Changes here affect automation workflows

---

## UI.Vision Macros

- Automate eBird checklist workflows
- Depend on GPS script output
- External to Python app but tightly coupled

⚠️ Treat as part of the system

---

# Design Principles

## Data

## Imports and layering (discoverability)

- **Prefer explicit submodule imports in new code**: e.g. `from explorer.core.stats import yearly_summary_stats`.
- Treat `explorer.core` (the package entry module `explorer/core/__init__.py`) as a **compatibility barrel**.
  It re-exports some presentation helpers and uses **lazy imports** for optional heavy stacks.
- If your IDE can’t jump to definitions for lazy names, import from the defining module directly
  (for example `explorer.presentation.map_renderer`) or search for the name in
  `explorer/core/__init__.py` under `_LAZY_IMPORTS`.

- Dataset is static during runtime
- No mutation of main dataframe
- Rebuild working sets when filtering

---

## Caching

- Simple in-memory caching
- Cache:
  - groupbys
  - popup HTML
- Ensure cache invalidation remains correct

---

## Separation of Concerns

| Layer | Responsibility |
|------|---------------|
| Streamlit | UI only |
| Core modules | Logic + computation |
| Presentation | HTML + map rendering |

---

## Streamlit Guidelines

The full write-up lives in **[explorer/app/streamlit/README.md](../explorer/app/streamlit/README.md)** (UI guidelines, local run, defaults, and formatter rules). The bullets below stay high level.

- Use native components where possible
- Use HTML formatters for rich tables
- Do not duplicate HTML in UI
- Keep eBird links

**Map/theme tweakables** (clustering, pin geometry, colours, layout) live in:

```
explorer/app/streamlit/defaults.py
```

**Fixed UI strings and URLs** (tab names, spinner emoji strip, footer links) live in `explorer/app/streamlit/streamlit_ui_constants.py`. **Persisted settings schema defaults** (YAML-backed) live in `explorer/core/settings_schema_defaults.py`.

### Map marker colour schemes (data model and usage)

Presets are **frozen dataclasses** in `explorer/core/map_marker_scheme_model.py`: a top-level `MapMarkerColourScheme` bundles `global_defaults` (default fill/stroke hex, radius, fill opacity, stroke weight) plus nested styles for each map mode — e.g. `all_locations` (visit pins + optional `cluster` tier colours), `species_locations`, `species_map_background`, `lifer_locations`, `family_locations` (required `density_fill_hex` + `legend_highlight_band_index`; optional `density_stroke_hex`, radii, stroke weights, optional `highlight_stroke_hex` / halo fields, fill opacity — omit `highlight_stroke_hex` to keep the species-highlight pin’s edge on the same **density-band** stroke as non-highlight pins; other unset fields follow `map_marker_colour_resolve`). Popup width and initial `fit_bounds` for the **family-locations** map are **not** part of the colour scheme; they live as `MAP_FAMILY_MAP_*` constants in `explorer/app/streamlit/defaults.py` (see `explorer/core/family_map_folium.py`).

**Where presets live:** `explorer/app/streamlit/defaults.py` as `MAP_MARKER_COLOUR_SCHEME_1`, `_2`, and `_3` — all three are **production** presets shipped with Explorer (not experimental placeholders). The active index is `MAP_MARKER_ACTIVE_COLOUR_SCHEME`; `active_map_marker_colour_scheme(index)` returns the scheme used by the app and tests. New slots require wiring in that helper.

**Resolution:** `explorer/core/map_marker_colour_resolve.py` turns scheme + optional overrides into concrete Folium colours and geometry. Per-channel rules are documented there (fill/stroke independently: role-specific hex, then globals, then scheme defaults / catch-all). Call sites include species-filtered visit pins (`resolve_species_visit_pin` — roles such as species emphasis, lifer, last-seen, background), lifer-locations map (`resolve_lifer_overlay_pin_params` — lifer vs subspecies), and family density bands (`resolve_family_band_colours`). Folium builders under `explorer/core/` (e.g. `map_overlay_visit_map.py`, `family_map_folium.py`) consume those helpers so the design utility and production maps stay aligned.

Omitted or `None` per-collection fields are intended to **inherit** `global_defaults` where the model allows it (including optional `family_locations.fill_opacity`); the design utility’s export tab emits sparse Python to match (see `explorer/presentation/design_map_export.py`).

### Map marker colour design utility (developers)

The main explorer does **not** expose this in the product UI; it is a **developer-only** Streamlit app for building and sanity-checking `MapMarkerColourScheme` presets in `explorer/app/streamlit/defaults.py` before merge.

**Run** (repository root):

```
streamlit run explorer/app/streamlit/design_map_app.py
```

| Piece | Location |
|-------|----------|
| Streamlit UI (sliders, export) | `explorer/app/streamlit/design_map_app.py` |
| Dummy Folium preview map | `explorer/presentation/design_map_preview.py` |
| Paste-ready export | `explorer/presentation/design_map_export.py` |
| Hierarchical hex resolution (shared with production maps that use schemes) | `explorer/core/map_marker_colour_resolve.py` |
| Preset dataclasses / registration | `explorer/app/streamlit/defaults.py` |

**All locations — MarkerCluster “cluster icons”:** the plugin expects the same DOM as its default `iconCreateFunction` — **one** inner `<div>` wrapping the count `<span>`. Extra nested divs interact badly with `.marker-cluster div { … }` sizing rules and look offset or triple-stacked. Custom colours in this repo use that single inner div: **fill** = `background-color`, **border** = `border`, **halo** = a `box-shadow` ring, and the default tier background on the icon root is cleared so it does not add another coloured layer. Hex tier colours sit on `MapMarkerClusterStyle` under **`all_locations.cluster`**; optional **opacity** and **spread/width** fields there (`inner_fill_opacity`, `halo_opacity`, `border_opacity`, `halo_spread_px`, `border_width_px`; defaults `MAP_MARKER_CLUSTER_*_DEFAULT` in `defaults.py`) approximate the plugin’s semi-transparent rgba layers without nested divs. Implementation: `explorer/core/map_overlay_visit_map.py`.

> The website [Coolors](https://coolors.co/?home) is an excellent resource when working on colour schemes.

---

# Testing

## Testing workflow

```
pytest tests/ -v
```

Optional coverage (same package scope used by CI):

```
pytest tests/ -v --cov=explorer --cov-report=term-missing
```

### Signal-over-coverage policy

- Use automated tests where they catch real regressions:
  - pure logic and data transforms,
  - hot paths used across tabs/maps,
  - bug fixes and edge-case handling.
- Prefer focused, table-driven tests for fragile logic (for example family/taxonomy grouping logic when touched).
- Avoid broad Streamlit wiring or HTML-heavy snapshot tests when they mostly inflate coverage without meaningful failure signal.
- Keep CI coverage gates as baseline protection only; do not chase percentage increases for their own sake.

### Current scope

- Unit tests for `explorer/core` and presentation helpers under `tests/explorer/`.
- Integration fixture coverage for realistic eBird exports (see `tests/fixtures/ebird_integration_fixture_notes.md`).
- Focused guardrail tests for CI/runtime behavior (for example debug defaults and selected script checks).

### Optional higher-cost testing

- Browser E2E automation for Streamlit is optional and should be added only if manual smoke repeatedly misses impactful UI regressions.
- For git-dependent behavior in `explorer/core/repo_git.py`, add/expand tests when there is an incident-driven need; avoid brittle over-mocking for low-value paths.
- Minimal Playwright example tests live in `tests/explorer/test_streamlit_map_e2e.py` (map banner/legend/focus smoke checks). Local setup:
  - `pip install playwright`
  - `python -m playwright install chromium`
  - `pytest tests/explorer/test_streamlit_map_e2e.py -v`

---

## GPS Script Testing

- Internal test function
- Separate test file

---

# Development Guidelines

## Make small changes

- Prefer incremental updates
- Avoid large rewrites

---

## Preserve structure

- Do not move logic into UI
- Keep modules clean and testable

---

## Dependencies

Avoid adding new dependencies unless necessary.

---

# Refactor Guidance

- Maintain module boundaries
- Keep caching correct
- Document new behaviour
- Keep config handling consistent

---

# Performance Instrumentation Guardrails

Performance instrumentation from #179 is intentionally kept in the codebase (off by default) so
regressions can be diagnosed quickly without re-adding scaffolding.

- Keep the current perf switches and payload shape stable where practical:
  - `EXPLORER_PERF` enables session buffering/sidebar panel
  - `EXPLORER_PERF_LOG` mirrors events to logs as JSONL
- Avoid renaming/removing existing stage names unless there is a clear reason. If a rename is needed,
  document old -> new mapping in the PR/issue so historical comparisons stay meaningful.
- When changing known expensive paths (map build/embed, working-set rebuild, heavy tab rendering),
  update instrumentation in the touched area (`perf_span`, `perf_fragment`, `perf_record_point`).
- Map prep uses **two** sidebar spinners (map + Folium first, then checklist/rankings/maint caches and
  tab sync) so large exports can show the map before the heaviest non-map work finishes (#179).
- Instrumentation should remain lightweight and optional: no behaviour changes when disabled.
- For map/perf-related changes, run at least one focused before/after journey and include key stage
  medians or representative timings in issue/PR notes.

### Explorer E2E (Playwright) and perf guardrails

- **Smoke + journeys** (fixture CSV via temp `config`): `pip install playwright` ·
  `python -m playwright install chromium` ·  
  `pytest tests/explorer/test_streamlit_map_e2e.py tests/explorer/test_streamlit_journeys_e2e.py -m e2e -v`
- **Opt-in perf + JSONL capture** (sets ``EXPLORER_PERF_LOG_FILE`` in the test fixture):  
  `pytest tests/explorer/test_map_perf_e2e.py --perf -v`  
  Loose ceilings live in **`benchmarks/map_perf/stage_ceilings.json`** (see **`benchmarks/map_perf/README.md`**).
- **Your real export instead of the tiny integration fixture** — copy is written under pytest’s temp dir (your file is not modified):  
  `export EXPLORER_E2E_DATASET_CSV=/path/to/MyEBirdData.csv`  
  When that variable is set, tests use longer **HTTP** (120s) and **map banner** (180s) waits. Override with ``EXPLORER_E2E_HTTP_TIMEOUT_S`` and ``EXPLORER_E2E_MAP_TIMEOUT_MS`` if needed.
- **Keep perf JSONL after the perf test** (optional):  
  `export EXPLORER_E2E_PERF_JSONL_ARCHIVE=/path/to/last_run.jsonl`  
  then run **`pytest … --perf`**; archive **`benchmarks/map_perf/snapshots/last_run.jsonl`** is gitignored. Feed it to **`scripts/snapshot_explorer_perf_log.py`** for a dated JSON snapshot.

---

# Configuration

- YAML configs for data paths
- Streamlit: `defaults.py` (map/theme tweakables), `streamlit_ui_constants.py` (fixed UI strings/URLs), `settings_schema_defaults.py` (persisted settings schema) — see Streamlit Guidelines above

---

# AI Guardrails (Summary)

- No architectural rewrites without instruction
- Prefer incremental changes
- Keep UI thin
- Do not add dependencies unnecessarily
- Ask when unsure

---

# Summary

- Data is static
- UI is thin
- Logic is modular
- Caching is simple
- Supporting scripts are part of the system
