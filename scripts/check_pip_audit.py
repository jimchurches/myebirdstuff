#!/usr/bin/env python3
"""Run pip-audit and enforce dependency vulnerability policy for CI.

Advisories listed in :data:`IGNORE_UNTIL_FIX_AVAILABLE` are tolerated only while
the vulnerability database reports no ``fix_versions``. When a fix appears on
PyPI, this script fails so the team upgrades and removes the deferral entry.

See SECURITY.md for rationale per advisory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Vulnerability ID -> package name (for error messages). CI fails once fix_versions is non-empty.
IGNORE_UNTIL_FIX_AVAILABLE: dict[str, str] = {
    "PYSEC-2024-277": "joblib",
}

_DEFAULT_REQUIREMENTS = (
    _REPO_ROOT / "requirements.txt",
    _REPO_ROOT / "requirements-gps-script.txt",
)


def evaluate_audit_report(
    dependencies: list[dict[str, Any]],
    *,
    ignore_until_fix: dict[str, str] | None = None,
) -> tuple[int, list[str]]:
    """Apply policy to pip-audit JSON ``dependencies`` list.

    Returns ``(exit_code, lines)`` where exit code 0 means pass.
    """
    deferrals = ignore_until_fix if ignore_until_fix is not None else IGNORE_UNTIL_FIX_AVAILABLE
    failures: list[str] = []
    deferred_ok: list[str] = []

    for dep in dependencies:
        name = str(dep.get("name") or "?")
        for vuln in dep.get("vulns") or []:
            vid = str(vuln.get("id") or "")
            if not vid:
                continue
            fix_versions = [str(v) for v in (vuln.get("fix_versions") or []) if v]
            if vid in deferrals:
                expected_pkg = deferrals[vid]
                if fix_versions:
                    failures.append(
                        f"{vid} ({name}, deferral registered for {expected_pkg!r}): "
                        f"fix now available — upgrade and remove from "
                        f"IGNORE_UNTIL_FIX_AVAILABLE in scripts/check_pip_audit.py "
                        f"(fix versions: {', '.join(fix_versions)})"
                    )
                else:
                    deferred_ok.append(
                        f"{vid} ({name}): deferred — no fix version on PyPI "
                        f"(see SECURITY.md)"
                    )
                continue
            failures.append(
                f"{vid} ({name}): reported vulnerability"
                + (f" — fix versions: {', '.join(fix_versions)}" if fix_versions else "")
            )

    if failures:
        lines = ["pip-audit policy: FAILED", *failures]
        if deferred_ok:
            lines.append("")
            lines.append("Still deferred (no fix yet):")
            lines.extend(f"  - {line}" for line in deferred_ok)
        return 1, lines

    lines = ["pip-audit policy: OK"]
    if deferred_ok:
        lines.append("Deferred until fix available:")
        lines.extend(f"  - {line}" for line in deferred_ok)
    else:
        lines.append("No known vulnerabilities.")
    return 0, lines


def _run_pip_audit(
    requirement_files: list[Path],
    *,
    cache_dir: Path | None,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "-f",
        "json",
        "--progress-spinner",
        "off",
    ]
    for req in requirement_files:
        cmd.extend(["-r", str(req)])
    if cache_dir is not None:
        cmd.extend(["--cache-dir", str(cache_dir)])

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO_ROOT)
    stdout = (proc.stdout or "").strip()
    if not stdout:
        err = proc.stderr or ""
        raise RuntimeError(
            f"pip-audit produced no JSON (exit {proc.returncode}).\n{err}".strip()
        )
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pip-audit JSON parse failed: {exc}\n{stdout[:500]}") from exc
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-r",
        "--requirement",
        action="append",
        type=Path,
        dest="requirements",
        help="requirements file (default: requirements.txt + requirements-gps-script.txt)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="pip-audit HTTP cache directory (optional)",
    )
    args = parser.parse_args(argv)

    req_files = list(args.requirements) if args.requirements else list(_DEFAULT_REQUIREMENTS)
    for path in req_files:
        if not path.is_file():
            print(f"ERROR: requirements file not found: {path}", file=sys.stderr)
            return 1

    try:
        report = _run_pip_audit(req_files, cache_dir=args.cache_dir)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    code, lines = evaluate_audit_report(report.get("dependencies") or [])
    out = sys.stdout if code == 0 else sys.stderr
    for line in lines:
        print(line, file=out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
