"""Tests for scripts/build_all_locations_map_frontend.py sanity checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts/build_all_locations_map_frontend.py"
_BUILD = _REPO / "explorer/components/all_locations_map/frontend/build"
sys.path.insert(0, str(_REPO / "scripts"))

import build_all_locations_map_frontend as mod  # noqa: E402


def test_check_only_passes_on_current_build():
    assert (_BUILD / "asset-manifest.json").is_file(), (
        "committed frontend build is required"
    )
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--check-only"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_manifest_paths_include_assets_but_exclude_source_maps(tmp_path: Path) -> None:
    build = tmp_path / "build"
    (build / "static" / "js").mkdir(parents=True)
    (build / "static" / "js" / "main.abc.js").write_text("", encoding="utf-8")
    (build / "asset-manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "main.js": "./static/js/main.abc.js",
                    "main.js.map": "./static/js/main.abc.js.map",
                },
                "entrypoints": ["static/js/main.abc.js"],
            }
        ),
        encoding="utf-8",
    )

    assert mod._manifest_paths(build) == {
        Path("asset-manifest.json"),
        Path("index.html"),
        Path("static/js/main.abc.js"),
    }


def test_detects_only_macos_junk_dirs(tmp_path: Path) -> None:
    build = tmp_path / "build"
    (build / "static" / "css 4").mkdir(parents=True)
    (build / "static" / "css").mkdir()
    (build / "static" / "images 4").mkdir()

    assert mod._find_junk_dirs(build) == [build / "static" / "css 4"]


def test_unexpected_files_ignores_source_maps(tmp_path: Path) -> None:
    build = tmp_path / "build"
    (build / "static" / "js").mkdir(parents=True)
    expected_file = build / "static" / "js" / "main.js"
    expected_file.write_text("", encoding="utf-8")
    (build / "static" / "js" / "main.js.map").write_text("", encoding="utf-8")
    orphan = build / "static" / "js" / "old.js"
    orphan.write_text("", encoding="utf-8")

    assert mod._find_unexpected_files(build, {Path("static/js/main.js")}) == [
        Path("static/js/old.js")
    ]
