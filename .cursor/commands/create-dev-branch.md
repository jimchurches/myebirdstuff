# Create development branch (myebirdstuff)

You are creating a new local development branch for **myebirdstuff**, following this repo’s branching model.

## Branching model (important)

- `main` = stable / current beta (live)
- `beta-next` = integration branch for the upcoming release
- New feature/fix work should branch from **`beta-next`** unless the user explicitly names another base (e.g. a hotfix from `main`)

This matches **Commit work**, **Open PR**, and **Merge PR** in this repo.

---

## Step 1 — Confirm inputs

From the user (or infer only when obvious, e.g. from an open issue in context):

1. **GitHub issue number** (optional)
2. **Short description** — slug-style: lowercase words separated by hyphens
3. **Base branch** (optional) — default **`beta-next`**

If there is no issue number, omit it from the branch name (do not invent a number).

---

## Step 2 — Determine branch name

**With issue number** (preferred when an issue exists):

```text
<issue-number>-<short-description>
```

Examples:

- `123-map-focus-improvements`
- `245-fix-banner-title`
- `167-enhancement-improve-all-locations-map-banner-content` (optional type word after the number is fine)

**Without issue number:**

```text
<short-description>
```

Example:

- `refactor-colour-schemes`

**Rules**

- Lowercase only; hyphens (`-`) only; no spaces or shell‑unsafe characters
- Keep it concise but meaningful (roughly **≤ 60 characters** total is a good target)
- Avoid a slug that is **only digits**, so it is not mistaken for an issue id

There is **no** separate “confirm the branch name” step: once inputs and preconditions pass, create the branch with the name you derived.

---

## Step 3 — Preconditions (do not skip)

1. **Working tree** must be clean (`git status`). If not, stop and ask whether to **commit**, **stash**, or **abort** — do not switch branches with uncommitted work unless the user explicitly chooses that path.

2. **Branch name must not already exist** locally or on `origin`:
   - Local: `git show-ref --verify --quiet refs/heads/<branch-name>` — if exit code `0`, the branch exists; stop and ask
   - Remote: `git ls-remote --heads origin <branch-name>` — if non‑empty, stop and ask (use a different name or delete only if the user explicitly requests and it is safe)

3. **Execute from the repository root** (where `.git` lives). Use **`git switch`** (not legacy `git checkout` for branch changes).

---

## Step 4 — Update base and create branch

Use the chosen base (default **`beta-next`**). Replace `beta-next` below if the user overrode the base.

```bash
git fetch origin
git switch <base-branch>
git pull origin <base-branch>
git switch -c <branch-name>
```

Notes:

- **`git fetch origin`** first avoids creating a branch from a stale local `beta-next`.
- **`git pull origin <base-branch>`** is explicit and works even if upstream tracking is misconfigured.

---

## Step 5 — Optional: push and set upstream

Only if the user wants the branch on GitHub immediately (or your workflow expects an early push):

```bash
git push -u origin <branch-name>
```

Do **not** force‑push when creating a new branch. If push is rejected because the name exists on the remote, stop and reconcile with the user.

---

## Step 6 — Output summary

Report clearly:

- **Branch name** created
- **Base branch** and tip (e.g. short `git rev-parse --short HEAD` after pull)
- **Current branch** after `git switch -c` (must be the new branch)

Example:

> Created and switched to `123-map-focus-improvements` from `beta-next` at `abc1234`. Remote not pushed yet.

---

## Do not

- Create the new branch from **`main`** unless the user explicitly asked for that base
- Proceed with a **dirty** working tree without confirmation
- **Invent** issue numbers
- **Overwrite** an existing branch (`-C`, `-f`, force push) unless the user explicitly instructs and risks are understood

---

## For Cursor / agent execution

- Run the git commands yourself from the repo root; use **`git_write`** and **`network`** (for `fetch` / `pull` / `push`) when the environment requires it.
- If any step fails, stop, show the command output, and ask how to proceed.

---

## Why this command exists

- Keeps new work aligned with **`beta-next`** so PRs do not replay unrelated `main` history or miss integration commits.
- Enforces predictable branch names for issue linking and review.
