#!/usr/bin/env python3
"""Fail when embedded Explorer build id is older than GitHub ``releases/latest`` (refs #189).

Loads :mod:`explorer.core.explorer_release_version` by file path so this script does not import
``explorer.core`` (which eagerly pulls ``pandas`` via ``explorer.core.__init__``).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = _REPO_ROOT / "explorer" / "app" / "streamlit" / "explorer_build_version.txt"
_GITHUB_LATEST_API = "https://api.github.com/repos/jimchurches/myebirdstuff/releases/latest"
_HTTP_TIMEOUT_SEC = 15.0
_HTTP_USER_AGENT = "myebirdstuff-ci-explorer-build-vs-latest (+https://github.com/jimchurches/myebirdstuff)"


def _load_explorer_release_version_module():
    path = _REPO_ROOT / "explorer" / "core" / "explorer_release_version.py"
    spec = importlib.util.spec_from_file_location("_explorer_release_version_ci", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = _load_explorer_release_version_module()
    if not _VERSION_FILE.is_file():
        print(f"ERROR: missing {_VERSION_FILE}", file=sys.stderr)
        return 1
    embedded = _VERSION_FILE.read_text(encoding="utf-8").strip()
    if not embedded:
        print("ERROR: explorer_build_version.txt is empty", file=sys.stderr)
        return 1
    if mod.parse_explorer_release_tuple(embedded) is None:
        print(
            f"ERROR: explorer_build_version.txt is not a valid release id: {embedded!r}",
            file=sys.stderr,
        )
        return 1

    req = urllib.request.Request(
        _GITHUB_LATEST_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": _HTTP_USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SEC) as resp:  # noqa: S310
            if int(resp.status) != 200:
                print(f"ERROR: GitHub HTTP {resp.status}", file=sys.stderr)
                return 1
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        print(f"ERROR: could not fetch GitHub latest release: {e}", file=sys.stderr)
        return 1

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON from GitHub: {e}", file=sys.stderr)
        return 1

    tag = data.get("tag_name")
    if not isinstance(tag, str) or not tag.strip():
        print("ERROR: GitHub releases/latest response missing tag_name", file=sys.stderr)
        return 1
    tag = tag.strip()
    if mod.parse_explorer_release_tuple(tag) is None:
        print(
            f"ERROR: cannot parse GitHub latest tag_name {tag!r}; fix the tag or extend parsing",
            file=sys.stderr,
        )
        return 1

    if mod.remote_release_is_newer_than_embedded(tag, embedded):
        print(
            "ERROR: explorer_build_version.txt is behind GitHub latest release.\n"
            f"  embedded: {embedded!r}\n"
            f"  GitHub:   {tag!r}\n"
            "Bump explorer/app/streamlit/explorer_build_version.txt before merging to main.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: embedded {embedded!r} is not behind GitHub latest {tag!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
