# PR Review (myebirdstuff)

**When to use:** Pre-merge review of a **single** linked issue and its PR — e.g. a focused bug fix or small feature. For larger or multi-area changes, use `/code-review` instead.

## Relationship to `/code-review`

| | `/pr-review` | `/code-review` |
|---|---|---|
| **Scope** | One issue + one PR diff vs `beta-next` | Whole change set; architecture and cross-cutting concerns |
| **When** | Small fixes, pre-merge sanity check | Before opening/updating a large PR, or multi-file behaviour changes |
| **Fixes during review** | Apply minor, low-risk nits without asking | Default to listing gaps; only trivial fixes if the author wants them in-session |

This command **does not replace or rewrite** `/code-review`. It reuses the same quality bar and checklist items, but constrains scope and workflow for targeted PR reviews.

For **myebirdstuff**, skim `docs/AI_CONTEXT.md` for repo guardrails (Streamlit vs core, caching, dataframe usage) and call out anything that conflicts within the PR scope.

---

## Step 1 — Resolve issue and PR

1. Identify the **GitHub issue** and **PR** from:
   - user message (e.g. “review #251 and PR #252”)
   - branch name (e.g. `251-fix-banner-title`)
   - `gh pr view` on the current branch
2. If either is missing or ambiguous, **stop and ask** — do not review the whole project by default.
3. Fetch context:
   - `gh issue view <issue-number>`
   - `gh pr view <pr-number>` (or PR for current branch)
4. Summarise in one sentence: what problem the PR solves and what files/areas it touches.

---

## Step 2 — Establish the diff (vs `beta-next`)

Review **only** what the PR changes relative to the merge target.

```bash
git fetch origin
git diff origin/beta-next...HEAD
# or, when reviewing a remote PR without checkout:
gh pr diff <pr-number>
```

- Do **not** expand scope to unrelated files or prior commits on the branch unless they are part of this PR’s diff.
- If the PR targets a base other than `beta-next`, use that base instead and say so in the output.

---

## Step 3 — Right-sized quality gate

Run checks proportional to the diff — not a full-project pass unless the change warrants it.

**Python touched:**

```bash
python3 -m ruff check explorer/
python3 -m pytest tests/ -q -m "not e2e"
```

Prefer a **narrower** pytest path when the diff is clearly isolated (e.g. `tests/path/to/test_module.py`). Fold failures into the review; fix trivial ones in Step 4.

**Docs / config only:** skip pytest unless the change affects runtime behaviour.

---

## Step 4 — Scoped review checklist

Apply the checklist **only to files in the PR diff**. Do not audit the rest of the repo.

### Functionality

- [ ] Intended behaviour matches the linked issue / PR description
- [ ] Edge cases in the changed code handled gracefully
- [ ] Error handling appropriate for the change

### Code quality

- [ ] Change is focused — no unrelated drive-by edits
- [ ] Names clear; structure readable
- [ ] Tests/documentation updated if behaviour changed
- [ ] Comments explain *what* and *why*, not “see #123” as the only explanation

### Security & safety (in-scope)

- [ ] No secrets or credentials exposed
- [ ] Inputs validated where the change introduces or touches user/API data

### PR hygiene

- [ ] PR title and description match the change
- [ ] Issue linkage correct (`Fixes #…` / `Refs #…`)
- [ ] Anything a human reviewer should know is in the PR body, not only in chat

---

## Step 5 — In-review fixes (minor only)

**Do fix without asking** when all of these hold:

- Clearly within the PR diff (or directly required to make the diff correct)
- Low risk (typos, lint, tiny readability, missing import, obvious test gap for the same behaviour)
- No behaviour change beyond what the issue/PR already intends

**Do not fix without asking** when:

- The fix changes behaviour, API, or architecture
- It expands scope beyond the linked issue
- It would be better as a follow-up issue

After fixes: re-run the relevant checks from Step 3 and note what changed in the output.

---

## Step 6 — Report (standard output)

Use this structure so results are consistent across reviews. Adapt sections as needed; do not omit material findings to fit the template.

### Scope

- **Issue:** #… — one-line summary
- **PR:** #… — link or branch name
- **Base:** `beta-next` (or other) — N files changed

### Verdict

One of: **Ready to merge** | **Ready with nits** | **Changes requested**

Short rationale (1–2 sentences).

### Findings

Group by severity:

1. **Blockers** — must fix before merge
2. **Should fix** — worth addressing in this PR or called out for author decision
3. **Nits / suggestions** — optional polish

Use concrete file/line references where helpful.

### Fixes applied during review

- Bullet list of minor fixes made in-repo, or “None”

### Checks run

- Commands executed and pass/fail (e.g. `ruff`, `pytest …`)

### Follow-ups (optional)

- Out-of-scope items → suggest a GitHub issue so they are not lost

---

## Do not

- Treat this as a full-project or architecture review — use `/code-review` for that
- Rewrite large areas without author agreement
- Block on nits that you could safely fix under Step 5
- Substitute for CI or required human reviewers when policy applies

Provide constructive, actionable feedback scoped to the linked issue and PR.
