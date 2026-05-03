"""Opt-in map performance E2E: JSONL via ``EXPLORER_PERF_LOG_FILE`` + scripted journeys.

Run::

    python -m pip install playwright
    python -m playwright install chromium
    pytest tests/explorer/test_map_perf_e2e.py --perf -v

Events are captured via ``EXPLORER_PERF_LOG_FILE`` (JSONL); guardrails read
``benchmarks/map_perf/stage_ceilings.json`` (very loose ceilings).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.explorer.e2e_support import (
    REPO_ROOT,
    choose_map_view_mode,
    launch_chromium_or_skip,
    max_elapsed_ms_by_stage,
    parse_perf_json_objects_from_log_lines,
    wait_for_pebird_map_markup,
)

pytestmark = [pytest.mark.e2e, pytest.mark.perf]

_CEILINGS_PATH = REPO_ROOT / "benchmarks" / "map_perf" / "stage_ceilings.json"


def _load_stage_ceilings() -> dict[str, float]:
    raw = json.loads(_CEILINGS_PATH.read_text(encoding="utf-8"))
    caps = raw.get("max_elapsed_ms")
    if not isinstance(caps, dict):
        raise AssertionError(f"Invalid ceilings file: {_CEILINGS_PATH}")
    out: dict[str, float] = {}
    for k, v in caps.items():
        out[str(k)] = float(v)
    return out


def test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    url, log_file = streamlit_perf_url_and_logfile
    ceilings = _load_stage_ceilings()

    with launch_chromium_or_skip() as browser:
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )
        choose_map_view_mode(page, "Lifer locations")
        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">Lifer locations</span>'],
        )
        choose_map_view_mode(page, "All locations")
        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )

    time.sleep(0.5)
    raw_lines = []
    if log_file.exists():
        raw_lines = log_file.read_text(encoding="utf-8").splitlines()
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    assert len(events) >= 3, f"expected perf JSON events in Streamlit logs, got {len(events)}"

    stages_seen = {str(e.get("stage")) for e in events if isinstance(e.get("stage"), str)}
    must = {"prep.map_iframe_embed", "prep.folium_map_to_html_bytes", "prep.map_context_prepare"}
    missing = must - stages_seen
    assert not missing, f"missing expected stages {missing!r} in {sorted(stages_seen)!r}"

    highs = max_elapsed_ms_by_stage(events)
    failures: list[str] = []
    for stage, cap in ceilings.items():
        obs = highs.get(stage)
        if obs is None:
            continue
        if obs > cap:
            failures.append(f"{stage}: {obs:.1f}ms > ceiling {cap:.1f}ms")
    assert not failures, "Perf ceilings exceeded:\n" + "\n".join(failures)
