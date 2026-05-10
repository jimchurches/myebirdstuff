"""Tests for :mod:`scripts.aggregate_perf_jsonl` (#205 batch 4 I5)."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = REPO_ROOT / "scripts" / "aggregate_perf_jsonl.py"


def _load_module() -> Any:
    """Import ``scripts/aggregate_perf_jsonl.py`` as a module (path isn't on PYTHONPATH)."""
    spec = importlib.util.spec_from_file_location("aggregate_perf_jsonl", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["aggregate_perf_jsonl"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )


def test_parse_jsonl_skips_malformed_and_non_object_lines(tmp_path: Path) -> None:
    """``parse_jsonl`` must tolerate stray log preludes / blank lines without raising."""
    mod = _load_module()
    f = tmp_path / "noisy.jsonl"
    f.write_text(
        "INFO some prelude\n"
        '{"stage": "prep.x", "elapsed_ms": 1.5}\n'
        "\n"
        "not a json line\n"
        '{"stage": "prep.y", "elapsed_ms": 2.0}\n',
        encoding="utf-8",
    )
    out = mod.parse_jsonl(f)
    assert [e["stage"] for e in out] == ["prep.x", "prep.y"]


def test_percentile_handles_singletons_and_uses_nearest_rank() -> None:
    """``percentile`` is the nearest-rank style used by the original /tmp aggregator."""
    mod = _load_module()
    assert mod.percentile([], 50.0) != mod.percentile([], 50.0)  # NaN
    assert mod.percentile([42.0], 50.0) == 42.0
    assert mod.percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50.0) == 3.0
    assert mod.percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95.0) == 5.0


def test_group_label_uses_named_captures() -> None:
    mod = _load_module()
    rx = re.compile(r"baseline-(?P<dataset>[^-]+)-r(?P<run>\d+)")
    assert (
        mod.group_label_for_filename("baseline-fixture-r2.jsonl", rx)
        == "dataset=fixture/run=2"
    )
    # No match -> filename itself is the group label.
    assert (
        mod.group_label_for_filename("unmatched-name.jsonl", rx) == "unmatched-name.jsonl"
    )
    # No regex -> filename itself.
    assert mod.group_label_for_filename("a.jsonl", None) == "a.jsonl"


def test_aggregate_counts_events_and_summarises_elapsed_ms(tmp_path: Path) -> None:
    mod = _load_module()
    f1 = tmp_path / "baseline-fixture-r1.jsonl"
    f2 = tmp_path / "baseline-fixture-r2.jsonl"
    _write_jsonl(
        f1,
        [
            {"stage": "prep.build_species_overlay_map", "elapsed_ms": 100.0},
            {"stage": "prep.build_species_overlay_map", "elapsed_ms": 110.0},
        ],
    )
    _write_jsonl(
        f2,
        [
            {"stage": "prep.build_species_overlay_map", "elapsed_ms": 200.0},
        ],
    )
    rx = re.compile(r"baseline-(?P<dataset>[^-]+)-r(?P<run>\d+)")
    result = mod.aggregate(
        [f1, f2],
        group_regex=rx,
        stages={"prep.build_species_overlay_map"},
        extra_keys=[],
    )
    # Different runs -> different group labels (run-keyed).
    assert set(result["groups"].keys()) == {
        "dataset=fixture/run=1",
        "dataset=fixture/run=2",
    }
    g1 = result["groups"]["dataset=fixture/run=1"]["stages"][
        "prep.build_species_overlay_map"
    ]
    assert g1["n_runs"] == 1
    assert g1["total_events"] == 2
    assert g1["events_per_run"] == [2]
    # Nearest-rank median on even-sample input picks the lower middle (same convention as
    # the original /tmp/aggregate_w1_ab.py; ``round(0.5)`` is banker's-rounded to ``0``).
    assert g1["elapsed_ms"]["median"] == 100.0
    assert g1["elapsed_ms"]["max"] == 110.0
    assert g1["elapsed_ms"]["n_samples"] == 2


def test_aggregate_groups_collapsing_when_regex_only_captures_dataset(tmp_path: Path) -> None:
    """Files differing only in run-number collapse into one group when the regex omits run capture."""
    mod = _load_module()
    f1 = tmp_path / "baseline-fixture-r1.jsonl"
    f2 = tmp_path / "baseline-fixture-r2.jsonl"
    f3 = tmp_path / "baseline-real-r1.jsonl"
    _write_jsonl(f1, [{"stage": "s.a", "elapsed_ms": 10.0}])
    _write_jsonl(f2, [{"stage": "s.a", "elapsed_ms": 20.0}])
    _write_jsonl(f3, [{"stage": "s.a", "elapsed_ms": 1000.0}])
    rx = re.compile(r"baseline-(?P<dataset>[^-]+)-r")
    result = mod.aggregate(
        [f1, f2, f3], group_regex=rx, stages=None, extra_keys=[]
    )
    assert set(result["groups"].keys()) == {"dataset=fixture", "dataset=real"}
    fixture = result["groups"]["dataset=fixture"]["stages"]["s.a"]
    assert fixture["n_runs"] == 2
    assert fixture["events_per_run"] == [1, 1]
    # Nearest-rank median on ``[10, 20]`` -> lower middle = 10.
    assert fixture["elapsed_ms"]["median"] == 10.0


def test_aggregate_pulls_extra_keys_from_nested_extra_and_top_level(tmp_path: Path) -> None:
    """``extra_keys`` must look at both ``event.extra.<k>`` and top-level ``event.<k>``.

    Top-level fallback is required for the E2E ``e2e.first_paint`` records since they store
    fields like ``banner_ms`` at the top level rather than nested under ``extra``.
    """
    mod = _load_module()
    f = tmp_path / "metrics.jsonl"
    _write_jsonl(
        f,
        [
            {
                "stage": "prep.build_species_overlay_map",
                "elapsed_ms": 100.0,
                "extra": {"marker_count": 50, "popup_build_count": 10},
            },
            {
                "stage": "e2e.first_paint",
                "elapsed_ms": 5000.0,
                "banner_ms": 5000.0,
                "goto_ms": 800.0,
            },
        ],
    )
    result = mod.aggregate(
        [f],
        group_regex=None,
        stages=None,
        extra_keys=["marker_count", "banner_ms"],
    )
    stages = result["groups"]["metrics.jsonl"]["stages"]
    assert stages["prep.build_species_overlay_map"]["extras"]["marker_count"]["max"] == 50
    assert stages["e2e.first_paint"]["extras"]["banner_ms"]["max"] == 5000.0


def test_render_text_includes_header_and_one_row_per_group_stage(tmp_path: Path) -> None:
    mod = _load_module()
    f = tmp_path / "a.jsonl"
    _write_jsonl(f, [{"stage": "x", "elapsed_ms": 1.0}, {"stage": "y", "elapsed_ms": 2.0}])
    result = mod.aggregate([f], group_regex=None, stages=None, extra_keys=[])
    text = mod.render_text(result, [])
    assert "group" in text
    assert "stage" in text
    assert "a.jsonl" in text
    # Two stages -> two data rows + header + separator = at least 3 newlines.
    assert text.count("\n") >= 4


def test_main_returns_nonzero_for_missing_dir(tmp_path: Path) -> None:
    mod = _load_module()
    rc = mod.main([str(tmp_path / "does_not_exist")])
    assert rc == 2
