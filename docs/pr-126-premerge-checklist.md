# PR #126 Pre-Merge Checklist (Beta 2)

Scope reviewed: `main...beta-next` (PR #126), with `ruff` + full tests passing locally (`pytest tests/`).

## Must Address Before Merging to `main` (Beta 2)

- [x] **Fix landing-page typo in user-facing copy** (`explorer/app/streamlit/app_landing_ui.py`).
  - ~~Current heading is `Taxononmy` and should be `Taxonomy`.~~ Fixed: landing heading now reads `Taxonomy`.
  - Why now: visible polish issue on first-load UX.

- [x] **Run targeted manual smoke test on hosted notice flag path** (`explorer/app/streamlit/app_landing_ui.py`).
  - **Done (manual):** Verified with local `.streamlit/secrets.toml` and on Streamlit Community Cloud — `STREAMLIT_SHOW_HOSTED_PERFORMANCE_NOTICE` via `st.secrets` and env fallback; banner behaves as desired.
  - **Automated:** `tests/explorer/test_streamlit_ui_helpers.py` (`test_hosted_notice_*`) covers env truthy/falsey values, secrets-on, secrets-over-env, and env fallback when `st.secrets` access fails.

- [x] **Run a release smoke pass for critical app flows after large refactor merge**.
  - **Done (manual UI):** Landing CSV load; map modes (All locations / Species / Family / Lifers); species search select and clear; Settings save/apply for basemap and map height; export map HTML and footer links — exercised repeatedly; Explorer looks solid for release.
  - Automated tests were already green; this item satisfied release confidence via repeated hands-on passes (PR #126 large refactor).

- [x] **Decide whether AI workflow files should ship in Beta 2 branch merge**.
  - **Decision:** Ship with Beta 2 — intentional developer-only repo maintenance (`.cursor/commands/*`, expanded assistant guidance such as `docs/AI_CONTEXT.md`). No runtime or end-user impact.
  - **PR:** No need to call this out in the PR description unless you want a single line for other contributors.

## Defer to Beta 3 (Create Follow-Up Issues)

- [ ] **Performance profiling and tuning for map rendering/search paths**.
  - **Tracked in [#179](https://github.com/jimchurches/myebirdstuff/issues/179)** (Explorer responsiveness + benchmark instrumentation — superset of map/search tuning).
  - Candidate focus within that issue: species search rerun behaviour, map HTML generation, and cache-hit rates on real datasets.
  - Reason to defer: functional baseline is test-green; optimization fits your Beta 3 focus.

- [x] **Reduce integration PR blast radius for future releases**.
  - **Done (process intent):** Beta 2 / PR #126 scale was a deliberate one-off; going forward, smaller feature/polish PRs and less monolithic promotion from `beta-next` → `main` where practical.

- [x] **Rationalize experimental/design-map scheme evolution docs**.
  - **Resolved:** All three `MAP_MARKER_COLOUR_SCHEME_*` presets in `defaults.py` are **production** ship quality (none are experimental placeholders). The map marker **design utility** is **developer-only** (faster iteration than editing the full app); see `docs/development.md` § *Map marker colour design utility (developers)*. `defaults.py` remains the place for code-aware tuning.

- [ ] **Testing strategy follow-ups (signal over coverage %)**.
  - Prefer **targeted unit tests** for pure logic and hot paths (e.g. table-driven cases for `explorer/core/species_family.py`, which is under-covered vs core map/stats modules) when fixing bugs or touching fragile behaviour — not broad HTML/Streamlit wiring coverage for statistics alone.
  - Avoid raising **`--cov-fail-under`** just to force work; it tends to encourage noisy tests. Keep CI gate meaningful; add tests when regressions or edge cases warrant it.
  - **E2E / browser automation** for Streamlit (Playwright, etc.) is optional and high cost — only worth it if manual smoke starts missing repeated UI regressions.
  - **`repo_git.py`**: git-dependent; add tests only if branch/README URL logic causes real incidents (otherwise flaky or over-mocked).

## Suggested GitHub Issues to Open (Beta 3 Queue)

- [ ] `perf: profile species search + map render latency on realistic datasets`
- [ ] `process: split beta-next integration into smaller release candidates`
- [ ] `test: targeted unit tests for explorer/core/species_family.py (table-driven; bug-driven)`

