# Nit-Fixer (myebirdstuff)

**When to use:** Pre-merge polish on a PR or local branch — aggressive **see it, fix it** for mechanical and readability nits in **PR-touched files**. Also invoked automatically from `/pr-review` (Step 4b) and `/code-review` (final step).

**When not to use alone:** Full architecture review — use `/code-review`. Test honesty / assertion quality — use Test Integrity Sentinel in `/pr-review` (Step 4), not Nit-Fixer.

Fixes are applied **in the working tree only** — do **not** commit. The author reviews and runs `/commit-work`.

For **myebirdstuff**, skim `docs/AI_CONTEXT.md` when touching production code under `explorer/`.

---

## Relationship to CI, Sentinel, and `/pr-review`

| Actor | Role |
|-------|------|
| **CI** (`tests.yml`, ruff, hygiene) | Authoritative pass/fail gate — Nit-Fixer does not replace it |
| **Test Integrity Sentinel** (`/pr-review` Step 4) | Test *honesty* — assertions, mocks, fixtures, missing regression tests |
| **Nit-Fixer (this command)** | Mechanical + readability fixes in touched production/docs/command/frontend source; **never** edits test files |

**Ordering when combined with `/pr-review`:** Sentinel first (when triage launches it), then Nit-Fixer. Nit-Fixer must not edit paths Sentinel just changed under `tests/`.

---

## Step 1 — Resolve diff scope

1. Identify **PR** and **merge target**:
   - `gh pr view` on current branch when a PR exists — read `baseRefName`.
   - No PR: apply **[base branch resolution](base-branch-resolution.md)** from linked issue or default `beta-next`.
2. Build **touched file list** (files in the PR diff, not only diff hunks):

```bash
git fetch origin
# With PR:
gh pr diff <pr-number> --name-only
# Without PR:
git diff --name-only origin/<merge-target>...HEAD
```

3. Summarise in one line: branch/PR, merge target, file count.

State the resolved merge target in the output.

---

## Step 2 — Triage (skip when nothing to fix)

Classify touched files:

- **Nit-Fixer surface** — production/runtime code (`explorer/`, scripts), Cursor command/rule files, docs, map frontend **source** under `explorer/components/all_locations_map/frontend/src/`.
- **Sentinel-only surface** — `tests/**`, `conftest.py`, fixtures, snapshots, golden outputs, UI.Vision macros, committed test assets.
- **Neither / skip** — CI/workflow-only changes with no files on Nit-Fixer surface (e.g. pure `.github/workflows` edit with no companion doc).

**Skip Nit-Fixer** when the touched file list has **no** Nit-Fixer surface files. Record `Nit-Fixer: not applicable — [reason]` and stop (unless the parent command requires a one-line confirmation).

When **only** test paths changed, skip Nit-Fixer — Sentinel owns that surface in `/pr-review`.

---

## Step 3 — Quality gate (proportionate)

Run before launching the subagent. Fold failures into context passed to Nit-Fixer.

**Python (when `explorer/` or Python scripts touched):**

```bash
python3 -m ruff check explorer/
python3 -m pytest tests/ -q -m "not e2e"
```

Prefer a **narrower** pytest path when the diff is clearly isolated.

**Map frontend source** (when any path under `explorer/components/all_locations_map/frontend/src/` is touched):

```bash
cd explorer/components/all_locations_map/frontend
npm test -- --watchAll=false
npx tsc --noEmit
```

**Docs / commands only:** skip pytest/npm unless the change affects runtime behaviour.

---

## Step 4 — Nit-Fixer subagent

When triage selects **run**, start exactly one subagent. Parent waits for result before reporting; use background only if the session requires it.

```text
description: Nit-Fixer
subagent_type: generalPurpose
model: composer-2.5-fast
readonly: false
run_in_background: false
```

### Parent preparation

Collect before launching:

- Repository absolute path
- Issue/PR summary (if known)
- Merge target and **full touched file list** from Step 1
- Quality-gate command output (pass/fail, tracebacks)
- Sentinel summary if `/pr-review` Step 4 ran (verdict, files Sentinel edited)

### Task prompt

Fill bracketed fields from the current run:

```text
You are the Nit-Fixer for the myebirdstuff repository.

Full repository path: [absolute repository path]
Issue / PR: [number, title, one-line summary, or "standalone /nit-fixer"]
Base branch: [merge target]
Touched files (whole-file scope — you may edit anywhere in these files):
[list paths]

Quality-gate results: [commands run and pass/fail summary]
Sentinel already ran: [yes/no — if yes, summary and test files Sentinel edited]

Philosophy: see it, fix it. Within guardrails, fix mechanical and readability nits
in touched files without asking. Prefer fixing over listing deferrable nits.

In scope (fix without asking):
- Broken/missing imports, typos, syntax errors
- ruff-fixable lint — run `python3 -m ruff check <paths> --fix` and `python3 -m ruff format <paths>` on in-scope Python files
- Readability in touched files: unclear names, weak comments, small docstring gaps
- Trivial TS/lint issues in touched map frontend source
- Whole-file polish within each touched file (not only diff hunks)

Out of scope (do NOT edit — report to parent instead):
- tests/**, conftest.py, fixtures, snapshots, golden outputs, UI.Vision macros
- Adding, weakening, or rewriting tests (Sentinel owns test integrity)
- Behaviour, API, or architecture changes beyond trivial typo-level fixes
- Files not in the touched file list
- Committed frontend/build/ assets unless the PR changes TS/CSS source
- Secrets, config templates, generated assets
- Fixes requiring more than ~3 lines of behavioural change

Hard caps:
- Maximum ~10 files edited and ~150 lines changed per run — if you would exceed, stop and report remaining nits
- Maximum 2 fix attempts if pytest/tsc/ruff still fail after edits — then revert your edits and report

Project notes:
- Streamlit UI stays thin; prefer readability fixes that do not move logic into app layer
- Do not drive-by refactor unrelated modules

After edits:
- Re-run the narrowest relevant checks (ruff, pytest, npm test, tsc) yourself when feasible
- Do NOT commit — leave changes unstaged for the author

Output format:
1. Verdict: `No nits found` | `Nits fixed` | `Stopped — out of scope or cap exceeded`
2. `Fixes applied` — bullet list with file paths (or "None")
3. `Remaining nits` — only items truly out of scope or blocked (or "None")
4. `Checks run` — pass/fail
5. Approximate files/lines touched
```

### Parent follow-up

After the subagent returns:

- Inspect edits before reporting.
- Re-run Step 3 quality gate if Nit-Fixer changed production or frontend source.
- Do **not** commit.

---

## Step 5 — Report (standard output)

### Scope

- **PR / branch:** …
- **Base:** `beta-next` (or other)
- **Touched files:** N files

### Nit-Fixer

- Triage: **ran** | **skipped** (reason)
- Verdict from subagent
- Fixes applied (bullets) or "None"
- Remaining out-of-scope nits or "None"
- Approx files/lines touched

### Checks run

- Commands before and after Nit-Fixer, with pass/fail

### Next step

- Remind author: review `git diff`, then `/commit-work` if satisfied

---

## Do not

- Commit or push fixes
- Edit test files, fixtures, or snapshots
- Replace CI, Sentinel, or full `/pr-review`
- Leave fixable in-scope nits as suggestions only — fix them when within caps
- Expand scope beyond the touched file list
- Force-push or amend commits

Provide a concise report. Fixes stay in the working tree for human review.
