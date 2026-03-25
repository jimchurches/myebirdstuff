# Streamlit v3 — issue backlog (from #70 code review)

Parent: **#70** (Personal eBird Explorer — Streamlit / migration).

Use this document to open **child issues** under #70. Each section below is written so you can **copy the block** into a new GitHub issue (title + body). Labels are suggestions: **Enhancement** (default), **Bug** only where behaviour is wrong today.

**Conventions**

- **(Optional)** — nice-to-have; can ship v3 without it.
- **Depends on** — complete or plan together with the named item to avoid rework.

---

## 1. [Enhancement] Decouple `personal_ebird_explorer` from `streamlit_app.defaults`

**Type:** Enhancement  
**Optional:** No (foundational for package layout)

**Problem**

Core modules (`map_controller`, `map_renderer`, `streamlit_settings_config`) import constants (pin geometry, legend dots, etc.) from `streamlit_app.defaults`. That inverts layering: the explorer library depends on the Streamlit app package.

**Goal**

Move shared UI/geometry constants into a **neutral module** under `personal_ebird_explorer` (e.g. `ui_constants.py` or `map_constants.py`), or a small `explorer` package root after restructure. Update imports in `map_controller`, `map_renderer`, `streamlit_settings_config`, and tests. `streamlit_app.defaults` can re-export for backward compatibility during migration, then slim down.

**Acceptance**

- No `import streamlit_app` from `personal_ebird_explorer` except where explicitly intentional (e.g. none).
- Tests and Streamlit app still pass.

**Depends on**

