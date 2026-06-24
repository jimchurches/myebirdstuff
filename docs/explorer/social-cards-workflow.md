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

- **Test Integrity Sentinel** (Cursor automation): targets PRs to `beta-next`. For PRs to **`feat/social-cards`**, duplicate or extend the automation — [#297](https://github.com/jimchurches/myebirdstuff/issues/297). GitHub Actions unit tests still run on push/PR per `.github/workflows/tests.yml`.

---

## Related docs

- [issue-157-share-summary-tracker.md](issue-157-share-summary-tracker.md) — feature status
- [issue-157-social-summary-prototype.md](issue-157-social-summary-prototype.md) — prototype notes
- Design app: `streamlit run explorer/app/streamlit/design_share_summary_app.py`
