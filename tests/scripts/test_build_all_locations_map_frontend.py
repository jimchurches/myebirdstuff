"""Tests for scripts/build_all_locations_map_frontend.py sanity checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts/build_all_locations_map_frontend.py"
_BUILD = _REPO / "explorer/components/all_locations_map/frontend/build"


def test_check_only_passes_on_current_build():
    if not (_BUILD / "asset-manifest.json").is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--check-only"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_detects_macos_junk_dir(tmp_path):
    build = tmp_path / "build"
    (build / "static" / "css 4").mkdir(parents=True)
    (build / "index.html").write_text("<html></html>", encoding="utf-8")
    (build / "asset-manifest.json").write_text(
        json.dumps({"files": {}, "entrypoints": []}),
        encoding="utf-8",
    )
    # Import helpers without running npm
    sys.path.insert(0, str(_REPO / "scripts"))
    import build_all_locations_map_frontend as mod  # noqa: E402

    junk = mod._find_junk_dirs(build)
    assert any(p.name == "css 4" for p in junk)