- Coordinate with folder move (#70) if you do both in one branch; otherwise do this **before** moving Streamlit into explorer tree.

**Clarify if**

- You want a single “constants” module vs split map vs settings schema defaults.

---

## 2. [Enhancement] Unify `streamlit_app` import paths and entrypoint assumptions

**Type:** Enhancement  
**Optional:** No

**Problem**

`app.py` adds `streamlit_app/` to `sys.path` and imports **sibling** modules (`from map_working import …`, `from checklist_stats_streamlit_html import …`) while other code uses **`from streamlit_app.map_working import …`**. Behaviour depends on cwd / how Streamlit is launched.

**Goal**

- Standardise on **`streamlit_app.<module>`** imports everywhere in `streamlit_app/`.
- Document or enforce one supported command: e.g. `streamlit run streamlit_app/app.py` from repo root (or a `Makefile` / script).
- Align `tests/explorer/test_streamlit_map_working.py` imports with production style.

**Acceptance**

- Grep shows no bare `from map_working` / `from checklist_stats_streamlit_html` in app code (tests included unless exempt).

**Depends on**

- None, but pairs naturally with **§1** if you touch many imports at once.

---

## 3. [Enhancement] Stabilise Country tab dependency on private `checklist_stats_display` helpers

**Type:** Enhancement  
**Optional:** No (small, safe refactor)

**Problem**

`country_stats_streamlit_html.py` imports **`_sort_country_sections`** (private) from `checklist_stats_display`. Refactors to “private” helpers can break Country without a clear contract.

**Goal**

- Expose a **public** function (e.g. `sort_country_sections_for_display(...)`) with a short docstring, or document `_sort_country_sections` as supported API.
- Update Country tab to use the public name only.

**Acceptance**

- No imports of underscore-prefixed names from `checklist_stats_display` in Streamlit modules (unless explicitly documented).

---

## 4. [Enhancement] Remove legacy session-state bridge (`streamlit_yearly_country` → `streamlit_country_tab_country`)

**Type:** Enhancement (cleanup)  
**Optional:** Yes — only if you are comfortable dropping old browser sessions

**Problem**

`country_stats_streamlit_html.py` copies `streamlit_yearly_country` into `streamlit_country_tab_country` for older sessions.

**Goal**

After v3.0.0 with **no backward compatibility**, remove the fallback block and any docs referencing the old key.

**Acceptance**

- Grep finds no `streamlit_yearly_country` in codebase.

**Depends on**

- Release policy: ship only when you’re OK invalidating long-lived Streamlit sessions.

---

## 5. [Enhancement] Remove unused `species_url_fn` from Checklist Statistics Streamlit renderer

**Type:** Enhancement  
**Optional:** Yes

**Problem**

`render_checklist_stats_streamlit_html` accepts `species_url_fn` but does not use it (`_ = species_url_fn`).

**Goal**

- Remove `species_url_fn` from `render_checklist_stats_streamlit_html` and update call sites.
- Keep Checklist Statistics focused on checklist counts/types/hours (no species-name content planned).

**Acceptance**

- No dead parameter unless documented as reserved with a tracking issue.

---

## 6. [Enhancement] Single source for HTML table theme (green vs blue) across Streamlit tab modules

**Type:** Enhancement  
**Optional:** Yes

**Problem**

`_USE_EBIRD_BLUE_HTML_TAB_THEME` is duplicated in `checklist_stats_streamlit_html`, `yearly_summary_streamlit_html`, `country_stats_streamlit_html`, `maintenance_streamlit_html`.

**Goal**

- One constant or small helper (e.g. in `defaults.py` or `streamlit_theme.py`) that selects the correct `CHECKLIST_STATS_*_CSS` bundle.
- All tab modules read from that.

**Acceptance**

- One place to flip global table theme.

---

## 7. [Enhancement] DRY optional helper for scoped checklist CSS injection

**Type:** Enhancement  
**Optional:** Yes

**Problem**

Several modules repeat: concatenate `CHECKLIST_STATS_TABLE_CSS` + tab-surface CSS (+ extras), then `st.markdown(..., unsafe_allow_html=True)`.

**Goal**

- Add something like `inject_streamlit_checklist_css(extra_css: str = "", use_blue_theme: bool = False)` in a small Streamlit helper module.
- Refactor tab modules to use it (incremental OK).

**Depends on**

- Pairs with **§6** if you want one theme switch for both injection and bundle choice.

---

## 8. [Enhancement] Split `streamlit_app/app.py` into focused modules

**Type:** Enhancement  
**Optional:** Yes (large refactor; plan milestone)

**Problem**

`app.py` is ~1.4k lines: settings, data load, map, caches, fragments, CSS.

**Goal**

- Extract coherent units, e.g. `settings_state.py`, `data_loading.py`, `map_tab.py`, or mirror tab boundaries.
- Keep `app.py` as thin orchestration + `main()`.

**Acceptance**

- New modules have clear names; no circular imports; tests pass.

**Depends on**

- **§2** (import hygiene) reduces pain when moving files.

---

## 9. [Enhancement] Centralise Streamlit session-state key names

**Type:** Enhancement  
**Optional:** Yes

**Problem**

Many string keys and module-local `_SESSION_*` constants; risk of typos and hard-to-find bugs.

**Goal**

- Single module or class with **all** `streamlit_*` / internal keys as constants (or enum-like strings).
- Gradual migration from scattered literals.

**Acceptance**

- Documented pattern for new keys.

---

## 10. [Enhancement] Narrow or log broad `except Exception` in settings persistence

**Type:** Enhancement  
**Optional:** Yes

**Problem**

`streamlit_settings_config.py` (and parts of `app.py`) use broad exception handlers around config I/O.

**Goal**

- Catch expected failures (`OSError`, `yaml` errors, `ValidationError`) where possible.
- Log or surface a distinguishable message for unexpected errors in dev.

**Acceptance**

- No silent failures for “save settings” without user-visible feedback.

---

## 11. [Enhancement] Add automated coverage for Streamlit UI modules (smoke / integration)

**Type:** Enhancement  
**Optional:** Yes

**Problem**

Core explorer modules are tested; **`app.py` and tab `*_streamlit_html.py` files have little or no tests**.

**Goal (incremental)**

- **Smoke:** import `app` or `main` with Streamlit/mocks without full run (may be limited by Streamlit design).
- **Unit:** pure helpers extracted from fragments (e.g. CSS builder, payload sync) with no `st` calls.
- **CI:** ensure `requirements-streamlit.txt` installed so `test_streamlit_*` tests run.

**Acceptance**

- At least one new test file or expanded tests targeting extracted helpers; CI documented.

---

## 12. [Enhancement] Documentation pass for v3 (prototype wording, Settings paths, install)

**Type:** Enhancement  
**Optional:** No for release, but can trail code changes

**Problem**

Some docs still imply “prototype”, old tab names, or Binder-first flows.

**Goal**

- Align `streamlit_app/README.md`, `docs/explorer/*.md`, and `docs/AI_CONTEXT.md` with **Streamlit as primary** and notebook removal.
- Single “run locally / Cloud” story.

**Depends on**

- Final folder layout and entrypoint (**§1–2**).

---

## Suggested grouping into fewer GitHub issues

If you want **fewer** child issues under #70, merge as follows:

| Combined issue | Includes sections |
|----------------|-------------------|
| **Packaging & imports** | §1, §2, §3 |
| **Streamlit UX parity & cleanup** | §4, §5 |
| **Theming & CSS DRY** | §6, §7 |
| **Maintainability** | §8, §9 |
| **Hardening & tests** | §10, §11 |
| **Docs** | §12 |

---

## Open questions (resolve in #70 or per-issue)

1. Target package name after move: keep `streamlit_app` under `personal_ebird_explorer/` or rename?

## Decisions already made

- CI runs Streamlit tests on **every PR** (not optional).
- Checklist Statistics will **not** include species-name content; remove unused `species_url_fn` wiring.

---

*Generated from internal code review; edit freely before pasting into GitHub.*
