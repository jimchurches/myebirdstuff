# Base branch resolution (shared guidance)

**Not a slash command.** Workflow commands (`/start-issue-work`, `/create-dev-branch`, `/open-pr`, `/merge-pr`, `/finish-issue-work`) use this logic to pick a **development base** and **PR target**.

Default when nothing else applies: **`beta-next`**.

---

## Priority order

Apply in order. Explain your choice briefly before acting. **Never invent** a base branch — when uncertain after reading the issue and git state, **ask once**, concisely.

### 1. Issue body (preferred source of truth)

When an issue number is known, read it with `gh issue view <number> --json title,body,labels` and look for explicit guidance:

- `## Base branch` section
- `Base branch: feat/social-cards` (inline)
- `## PR target` (often same as base for feature-line work)
- Parent/epic issues linked in the body (e.g. #157 → Social Cards line)

If found, **use that branch** as development base and PR target unless the user overrides in the same session.

### 2. Current branch context (when issue is silent)

If the issue does **not** specify a base branch, consider the **currently checked-out branch**:

- If it looks like a **feature integration line** (e.g. `feat/*`, or a long-lived branch with clear feature purpose from name and recent commits), **pause and ask** whether new issue work should branch from **the current branch** rather than `beta-next`. Example: “You’re on `feat/social-cards`; issue #NNN doesn’t specify a base — should I branch from here?”
- If the current branch is an **issue branch** (e.g. `293-audit-grid-stat-min-max`), infer its likely base from merge history or `git merge-base` against known integration branches (`beta-next`, `feat/social-cards`, …) and **confirm** with the user if unclear.
- If the current branch is **`main`**, **`beta-next`**, or otherwise **not** a feature line, **do not assume** the current branch is the base. State that **`beta-next` is the default** and ask only if something in the issue or conversation suggests otherwise.

### 3. Default: `beta-next`

When the issue is silent and current-branch context does not suggest a feature line, use **`beta-next`** without unnecessary prompts — but mention the default in the summary (“Using `beta-next`; say if you need another base”).

### 4. Nuanced inference (optional — ask, don’t guess)

If a quick check suggests an alternative base — e.g. issue labels (`social-cards`), open PRs on the same issue targeting `feat/social-cards`, or parent issue #157 in the body — **surface that as a question** rather than silently switching away from `beta-next`.

Example phrasing:

> Issue #NNN doesn’t name a base branch. You’re on `feat/social-cards`, and the issue has the `social-cards` label. Should I create the dev branch from **`feat/social-cards`** (recommended) or **`beta-next`**?

---

## PR target

For most work, **PR target = development base**. When an issue names both `## Base branch` and `## PR target`, honour both; if only base is named, use it for the PR base too.

---

## Feature-line pointers

When resolved base is **`feat/social-cards`** (or the issue/body references Social Cards / #157):

- Point at `docs/explorer/social-cards-workflow.md` when that file exists on the base branch.
- PRs target the feature integration branch, not `beta-next`, until a milestone merge.

---

## User override

A explicit override in the same chat session always wins (e.g. “branch from beta-next not from the feature branch currently in focus”).
