# PR Review (myebirdstuff)

**When to use:** Pre-merge review of a **single** linked issue and its PR — e.g. a focused bug fix or small feature. For larger or multi-area changes, use `/code-review` instead.

Every `/pr-review` run includes **Test Integrity Sentinel** triage (Step 4) and **Nit-Fixer** triage (Step 4b). The parent agent resolves PR context and local checks, then delegates to pinned subagents when triage selects launch: Sentinel for test honesty (`gpt-5.5-medium`), Nit-Fixer for mechanical and readability nits in touched files (`composer-2.5-fast`). See **[nit-fixer.md](nit-fixer.md)** for Nit-Fixer guardrails and prompt.

## Relationship to `/code-review`

| | `/pr-review` | `/code-review` |
|---|---|---|
| **Scope** | One issue + one PR diff vs **merge target** (often `beta-next`; may be a feature line) | Whole change set; architecture and cross-cutting concerns |
| **When** | Small fixes, pre-merge sanity check | Before opening/updating a large PR, or multi-file behaviour changes |
| **Fixes during review** | Sentinel strengthens in-scope tests; Nit-Fixer fixes mechanical/readability nits in touched files (Step 4b) | Architecture review first; **always** runs Nit-Fixer last (see [code-review.md](code-review.md)) |

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

## Step 2 — Establish the diff (vs merge target)

Review **only** what the PR changes relative to its **merge target** — not always `beta-next`. On feature-line work (e.g. Social Cards), the target is often `feat/social-cards`; diffing against `beta-next` would include unrelated feature-line history.

### Resolve merge target

1. **PR exists:** read `baseRefName` from `gh pr view <pr-number> --json baseRefName,headRefName,title`.
2. **No PR yet:** apply **[base branch resolution](base-branch-resolution.md)** from the linked issue (PR target = merge target for review).
3. **Default:** `beta-next` when nothing else applies.

State the resolved merge target in the review output.

### Get the diff

**Prefer** `gh pr diff` when a PR number is known — it always matches the PR’s base:

```bash
git fetch origin
gh pr diff <pr-number>
```

When there is no PR, or you need a local three-dot diff:

```bash
git fetch origin
git diff origin/<merge-target>...HEAD
```

Replace `<merge-target>` with the resolved base (e.g. `beta-next`, `feat/social-cards`).

- Do **not** expand scope to unrelated files or prior commits on the branch unless they are part of this PR’s diff.
- Do **not** default to `origin/beta-next...HEAD` when the PR targets another base.

---

## Step 3 — Right-sized quality gate

Run checks proportional to the diff — not a full-project pass unless the change warrants it.

**Python touched:**

```bash
python3 -m ruff check explorer/
python3 -m pytest tests/ -q -m "not e2e"
```

Prefer a **narrower** pytest path when the diff is clearly isolated (e.g. `tests/path/to/test_module.py`). Fold failures into the review; Nit-Fixer addresses mechanical failures in Step 4b.

**Docs / config only:** skip pytest unless the change affects runtime behaviour.

---

## Step 4 — Test Integrity Sentinel

Every `/pr-review` runs this **triage**. Whether the pinned subagent is launched depends on what the diff touches — do not spawn a subagent when there is genuinely nothing for it to review.

### Triage — decide whether to launch the subagent

Classify the PR diff (vs the base from Step 2) into these surfaces:

- **Test surface** — files under `tests/`, `conftest.py`, fixtures, snapshots, golden/expected outputs, test helpers, committed test assets, or UI.Vision macros.
- **Behaviour surface** — production/runtime code whose behaviour tests are meant to protect: Python under `explorer/`, GPS scripts, frontend map source, and similar runtime code.
- **Neither** — documentation, Cursor command/rule files, CI/workflow config, or dependency manifests with no runtime-behaviour change.

Decide using the **first** matching rule:

1. **Test surface changed → always launch.** Tests were edited; verify they still honestly validate behaviour.
2. **No test surface, but behaviour surface changed → launch.** Changed behaviour should have matching tests; focus on missing or weak coverage, especially for bug fixes.
3. **Neither changed → skip.** Do not spawn a subagent for pure docs/command/config changes. Record `Sentinel: not applicable — documentation/config-only diff` (or the specific reason) in the Step 7 report.

