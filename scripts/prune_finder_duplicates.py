#!/usr/bin/env python3
"""Detect and optionally remove macOS Finder "copy N" duplicates in the repo.

Finder often creates siblings like ``README 2.md``, ``module 2.py``, or
``frontend/build/static/css 4/``. These are never intentional project files.

Usage (repo root)::

    python3 scripts/prune_finder_duplicates.py          # delete matches
    python3 scripts/prune_finder_duplicates.py --check  # exit 1 if any remain

CI uses ``--check``. The Cursor **commit-work** command runs the default (prune).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Do not walk dependency / cache trees (duplicates inside them are harmless noise).
_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".hypothesis",
        "htmlcov",
        "_ruff_local",
    }
)
_SKIP_DIR_PREFIXES = (".venv-",)

# "file 2.py", "README 2.md"
_FINDER_FILE_RE = re.compile(r" \d+\.")
# "something 2" directory
_FINDER_DIR_RE = re.compile(r" \d+$")
# build/static/css 4 — shared with build_all_locations_map_frontend.py
_BUILD_STATIC_JUNK_RE = re.compile(r"^(css|js) \d+$")


def _should_skip_dir(name: str) -> bool:
    if name in _SKIP_DIR_NAMES:
        return True
    return any(name.startswith(p) for p in _SKIP_DIR_PREFIXES)


def find_finder_duplicates(root: Path) -> list[Path]:
    """Return paths under *root* that look like Finder copy duplicates."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        base = Path(dirpath)
        for name in list(dirnames):
            full = base / name
            if _FINDER_DIR_RE.search(name) or (
                base.name == "static" and _BUILD_STATIC_JUNK_RE.match(name)
            ):
                found.append(full)
        for name in filenames:
            if _FINDER_FILE_RE.search(name):
                found.append(base / name)
    return sorted(found)


def prune_finder_duplicates(root: Path) -> list[Path]:
    """Delete duplicate paths; return the list that was removed."""
    removed: list[Path] = []
    for path in find_finder_duplicates(root):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
        else:
            continue
        removed.append(path)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not delete; exit 1 if any duplicates are present.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root (default: parent of scripts/).",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        dupes = find_finder_duplicates(root)
        if dupes:
            print("macOS Finder duplicate paths (remove or run without --check):", file=sys.stderr)
            for p in dupes:
                print(f"  {p.relative_to(root).as_posix()}", file=sys.stderr)
            sys.exit(1)
        print("OK: no Finder duplicate paths under", root)
        return

    removed = prune_finder_duplicates(root)
    if removed:
        print(f"Removed {len(removed)} Finder duplicate path(s):")
        for p in removed:
            print(f"  {p.relative_to(root).as_posix()}")
    else:
        print("No Finder duplicate paths found.")


if __name__ == "__main__":
    main()
