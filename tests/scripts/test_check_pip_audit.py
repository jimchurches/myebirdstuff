"""Tests for scripts/check_pip_audit.py policy evaluation."""

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
    assert code == 0
    assert any("OK" in line for line in lines)


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
    assert any("deferred" in line.lower() for line in lines)


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
    assert code == 1
    assert any("CVE-2099-0001" in line for line in lines)


def test_integration_against_repo_requirements() -> None:
    """Live pip-audit run; joblib deferral should pass while no fix is published."""
    proc = __import__("subprocess").run(
        [sys.executable, str(_REPO / "scripts" / "check_pip_audit.py")],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
