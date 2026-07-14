"""Tests for scripts/prune_finder_duplicates.py."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "scripts"))
import prune_finder_duplicates as mod  # noqa: E402


def test_find_finder_file_duplicate(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("x", encoding="utf-8")
    (tmp_path / "real 2.py").write_text("y", encoding="utf-8")
    (tmp_path / "chapter 2").write_text(
        "not a Finder-style file copy", encoding="utf-8"
    )
    dupes = mod.find_finder_duplicates(tmp_path)
    assert dupes == [tmp_path / "real 2.py"]


def test_prune_removes_duplicates(tmp_path: Path) -> None:
    junk = tmp_path / "notes 2.md"
    junk.write_text("dup", encoding="utf-8")
    retained = tmp_path / "notes.md"
    retained.write_text("original", encoding="utf-8")
    removed = mod.prune_finder_duplicates(tmp_path)
    assert removed == [junk]
    assert not junk.exists()
    assert retained.read_text(encoding="utf-8") == "original"


def test_build_static_junk_dir(tmp_path: Path) -> None:
    static = tmp_path / "build" / "static"
    (static / "css").mkdir(parents=True)
    (static / "css 4").mkdir(parents=True)
    dupes = mod.find_finder_duplicates(tmp_path)
    assert dupes == [static / "css 4"]


def test_dependency_and_cache_trees_are_not_scanned(tmp_path: Path) -> None:
    for skipped_name in ("node_modules", ".venv", ".venv-audit", "__pycache__"):
        skipped = tmp_path / skipped_name
        skipped.mkdir()
        (skipped / "module 2.py").write_text("ignored", encoding="utf-8")

    assert mod.find_finder_duplicates(tmp_path) == []


def test_prune_removes_duplicate_directory_tree(tmp_path: Path) -> None:
    duplicate_dir = tmp_path / "assets 2"
    duplicate_dir.mkdir()
    (duplicate_dir / "nested.txt").write_text("duplicate", encoding="utf-8")

    assert mod.prune_finder_duplicates(tmp_path) == [duplicate_dir]
    assert not duplicate_dir.exists()
