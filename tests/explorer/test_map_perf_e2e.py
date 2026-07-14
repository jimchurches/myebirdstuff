"""Opt-in map performance E2E: JSONL via ``EXPLORER_PERF_LOG_FILE`` + scripted journeys.

Run::

    python -m pip install playwright
    python -m playwright install chromium
    pytest tests/explorer/test_map_perf_e2e.py --perf -v

Events are captured via ``EXPLORER_PERF_LOG_FILE`` (JSONL); guardrails read
``benchmarks/map_perf/stage_ceilings.json`` (very loose ceilings).

Headline journey (``test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling``):
cold **All locations** → **Lifer** → warm **All** → cold **Species** (Grey Teal) → **Lifer** → warm **Species**
→ cold **Family** → warm **Family**.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("playwright.sync_api")

from tests.explorer.e2e_support import (
    E2E_FIXTURE_SPECIES_COMMON,
    REPO_ROOT,
    append_e2e_first_paint_record,
    choose_family_by_label,
    choose_first_recorded_family,
    choose_map_view_mode,
    choose_species_by_common_name,
    launch_chromium_or_skip,
    map_banner_must_contain,
    max_elapsed_ms_by_stage,
    measure_first_paint_ms,
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


def _assert_payload_stage_with_cold_miss(
    events: list[dict],
    stage: str,
    *,
    require_marker_count: bool = False,
) -> None:
    stage_events = [e for e in events if e.get("stage") == stage]
    assert stage_events, f"expected perf stage {stage!r} in JSONL"
    misses = [
        e
        for e in stage_events
        if isinstance(e.get("extra"), dict) and not e["extra"].get("payload_cache_hit")
    ]
    assert misses, f"expected at least one cold {stage} payload build"
    if require_marker_count:
        assert any(
            isinstance(e["extra"].get("marker_count"), int) and e["extra"]["marker_count"] >= 0
            for e in misses
        ), f"{stage} miss should include marker_count in extra"


def _assert_at_least_one_payload_cache_hit(events: list[dict], stage: str) -> None:
    hits = [
        e
        for e in events
        if e.get("stage") == stage
        and isinstance(e.get("extra"), dict)
        and e["extra"].get("payload_cache_hit")
    ]
    assert hits, f"expected warm {stage} with payload_cache_hit=true"


def _assert_ceilings(events: list[dict], ceilings: dict[str, float]) -> None:
    highs = max_elapsed_ms_by_stage(events)
    failures: list[str] = []
    for stage, cap in ceilings.items():
        obs = highs.get(stage)
        if obs is None:
            continue
        if obs > cap:
            failures.append(f"{stage}: {obs:.1f}ms > ceiling {cap:.1f}ms")
    assert not failures, "Perf ceilings exceeded:\n" + "\n".join(failures)


def _run_headline_real_export_journey(page: Any) -> None:
    """Headline journey on large exports: All (cold, in first_paint) → Lifer → warm All."""
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


def _run_headline_four_map_mode_journey(page: Any) -> None:
    """Playwright steps after cold All first paint (four-map headline journey)."""
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

    choose_species_by_common_name(page, E2E_FIXTURE_SPECIES_COMMON)

    # Warm species LRU: leave Species and return with the same pick (avoid All prep between visits).
    choose_map_view_mode(page, "Lifer locations")
    wait_for_pebird_map_markup(
        page,
        must_contain=['class="pebird-map-banner__title">Lifer locations</span>'],
    )
    choose_species_by_common_name(page, E2E_FIXTURE_SPECIES_COMMON)

    family_label = choose_first_recorded_family(page)
    wait_for_pebird_map_markup(
        page,
        must_contain=map_banner_must_contain(family_label),
    )

    choose_map_view_mode(page, "Lifer locations")
    wait_for_pebird_map_markup(
        page,
        must_contain=['class="pebird-map-banner__title">Lifer locations</span>'],
    )

    choose_family_by_label(page, family_label)
    wait_for_pebird_map_markup(
        page,
        must_contain=map_banner_must_contain(family_label),
    )


def test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    url, log_file = streamlit_perf_url_and_logfile
    ceilings = _load_stage_ceilings()
    is_real_export = bool(os.environ.get("EXPLORER_E2E_DATASET_CSV"))
    dataset_label = "real" if is_real_export else "fixture"
    journey_name = "real_export_headline" if is_real_export else "fixture_four_map_modes"

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
                "journey": journey_name,
            },
        )
        if is_real_export:
            _run_headline_real_export_journey(page)
        else:
            _run_headline_four_map_mode_journey(page)

    time.sleep(0.5)
    raw_lines = []
    if log_file.exists():
        raw_lines = log_file.read_text(encoding="utf-8").splitlines()
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    assert len(events) >= 5, f"expected perf JSON events in Streamlit logs, got {len(events)}"

    stages_seen = {str(e.get("stage")) for e in events if isinstance(e.get("stage"), str)}
    must = {
        "prep.map_context_prepare",
        "map.all_locations_leaflet.component_embed",
        "map.lifer_leaflet.payload",
    }
    if not is_real_export:
        must |= {
            "map.species_leaflet.payload",
            "map.family_leaflet.payload",
        }
    missing = must - stages_seen
    assert not missing, f"missing expected stages {missing!r} in {sorted(stages_seen)!r}"

    _assert_payload_stage_with_cold_miss(events, "map.all_locations_leaflet.payload")
    _assert_payload_stage_with_cold_miss(events, "map.lifer_leaflet.payload")
    if not is_real_export:
        _assert_payload_stage_with_cold_miss(
            events, "map.species_leaflet.payload", require_marker_count=True
        )
        _assert_payload_stage_with_cold_miss(events, "map.family_leaflet.payload")

    _assert_at_least_one_payload_cache_hit(events, "map.all_locations_leaflet.payload")
    if not is_real_export:
        _assert_at_least_one_payload_cache_hit(events, "map.species_leaflet.payload")
        _assert_at_least_one_payload_cache_hit(events, "map.family_leaflet.payload")

    payload_misses = [
        e
        for e in events
        if e.get("stage") == "map.all_locations_leaflet.payload"
        and isinstance(e.get("extra"), dict)
        and not e["extra"].get("payload_cache_hit")
    ]
    assert any(
        isinstance(e["extra"].get("marker_count"), int) and e["extra"]["marker_count"] >= 0
        for e in payload_misses
    ), "all-locations cold payload should include marker_count in extra"

    _assert_ceilings(events, ceilings)
