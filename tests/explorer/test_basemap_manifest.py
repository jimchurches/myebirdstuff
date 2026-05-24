"""Tests for the shared basemap manifest (``explorer/data/basemaps.yaml``)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_basemap_manifest_options_labels_and_tiles():
    from explorer.core.basemap_manifest import (
        MAP_BASEMAP_DEFAULT,
        MAP_BASEMAP_LABELS,
        MAP_BASEMAP_OPTIONS,
        basemap_tile_layers_for_component,
        basemap_tile_layers_for_export,
        get_basemap_entries,
    )

    entries = get_basemap_entries()
    assert len(entries) >= 5
    assert MAP_BASEMAP_OPTIONS == tuple(e.key for e in entries)
    assert MAP_BASEMAP_DEFAULT in MAP_BASEMAP_OPTIONS
    assert list(MAP_BASEMAP_LABELS) == list(MAP_BASEMAP_OPTIONS)

    component = basemap_tile_layers_for_component()
    export = basemap_tile_layers_for_export()
    for key in MAP_BASEMAP_OPTIONS:
        assert key in component
        assert key in export
        assert component[key]["url"] == export[key]["url"]
        assert component[key]["opts"]["maxZoom"] == export[key]["opts"]["maxZoom"]


def test_generated_basemap_ts_is_fresh():
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts/generate_basemap_assets.py"), "--check"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
