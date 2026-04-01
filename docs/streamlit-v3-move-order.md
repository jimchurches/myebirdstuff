# Streamlit v3 move order (end-state prep)

**Document status — closed as a planning guide.** Phases **1–2** and **Phase 3 shim removal** are **done** (canonical entry: `streamlit run explorer/app/streamlit/app.py`; the old `streamlit_app/` package was removed). Remaining **Phase 3** items are optional **docs polish** and **optional** `personal_ebird_explorer` → `explorer/core` reshaping.

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
2. ~~Standardize Streamlit imports (`streamlit_app.<module>` consistently).~~ (canonical: `explorer.app.streamlit`.)
3. ~~Replace private helper dependency in Country tab (`_sort_country_sections`).~~ (public `sort_country_sections_for_display` API)
4. ~~Remove dead Checklist Statistics `species_url_fn` wiring.~~

### Phase 2 — package move — **done**

5. **Deferred / optional:** Copy/move non-UI shared modules from `personal_ebird_explorer/` into `explorer/core/` and `explorer/presentation/`. Today those directories exist as **skeleton packages**; framework-agnostic logic still lives primarily in `personal_ebird_explorer/`. Doing this move is **not required** for v3 merge; treat as future tidy-up if you want a stricter tree.
6. ~~Move Streamlit modules from `streamlit_app/` to `explorer/app/streamlit/`.~~ **Done.** ~~Compatibility shims~~ removed; use `streamlit run explorer/app/streamlit/app.py`.
7. **Partial:** Tests remain under `tests/explorer/` with `test_streamlit_*` naming; a physical split to `tests/streamlit/` is optional.

### Phase 3 — deprecations and deletion — **partially done**

8. ~~Remove legacy session-state bridges~~ (done: #93).
9. **Docs / narrative:** Remove remaining legacy UI references (Jupyter-first wording, etc.) in a **manual doc pass**; there is no notebook UI in-repo today.
10. ~~**Mechanical:** Remove `streamlit_app/*.py` shims, switch docs/CI to **`streamlit run explorer/app/streamlit/app.py`**, imports/tests use `explorer.app.streamlit` only.~~ **Done.**

## Checklist per move PR (use on future hardening PRs)

- [ ] `pytest tests/explorer -q` (or updated equivalent) passes — repo root is on `PYTHONPATH` via `pytest.ini` (`pythonpath = .`) and import mode is `importlib`, so the top-level `explorer` package is not confused with `tests/explorer/`.
- [ ] Streamlit-focused tests run in CI
- [ ] `streamlit run ...` smoke run works locally
- [ ] docs updated for any path/command changes

## Current status (snapshot)

- **Canonical Streamlit implementation:** `explorer/app/streamlit/*.py`
- **Entry:** `streamlit run explorer/app/streamlit/app.py` (from repo root)
- **Library:** `personal_ebird_explorer/` — shared map/settings/stats logic (not yet split into `explorer/core/` beyond placeholders)
- **Skeleton:** `explorer/core/`, `explorer/presentation/` — reserved for optional future moves