If you are unsure whether a changed file affects behaviour, treat it as the behaviour surface and **launch** (fail safe toward review).

When triage selects **skip**, go straight to Step 4b. The remainder of Step 4 applies only when launching.

### Parent preparation

Before launching the subagent, collect:

- Issue and PR summary from Step 1
- Base branch and diff source from Step 2
- Changed production files, changed test files, changed fixtures, and deleted/skipped/xfailed tests
- Relevant quality-gate results from Step 3
- Any PR description claims about test coverage, bug reproduction, regression coverage, or edge cases

Treat these as test-integrity signals:

- Files under `tests/`
- `conftest.py`, fixtures, snapshots, golden outputs, UI.Vision macros, or committed browser/frontend test assets
- Test helpers, data fixtures, mock payloads, or expected-output files
- Production changes that add, fix, or alter behaviour without accompanying tests

### Subagent invocation

When triage selects launch, start exactly one subagent for this phase. The parent should wait for its result before completing `/pr-review`; use background execution only if the current Cursor session requires it.

```text
description: Test Integrity Sentinel
subagent_type: generalPurpose
model: gpt-5.5-medium
readonly: false
run_in_background: false
```

Use this task prompt shape, filling in the bracketed context from the current PR review:

```text
You are the Test Integrity Sentinel for the myebirdstuff repository.

Full repository path: [absolute repository path]
Issue: [issue number, title, and concise summary]
PR: [PR number or branch name, title, and concise summary]
Base branch: [base branch]
Diff scope: Review only changes in this PR relative to the base branch.
Changed production files: [paths or "none"]
Changed test files: [paths or "none"]
Changed fixtures / golden outputs / test helpers: [paths or "none"]
Quality-gate results already run by parent: [commands and pass/fail summary]

Your job is to check whether this PR's tests honestly validate the intended behaviour, or whether tests appear weakened, over-mocked, skipped, deleted, or shaped mainly to make the PR pass.

Scope:
- Focus primarily on new, modified, deleted, or renamed tests, fixtures, snapshots, golden outputs, and test helpers.
- Read related production code only as needed to understand what the tests are supposed to prove.
- Do not perform a full code review; leave general code-quality findings to the parent /pr-review pass.
- Do not expand beyond this PR diff unless a directly related production file is required to understand or repair a test.

Project-specific expectations:
- Streamlit UI code should stay thin; meaningful logic should be tested in core, presentation, helper, dataframe, or map-payload modules where possible.
- Tests should protect dataframe behaviour, filtering, caching, map payload generation, popup/banner formatting, share-summary rendering, GPS script behaviour, and frontend map behaviour when those areas are touched.
- Be cautious around caching, static dataframe assumptions, map performance instrumentation, GPS script behaviour, UI.Vision macro dependencies, committed Leaflet frontend build assets, snapshots, and golden-output updates.
- Do not ask for broad rewrites or perfect coverage. Focus on whether the tests in this PR give honest confidence.

Look for test shortcuts such as:
- `assert True`, trivial smoke-only assertions, or tests that only assert "does not crash" when behaviour should be checked.
- Assertions weakened from specific outputs to vague existence, length, type, or truthiness checks.
- Excessive mocking or monkeypatching of the code under test so the real behaviour is not exercised.
- Fixtures changed to avoid the failing case instead of preserving the real edge case.
- Deleted, skipped, or xfailed tests without a clear reason tied to this PR.
- Broad exception handling such as `pytest.raises(Exception)` where a precise failure is expected.
- Snapshot or golden-output updates that remove meaningful checks.
- Tests that only verify implementation details while missing user-visible or data-visible behaviour.
- New production behaviour with no corresponding test, especially for bug fixes.
- Test names or PR descriptions that claim a behaviour is covered when assertions do not actually cover it.
- E2E or performance-related tests being disabled, narrowed, or made less representative without explanation.

Fix policy:
- You are authorised to be fairly aggressive in fixing test-integrity problems within this PR's scope.
- You may strengthen assertions, restore meaningful edge-case fixture data, add missing regression tests, remove unjustified skips/xfails, narrow overbroad mocks, and update expected outputs only when the new expectations genuinely reflect intended behaviour.
- You may edit tests, fixtures, snapshots, golden outputs, and test helpers when the fix is clearly tied to this PR.
- You may make only minimal production-code edits needed to expose existing behaviour for testability, and only when they are clearly within the PR's intended behaviour. Otherwise, report the blocker/question to the parent instead of changing production code.
- Do not rewrite unrelated tests, broaden product scope, change public behaviour to satisfy a test, or perform suite-wide refactors.

After any edits:
- Run the narrowest relevant pytest command yourself when feasible, or tell the parent exactly which command must be rerun.
- Return a concise summary of files changed and checks run.

Output format:
1. Start with one verdict:
   - `No test-integrity concerns found`
   - `Test-integrity concerns found`
   - `Likely blocker: tests may be masking a problem`
2. If you made fixes, include `Fixes applied` with concise bullets.
3. If concerns remain, list them by severity: blocker, should fix, nit.
4. For each remaining finding, include:
   - the changed test file or fixture
   - what looks suspicious
   - why it weakens confidence
   - the concrete improvement recommended
5. Include `Checks run` with pass/fail status.
6. If uncertain, phrase it as a question for the parent/author rather than an accusation.
```

