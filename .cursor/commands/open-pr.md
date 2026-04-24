# Create Pull Request (myebirdstuff)

You are creating a pull request for myebirdstuff following this repo’s workflow and conventions.

## Branching model (important)

- main = stable / current beta (live)
- beta-next = integration branch for upcoming release
- Feature/bug branches are created from beta-next
- PRs are normally:
  → feature branch → beta-next

Only target main if explicitly instructed.

---

## Step 1 — Confirm state

Before doing anything:

1. Confirm current branch name
2. Confirm:
   - all intended changes are committed
   - no unintended files are included
3. If uncommitted changes exist:
   - ask whether to include them or ignore them

---

## Step 2 — Identify context

1. Detect linked issues from:
   - branch name (e.g. 123-fix-map-bug)
   - commit messages
2. Summarise:
   - what problem is being solved
   - what areas of the code are affected

If unclear, ask before proceeding.

---

## Step 3 — Quality gate (Python changes)

If Python code is involved, run:

python3 -m ruff check explorer/
python3 -m pytest tests/ -q

If failures:
- fix if trivial
- otherwise report clearly before continuing

Do not open PR with failing tests unless explicitly instructed.

---

## Step 4 — Prepare PR content

### Title

Write a clear, meaningful title:

- Prefer:
  Improve species map marker clarity on hybrid basemap
- Avoid:
  Fix stuff, Update code

### Description

Use this structure:

Summary
Short explanation of what changed and why.

Changes
- Bullet list of key changes
- Group related changes logically

Testing
- Commands run
- Manual testing (if relevant)

Notes (optional)
- Design decisions
- Trade-offs
- Anything reviewer should know

Issues
Include references:
- Fixes #123
- Refs #456

---

## Step 5 — Push branch

Run:

git push -u origin HEAD

Ask for network permission if required.

---

## Step 6 — Create PR

Use GitHub CLI if available:

gh pr create --base beta-next --head <branch> --title "..." --body-file ...

Defaults:
- base = beta-next
- head = current branch

If CLI fails:
Provide:
- compare URL
- PR title
- PR body (ready to paste)

---

## Step 7 — Final confirmation

Before creating PR, confirm:

- title
- base branch
- ready vs draft

---

## Do not

- Do not force push
- Do not rewrite history
- Do not include unrelated changes
- Do not open PR without confirmation

---

## Output

When complete, provide:

- branch name
- base branch
- PR title
- PR URL (or compare link)
- any follow-up actions