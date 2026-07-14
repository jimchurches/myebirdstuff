"""Registry and CI helpers for Streamlit :mod:`explorer.app.streamlit.defaults` debug toggles."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import scripts.warn_streamlit_debug_defaults as warning_script


def test_debug_defaults_enabled_matches_map_debug_constant():
    from explorer.app.streamlit import defaults as d

    got = d.debug_defaults_enabled()
    assert isinstance(got, list)
    assert all(isinstance(x, str) for x in got)
    if d.MAP_DEBUG_SHOW_ZOOM_LEVEL:
        assert "MAP_DEBUG_SHOW_ZOOM_LEVEL" in got
    else:
        assert "MAP_DEBUG_SHOW_ZOOM_LEVEL" not in got


def test_warning_script_emits_one_github_annotation_per_enabled_toggle(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        warning_script,
        "debug_defaults_enabled",
        lambda: ["MAP_DEBUG_SHOW_ZOOM_LEVEL", "SECOND_DEBUG_TOGGLE"],
    )

    assert warning_script.main() is None
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "::warning::explorer/app/streamlit/defaults.py — MAP_DEBUG_SHOW_ZOOM_LEVEL=True "
        "(debug; set False for production)",
        "::warning::explorer/app/streamlit/defaults.py — SECOND_DEBUG_TOGGLE=True "
        "(debug; set False for production)",
    ]


def test_warn_streamlit_debug_defaults_script_exits_zero():
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "warn_streamlit_debug_defaults.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""
