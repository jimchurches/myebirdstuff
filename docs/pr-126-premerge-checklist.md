# PR #126 Pre-Merge Checklist (Beta 2)

Scope reviewed: `main...beta-next` (PR #126), with `ruff` + full tests passing locally (`473 passed`).

## Must Address Before Merging to `main` (Beta 2)

- [ ] **Fix landing-page typo in user-facing copy** (`explorer/app/streamlit/app_landing_ui.py`).
  - Current heading is `Taxononmy` and should be `Taxonomy`.
  - Why now: visible polish issue on first-load UX.

- [ ] **Run targeted manual smoke test on hosted notice flag path** (`explorer/app/streamlit/app_landing_ui.py`).
  - Validate both `st.secrets` and env fallback behavior for `STREAMLIT_SHOW_HOSTED_PERFORMANCE_NOTICE`.
  - Why now: this is release-facing behavior on hosted deployments and was introduced through a WIP/follow-up sequence.

- [ ] **Run a release smoke pass for critical app flows after large refactor merge**.
  - Minimum suggested checks:
    - load CSV from landing page
    - switch between All locations / Species / Family / Lifers map modes
    - species search select + clear behavior
    - Settings save/apply for basemap + map height
    - export map HTML and footer links
  - Why now: PR #126 is a large integration delta (84 files; major Streamlit decomposition + map logic movement). Automated tests pass, but release confidence still needs UI smoke coverage.

- [ ] **Decide whether AI workflow files should ship in Beta 2 branch merge**.
  - New files include `.cursor/commands/*` and expanded assistant guidance docs.
  - Why now: not runtime code, but impacts repo hygiene and contributor experience on `main`. Confirm intentional inclusion vs follow-up cleanup.

## Defer to Beta 3 (Create Follow-Up Issues)

- [ ] **Performance profiling and tuning for map rendering/search paths**.
  - Candidate focus: species search rerun behavior, map HTML generation, and cache-hit rates in real user datasets.
  - Reason to defer: functional baseline is test-green; optimization fits your Beta 3 focus.

- [ ] **Reduce integration PR blast radius for future releases**.
  - Process improvement: smaller batched merges from `beta-next` to reduce verification load and risk concentration.
  - Reason to defer: no immediate functional defect; delivery workflow improvement.

- [ ] **Rationalize experimental/design-map scheme evolution docs**.
  - Clarify which map marker schemes are production defaults vs design utility experiments.
  - Reason to defer: documentation/maintenance clarity rather than release blocker.

## Suggested GitHub Issues to Open (Beta 3 Queue)

- [ ] `perf: profile species search + map render latency on realistic datasets`
- [ ] `process: split beta-next integration into smaller release candidates`
- [ ] `docs: clarify production vs experimental map marker schemes/design utility`