### Parent follow-up

After the subagent returns:

- Inspect any edits it made before proceeding.
- Re-run the relevant checks from Step 3 if the subagent edited tests, fixtures, helpers, snapshots, or production code.
- Fold the Sentinel verdict, fixes, remaining concerns, and rerun checks into the final `/pr-review` report.
- If the Sentinel reports a likely blocker, the overall `/pr-review` verdict should be **Changes requested** unless the parent can fix and verify it in-session.

---

## Step 4b — Nit-Fixer

Every `/pr-review` runs **Nit-Fixer triage** after Step 4 (whether Sentinel launched or skipped). Nit-Fixer fixes mechanical and readability nits in **PR-touched files** (whole-file scope). It does **not** edit test files — Sentinel owns test integrity.

### Sentinel vs Nit-Fixer

| Aspect | Sentinel (Step 4) | Nit-Fixer (Step 4b) |
| --- | --- | --- |
| **Focus** | Test honesty, assertions, mocks, fixtures | Imports, lint, format, typos, readability |
| **Edits tests?** | Yes, when justified | **Never** |
| **Model** | `gpt-5.5-medium` | `composer-2.5-fast` |
| **Philosophy** | Strengthen confidence in tests | See it, fix it in touched files |

### Triage — decide whether to launch Nit-Fixer

Use the **touched file list** from Step 2 (`gh pr diff --name-only` or `git diff --name-only origin/<base>...HEAD`).

**Run Nit-Fixer** when any touched file is on the **Nit-Fixer surface**: `explorer/`, scripts, Cursor commands/rules, docs, or map frontend source under `explorer/components/all_locations_map/frontend/src/`.

**Skip Nit-Fixer** when the diff touches **only** Sentinel-only paths (`tests/**`, fixtures, snapshots, etc.) or CI/workflow-only paths with no Nit-Fixer surface files. Record `Nit-Fixer: not applicable — [reason]` in the Step 7 report.

When triage selects **skip**, go to Step 5.

### Subagent invocation

When triage selects **run**, follow **[nit-fixer.md](nit-fixer.md)** Steps 3–4: run the proportionate quality gate, then launch exactly one Nit-Fixer subagent.

Pass the Sentinel summary (if Step 4 ran) in the subagent prompt so Nit-Fixer does not conflict with test edits.

```text
description: Nit-Fixer
subagent_type: generalPurpose
model: composer-2.5-fast
readonly: false
run_in_background: false
```

Use the task prompt and guardrails from **nit-fixer.md** (caps: ~10 files / ~150 lines; no commits).

### Parent follow-up

After the subagent returns:

- Inspect edits; re-run Step 3 checks if production or frontend source changed.
- Do **not** commit — author runs `/commit-work`.
- Fold Nit-Fixer verdict, fixes, and rerun checks into the Step 7 report.

---

## Step 5 — Scoped review checklist

