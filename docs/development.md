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
| map_controller | Map orchestration |
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

Defaults must live in:

```
explorer/app/streamlit/defaults.py
```

---

# Testing

## Running tests

```
pytest tests/ -v
```

Optional coverage:

```
pytest tests/ -v --cov=explorer
```

---

## Scope

- Unit tests for core modules
- Integration fixture available

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

# Configuration

- YAML configs for data paths
- Defaults centralised in Streamlit defaults module

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
