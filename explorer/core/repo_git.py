"""Best-effort git ref for linking to source files on GitHub (local dev).

Deployed builds (Streamlit Cloud, etc.) usually have no ``.git`` directory; in
that case we fall back to ``main``. Override with environment variable
``EXPLORER_README_GITHUB_BRANCH`` when the deployed branch is not ``main``.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote


def _repo_root() -> Path | None:
    """Return repository root (directory containing ``.git``), if known."""
    # explorer/core/repo_git.py -> parents[2] == repo root
    here = Path(__file__).resolve()
    return here.parents[2]


def github_blob_ref_for_readme() -> str:
    """Branch name or short commit SHA for ``github.com/.../blob/<ref>/...``.

    Environment ``EXPLORER_README_GITHUB_BRANCH`` overrides (not cached).

    Returns ``main`` when not in a git checkout or when git commands fail.
    """
    override = os.environ.get("EXPLORER_README_GITHUB_BRANCH", "").strip()
    if override:
        return override
    root = _repo_root()
    if root is None or not (root / ".git").exists():
        return "main"
    return _git_ref_at_repo_root(str(root.resolve()))


@lru_cache(maxsize=8)
def _git_ref_at_repo_root(resolved_root: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", resolved_root, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if r.returncode == 0:
            name = (r.stdout or "").strip()
            if name and name != "HEAD":
                return name
        r2 = subprocess.run(
            ["git", "-C", resolved_root, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if r2.returncode == 0 and (r2.stdout or "").strip():
            return (r2.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "main"


def explorer_readme_github_page_url(repo_root_url: str) -> str:
    """URL to ``docs/explorer/README.md`` on GitHub for the current ref."""
    base = repo_root_url.rstrip("/")
    ref = github_blob_ref_for_readme()
    safe_ref = quote(ref, safe="")
    return f"{base}/blob/{safe_ref}/docs/explorer/README.md"
