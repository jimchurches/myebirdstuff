# Start issue work

You are helping work on an issue in the `myebirdstuff` repository.

## Inputs

The user will provide a GitHub issue number, for example:

- `#254`
- `254`

If no issue number is provided, ask for it before continuing.

---

## Repository workflow

- `main` is the stable/release branch
- `beta-next` is the integration branch
- Development work must happen on a new issue branch created from `beta-next`
- Do not work directly on `main` or `beta-next`

---

## Step 1 — Confirm starting state

1. Confirm the current branch.
2. If currently on `beta-next`, continue.
3. If on another branch, check whether there are uncommitted changes.
4. If there are uncommitted changes, stop and ask what to do.

---

## Step 2 — Read context

Before coding:

1. Read the GitHub issue.
2. Explore the repository enough to understand the relevant area.
3. Focus especially on the `explorer` app.
4. Read relevant technical documentation, including repo guidance files and docs under `docs/explorer/`.

Summarise briefly:

- what the issue is asking for
- likely files or areas involved
- any assumptions or risks

---

## Step 3 — Create development branch

Use the existing `/create-dev-branch` command for the issue.

The branch should:

- be based on `beta-next`
- include the issue number as a prefix
- use a short descriptive slug

Example:

`254-add-basemap-options`

If `/create-dev-branch` cannot be invoked directly from this command, perform the same steps manually.

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
- the implementation has meaningful design choices
- the requested change conflicts with existing behaviour
- there is risk of unintended regression

Otherwise, make reasonable, conservative choices and continue.

---

## Step 6 — Before finishing

Provide a summary of:

- branch created
- files changed
- behaviour implemented
- tests run
- any follow-up concerns

If tests were not run, say so clearly.