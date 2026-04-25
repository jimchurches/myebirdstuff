#!/usr/bin/env python3
"""Validate ``explorer/app/streamlit/explorer_build_version.txt`` format (CI + local). Refs #189."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_VERSION_FILE = _REPO_ROOT / "explorer" / "app" / "streamlit" / "explorer_build_version.txt"
_BASE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SUFFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.(?:[2-9]|[1-9]\d+)$")


def _is_valid_build_version(value: str) -> bool:
    """Standalone format check (keeps repo-hygiene job independent of heavy imports)."""
    return bool(_BASE_RE.match(value) or _SUFFIX_RE.match(value))


def main() -> int:
    if not _VERSION_FILE.is_file():
        print(f"ERROR: missing {_VERSION_FILE}", file=sys.stderr)
        return 1
    raw = _VERSION_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        print("ERROR: explorer_build_version.txt is empty", file=sys.stderr)
        return 1
    if not _is_valid_build_version(raw):
        print(
            "ERROR: explorer_build_version.txt must be YYYY-MM-DD or YYYY-MM-DD.N with N >= 2 "
            f"(got {raw!r})",
            file=sys.stderr,
        )
        return 1
    print(f"OK: Explorer build version {raw!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
