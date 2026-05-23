# Security

## Reporting a vulnerability

If you discover a **security vulnerability** in this project, please report it responsibly:

- Prefer **[GitHub private vulnerability reporting](https://github.com/jimchurches/myebirdstuff/security/advisories/new)** (Security → Report a vulnerability) if that option is enabled for this repository.
- Otherwise, contact the repository owner **privately** (do not open a public issue or PR with exploit details before it is addressed).

Please include enough detail to reproduce or understand the issue. We will treat reports seriously and aim to respond in a reasonable timeframe.

---

## Dependency scanning (CI)

Continuous integration runs **`pip-audit`** via [`scripts/check_pip_audit.py`](scripts/check_pip_audit.py) against the repository’s requirement files (see [.github/workflows/tests.yml](.github/workflows/tests.yml)).

Policy:

- **Fail** on any reported vulnerability that is not explicitly deferred.
- **Defer** only advisories listed in `IGNORE_UNTIL_FIX_AVAILABLE` inside that script, and **only while** the audit database reports **no** `fix_versions` for that ID. When a fix appears on PyPI, CI **fails** with instructions to upgrade and remove the deferral entry.

### Deferred until fix available (CI)

| ID | Package | Rationale |
|----|---------|-----------|
| `PYSEC-2024-277` | `joblib` (transitive via `scikit-learn`) | CVE-2024-34997: supplier-disputed; `NumpyArrayWrapper.read_array` is for trusted cache IPC only. No fix on PyPI yet. CI auto-fails once `fix_versions` is non-empty. |

---

## Scope

This document is about **coordinated disclosure** and **automated dependency checks**. It is not a full threat model. Personal data (eBird exports, API keys in local config) should stay out of git; see [CONTRIBUTING.md](CONTRIBUTING.md) and the explorer install docs.
