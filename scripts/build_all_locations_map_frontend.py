#!/usr/bin/env python3
"""Build the All locations Streamlit map component and sanity-check ``frontend/build``.

Run from repo root after editing ``explorer/components/all_locations_map/frontend/src/``:

    python3 scripts/build_all_locations_map_frontend.py

The committed ``frontend/build/`` tree is what Explorer loads at runtime (see component README).
This script runs ``npm ci`` + ``npm run build``, then reports expected vs stray files so you know
what to ``git add`` and what to delete (e.g. macOS Finder duplicates like ``static/css 4/``).

Exit 1 if junk or unexpected files remain under ``build/`` (use ``--prune-junk`` to remove known junk only).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND = _REPO_ROOT / "explorer/components/all_locations_map/frontend"
_BUILD = _FRONTEND / "build"

# macOS Finder "copy N" folders — never produced by Create React App.
_JUNK_DIR_RE = re.compile(r"^(css|js) \d+$")


def _run_npm_build(*, skip_install: bool) -> None:
    if not (_FRONTEND / "package.json").is_file():
        print(f"error: missing {_FRONTEND / 'package.json'}", file=sys.stderr)
        sys.exit(1)
    if not skip_install:
        subprocess.run(["npm", "ci"], cwd=_FRONTEND, check=True)
    subprocess.run(["npm", "run", "build"], cwd=_FRONTEND, check=True)


def _manifest_paths(build_dir: Path) -> set[Path]:
    manifest_path = build_dir / "asset-manifest.json"
    if not manifest_path.is_file():
        return set()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    out: set[Path] = set()
    for rel in data.get("files", {}).values():
        if isinstance(rel, str) and rel.startswith("./"):
            path = Path(rel[2:])
            if path.suffix != ".map":
                out.add(path)
    for rel in data.get("entrypoints", []):
        if isinstance(rel, str):
            out.add(Path(rel))
    out.add(Path("index.html"))
    out.add(Path("asset-manifest.json"))
    # LICENSE is emitted beside hashed main.js but not listed in asset-manifest.
    for js in (build_dir / "static/js").glob("main.*.js"):
        lic = js.with_suffix(js.suffix + ".LICENSE.txt")
        if lic.is_file():
            out.add(lic.relative_to(build_dir))
    return out


def _find_junk_dirs(build_dir: Path) -> list[Path]:
    """Finder duplicates like ``static/css 4/`` or ``static/js 5/`` (siblings of real ``css/``, ``js/``)."""
    junk: list[Path] = []
    static = build_dir / "static"
    if not static.is_dir():
        return junk
    for child in static.iterdir():
        if child.is_dir() and _JUNK_DIR_RE.match(child.name):
            junk.append(child)
    return junk


def _find_unexpected_files(build_dir: Path, expected: set[Path]) -> list[Path]:
    unexpected: list[Path] = []
    if not build_dir.is_dir():
        return [Path("(build directory missing)")]
    for path in sorted(build_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(build_dir)
        if rel.suffix == ".map":
            continue  # gitignored; safe to delete locally
        if rel in expected:
            continue
        unexpected.append(rel)
    return unexpected


def _prune_junk(junk_dirs: list[Path]) -> None:
    for d in junk_dirs:
        shutil.rmtree(d)
        print(f"removed junk directory: {d}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Run only ``npm run build`` (skip ``npm ci``).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Do not run npm; only validate existing ``frontend/build/``.",
    )
    parser.add_argument(
        "--prune-junk",
        action="store_true",
        help="Delete macOS Finder duplicate folders (``css 4/``, ``js 5/``, …) under ``build/static``.",
    )
    args = parser.parse_args()

    if not args.check_only:
        print(f"Building {_FRONTEND.relative_to(_REPO_ROOT)} …")
        _run_npm_build(skip_install=args.skip_install)

    if not _BUILD.is_dir():
        print(f"error: no build output at {_BUILD}", file=sys.stderr)
        sys.exit(1)

    expected = _manifest_paths(_BUILD)
    junk_dirs = _find_junk_dirs(_BUILD)
    unexpected = _find_unexpected_files(_BUILD, expected)

    print("\nCommit these paths under frontend/build/ (with your src/ changes):")
    for rel in sorted(expected):
        print(f"  {rel.as_posix()}")

    map_files = sorted(_BUILD.rglob("*.map"))
    if map_files:
        print("\nSource maps (gitignored — do not commit; safe to delete locally):")
        for p in map_files:
            print(f"  {p.relative_to(_BUILD).as_posix()}")

    if junk_dirs:
        print("\nJunk (not from npm — usually macOS Finder duplicates). Do not commit:", file=sys.stderr)
        for d in junk_dirs:
            print(f"  {d.relative_to(_BUILD).as_posix()}/", file=sys.stderr)
        if args.prune_junk:
            _prune_junk(junk_dirs)
            junk_dirs = _find_junk_dirs(_BUILD)

    if unexpected:
        print("\nUnexpected files under build/ (orphan bundles or manual copies). Remove or rebuild:", file=sys.stderr)
        for rel in unexpected:
            print(f"  {rel.as_posix()}", file=sys.stderr)

    if junk_dirs or unexpected:
        print(
            "\nTip: run `python3 scripts/build_all_locations_map_frontend.py` from repo root "
            "(add `--prune-junk` for Finder duplicate folders only).",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nbuild/ looks clean. Next: git status, then commit src/ + build/ together.")


if __name__ == "__main__":
    main()
