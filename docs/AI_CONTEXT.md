# AI Context for Personal eBird Explorer

This document provides context and guardrails for AI coding assistants (Cursor, Copilot, ChatGPT) working in this repository.

**Read this before suggesting architectural or structural changes.**

---

## Project Purpose

Personal eBird Explorer visualises a user's personal eBird data.

It supports exploration of:

- checklist locations (map-based)
- species-specific observations
- visit statistics
- first/last seen data

Primary interface: **Streamlit app** with a **Leaflet** map custom component (four Map-tab modes; no Folium in production)

---

## Repository Scope (IMPORTANT)

This repository contains more than just the Streamlit app.

### Streamlit App (Primary UI)
- Main application for exploring eBird data
- Located under `explorer/`

### GPS Location Script
- Standalone Python script used to convert GPS coordinates into human-readable location names
- Uses Google Maps API
- Includes:
  - internal test function
  - separate test file
- This script is also used by automation workflows

### UI.Vision Macros
- Browser automation macros for eBird workflows
- Used for:
  - creating/editing checklists
  - applying formatted location names
- These depend on the GPS script for location naming

---

## Python Style Guide

**[`docs/python-style-guide.md`](python-style-guide.md) is the single source of truth for Python style, readability, naming, comments, docstrings, and related code review expectations in this project.**

Read it before writing or reviewing Python in this repository.

The short version:

- Prefer clear names over abbreviations.
- Keep functions small and single-purpose.
- Write comments that explain *why*, not *what*.
- Use docstrings for all public functions and modules.
- Do not hardcode magic values — give them names in the right constants file.
- Do not rewrite working code purely for style compliance.

---

## Core Principles (Follow These First)

### 1. Prefer small changes

- Make incremental improvements
- Avoid large rewrites unless explicitly requested

---

### 2. Keep logic out of the UI

- Streamlit = UI layer only
- Core logic belongs in modules
- Do not embed complex logic in UI code

---

### 3. Respect the data model

- CSV is loaded once
- Data is **static during runtime**
- Do not mutate the main dataframe

Caching relies on this assumption.

---

### 4. Do not break caching

Caching is simple and in-memory.

Be careful when modifying:
- grouping logic
- filtering
- popup generation

Preserve cache correctness.

---

### 5. Prefer readability over cleverness

- Code should be easy to understand later
- Avoid unnecessary abstraction or optimisation

See **[`docs/python-style-guide.md`](python-style-guide.md)** for concrete guidance on naming, comments, functions, and docstrings.

---

### 5.5. Code as if you are being mentored (and graded)

Assume an experienced teacher/mentor is reviewing every change for **readability, discoverability, and maintainability**.

Act like you are writing for:

- a Year 12 student who is learning good engineering habits, and
- a future maintainer who did not write the code.

Expectations (the “marking rubric”):

- Prefer **clear names** over abbreviations (`date_filter_status_line` not `dfs`).
- Keep **functions small** and single-purpose; split large modules when they become hard to navigate.
- Make invariants obvious (e.g. document hidden/workframe columns like `_base`, `_family` at the point they are introduced).
- Avoid “magic”: centralize shared strings/keys/constants, avoid clever indirection unless it pays for itself.
- Choose the simplest design that keeps the UI thin and the logic testable.
- Optimise only when necessary, and do it transparently (measure → change → re-check).

See **[`docs/python-style-guide.md`](python-style-guide.md)** for the full project standard, including the guiding mindset.

---

### 6. Avoid unnecessary dependencies

Do not introduce:
- new frameworks
- databases
- heavy UI libraries

The project is intentionally lightweight.

---

### 7. Git discipline (IMPORTANT)

- Do not commit or push code without explicit user direction
- Always write clear commit messages
- Reference GitHub issues in commits when applicable

---

## Architecture Overview (Streamlit App)

```
CSV (eBird export)
    ↓
data_loader.py
    ↓
canonical dataframe
    ↓
core logic modules (stats, geojson builders, …)
    ↓
presentation (HTML tables, map banners/legends, theme CSS)
    ↓
Streamlit UI + Leaflet component iframe (Map tab)
```

**Key rule:** UI stays thin, logic stays in modules.

**Map stack:** Production maps use `explorer/components/all_locations_map/` (Streamlit `declare_component` + committed React build). Python builds GeoJSON and structured popup payloads in `explorer/core/*_locations_geojson.py`; prep and session LRU live in `app_prep_map_ui.py`. Do not reintroduce Folium unless explicitly requested.

