"""Opt-in map performance E2E: JSONL via ``EXPLORER_PERF_LOG_FILE`` + scripted journeys.

Run::

    python -m pip install playwright
    python -m playwright install chromium
    pytest tests/explorer/test_map_perf_e2e.py --perf -v

**Lazy popups (Batch B) automated A/B:** the fixture ``streamlit_perf_url_logfile_and_lazy_expected``
runs each dependent test **twice** (``EXPLORER_MAP_LAZY_POPUPS=0`` then ``=1``; **lite always off**).
See ``test_map_perf_lazy_journey_tags_build_extra``. Compare archived JSONL with
``aggregate_perf_jsonl`` using ``--extra-key html_bytes_len`` on ``prep.folium_map_to_html_bytes``.

**Lite popups (W2) automated A/B:** the fixture ``streamlit_perf_url_logfile_and_lite_expected``
runs each dependent test **twice** (``EXPLORER_MAP_LITE_POPUPS=0`` then ``=1`` in the Streamlit
child process). See ``test_map_perf_w2_lite_journey_tags_build_extra``.

**Manual app with lite popups** (from repo root)::

    EXPLORER_MAP_LITE_POPUPS=1 streamlit run explorer/app/streamlit/app.py

**Archive lazy JSONL locally** (example: 3 runs × lazy off/on; directory is gitignored)::

    mkdir -p benchmarks/map_perf/snapshots/issue-205-lazy
    for lazy in 0 1; do for run in 1 2 3; do
      EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/benchmarks/map_perf/snapshots/issue-205-lazy/fixture-lazy${lazy}-r${run}.jsonl" \\
        python -m pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_lazy_journey_tags_build_extra --perf -v
    done; done

**Archive W2 JSONL locally** (6 files: 3 runs × lite off/on; directory is gitignored)::

    mkdir -p benchmarks/map_perf/snapshots/issue-205-w2
    for lite in 0 1; do for run in 1 2 3; do
      EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/benchmarks/map_perf/snapshots/issue-205-w2/w2-fixture-lite${lite}-r${run}.jsonl" \\
      EXPLORER_E2E_MAP_LITE_POPUPS=$lite \\
        python -m pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling --perf -v
    done; done

Optional perf JSONL + sidebar buffer::

    EXPLORER_PERF=1 EXPLORER_PERF_LOG_FILE=$PWD/tmp/perf.jsonl EXPLORER_MAP_LITE_POPUPS=1 \\
      streamlit run explorer/app/streamlit/app.py

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
    append_e2e_first_paint_record,
    e2e_map_lazy_popups_for_streamlit_child,
    e2e_map_lite_popups_for_streamlit_child,
    choose_map_view_mode,
    launch_chromium_or_skip,
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


def _run_fixture_view_mode_cycle_journey(
    url: str,
    log_file: Path,
    *,
    dataset_label: str,
    lite_map_popups: bool,
    lazy_map_popups: bool,
) -> None:
    """All → Lifer → All map view-mode cycle; records ``e2e.first_paint`` with W2 tag."""
    with launch_chromium_or_skip() as browser:
        page = browser.new_page()
        # I4 (#205 batch 4): measure end-to-end first paint *before* any other navigation work,
        # so the timing captures the cold pipeline as a user would experience it.
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
                "journey": "fixture_view_mode_cycle",
                "lite_map_popups": lite_map_popups,
                "lazy_map_popups": lazy_map_popups,
            },
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


def test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    url, log_file = streamlit_perf_url_and_logfile
    ceilings = _load_stage_ceilings()
    dataset_label = "real" if os.environ.get("EXPLORER_E2E_DATASET_CSV") else "fixture"

    _run_fixture_view_mode_cycle_journey(
        url,
        log_file,
        dataset_label=dataset_label,
        lite_map_popups=e2e_map_lite_popups_for_streamlit_child() == "1",
        lazy_map_popups=e2e_map_lazy_popups_for_streamlit_child() == "1",
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


def test_map_perf_w2_lite_journey_tags_build_extra(
    streamlit_perf_url_logfile_and_lite_expected: tuple[str, Path, bool],
) -> None:
    """W2 A/B: child env forces ``EXPLORER_MAP_LITE_POPUPS``; JSONL must match on every build."""
    url, log_file, lite_on = streamlit_perf_url_logfile_and_lite_expected
    ceilings = _load_stage_ceilings()
    dataset_label = "real" if os.environ.get("EXPLORER_E2E_DATASET_CSV") else "fixture"

    _run_fixture_view_mode_cycle_journey(
        url,
        log_file,
        dataset_label=dataset_label,
        lite_map_popups=lite_on,
        lazy_map_popups=False,
    )

    time.sleep(0.5)
    raw_lines = []
    if log_file.exists():
        raw_lines = log_file.read_text(encoding="utf-8").splitlines()
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    assert len(events) >= 3, f"expected perf JSON events in Streamlit logs, got {len(events)}"

    builds = [e for e in events if e.get("stage") == "prep.build_species_overlay_map"]
    assert builds, (
        "expected at least one prep.build_species_overlay_map in JSONL "
        f"(lite_map_popups env={lite_on!r}); stages: "
        f"{sorted({str(e.get('stage')) for e in events if e.get('stage')})!r}"
    )
    for e in builds:
        extra = e.get("extra") or {}
        assert extra.get("lite_map_popups") is lite_on, (
            f"prep.build_species_overlay_map extra.lite_map_popups={extra.get('lite_map_popups')!r} "
            f"expected {lite_on!r} for EXPLORER_MAP_LITE_POPUPS={'1' if lite_on else '0'}"
        )
        assert extra.get("lazy_map_popups") is False, (
            f"prep.build_species_overlay_map extra.lazy_map_popups={extra.get('lazy_map_popups')!r} "
            f"expected False (W2 fixture forces lazy off)"
        )

    fp_events = [e for e in events if e.get("stage") == "e2e.first_paint"]
    assert fp_events, "expected e2e.first_paint row from journey"
    for e in fp_events:
        assert e.get("lite_map_popups") is lite_on
        assert e.get("lazy_map_popups") is False

    highs = max_elapsed_ms_by_stage(events)
    failures: list[str] = []
    for stage, cap in ceilings.items():
        obs = highs.get(stage)
        if obs is None:
            continue
        if obs > cap:
            failures.append(f"{stage}: {obs:.1f}ms > ceiling {cap:.1f}ms")
    assert not failures, "Perf ceilings exceeded:\n" + "\n".join(failures)


def test_map_perf_lazy_journey_tags_build_extra(
    streamlit_perf_url_logfile_and_lazy_expected: tuple[str, Path, bool],
) -> None:
    """Batch B A/B: child env forces ``EXPLORER_MAP_LAZY_POPUPS`` (lite off); JSONL tags builds + HTML size.

    Use archived JSONL + ``aggregate_perf_jsonl`` with ``--extra-key html_bytes_len`` on
    ``prep.folium_map_to_html_bytes`` to compare default vs lazy serialized map size.
    """
    url, log_file, lazy_on = streamlit_perf_url_logfile_and_lazy_expected
    ceilings = _load_stage_ceilings()
    dataset_label = "real" if os.environ.get("EXPLORER_E2E_DATASET_CSV") else "fixture"

    _run_fixture_view_mode_cycle_journey(
        url,
        log_file,
        dataset_label=dataset_label,
        lite_map_popups=False,
        lazy_map_popups=lazy_on,
    )

    time.sleep(0.5)
    raw_lines = []
    if log_file.exists():
        raw_lines = log_file.read_text(encoding="utf-8").splitlines()
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    assert len(events) >= 3, f"expected perf JSON events in Streamlit logs, got {len(events)}"

    builds = [e for e in events if e.get("stage") == "prep.build_species_overlay_map"]
    assert builds, (
        "expected at least one prep.build_species_overlay_map in JSONL "
        f"(lazy_map_popups env={lazy_on!r}); stages: "
        f"{sorted({str(e.get('stage')) for e in events if e.get('stage')})!r}"
    )
    for e in builds:
        extra = e.get("extra") or {}
        assert extra.get("lite_map_popups") is False, (
            f"prep.build_species_overlay_map extra.lite_map_popups={extra.get('lite_map_popups')!r} "
            "expected False (lazy fixture forces lite off)"
        )
        assert extra.get("lazy_map_popups") is lazy_on, (
            f"prep.build_species_overlay_map extra.lazy_map_popups={extra.get('lazy_map_popups')!r} "
            f"expected {lazy_on!r} for EXPLORER_MAP_LAZY_POPUPS={'1' if lazy_on else '0'}"
        )

    folium_rows = [e for e in events if e.get("stage") == "prep.folium_map_to_html_bytes"]
    assert folium_rows, "expected at least one prep.folium_map_to_html_bytes (cold HTML generation)"
    for e in folium_rows:
        extra = e.get("extra") or {}
        n = extra.get("html_bytes_len")
        assert isinstance(n, int) and n > 500, (
            f"expected extra.html_bytes_len positive int on folium_map_to_html_bytes, got {n!r}"
        )

    fp_events = [e for e in events if e.get("stage") == "e2e.first_paint"]
    assert fp_events, "expected e2e.first_paint row from journey"
    for e in fp_events:
        assert e.get("lite_map_popups") is False
        assert e.get("lazy_map_popups") is lazy_on

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

    Originally added for #205 batch 3 W1 (testing whether ``@st.fragment`` could short-circuit
    the warm-rerun ``prep.map_iframe_embed`` cost). W1 was dropped — fragments do not isolate
    from full-script ``st.rerun()`` calls — but the journey itself remains the canonical perf
    measurement for **off-map** reruns: any future experiment that targets warm-rerun cost
    needs this path covered, since the default perf E2E only exercises view-mode changes
    (which always invalidate the map cache key).

    The journey lands on All-locations, opens the **Performance / debug** sidebar expander
    (always present when ``EXPLORER_PERF=1``), and clicks **Clear session buffer** which calls
    ``st.rerun()``. ``st.rerun`` is a clean full-script rerun trigger that doesn't touch any
    component of :func:`static_map_cache_key`, so the LRU serves the All-locations entry on
    cache hit while the embed call is paid every time (the warm-rerun shape is what future
    experiments will A/B against).

    Pass condition: cold-load + post-rerun both observed via ``prep.tab_session_sync`` count
    growth, and ``prep.map_iframe_embed`` fired at least once. The A/B inequality itself comes
    from running the same test twice across whatever experimental knob is being measured.
    """
    url, log_file = streamlit_perf_url_and_logfile

    with launch_chromium_or_skip() as browser:
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )

        # Wait until the cold load fully completes — ``prep.tab_session_sync`` fires near the
        # end of every full script run, so its first appearance is a clean cold-load-complete
        # signal even on real CSV (where the cold pipeline takes ~10s).
        def _count_stage_events(path: Path, stage: str) -> int:
            if not path.exists():
                return 0
            return sum(
                1
                for e in parse_perf_json_objects_from_log_lines(
                    path.read_text(encoding="utf-8").splitlines()
                )
                if e.get("stage") == stage
            )

        cold_load_deadline = time.monotonic() + 60.0
        cold_sync_count = 0
        while time.monotonic() < cold_load_deadline:
            cold_sync_count = _count_stage_events(log_file, "prep.tab_session_sync")
            if cold_sync_count >= 1:
                break
            time.sleep(0.5)
        assert cold_sync_count >= 1, (
            "cold load never logged prep.tab_session_sync within 60s"
        )
        cold_embed_count = _count_stage_events(log_file, "prep.map_iframe_embed")

        # Trigger an off-map full-app rerun via the perf-debug sidebar's Clear button (calls
        # ``st.rerun()`` and changes nothing in the map cache key). The expander is a
        # ``<details><summary>`` element rather than a button, so target the summary by text.
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar.locator('summary:has-text("Performance / debug")').click()
        clear_btn = sidebar.get_by_role("button", name="Clear session buffer")
        clear_btn.wait_for(timeout=10000)
        clear_btn.click()

        # Wait for the rerun to fully complete: ``prep.tab_session_sync`` fires once per full
        # script run (it sits at the end of the prep pipeline). Polling the JSONL count avoids
        # assuming any specific wall-clock budget — real CSV warm reruns take ~7-10 s, fixture
        # warm reruns ~1 s.
        rerun_deadline = time.monotonic() + 60.0
        while time.monotonic() < rerun_deadline:
            current_sync_count = _count_stage_events(log_file, "prep.tab_session_sync")
            if current_sync_count > cold_sync_count:
                break
            time.sleep(0.25)
        else:
            current_sync_count = _count_stage_events(log_file, "prep.tab_session_sync")
        assert current_sync_count > cold_sync_count, (
            f"off-map rerun never logged a follow-up prep.tab_session_sync within 60s "
            f"(cold={cold_sync_count}, current={current_sync_count})"
        )
        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )

    # Settle for buffered JSONL writes to flush.
    time.sleep(1.0)
    raw_lines = log_file.read_text(encoding="utf-8").splitlines() if log_file.exists() else []
    events = parse_perf_json_objects_from_log_lines(raw_lines)
    embed_events = [e for e in events if e.get("stage") == "prep.map_iframe_embed"]
    assert len(embed_events) >= 1, (
        f"expected at least one prep.map_iframe_embed event; got {len(embed_events)}"
    )
    # Pass criterion: the journey completes (cold-load + post-rerun both observed via
    # ``prep.tab_session_sync`` count growth). Any A/B comparison itself happens by
    # aggregating archived JSONL across the experimental knob.
    assert cold_embed_count >= 1, (
        f"expected at least one prep.map_iframe_embed event during cold load; "
        f"got {cold_embed_count}"
    )


