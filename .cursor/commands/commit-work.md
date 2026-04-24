# Commit Work (myebirdstuff)

You are creating a git commit for **myebirdstuff** following this repo’s workflow and conventions.

## Branching model (important)

- `main` = stable / current beta (live)
- `beta-next` = integration branch for upcoming release
- Feature/bug branches are normally created from `beta-next`
- Most work should be committed on an issue/feature branch, not directly on `main` or `beta-next`

If the current branch is `main` or `beta-next`, stop and ask before committing unless the user explicitly says this is intentional.

---

## Step 1 — Confirm state

Before doing anything:

1. Confirm current branch name
2. Review `git status`
3. Identify:
   - staged files
   - unstaged files
   - untracked files
4. Summarise what appears to have changed

If the working tree includes unrelated changes, stop and ask what should be included.

Do not guess.

---

## Step 2 — Identify context

Use the following as input:

- branch name
- staged diff
- recent commit history
- linked GitHub issue number if obvious
- issue title or notes if available in the branch/commit context

Summarise in 1–3 sentences:

- what problem is being solved
- what was changed
- whether this looks like:
  - feat
  - fix
  - refactor
  - ui
  - data
  - docs
  - test

If unclear, ask before committing.

---

## Step 3 — Stage carefully

If files are not already staged:

1. Stage only the files relevant to this unit of work
2. Do not stage unrelated files
3. If the changes should be split into multiple commits, stop and say so

Prefer a clean, focused commit over a large mixed commit.

---

## Step 4 — Run quality gate before commit

If Python code is involved, run:

python3 -m ruff check explorer/

If the change is broader than a tiny local edit, also run:

python3 -m pytest tests/ -q

If checks fail:
- fix if trivial
- otherwise stop and report clearly
- do not commit broken work unless the user explicitly wants that

---

## Step 5 — Write commit message

Create a clear commit message using this format:

<type>: <short meaningful summary>

Refs: #<issue numbers>

Rules:
- keep the first line concise and readable in `git log --oneline`
- use one of:
  - feat:
  - fix:
  - refactor:
  - ui:
  - data:
  - docs:
  - test:
- use sentence case for the summary
- do not end the first line with a full stop
- include `Refs:` line if issue numbers are known
- if no issue is known, omit `Refs:`

Examples:

fix: restore compact layout in default location popup

Refs: #142

ui: improve hybrid basemap marker visibility

Refs: #138, #141

data: refine Eucalypt and Thermal Shift marker schemes

Refs: #150

Do not write vague messages like:
- update code
- fix stuff
- tweaks
- WIP

NOTE: 'WIP' may be added to the heading or text if the user is clear the commit is to capture work in progress or WIP

---

## Step 6 — Commit

Create the commit only after:

- relevant files are staged
- checks have passed
- the commit message is clear

Run:

git commit -m "<first line>" -m "Refs: #..."

If no issue references exist, use a single `-m` with just the summary line.

**Footer tags (e.g. `Made-with: Cursor`):** A `prepare-commit-msg` hook (or similar) may append lines such as `Made-with: Cursor` after the message you pass to `git commit`. **That is intentional here and always OK.** Do not warn the user about it, suggest amending the commit to strip it, or call it out as an error in Step 7 — you can ignore it entirely.

---

## Step 7 — Final output

When complete, provide:

- branch name
- commit hash
- commit message
- issue references used
- whether tests/lint were run
- anything still unstaged or left out intentionally

---

## Do not

- Do not commit unrelated files
- Do not commit failing code unless explicitly instructed
- Do not use vague commit messages
- Do not create a giant mixed commit if the work should be split
- Do not push as part of this command
- Do not rewrite history unless explicitly instructed

---

## Preferred behaviour

Be conservative and tidy.

If the changes represent more than one logical unit of work:
- stop
- explain what should be split
- ask before committing