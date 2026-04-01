# Streamlit v3 move order (end-state prep)

**Document status — closed as a planning guide.** Phases **1** and **2** (Streamlit code under `explorer/app/streamlit/`, shims in `streamlit_app/`) are **done**. **Phase 3** is optional **hardening** (remove shims, optional package reshaping); track as its own small PRs or issues when you want a tidier repo, not as a blocker for merging the v3 branch to `main`.

You can **delete this file** when you no longer need it in the working tree; Git history keeps prior versions.

---

This document defined a safe, incremental move path toward the agreed v3 structure:

- product branding: **Personal eBird Explorer**
- code package root: **`explorer/`** (app + Streamlit modules live here)
- keep UI/runtime adapter separate from framework-agnostic logic (`personal_ebird_explorer/` remains the shared library for now)

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

### Phase 1 — boundary cleanup (no runtime move yet) — **done**

1. ~~Decouple `personal_ebird_explorer` from `streamlit_app.defaults`.~~
2. ~~Standardize Streamlit imports (`streamlit_app.<module>` consistently).~~ (canonical code imports `explorer.app.streamlit`; shims re-export.)
3. ~~Replace private helper dependency in Country tab (`_sort_country_sections`).~~ (public `sort_country_sections_for_display` API)
4. ~~Remove dead Checklist Statistics `species_url_fn` wiring.~~

### Phase 2 — package move with compatibility shims — **done** (shims intentionally remain)

5. **Deferred / optional:** Copy/move non-UI shared modules from `personal_ebird_explorer/` into `explorer/core/` and `explorer/presentation/`. Today those directories exist as **skeleton packages**; framework-agnostic logic still lives primarily in `personal_ebird_explorer/`. Doing this move is **not required** for v3 merge; treat as future tidy-up if you want a stricter tree.
6. ~~Move Streamlit modules from `streamlit_app/` to `explorer/app/streamlit/`.~~ **Done.** Keep a thin compatibility entrypoint in `streamlit_app/app.py` (and sibling shim modules) until Phase 3.
7. **Partial:** Tests remain under `tests/explorer/` with `test_streamlit_*` naming; a physical split to `tests/streamlit/` is optional.

### Phase 3 — deprecations and deletion — **hardening (optional)**

8. ~~Remove legacy session-state bridges~~ (done: #93).
9. **Docs / narrative:** Remove remaining legacy UI references (Jupyter-first wording, etc.) in a **manual doc pass**; there is no notebook UI in-repo today.
10. **Mechanical:** Remove `streamlit_app/*.py` shims (except possibly one bootstrap), switch docs/CI to **`streamlit run`** on the canonical module under `explorer/`, update imports/tests to `explorer.app.streamlit` only, then delete empty shim files when `grep` is clean.

## Checklist per move PR (use on future hardening PRs)

- [ ] `pytest tests/explorer -q` (or updated equivalent) passes — repo root is on `PYTHONPATH` via `pytest.ini` (`pythonpath = .`) and import mode is `importlib`, so the top-level `explorer` package is not confused with `tests/explorer/`.
- [ ] Streamlit-focused tests run in CI
- [ ] `streamlit run ...` smoke run works locally
- [ ] docs updated for any path/command changes

## Current status (snapshot)

- **Canonical Streamlit implementation:** `explorer/app/streamlit/*.py`
- **Entry:** `streamlit run streamlit_app/app.py` (shim imports `explorer.app.streamlit.app:main`)
- **Shims:** `streamlit_app/*.py` re-export `explorer.app.streamlit.*` for compatibility
- **Library:** `personal_ebird_explorer/` — shared map/settings/stats logic (not yet split into `explorer/core/` beyond placeholders)
- **Skeleton:** `explorer/core/`, `explorer/presentation/` — reserved for optional future moves

