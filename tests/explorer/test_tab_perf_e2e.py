"""Opt-in tab/table prep performance E2E (JSONL via ``EXPLORER_PERF_LOG_FILE``).

Run::

    pytest tests/explorer/test_tab_perf_e2e.py --perf -v

Complements ``test_map_perf_e2e.py``: asserts tab-prep ``prep.cache_*`` stages after cold load.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.explorer.e2e_support import (
    append_e2e_first_paint_record,
    launch_chromium_or_skip,
    max_elapsed_ms_by_stage,
    measure_first_paint_ms,
    parse_perf_json_objects_from_log_lines,
)

pytestmark = [pytest.mark.e2e, pytest.mark.perf]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CEILINGS_PATH = _REPO_ROOT / "benchmarks" / "map_perf" / "stage_ceilings.json"


def _load_stage_ceilings() -> dict[str, float]:
    raw = json.loads(_CEILINGS_PATH.read_text(encoding="utf-8"))
    caps = raw.get("max_elapsed_ms")
    if not isinstance(caps, dict):
        raise AssertionError(f"Invalid ceilings file: {_CEILINGS_PATH}")
    return {str(k): float(v) for k, v in caps.items()}


def test_tab_prep_stages_emitted_after_cold_load(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    """Cold load logs map + tab prep stages; checklist nested tab ``Overview`` becomes visible."""
    url, log_file = streamlit_perf_url_and_logfile
    ceilings = _load_stage_ceilings()
    dataset_label = "real" if os.environ.get("EXPLORER_E2E_DATASET_CSV") else "fixture"

    with launch_chromium_or_skip() as browser:
        page = browser.new_page()
        first_paint = measure_first_paint_ms(
            page,
            url,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)
        append_e2e_first_paint_record(
            log_file,
            {
                "elapsed_ms": first_paint["banner_ms"],
                "goto_ms": first_paint["goto_ms"],
                "banner_ms": first_paint["banner_ms"],
                "dataset_label": dataset_label,
                "journey": "tab_prep_cold_load",
            },
        )
        page.get_by_role("tab", name="Checklist Statistics").wait_for(timeout=120_000)
        page.get_by_role("tab", name="Overview").wait_for(timeout=120_000)

    time.sleep(0.5)
    raw_lines = log_file.read_text(encoding="utf-8").splitlines() if log_file.exists() else []
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    assert len(events) >= 3, f"expected perf JSON events, got {len(events)}"

    stages_seen = {str(e.get("stage")) for e in events if isinstance(e.get("stage"), str)}
    must = {
        "prep.cache_checklist_stats.working",
        "prep.cache_checklist_stats.full_export",
        "prep.cache_rankings_bundle",
        "prep.tab_session_sync",
    }
    missing = must - stages_seen
    assert not missing, f"missing tab prep stages {missing!r} in {sorted(stages_seen)!r}"

    highs = max_elapsed_ms_by_stage(events)
    failures: list[str] = []
    for stage, cap in ceilings.items():
        obs = highs.get(stage)
        if obs is None:
            continue
        if obs > cap:
            failures.append(f"{stage}: {obs:.1f}ms > ceiling {cap:.1f}ms")
    assert not failures, "Perf ceilings exceeded:\n" + "\n".join(failures)
