# Social Cards — development workflow

How to work on [#157 — Social Media Summary Generator](https://github.com/jimchurches/myebirdstuff/issues/157) on the **`feat/social-cards`** integration branch.

## Branches

| Branch | Role |
|--------|------|
| `feat/social-cards` | Long-lived integration line for design studio + share card work |
| `NNN-short-description` | Issue branch; **base = `feat/social-cards`** |
| `beta-next` | Receives `feat/social-cards` at **milestones** only |

Do **not** develop directly on `feat/social-cards`. Merge issue branches via PR (or local merge if solo).

---

## Starting an issue

1. Read the GitHub issue (must include **Base branch: `feat/social-cards`**).
2. Ensure working tree is clean on `feat/social-cards` and pulled.
3. Create branch — either tell the agent:

   > Base branch `feat/social-cards`, not beta-next. Issue #NNN.

   or use `/create-dev-branch` with base **`feat/social-cards`** (supported by that command).

4. Implement **only** the issue scope.
5. `/commit-work` on the issue branch.
6. Open PR: **base `feat/social-cards`**, not `beta-next`.

---

## Agent prompt pattern

```text
Issue #NNN. Base branch feat/social-cards. PR target feat/social-cards.
Read docs/explorer/social-cards-workflow.md and the issue.
One issue only — do not expand scope.
```

Use a **new agent session** per issue when possible.

---

## Circle layout iteration

1. Tune in design app → **Circle layout** playground tab.
2. Copy export block.
3. File or use existing issue for that format/count.
4. Paste positions into `CIRCLE_CARD_TEMPLATES` in `share_summary_circles_preview.py`.
5. Tests + PR to `feat/social-cards`.

---

## Merging to `beta-next`

Only when a **milestone** is agreed, e.g.:

- Design studio + PNG export stable enough to port (#276), or
- Social Cards tab ready for beta testers.

Open **one PR**: `feat/social-cards` → `beta-next`, with test plan and tracker update.

## CI / automations

- **GitHub Actions** (`.github/workflows/tests.yml`): unit tests on push/PR to `main`, `beta-next`, and **`feat/social-cards`**.
- **Test Integrity Sentinel** (Cursor automation): test-integrity PR comments for targets to `beta-next`. For **`feat/social-cards`** PRs, duplicate or extend — [#297](https://github.com/jimchurches/myebirdstuff/issues/297).

---

## Related docs

- [issue-157-share-summary-tracker.md](issue-157-share-summary-tracker.md) — feature status
- [issue-157-social-summary-prototype.md](issue-157-social-summary-prototype.md) — prototype notes
- Design app: `streamlit run explorer/app/streamlit/design_share_summary_app.py`

## Performance and lazy tab mount (#328)

Social Cards is the **only** main tab lazy-mounted on `tab.open` in `app_dashboard_shell.py`. Period stats, insight facts, and card preview run only when the tab is selected; other data tabs always enter their `@st.fragment` blocks on every full rerun. **Map prep is skipped** while Social Cards is active (rankings/taxonomy caches still warm on full reruns). Period / geo / layout / format / theme stay in the **main-script sidebar** so the chrome matches other explorer tabs. Those sidebar widgets still trigger a full app rerun today; Streamlit 1.59+ allows fragment→sidebar writes if we move that block into the Social Cards fragment later.

**Instrumentation** (`EXPLORER_PERF=1`): coarse `fragment.social_cards` plus sub-stages:

| Stage | Where |
|-------|--------|
| `social_cards.resolve_stats` | `social_cards_streamlit_html.py` |
| `social_cards.compute_insight_facts` | `social_cards_streamlit_html.py` (Interesting Insights layout only) |
| `social_cards.render_preview` | `social_cards_streamlit_html.py` |
| `social_cards.png_export` | `social_cards_streamlit_ui.py` |

Stat picker ↑/↓/✕/Add/Reset and lazy PNG export use fragment-scoped updates so they do **not** re-run map prep (~5s full reruns observed on a ~47k-row export before these fixes). Sidebar layout/format/period changes still full-rerun the app (with map prep skipped).

See `docs/development.md` § Performance Instrumentation Guardrails for stable stage names.

**PNG on Streamlit Cloud:** headless Chromium availability is not yet verified on a live deploy — see tracker § Streamlit Cloud verification (#275). Graceful `RuntimeError` if Chromium is missing.
