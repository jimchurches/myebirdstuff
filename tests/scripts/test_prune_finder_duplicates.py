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
    dupes = mod.find_finder_duplicates(tmp_path)
    assert len(dupes) == 1
    assert dupes[0].name == "real 2.py"


def test_prune_removes_duplicates(tmp_path: Path) -> None:
    junk = tmp_path / "notes 2.md"
    junk.write_text("dup", encoding="utf-8")
    removed = mod.prune_finder_duplicates(tmp_path)
    assert len(removed) == 1
    assert not junk.exists()


def test_build_static_junk_dir(tmp_path: Path) -> None:
    static = tmp_path / "build" / "static"
    (static / "css").mkdir(parents=True)
    (static / "css 4").mkdir(parents=True)
    dupes = mod.find_finder_duplicates(tmp_path)
    assert any(p.name == "css 4" for p in dupes)
