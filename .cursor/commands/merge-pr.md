# Merge Pull Request (myebirdstuff)

You are merging the current completed feature/bug branch into its target integration branch for **myebirdstuff**.

## Default workflow

- Default target branch: `beta-next`
- Only use another target branch if explicitly instructed
- After merge, switch to the updated target branch
- Delete the merged feature branch only if the merge succeeds cleanly

---

## Step 1 — Confirm merge intent

Before doing anything:

1. Confirm the current branch name
2. Confirm the target branch
   - default to `beta-next`
3. Confirm there are no uncommitted changes on the current branch
   - if there are, stop and ask what to do

Do not proceed if the branch is not ready.

---

## Step 2 — Update local state

From the repo root:

1. Fetch latest remote state
2. Switch to the target branch
3. Pull latest target branch from origin
4. Switch back to the feature branch
5. Confirm feature branch is up to date enough to merge safely

If there are problems at this stage, stop and report them.

---

## Step 3 — Run quality gate before merge

If Python code is involved, run:

python3 -m ruff check explorer/
python3 -m pytest tests/ -q

If checks fail:
- stop
- report the failures clearly
- do not merge

Do not continue with a known failing branch unless explicitly instructed.

---

## Step 4 — Perform a non-fast-forward merge

Merge the current branch into the target branch using a merge commit.

Use this sequence:

1. Switch to the target branch
2. Run:

git merge --no-ff <feature-branch>

If there is a merge conflict or any merge problem:
- stop immediately
- do not try to resolve automatically
- do not continue
- report the conflict clearly

Only continue if the merge succeeds cleanly.

---

## Step 5 — Create merge commit message

Use a clean merge commit message based on the branch, commits, and linked issues.

Format:

<type>: <clear one-line summary> (#<PR number if known>)

Refs: #<issue numbers>

Rules:
- keep the first line short and meaningful
- use one of:
  - feat:
  - fix:
  - refactor:
  - ui:
  - data:
- do not dump the whole PR description into the commit message
- if PR number is not known, omit it
- if no issue numbers are known, omit the Refs line

Example:

ui: improve hybrid basemap marker visibility

Refs: #138, #141

If Git requires a merge message editor, replace the default generated merge text with the standard format above.

---

## Step 6 — Validate merged target branch

After the merge succeeds, run:

python3 -m ruff check explorer/
python3 -m pytest tests/ -q

If these fail after merge:
- stop
- report clearly
- do not delete the feature branch
- do not push until the user decides what to do

---

## Step 7 — Push merged target branch

If everything succeeds, push the updated target branch:

git push origin <target-branch>

Ask for network permission if required.

If push fails:
- stop
- report clearly
- do not delete the feature branch

---

## Step 8 — Delete merged feature branch

Only if all of the following are true:

- merge succeeded cleanly
- post-merge checks passed
- push succeeded

Then:

1. Delete local feature branch:
   git branch -d <feature-branch>

2. If appropriate and safe, delete remote feature branch:
   git push origin --delete <feature-branch>

If branch deletion fails, report it but keep the successful merge.

---

## Step 9 — Final state

When complete:

1. Ensure the checked-out branch is the updated target branch
2. Summarise:
   - merged branch
   - target branch
   - merge commit message
   - whether local branch was deleted
   - whether remote branch was deleted
   - whether anything needs manual follow-up

---

## Do not

- Do not merge with conflicts
- Do not auto-resolve conflicts
- Do not force push
- Do not rewrite history
- Do not delete the branch if merge, tests, or push failed
- Do not continue past any uncertainty without asking

---

## Preferred behaviour

Be conservative.

If anything is unclear or risky:
- stop
- explain the issue
- ask before continuing