# Social Cards — integration checklist

Living checklist for landing the current design-studio iteration onto a **feature integration branch**, then resuming work in smaller issue-sized batches.

**Parent epic:** [#157 — Social Media Summary Generator](https://github.com/jimchurches/myebirdstuff/issues/157)

**Context:** Branch `275-share-summary-png-export` grew to ~97 commits ahead of `beta-next` (PNG export, circle layouts, playground, stat picker, and more). That work belongs on a long-lived feature line, not merged to `beta-next` as one blob.

---

## Branching model (target state)

```text
main
 └── beta-next                         ← general release integration
      └── feat/social-cards            ← social-cards feature integration (long-lived)
           ├── NNN-short-slug         ← one issue = one branch
           └── …
```

| Branch | Purpose |
|--------|---------|
| `beta-next` | App-wide integration; receives `feat/social-cards` only at **milestones** |
| `feat/social-cards` | Absorbs issue-branch PRs; no direct day-to-day development |
| `NNN-short-slug` | Single scoped change; branches from **`feat/social-cards`**, merges back there |

**Milestones to `beta-next` (later):** e.g. design studio stable enough for #276 port; then Social Cards tab in main app.

**Agent / Cursor note:** Issue branches use base branch **`feat/social-cards`**, not `beta-next`. Say so explicitly when starting work, or pass base to `/create-dev-branch`. See [social-cards-workflow.md](social-cards-workflow.md) once created.

---

## Phase 1 — Land current work (do once)

Work through in order. Check off as completed.

- [ ] **1.1** Confirm working tree is clean (`git status`)
- [ ] **1.2** `git fetch origin`
- [ ] **1.3** Create `feat/social-cards` from current `beta-next` (`git switch beta-next` → `git pull origin beta-next` → `git switch -c feat/social-cards`)
- [ ] **1.4** Merge `275-share-summary-png-export` into `feat/social-cards` (merge commit is fine)
- [ ] **1.5** Run quality gate on `feat/social-cards` (`ruff check explorer/`, `pytest tests/ -q`)
- [ ] **1.6** Push `feat/social-cards` to `origin` (`git push -u origin feat/social-cards`)
- [ ] **1.7** Switch local default for this work to `feat/social-cards`
- [ ] **1.8** Optional: delete local branch `275-share-summary-png-export` after merge (keep remote until comfortable)

**Do not** merge `feat/social-cards` → `beta-next` in this phase.

---

## Phase 2 — Document the new workflow

- [ ] **2.1** Add [social-cards-workflow.md](social-cards-workflow.md) — short ongoing reference (base branch, PR targets, agent prompt pattern, milestone rules)
- [ ] **2.2** Update [issue-157-share-summary-tracker.md](issue-157-share-summary-tracker.md) — note `feat/social-cards`, link workflow doc, update prototype branch row
- [ ] **2.3** Comment on [#275](https://github.com/jimchurches/myebirdstuff/issues/275) — narrow scope to PNG export (largely done); point remaining layout iteration to `feat/social-cards` and child issues

---

## Phase 3 — File issues for outstanding product work

Create GitHub issues (each branches from **`feat/social-cards`**). Suggested titles and scope:

- [ ] **3.1** **Audit grid stat min/max after circle count changes** — verify Statistics **grid** cards still use tighter min/max than circles; fix if circle work loosened grid limits
- [ ] **3.2** **Square format circle layouts** — hand-tune via playground (counts 1–6; square max today); export into `CIRCLE_CARD_TEMPLATES`
- [ ] **3.3** **Single-circle typography** — larger value/label fonts inside ~400px circles (design decision first; may be format-specific)
- [ ] **3.4** *(Optional)* **Story circles 7–10 regression pass** — visual QA after 1–6 diameter/layout changes

**Issue body template** (copy into each):

```markdown
## Parent
#157

## Base branch
`feat/social-cards` (not `beta-next`)

## PR target
`feat/social-cards`

## Acceptance criteria
- [ ] …

## Out of scope
- …
```

- [ ] **3.5** Label new issues (e.g. `social-cards`, `explorer`, `ui`) for filtering

---

## Phase 4 — Hygiene before pause / trip

- [ ] **4.1** Confirm no open PR targets `beta-next` for social-cards work (future PRs target `feat/social-cards`)
- [ ] **4.2** Mark this checklist Phase 1–2 complete with date in a short note below
- [ ] **4.3** First issue branch **after** return: start with **3.1** (grid audit) — small, validates the new workflow

---

## Discipline (going forward)

- [ ] One GitHub issue per iteration; no open-ended brainstorm → commit loops
- [ ] Playground export → issue → implement → commit → PR to `feat/social-cards`
- [ ] New Cursor agent per issue; prompt includes issue number + base branch
- [ ] `feat/social-cards` → `beta-next` only at named milestones (document milestone in PR)

---

## Product status snapshot (2026-06-24)

| Area | Status |
|------|--------|
| Portrait post circles 1–8 | Hand-tuned in code |
| Story circles 1–6 | Hand-tuned; 7–10 earlier |
| Story circles 1 | Centred; 400px all formats |
| Square circles 6–7 in code | Max 6 in app; layouts not design-reviewed |
| Playground max diameter | 400px |
| Stat picker | Unified dynamic behaviour (all formats) |
| Grid min/max vs circles | **Not audited** — issue 3.1 |
| Single-circle fonts | **TBD** — issue 3.3 |
| Main app Social Cards tab | #276 — after milestone to `beta-next` |

---

## Completion log

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
