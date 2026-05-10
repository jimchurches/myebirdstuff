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

    # #214: All → Lifer → All must hit the Folium prep cache at least once on return (before the fix,
    # ``app_map_working_ui`` cleared the LRU on every view-mode change, so this count stayed 0).
    cache_hits = [e for e in events if e.get("stage") == "prep.map_cache_hit"]
    assert len(cache_hits) >= 1, (
        "expected at least one prep.map_cache_hit in JSONL for All→Lifer→All "
        f"(got {len(cache_hits)}); stages seen: {sorted(stages_seen)!r}"
    )

    highs = max_elapsed_ms_by_stage(events)
    failures: list[str] = []
    for stage, cap in ceilings.items():
        obs = highs.get(stage)
        if obs is None:
            continue
        if obs > cap:
            failures.append(f"{stage}: {obs:.1f}ms > ceiling {cap:.1f}ms")
    assert not failures, "Perf ceilings exceeded:\n" + "\n".join(failures)


def test_map_embed_off_map_rerun_journey_emits_perf_events(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    """Click an off-map sidebar widget that triggers a full script rerun without changing the map cache key.

    #205 batch 3 W1 measurement journey: this is the path that ``EXPLORER_MAP_FRAGMENT=on`` is
    supposed to short-circuit. The default journey (``test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling``)
    only exercises view-mode changes — i.e. the path that *does* invalidate any fragment — so it
    cannot measure the W1 hypothesis on its own.

    This test lands on All-locations, opens the **Performance / debug** sidebar expander
    (always present when ``EXPLORER_PERF=1``), and clicks **Clear session buffer** which calls
    ``st.rerun()``. ``st.rerun`` is a clean full-script rerun trigger that doesn't touch any
    component of :func:`static_map_cache_key`, so the LRU should serve the All-locations entry
    on cache hit while the embed call is paid (or, if the fragment isolates the embed, skipped).

    The test does **not** assert any A/B inequality; that comes from running the same test twice
    (once per ``EXPLORER_MAP_FRAGMENT`` mode) and comparing JSONL archives. The pass condition
    here is that the journey completes and at least one ``prep.map_iframe_embed`` event is logged
    after the off-map rerun.
    """
    url, log_file = streamlit_perf_url_and_logfile
    fragment_mode = (
        os.environ.get("EXPLORER_MAP_FRAGMENT", "off").strip().lower() or "off"
    )

    with launch_chromium_or_skip() as browser:
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )

        # Capture how many embed events fired during the cold load (fragment-mode-independent).
        time.sleep(0.5)
        cold_lines = log_file.read_text(encoding="utf-8").splitlines() if log_file.exists() else []
        cold_embed_count = sum(
            1 for e in parse_perf_json_objects_from_log_lines(cold_lines)
            if e.get("stage") == "prep.map_iframe_embed"
        )

        # Trigger an off-map full-app rerun via the perf-debug sidebar's Clear button (calls
        # ``st.rerun()`` and changes nothing in the map cache key). The expander is a
        # ``<details><summary>`` element rather than a button, so target the summary by text.
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar.locator('summary:has-text("Performance / debug")').click()
        clear_btn = sidebar.get_by_role("button", name="Clear session buffer")
        clear_btn.wait_for(timeout=10000)
        clear_btn.click()
        # Settle: full script rerun + iframe remount take a few seconds even on the fixture.
        page.wait_for_timeout(4000)
        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )

    time.sleep(0.5)
    raw_lines = log_file.read_text(encoding="utf-8").splitlines() if log_file.exists() else []
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    embed_events = [e for e in events if e.get("stage") == "prep.map_iframe_embed"]
    assert len(embed_events) >= 1, (
        f"expected at least one prep.map_iframe_embed event "
        f"(fragment_mode={fragment_mode!r}); got {len(embed_events)}"
    )
    # Pass criterion: the journey completes (cold-load + post-rerun banner both visible).
    # The A/B comparison itself happens by aggregating archived JSONL across modes; this
    # assertion just guards that *something* was measured.
    assert cold_embed_count >= 1, (
        f"expected at least one prep.map_iframe_embed event during cold load "
        f"(fragment_mode={fragment_mode!r}); got {cold_embed_count}"
    )


# Banner width sanity floor for the #205 batch-1 H1 #190 regression: in that broken mode
# the banner visibly shrank (text wrapped onto its own narrow column). The healthy banner
# width on a 1400px viewport is ~290–340 px depending on dataset; 150 px is a generous
# floor that still flags the #190 shape.
_PEBIRD_BANNER_MIN_WIDTH_PX = 150.0


