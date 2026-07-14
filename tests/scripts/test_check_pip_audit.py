"""Tests for scripts/check_pip_audit.py policy evaluation.

Live pip-audit runs are covered by the ``dependency-audit`` CI job, not pytest
(the unit-tests job does not install pip-audit).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "scripts"))

import check_pip_audit as mod  # noqa: E402


def test_evaluate_passes_with_no_vulnerabilities() -> None:
    code, lines = mod.evaluate_audit_report(
        [{"name": "pandas", "version": "3.0.3", "vulns": []}],
        ignore_until_fix={"PYSEC-2024-277": "joblib"},
    )
    assert (code, lines) == (
        0,
        ["pip-audit policy: OK", "No known vulnerabilities."],
    )


def test_defers_advisory_when_no_fix_versions() -> None:
    code, lines = mod.evaluate_audit_report(
        [
            {
                "name": "joblib",
                "version": "1.5.3",
                "vulns": [
                    {
                        "id": "PYSEC-2024-277",
                        "fix_versions": [],
                        "aliases": ["CVE-2024-34997"],
                    }
                ],
            }
        ],
        ignore_until_fix={"PYSEC-2024-277": "joblib"},
    )
    assert code == 0
    assert lines == [
        "pip-audit policy: OK",
        "Deferred until fix available:",
        "  - PYSEC-2024-277 (joblib): deferred — no fix version on PyPI (see SECURITY.md)",
    ]


def test_fails_when_deferred_advisory_has_fix_versions() -> None:
    code, lines = mod.evaluate_audit_report(
        [
            {
                "name": "joblib",
                "version": "1.5.3",
                "vulns": [
                    {
                        "id": "PYSEC-2024-277",
                        "fix_versions": ["1.5.4"],
                    }
                ],
            }
        ],
        ignore_until_fix={"PYSEC-2024-277": "joblib"},
    )
    assert code == 1
    joined = "\n".join(lines)
    assert "fix now available" in joined
    assert "1.5.4" in joined
    assert "IGNORE_UNTIL_FIX_AVAILABLE" in joined


def test_fails_on_unlisted_vulnerability() -> None:
    code, lines = mod.evaluate_audit_report(
        [
            {
                "name": "example",
                "version": "1.0.0",
                "vulns": [{"id": "CVE-2099-0001", "fix_versions": ["1.0.1"]}],
            }
        ],
        ignore_until_fix={"PYSEC-2024-277": "joblib"},
    )
    assert (code, lines) == (
        1,
        [
            "pip-audit policy: FAILED",
            "CVE-2099-0001 (example): reported vulnerability — fix versions: 1.0.1",
        ],
    )


def test_reports_failures_and_still_deferred_advisories_together() -> None:
    code, lines = mod.evaluate_audit_report(
        [
            {
                "name": "joblib",
                "vulns": [{"id": "PYSEC-2024-277", "fix_versions": []}],
            },
            {
                "name": "example",
                "vulns": [{"id": "CVE-2099-0002", "fix_versions": []}],
            },
        ],
        ignore_until_fix={"PYSEC-2024-277": "joblib"},
    )

    assert code == 1
    assert lines == [
        "pip-audit policy: FAILED",
        "CVE-2099-0002 (example): reported vulnerability",
        "",
        "Still deferred (no fix yet):",
        "  - PYSEC-2024-277 (joblib): deferred — no fix version on PyPI (see SECURITY.md)",
    ]
