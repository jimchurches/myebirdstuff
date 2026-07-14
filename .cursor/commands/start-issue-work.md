# Start issue work

You are helping work on an issue in the `myebirdstuff` repository.

## Inputs

The user will provide a GitHub issue number, for example:

- `#254`
- `254`

If no issue number is provided, ask for it before continuing.

The user may also specify a **base branch override** (e.g. “branch from `beta-next` even though I’m on `feat/social-cards`”). Honour explicit overrides over inference.

---

## Repository workflow

- `main` is the stable/release branch
- `beta-next` is the default integration branch for most work
- **Feature integration lines** (e.g. `feat/social-cards`) are the base for issues that say so in the issue body
- Development happens on a new **issue branch** — not directly on `main`, `beta-next`, or a feature integration branch
- Do not work directly on `main` or `beta-next`

---

## Step 1 — Confirm starting state

1. Confirm the current branch.
2. Check whether there are uncommitted changes.
3. If there are uncommitted changes, stop and ask what to do (commit, stash, or abort).

---

## Step 2 — Read context

Before coding:

1. Read the GitHub issue (`gh issue view`).
2. Apply **[base branch resolution](base-branch-resolution.md)** — resolve **development base** and **PR target** before creating a branch.
3. Explore the repository enough to understand the relevant area.
4. Read relevant technical documentation (`docs/AI_CONTEXT.md`, `docs/explorer/`, issue-linked docs).

Summarise briefly:

- what the issue is asking for
- **resolved base branch** and **PR target**
- likely files or areas involved
- any assumptions or risks

When base is a feature integration branch (e.g. historically `feat/social-cards`), mention any workflow doc named in the issue; Social Cards playbook is archived on [#157](https://github.com/jimchurches/myebirdstuff/issues/157#issuecomment-4964282021).

---

## Step 3 — Create development branch

Use the existing `/create-dev-branch` command (or equivalent steps manually).

Pass the **resolved base** from Step 2 — do not hardcode `beta-next` when the issue or user specified another base.

The branch should:

- be based on the **resolved base branch**
- include the issue number as a prefix
- use a short descriptive slug

Example:

`254-add-basemap-options`

---

## Step 4 — Work the issue

Proceed with implementation once the branch is created.

Keep changes focused on the issue.

Do not:
- refactor unrelated code
- change behaviour outside the issue scope unless required
- commit secrets or local config files
- push or open a PR unless asked

---

## Step 5 — Ask only when needed

Only stop to ask questions if:

- the issue is ambiguous
- base branch resolution is uncertain (see [base-branch-resolution.md](base-branch-resolution.md))
- the implementation has meaningful design choices
- the requested change conflicts with existing behaviour
- there is risk of unintended regression

Otherwise, make reasonable, conservative choices and continue.

---

## Step 6 — Before finishing

Provide a summary of:

- branch created (name + base)
- resolved PR target
- files changed
- behaviour implemented
- tests run
- any follow-up concerns

If tests were not run, say so clearly. When implementation is complete, the user can run `/finish-issue-work` to push and open a PR.
