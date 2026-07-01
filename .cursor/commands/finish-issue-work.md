# Finish issue work (myebirdstuff)

You are closing the loop after implementation — from “code done” to “PR ready” — following this repo’s workflow.

## Purpose

Automate the handoff users currently do manually: confirm state → quality gate → push → open PR → optional review.

Be **conservative**: ask before push, before opening a PR, and before review subcommands.

---

## Step 1 — Confirm state

1. Confirm **current branch** and that it is an issue/feature branch (not `main` or `beta-next`).
2. Identify the **linked issue** from branch name (e.g. `312-issue-workflow-commands` → #312), commit messages, or ask the user.
3. Review `git status` — note staged, unstaged, and untracked files.
4. If there are **uncommitted changes**, ask whether to run `/commit-work` now or stop.

---

## Step 2 — Resolve PR target

Apply **[base branch resolution](base-branch-resolution.md)** using the linked issue number.

Summarise before continuing:

- linked issue and goal (one line)
- **resolved PR base / target**
- whether the user overrode the default

---

## Step 3 — Quality gate

If Python code was touched in this branch, run from repo root:

```bash
python3 -m ruff check explorer/
python3 -m pytest tests/ -q
```

Use the same proportionality as `/open-pr` — skip or narrow scope only for markdown-only command/doc changes.

If checks fail: fix if trivial; otherwise stop and report clearly.

---

## Step 4 — Push (ask first)

Check whether the branch exists on origin:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true
git ls-remote --heads origin <branch-name>
```

If not pushed or behind remote, **ask** before:

```bash
git push -u origin HEAD
```

Do not force-push.

---

## Step 5 — Open PR

Use `/open-pr` logic or `gh pr create` directly:

- **Base** = resolved PR target (not always `beta-next`)
- **Title** — clear, meaningful (sentence case; no “fix stuff”)
- **Body** — Summary, Changes, Testing, Issues (`Fixes #NNN` or `Refs #NNN` as appropriate)
- Confirm title, base, and draft vs ready with the user before creating

---

## Step 6 — Optional follow-ups (ask)

After the PR exists, offer (user confirms each):

- `/pr-review` on the new PR (includes Sentinel + Nit-Fixer)
- `/nit-fixer` for a standalone nit pass without full review
- **Future:** `/test-integrity-review` when [#310](https://github.com/jimchurches/myebirdstuff/issues/310) is implemented and test files changed

---

## Step 7 — Output summary

Report:

- branch name
- PR URL (or compare link if create failed)
- **PR base branch** used
- checks run (ruff / pytest / none)
- suggested manual follow-ups (merge target, labelling, etc.)

---

## Do not

- Do not push or open a PR without confirmation
- Do not commit secrets or unrelated files
- Do not assume PR base is always `beta-next`
- Do not merge or delete branches as part of this command