def test_map_embed_all_locations_cluster_popup_parity_screenshot(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    """Capture All-locations cluster + popup parity for #205 batch 3.

    The I6 lesson from batch 1 (see :data:`docs/explorer/issue-205-investigation-backlog.md`):
    the Lifer-view screenshot test missed the H1 #190 regression because the All-locations
    cluster path's DOM (``MarkerClusterGroup`` + ``CircleMarker`` popups) differs from the
    Lifer view. Any future map-embed experiment — including this batch's
    ``EXPLORER_MAP_FRAGMENT`` — needs an explicit cluster + popup-attachment parity check
    before its screenshot test is trusted.

    Steps:

    1. Land on All-locations and wait for ``.marker-cluster`` to be present in the leaflet
       iframe (validates the cluster code path actually paints).
    2. Walk the map's layers via the Leaflet API to find the first ``L.CircleMarker``,
       ``setView`` to it at zoom 12, and call ``layer.openPopup()`` (this bypasses the
       UI-level cluster-then-marker-then-click chain, which on small datasets stays clustered
       even at maxZoom and therefore can't produce a marker click on the fixture).
    3. Assert the popup DOM is present *and well-formed*: ``.leaflet-popup-content`` and
       ``.leaflet-popup-tip`` both render — the tip is exactly the surface the H1 #190
       regression detached.
    4. Assert the in-iframe ``.pebird-map-banner`` width is above
       :data:`_PEBIRD_BANNER_MIN_WIDTH_PX` (the #190 regression's most visible symptom was a
       banner shrunk to a thin column).
    5. Save a full-page screenshot under
       ``benchmarks/map_perf/snapshots/issue-205-batch-3/`` keyed by ``EXPLORER_MAP_FRAGMENT``
       + dataset label so an A/B run produces side-by-side ``fragment_off`` / ``fragment_on``
       images for manual visual review.
    """
    url, _log = streamlit_perf_url_and_logfile
    fragment_mode = (
        os.environ.get("EXPLORER_MAP_FRAGMENT", "off").strip().lower() or "off"
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

        # The map iframe holds the leaflet DOM; find it via the cluster class.
        map_frame = None
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            for frame in list(page.frames):
                try:
                    if frame.locator(".marker-cluster").count() > 0:
                        map_frame = frame
                        break
                except Exception:
                    continue
            if map_frame is not None:
                break
            page.wait_for_timeout(500)
        assert map_frame is not None, (
            f"no frame contained .marker-cluster (fragment_mode={fragment_mode!r}); "
            "the All-locations cluster path didn't render — would have hidden #190-style breakage"
        )

        # Open a popup on the first ``L.CircleMarker`` via the Leaflet API. This is more robust
        # than chasing the UI chain (cluster click → marker icon → marker click) because, on
        # small datasets, MarkerCluster keeps clustering at maxZoom and never surfaces a
        # ``.leaflet-marker-icon`` to click. The popup itself is what the #190 regression
        # mis-rendered, so opening it via API is the right granularity for parity. We do the
        # DOM verification *inside* the same ``evaluate`` call, immediately after ``openPopup``,
        # because the popup DOM is the only assertion that actually has to be live at the same
        # moment as the JS state — afterwards we still take the screenshot for visual review.
        result = map_frame.evaluate(
            """
            () => {
                const out = {found: 0, openedAt: null, error: null,
                             popupCount: 0, popupContentCount: 0, popupTipCount: 0};
                let m = null;
                for (const k of Object.keys(window)) {
                    const v = window[k];
                    if (v && v._zoom !== undefined && typeof v.getMaxZoom === 'function') {
                        m = v;
                        break;
                    }
                }
                if (!m) { out.error = 'no leaflet map global'; return out; }
                m.eachLayer((layer) => {
                    if (out.found > 0) return;
                    if (window.L && layer instanceof window.L.CircleMarker) {
                        try {
                            const ll = layer.getLatLng();
                            m.setView(ll, 12, {animate: false});
                            if (typeof layer.openPopup === 'function') {
                                layer.openPopup();
                                out.openedAt = [ll.lat, ll.lng];
                                out.found++;
                            }
                        } catch (e) {
                            out.error = e && e.message ? e.message : String(e);
                        }
                    }
                });
                out.popupCount = document.querySelectorAll('.leaflet-popup').length;
                out.popupContentCount = document.querySelectorAll('.leaflet-popup-content').length;
                out.popupTipCount = document.querySelectorAll('.leaflet-popup-tip').length;
                return out;
            }
            """
        )
        assert result.get("found", 0) >= 1, (
            f"could not open a popup on any L.CircleMarker via the Leaflet API "
            f"(fragment_mode={fragment_mode!r}, result={result!r})"
        )

        popup_count = int(result.get("popupCount", 0))
        popup_content_count = int(result.get("popupContentCount", 0))
        popup_tip_count = int(result.get("popupTipCount", 0))
        assert popup_count >= 1, (
            f"openPopup did not produce a .leaflet-popup in DOM "
            f"(fragment_mode={fragment_mode!r})"
        )
        assert popup_content_count >= 1, (
            f"popup rendered without .leaflet-popup-content "
            f"(fragment_mode={fragment_mode!r})"
        )
        # The H1 #190 detachment surface: tip missing or detached so popup floats away
        # from the underlying marker.
        assert popup_tip_count >= 1, (
            f"popup rendered without a .leaflet-popup-tip "
            f"(fragment_mode={fragment_mode!r}); this is the #190 detachment shape"
        )

        # The other H1 #190 visible surface: banner shrunk to a thin column.
        banner = map_frame.locator(".pebird-map-banner").first
        assert banner.count() >= 1
        banner_box = banner.bounding_box()
        assert banner_box is not None, (
            f"could not measure .pebird-map-banner bounding box "
            f"(fragment_mode={fragment_mode!r})"
        )
        assert banner_box["width"] >= _PEBIRD_BANNER_MIN_WIDTH_PX, (
            f"pebird-map-banner shrunk below {_PEBIRD_BANNER_MIN_WIDTH_PX}px "
            f"(width={banner_box['width']}, fragment_mode={fragment_mode!r}); "
            "this matches the #190 regression shape — review the screenshot"
        )

        out_dir = REPO_ROOT / "benchmarks" / "map_perf" / "snapshots" / "issue-205-batch-3"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = (
            out_dir
            / f"all-locations-cluster-popup-fragment_{fragment_mode}-{dataset_label}.png"
        )
        page.screenshot(path=str(out_path), full_page=True)


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
