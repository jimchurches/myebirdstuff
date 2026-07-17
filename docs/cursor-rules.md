# Cursor project rules

Persistent instructions for Cursor Agent/Chat in this repository.

**Location:** `.cursor/rules/*.mdc`

Rules inject context **automatically** (by `alwaysApply` or matching `globs`). They complement **slash commands** in `.cursor/commands/` — rules are instincts; commands are workflows (`/start-issue-work`, `/commit-work`, `/finish-issue-work`, …).

Design principle: rules are a **thin routing layer**. Detailed guidance stays in existing docs (`docs/AI_CONTEXT.md`, `docs/python-style-guide.md`, area-specific docs). Rules say **when** to read them and **what not to do**.

---

## Rule set (v1)

| File | Scope | Purpose |
|------|--------|---------|
| `project-context.mdc` | **Always** (`alwaysApply: true`) | Read `AI_CONTEXT` before architectural changes; one-issue scope; no drive-by fixes; rules vs commands |
| `python-style.mdc` | `explorer/**/*.py` | Link to `docs/python-style-guide.md`; touch-only style improvements |
| `streamlit-ui-thin.mdc` | `explorer/app/**/*.py` | UI layer only; **`defaults.py` for tunables**; constants locations; tests in core not Streamlit |
| `map-and-cache.mdc` | Map component, GeoJSON, prep, map presentation, Leaflet export | Static dataframe, LRU cache, committed frontend build, no Folium |
| `tests.mdc` | `tests/**/*.py` | Behaviour-focused tests; markers; venv/CI parity |
| `share-summary.mdc` | `**/share_summary*.py`, `design_share_summary_app.py` | Layout slot limits, defaults routing, design-app workflow — **Social Cards / feature-line** (on `feat/social-cards`, not part of the minimal `beta-next` v1 set) |

---

## Rule file format

```yaml
---
description: Shown in Cursor rule picker
globs: path/to/**/*.py    # optional — apply when matching files are in context
alwaysApply: false        # true = every session (use sparingly)
---

# Title

Markdown body — keep short; link to docs.
```

---

## When to add more rules

Add a new rule when the **same agent mistake happens twice**, or when a feature area needs repeated “read doc X first” routing.

**`share-summary.mdc`** is the example: added on `feat/social-cards` for active Social Cards work; merge to `beta-next` when that line lands if the rule should persist repo-wide.

Prefer **`globs`** over **`alwaysApply`** — always-on rules consume context budget. Reserve `alwaysApply: true` for universal guardrails (currently only `project-context.mdc`).

**Social Cards / feature lines:** base branch and PR target are resolved by `/start-issue-work` and [base-branch-resolution.md](../.cursor/commands/base-branch-resolution.md), not by rules (rules cannot read git branch). File-scoped rules such as `share-summary.mdc` live on the feature line until Social Cards merges to `beta-next`.

---

## Related

- Issue [#311](https://github.com/jimchurches/myebirdstuff/issues/311) — implemented this set (supersedes [#289](https://github.com/jimchurches/myebirdstuff/issues/289))
- [`docs/development.md`](development.md) — Cursor workflow commands and dev guide
- [`docs/AI_CONTEXT.md`](AI_CONTEXT.md) — project guardrails SSOT
