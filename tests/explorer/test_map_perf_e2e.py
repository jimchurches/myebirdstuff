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
import os
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


def test_map_embed_lifer_view_visual_parity_screenshot(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    """Capture full-page screenshots of the Lifer view for visual parity across embed modes.

    Guards the #190 regression surface for the #205 ``EXPLORER_MAP_EMBED=components_html``
    experiment: in that mode the live iframe is embedded via ``streamlit.components.v1.html``
    rather than ``streamlit-folium``. The original #190 symptoms (banner/legend shrunk,
    popups detached from markers) were caught visually rather than programmatically; this
    test makes that visual check repeatable and side-by-side comparable.

    Reads the active embed mode from the same ``EXPLORER_MAP_EMBED`` env var that
    ``app_prep_map_ui`` honours and saves a screenshot under
    ``benchmarks/map_perf/snapshots/issue-205-batch-1/`` named by mode + dataset label so
    the same test can be run twice (once per mode) and the outputs compared by eye.
    """
    url, _log = streamlit_perf_url_and_logfile
    embed_mode = (
        os.environ.get("EXPLORER_MAP_EMBED", "st_folium").strip().lower() or "st_folium"
    )
    dataset_label = "real" if os.environ.get("EXPLORER_E2E_DATASET_CSV") else "fixture"

    with launch_chromium_or_skip() as browser:
        page = browser.new_page(viewport={"width": 1400, "height": 900})
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

        # Confirm the Lifer overlay actually painted SVG markers in some frame; if not, the
        # embed mode is broken in a way no visual diff would forgive.
        map_frame = None
        for frame in list(page.frames):
            try:
                if frame.locator(".leaflet-interactive").count() > 0:
                    map_frame = frame
                    break
            except Exception:
                continue
        assert map_frame is not None, (
            f"no frame contained .leaflet-interactive markers (embed_mode={embed_mode!r})"
        )

        # Brief settle so any fit-bounds animation finishes before the screenshot.
        page.wait_for_timeout(1500)

        out_dir = REPO_ROOT / "benchmarks" / "map_perf" / "snapshots" / "issue-205-batch-1"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"lifer-{embed_mode}-{dataset_label}.png"
        page.screenshot(path=str(out_path), full_page=True)
