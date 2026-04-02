# Security

## Reporting a vulnerability

If you discover a **security vulnerability** in this project, please report it responsibly:

- Prefer **[GitHub private vulnerability reporting](https://github.com/jimchurches/myebirdstuff/security/advisories/new)** (Security → Report a vulnerability) if that option is enabled for this repository.
- Otherwise, contact the repository owner **privately** (do not open a public issue or PR with exploit details before it is addressed).

Please include enough detail to reproduce or understand the issue. We will treat reports seriously and aim to respond in a reasonable timeframe.

---

## Dependency scanning (CI)

Continuous integration runs **`pip-audit`** against the repository’s requirement files as defined in [.github/workflows/tests.yml](.github/workflows/tests.yml) (exact `-r` list may change as dependencies evolve).

**Allowlisted advisory:** **`CVE-2026-4539`** is passed to `pip-audit` with `--ignore-vuln` because, at the time this was added, **no fixed package version was available** and the audit would otherwise fail the job with no remediation path. CI is still configured to **fail on any other** reported vulnerability.

This allowlist is a **transparency** note about the pipeline, not a substitute for fixing the underlying issue when upstream publishes a fix. Revisit the ignore when dependencies or the advisory status changes.

---

## Scope

This document is about **coordinated disclosure** and **automated dependency checks**. It is not a full threat model. Personal data (eBird exports, API keys in local config) should stay out of git; see [CONTRIBUTING.md](CONTRIBUTING.md) and the explorer install docs.
