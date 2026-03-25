# Streamlit v3 move order (end-state prep)

This document defines a safe, incremental move path toward the agreed v3 structure:

- product branding: **Personal eBird Explorer**
- code package root: **`explorer/`**
- keep UI/runtime adapter separate from framework-agnostic logic

## Target structure

```text
explorer/
  core/                  # framework-agnostic logic (data, stats, taxonomy, map prep)
  presentation/          # HTML/table builders shared across UIs
  app/
    streamlit/           # Streamlit-specific app orchestration and tab modules
```

## Migration principles

1. Keep each PR small and runnable.
2. Move imports first, then files.
3. Avoid simultaneous logic refactors and path moves in one PR.
4. Keep Streamlit tests required on every PR.
5. Remove temporary compatibility only after all call sites are moved.

## Recommended issue-by-issue order

### Phase 1 — boundary cleanup (no runtime move yet)

1. Decouple `personal_ebird_explorer` from `streamlit_app.defaults`.
2. Standardize Streamlit imports (`streamlit_app.<module>` consistently).
3. Replace private helper dependency in Country tab (`_sort_country_sections`).
4. Remove dead Checklist Statistics `species_url_fn` wiring.

### Phase 2 — package move with compatibility shims

5. Copy/move non-UI shared modules:
   - from `personal_ebird_explorer/` to `explorer/core/` and `explorer/presentation/`
   - keep temporary re-export shims in old paths.
6. Move Streamlit modules:
   - from `streamlit_app/` to `explorer/app/streamlit/`
   - keep a thin compatibility entrypoint in `streamlit_app/app.py` temporarily.
7. Move tests to mirror structure (`tests/core`, `tests/streamlit`) and update imports.

### Phase 3 — deprecations and deletion

8. Remove legacy session-state bridges (`streamlit_yearly_country` fallback).
9. Delete notebook-specific references/docs and retire `notebooks/`.
10. Remove compatibility shims and old module paths when grep confirms no references.

## Checklist per move PR

- [ ] `pytest tests/explorer -q` (or updated equivalent) passes
- [ ] Streamlit-focused tests run in CI
- [ ] `streamlit run ...` smoke run works locally
- [ ] docs updated for any path/command changes

## Current status

- Skeleton package added:
  - `explorer/`
  - `explorer/core/`
  - `explorer/presentation/`
  - `explorer/app/streamlit/`
- No runtime files moved yet.

