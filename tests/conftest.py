"""Pytest bootstrap: repo root on ``sys.path``.

Do **not** add ``tests/explorer/__init__.py``: with pytest's path handling that directory can be
imported as top-level ``explorer`` and shadow :mod:`explorer` at the repo root (refs #70).

Opt-in map perf tests: ``pytest tests/explorer/test_map_perf_e2e.py --perf``.
"""

from __future__ import annotations

import os
import sys

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--perf",
        action="store_true",
        default=False,
        help="Run Explorer map perf + Playwright journeys (captures Streamlit stderr JSON lines).",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``@pytest.mark.perf`` tests unless explicitly requested with ``--perf``."""
    if config.getoption("--perf"):
        return
    skip_perf = pytest.mark.skip(
        reason="Map perf E2E is opt-in ('pytest … --perf'); excludes Playwright+Streamlit+jsonl flake from default runs.",
    )
    for item in items:
        if "perf" in item.keywords:
            item.add_marker(skip_perf)


def _add_repo_root_to_path():
    """Ensure the repo root is on sys.path for imports."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    # tests/ → repo root
    repo_root = os.path.dirname(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_add_repo_root_to_path()
