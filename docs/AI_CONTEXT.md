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

Primary interface: **Streamlit app + Folium map**

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

Mindset:

> Write Python the way a highly regarded engineer who loves teaching would want it written:
> neat, easy to read, efficient where it matters, and easy to follow.

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
core logic modules
    ↓
map rendering
    ↓
Streamlit UI
```

**Key rule:** UI stays thin, logic stays in modules.

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

- **`explorer/app/streamlit/defaults.py`** — **Developer tweakables**: map cluster options, pin **size / stroke / opacity**, legend dot sizes, theme hex, basemap list, map height slider bounds, layout widths, temporary map debug (live zoom). Edit here to change look/behaviour without hunting core modules.

- **Map marker design utility** — separate Streamlit app (not user-facing): `streamlit run explorer/app/streamlit/design_map_app.py`. Previews roles and exports scheme dicts; see [development.md](development.md#map-marker-colour-design-utility-developers).

- **`explorer/app/streamlit/streamlit_ui_constants.py`** — **Fixed UI content**: tab labels, species-search widget strings, spinner text and emoji list, export filename, sidebar footer URLs. Not “tweak colour/size” defaults.

- **`explorer/core/settings_schema_defaults.py`** — **Persisted YAML settings schema** defaults (tables, rankings bounds, taxonomy locale, maintenance distance, pin **colour** names allowed in settings).

Do not hardcode tunable numbers in UI files; use `defaults.py` for those.

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
