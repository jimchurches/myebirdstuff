"""Pytest bootstrap: repo root on ``sys.path``.

Do **not** add ``tests/explorer/__init__.py``: with pytest's path handling that directory can be
imported as top-level ``explorer`` and shadow :mod:`explorer` at the repo root (refs #70).
"""

import os
import sys


def _add_repo_root_to_path():
    """Ensure the repo root is on sys.path for imports."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    # tests/ → repo root
    repo_root = os.path.dirname(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_add_repo_root_to_path()
