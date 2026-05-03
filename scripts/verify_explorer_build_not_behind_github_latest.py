#!/usr/bin/env python3
"""Main-branch gate for ``explorer_build_version.txt`` (refs #189).

When ``RELEASE_TODAY`` is set (``YYYY-MM-DD``, from CI), the embedded id’s **calendar base date**
must match it exactly (so bare ``YYYY-MM-DD`` or same-day ``YYYY-MM-DD.N`` with ``N >= 2``).

Always checks GitHub ``releases/latest``: the embedded id must **not** be strictly older than that
tag (after parsing / ``Beta`` normalization).

Loads :mod:`explorer.core.explorer_release_version` by file path so this script does not import
``explorer.core`` (which eagerly pulls ``pandas`` via ``explorer.core.__init__``).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = _REPO_ROOT / "explorer" / "app" / "streamlit" / "explorer_build_version.txt"
_GITHUB_LATEST_API = "https://api.github.com/repos/jimchurches/myebirdstuff/releases/latest"
_HTTP_TIMEOUT_SEC = 15.0
_HTTP_USER_AGENT = "myebirdstuff-ci-explorer-build-vs-latest (+https://github.com/jimchurches/myebirdstuff)"
_RELEASE_TODAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
    tup = mod.parse_explorer_release_tuple(embedded)
    if tup is None:
        print(
            f"ERROR: explorer_build_version.txt is not a valid release id: {embedded!r}",
            file=sys.stderr,
        )
        return 1
    y, mo, d, _rev = tup
    base_yyyy_mm_dd = f"{y:04d}-{mo:02d}-{d:02d}"

    release_today = str(os.environ.get("RELEASE_TODAY", "")).strip()
    if release_today:
        if not _RELEASE_TODAY_RE.match(release_today):
            print(
                f"ERROR: RELEASE_TODAY must be YYYY-MM-DD (got {release_today!r})",
                file=sys.stderr,
            )
            return 1
        if base_yyyy_mm_dd != release_today:
            print(
                "ERROR: explorer_build_version.txt calendar date must match RELEASE_TODAY "
                f"(Australia/Sydney calendar day in CI).\n"
                f"  embedded base: {base_yyyy_mm_dd!r}\n"
                f"  RELEASE_TODAY: {release_today!r}\n"
                "Set explorer/app/streamlit/explorer_build_version.txt to today's date "
                "(or same-day .N with N >= 2).",
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

    msg = f"OK: embedded {embedded!r} is not behind GitHub latest {tag!r}"
    if release_today:
        msg += f"; base date matches RELEASE_TODAY {release_today!r}"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
