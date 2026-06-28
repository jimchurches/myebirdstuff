# PR Review (myebirdstuff)

**When to use:** Pre-merge review of a **single** linked issue and its PR — e.g. a focused bug fix or small feature. For larger or multi-area changes, use `/code-review` instead.

Every `/pr-review` run includes a **Test Integrity Sentinel** triage. The parent agent resolves the PR context and local checks, then — when the diff has a test or behaviour surface (see Step 4) — delegates a focused test-integrity review to a pinned reviewer subagent so tests are reviewed by a different model from the authoring flow. The reviewer model is defined once in the Step 4 invocation block.

## Relationship to `/code-review`

| | `/pr-review` | `/code-review` |
|---|---|---|
| **Scope** | One issue + one PR diff vs `beta-next` | Whole change set; architecture and cross-cutting concerns |
| **When** | Small fixes, pre-merge sanity check | Before opening/updating a large PR, or multi-file behaviour changes |
| **Fixes during review** | Apply minor, low-risk nits without asking; allow Sentinel to strengthen in-scope tests | Default to listing gaps; only trivial fixes if the author wants them in-session |

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

Prefer a **narrower** pytest path when the diff is clearly isolated (e.g. `tests/path/to/test_module.py`). Fold failures into the review; fix trivial ones under Step 6.

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

When triage selects **skip**, go straight to Step 5. The remainder of Step 4 applies only when launching.

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

## Step 6 — In-review fixes

There are two fix policies in this command:

- **Parent review fixes:** minor only, as described below.
- **Sentinel test-integrity fixes:** more assertive within tests and fixtures, but only under Step 4's scope and guardrails.

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

### Fixes applied during review

- Bullet list of parent review fixes and Sentinel fixes made in-repo, or “None”

### Checks run

- Commands executed and pass/fail (e.g. `ruff`, `pytest …`)
- Include parent quality-gate commands, Sentinel-run commands, and any reruns after fixes

### Follow-ups (optional)

- Out-of-scope items → suggest a GitHub issue so they are not lost

---

## Do not

- Treat this as a full-project or architecture review — use `/code-review` for that
- Rewrite large areas without author agreement
- Block on nits that you could safely fix under Step 6
- Self-review test integrity on the parent model when Step 4 triage says to launch the subagent — launch it instead
- Spawn the Sentinel subagent for a diff with no test or behaviour surface (e.g. docs/command/config-only) — record it as not applicable per Step 4 triage
- Substitute for CI or required human reviewers when policy applies

Provide constructive, actionable feedback scoped to the linked issue and PR.
