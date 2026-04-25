# Security

## Reporting a vulnerability

If you discover a **security vulnerability** in this project, please report it responsibly:

- Prefer **[GitHub private vulnerability reporting](https://github.com/jimchurches/myebirdstuff/security/advisories/new)** (Security → Report a vulnerability) if that option is enabled for this repository.
- Otherwise, contact the repository owner **privately** (do not open a public issue or PR with exploit details before it is addressed).

Please include enough detail to reproduce or understand the issue. We will treat reports seriously and aim to respond in a reasonable timeframe.

---

## Dependency scanning (CI)

Continuous integration runs **`pip-audit`** against the repository’s requirement files as defined in [.github/workflows/tests.yml](.github/workflows/tests.yml) (exact `-r` list may change as dependencies evolve).

Current policy is to run `pip-audit` without an allowlist in CI and fail on reported vulnerabilities so remediation decisions stay explicit in pull requests.

---

## Scope

This document is about **coordinated disclosure** and **automated dependency checks**. It is not a full threat model. Personal data (eBird exports, API keys in local config) should stay out of git; see [CONTRIBUTING.md](CONTRIBUTING.md) and the explorer install docs.