**Map perf history (#222):** `docs/explorer/issue-222-plain-summary.md`, `issue-222-section-8-baseline.md`, `issue-222-section-8-prior-art.md` — keep when editing architecture text.

---

## Streamlit Guidelines

Streamlit is the **primary UI**.

### Use native components first

- `st.dataframe`, `st.tabs`, `st.columns`, etc.
- simple metrics and key/value views

---

### Use shared HTML formatters when needed

Use formatter modules when tables require:

- embedded links (species, locations)
- mixed styling
- richer layout than `st.dataframe`

Render using:

- `st.markdown(..., unsafe_allow_html=True)`
- or `st.html`

Do not duplicate HTML in UI code — use shared formatters.

---

### Keep links

- Do not remove eBird links just to fit `st.dataframe`
- Prefer formatter-based tables when needed

---

### Defaults

- **`explorer/data/basemaps.yaml`** — **Map basemaps** (keys, labels, tile URLs); loaded by `explorer/core/basemap_manifest.py`. Regenerate React assets with `python3 scripts/generate_basemap_assets.py`.
- **`explorer/app/streamlit/defaults.py`** — **Developer tweakables** you edit for look/behaviour without hunting core modules: map cluster options, pin **size / stroke / opacity**, viewport/framing guards, **map marker colour scheme presets** (`MAP_MARKER_COLOUR_SCHEME_*`), theme hex, layout widths, cache sizes, temporary map debug (live zoom), spinner **theme CSS** cache-key suffix. Also a **re-export façade** for basemap labels/schema map-height bounds and share-summary defaults — those literals are **not** owned here (edit the defining module; section headers in the file label façade imports).

- **Map marker design utility** — separate Streamlit app (not user-facing): `streamlit run explorer/app/streamlit/design_map_app.py`. Previews roles and exports scheme dicts into `defaults.py`; dataclass shapes live in `explorer/core/map_marker_scheme_model.py`. See [development.md](development.md#map-marker-colour-design-utility-developers).

- **`explorer/app/streamlit/streamlit_ui_constants.py`** — **Fixed UI content**: tab labels, species-search widget strings, spinner **text** and emoji list, export filename, sidebar footer URLs. Not “tweak colour/size” defaults.
- **Map HTML export UX** — Shipped one-click sidebar export; alternative two-button design and browser-risk notes: [docs/explorer/map-html-export-ux-alternative.md](explorer/map-html-export-ux-alternative.md) (use if users report export/download failures).

- **`explorer/core/settings_schema_defaults.py`** — **Persisted YAML settings schema** defaults (tables, rankings bounds, taxonomy locale, maintenance distance, pin **colour** names allowed in settings). Owns `MAP_HEIGHT_PX_{MIN,MAX,DEFAULT}` and basemap default/options used by settings — re-exported from `defaults.py` as façade only.
- **`explorer/core/share_summary_defaults.py`** — **Share-summary card** colour schemes and layout stat defaults (#157); re-exported from `defaults.py` for a single Streamlit import surface (no duplicate literals in `defaults.py`).

Do not hardcode tunable numbers in UI files; use `defaults.py` (or the matching `explorer/core/*_defaults.py` module) for those. Prefer clarifying comments/section headers over large file splits unless an issue explicitly moves a block.

---

## Data & External API

- Dataset is static during runtime
- eBird taxonomy is fetched once at startup
- No API key required

If taxonomy fails:

- continue without links
- do not break the app

---

## Performance Approach

- Use simple in-memory caching
- Avoid recomputing:
  - groupbys
  - popup HTML
  - summaries

Optimise incrementally — do not redesign architecture.

---

## Performance Instrumentation (do not remove casually)

Instrumentation added in #179 is part of the developer toolkit and should stay available:

- `EXPLORER_PERF=1` enables performance event capture + sidebar debug panel.
- `EXPLORER_PERF_LOG=1` also emits JSONL records to logs; `EXPLORER_PERF_LOG_FILE=/path/to/file.jsonl` appends the same records (useful for subprocess tests).
- Keep instrumentation off by default and low-overhead when disabled.
- Do not remove or broadly rename stage keys without a clear reason; preserving continuity helps
  compare new runs with historical issue data.
- When touching expensive paths, add/update nearby `perf_span` / `perf_fragment` /
  `perf_record_point` calls so before/after benchmarks remain possible.

---

## Testing

### Streamlit / Core Logic
- data loading and parsing
- filtering and normalisation
- stats and rankings
- taxonomy lookup

### GPS Script
- has its own internal test function
- also includes standalone test file

Guidelines:

- new logic → put in testable modules
- avoid logic in UI

Run:

```
pytest tests/ -v
```

---

## Safe Changes

AI may safely:

- improve documentation
- improve comments
- add tests
- make small performance improvements
- add minor features

---

## Use Caution With

Do not change without discussion:

- data loading pipeline
- caching model
- map rendering structure
- GPS script behaviour (used by automation)
- UI.Vision macros (external workflow dependencies)

---

## When Unsure

If a change might affect:

- architecture
- caching
- data flow
- automation workflows

→ describe the approach before implementing

---

## Development Direction

- Streamlit remains the primary UI
- Core logic should remain modular and testable
- Supporting tools (GPS + macros) must remain compatible

---

## Summary (Mental Model)

- Data is static
- UI is thin
- Logic lives in modules
- Caching must remain simple
- Supporting scripts are part of the system
- Prefer clarity over cleverness