# Banner width sanity floor for the #205 batch-1 H1 #190 regression: in that broken mode
# the banner visibly shrank (text wrapped onto its own narrow column). The healthy banner
# width on a 1400px viewport is ~290–340 px depending on dataset; 150 px is a generous
# floor that still flags the #190 shape.
_PEBIRD_BANNER_MIN_WIDTH_PX = 150.0


def test_map_embed_all_locations_cluster_popup_parity_screenshot(
    streamlit_perf_url_and_logfile: tuple[str, Path],
) -> None:
    """Capture All-locations cluster + popup parity for #205.

    The I6 lesson from batch 1: the Lifer-view screenshot test missed the H1 #190 regression
    because the All-locations cluster path's DOM (``MarkerClusterGroup`` + ``CircleMarker``
    popups) differs from the Lifer view. This test makes that visual surface a repeatable
    regression check for any future map-embed experiment.

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
       ``benchmarks/map_perf/snapshots/issue-205-cluster-popup-parity/`` keyed by dataset
       label so future experiments can re-shoot side-by-side over their own A/B knob.
    """
    url, _log = streamlit_perf_url_and_logfile
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
            "no frame contained .marker-cluster; the All-locations cluster path didn't render"
            " — would have hidden #190-style breakage"
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
            f"(result={result!r})"
        )

        popup_count = int(result.get("popupCount", 0))
        popup_content_count = int(result.get("popupContentCount", 0))
        popup_tip_count = int(result.get("popupTipCount", 0))
        assert popup_count >= 1, "openPopup did not produce a .leaflet-popup in DOM"
        assert popup_content_count >= 1, "popup rendered without .leaflet-popup-content"
        # The H1 #190 detachment surface: tip missing or detached so popup floats away
        # from the underlying marker.
        assert popup_tip_count >= 1, (
            "popup rendered without a .leaflet-popup-tip; this is the #190 detachment shape"
        )

        # The other H1 #190 visible surface: banner shrunk to a thin column.
        banner = map_frame.locator(".pebird-map-banner").first
        assert banner.count() >= 1
        banner_box = banner.bounding_box()
        assert banner_box is not None, "could not measure .pebird-map-banner bounding box"
        assert banner_box["width"] >= _PEBIRD_BANNER_MIN_WIDTH_PX, (
            f"pebird-map-banner shrunk below {_PEBIRD_BANNER_MIN_WIDTH_PX}px "
            f"(width={banner_box['width']}); this matches the #190 regression shape — "
            "review the screenshot"
        )

        # Allow OSM (or whichever basemap) tiles to paint before the screenshot. Without this
        # wait the screenshot can capture a still-loading iframe with a blank gray pane,
        # which makes any side-by-side visual diff misleading even when the popup-DOM
        # assertions all pass.
        try:
            map_frame.locator(".leaflet-tile-loaded").first.wait_for(timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        out_dir = (
            REPO_ROOT
            / "benchmarks"
            / "map_perf"
            / "snapshots"
            / "issue-205-cluster-popup-parity"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"all-locations-cluster-popup-{dataset_label}.png"
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