Apply the checklist **only to files in the PR diff**. Do not audit the rest of the repo.

### Functionality

- [ ] Intended behaviour matches the linked issue / PR description
- [ ] Edge cases in the changed code handled gracefully
- [ ] Error handling appropriate for the change

### Code quality

- [ ] Change is focused — no unrelated drive-by edits
- [ ] Names clear; structure readable — apply `docs/python-style-guide.md` as the reference
- [ ] Tests/documentation updated if behaviour changed
- [ ] Comments explain *what* and *why*, not “see #123” as the only explanation
- [ ] Style issues in pre-existing code not flagged for wholesale rewrite; gentle local improvements in touched code are fine

### Security & safety (in-scope)

- [ ] No secrets or credentials exposed
- [ ] Inputs validated where the change introduces or touches user/API data

### PR hygiene

- [ ] PR title and description match the change
- [ ] Issue linkage correct (`Fixes #…` / `Refs #…`)
- [ ] Anything a human reviewer should know is in the PR body, not only in chat

---

## Step 6 — Fix policy (orchestration only)

The parent **does not** apply nits directly during `/pr-review`. Fixing is delegated:

| Actor | Fixes |
|-------|--------|
| **Sentinel (Step 4)** | Test integrity — assertions, fixtures, mocks, missing regression tests |
| **Nit-Fixer (Step 4b)** | Mechanical and readability nits in touched production/docs/command/frontend source |
| **Parent** | Blockers requiring author decision; verdict and report only |

**Parent may fix without asking** only when:

- Nit-Fixer or Sentinel failed to run (tooling error) **and** the fix is a single trivial typo clearly blocking the review report
- The fix is required to complete the review workflow itself (not general code polish)

**Do not fix without asking** when:

- The fix changes behaviour, API, or architecture beyond Nit-Fixer guardrails
- It expands scope beyond the linked issue
- Nit-Fixer reported the item as out of scope or cap-exceeded — list it for author decision instead

Prefer **Ready to merge** over **Ready with nits** when Nit-Fixer fixed all in-scope items. Do not list nits Nit-Fixer could have fixed within caps.

All fixes stay **unstaged** — author runs `/commit-work`.

---

## Step 7 — Report (standard output)

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

### Test Integrity Sentinel

- Triage decision: **launched** (test surface / behaviour surface) or **skipped** (with the reason)
- Verdict from the Sentinel subagent (omit if skipped)
- Fixes it applied, or “None”
- Remaining test-integrity concerns, or “None”
- Any tests/checks it ran directly

### Nit-Fixer

- Triage decision: **launched** or **skipped** (with the reason)
- Verdict from the Nit-Fixer subagent (omit if skipped)
- Fixes it applied, or “None”
- Remaining out-of-scope nits, or “None”
- Approx files/lines touched
- Reminder: fixes unstaged — author runs `/commit-work`

### Fixes applied during review

- Bullet list of Sentinel and Nit-Fixer fixes made in-repo, or “None” (parent fixes, if any)

### Checks run

- Commands executed and pass/fail (e.g. `ruff`, `pytest …`)
- Include parent quality-gate commands, Sentinel-run commands, Nit-Fixer reruns, and any reruns after fixes

### Follow-ups (optional)

- Out-of-scope items → suggest a GitHub issue so they are not lost

---

## Do not

- Treat this as a full-project or architecture review — use `/code-review` for that
- Rewrite large areas without author agreement
- Block on nits that Nit-Fixer could safely fix in scope — launch Nit-Fixer instead of listing them
- Apply mechanical/readability nits directly on the parent when Step 4b triage says to launch Nit-Fixer — launch the subagent instead
- Let Nit-Fixer edit test files — Sentinel owns tests
- Self-review test integrity on the parent model when Step 4 triage says to launch the subagent — launch it instead
- Spawn the Sentinel subagent for a diff with no test or behaviour surface (e.g. docs/command/config-only) — record it as not applicable per Step 4 triage
- Commit Nit-Fixer or Sentinel fixes during `/pr-review`
- Substitute for CI or required human reviewers when policy applies

Provide constructive, actionable feedback scoped to the linked issue and PR.
