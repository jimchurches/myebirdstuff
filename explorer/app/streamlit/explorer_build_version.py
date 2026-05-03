"""Committed Explorer build id (must match the GitHub release tag). Refs #189."""

from __future__ import annotations

from pathlib import Path

_STREAMLIT_DIR = Path(__file__).resolve().parent
_VERSION_FILE = _STREAMLIT_DIR / "explorer_build_version.txt"


def read_explorer_build_version_file() -> str:
    """Return trimmed contents of ``explorer_build_version.txt`` (single line)."""
    raw = _VERSION_FILE.read_text(encoding="utf-8")
    return raw.strip()


EXPLORER_BUILD_VERSION = read_explorer_build_version_file()
