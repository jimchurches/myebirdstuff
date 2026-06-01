"""Minimal browser E2E smoke tests for Streamlit map defaults.

- launch the real Streamlit app in a subprocess,
- point it at a fixture CSV via temporary ``config/config.yaml``,
- assert high-value map UI contracts (Leaflet component iframe / frames, not ``srcdoc``).

If Playwright is not installed locally, this module is skipped.
"""

from __future__ import annotations

import os
import time

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect

from tests.explorer.e2e_support import (
    REPO_ROOT,
    launch_chromium_or_skip,
    wait_for_pebird_map_markup,
)

pytestmark = pytest.mark.e2e

# Banner width floor for thin-column regression; see map E2E popup/cluster contracts.
_PEBIRD_BANNER_MIN_WIDTH_PX = 150.0


def test_map_default_view_with_config_shows_all_locations_banner(streamlit_app_url: str):
    with launch_chromium_or_skip() as browser:
        page = browser.new_page()
        page.goto(streamlit_app_url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar.get_by_text("Map view")).to_be_visible()
        expect(sidebar.get_by_text("All locations")).to_be_visible()

        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )


def test_all_locations_map_shows_legend_and_focused_default(streamlit_app_url: str):
    with launch_chromium_or_skip() as browser:
        page = browser.new_page()
        page.goto(streamlit_app_url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar.get_by_text("Map focus")).to_be_visible()
        expect(
            sidebar.get_by_text("Focused view shows your main birding regions.")
        ).to_be_visible()

        html = wait_for_pebird_map_markup(
            page,
            must_contain=[
                'class="pebird-map-banner__title">All locations</span>',
                "pebird-map-legend",
            ],
        )
        assert "pebird-map-legend" in html


def test_all_locations_cluster_popup_parity(streamlit_app_url: str) -> None:
    """All-locations cluster + popup DOM parity (Leaflet component).

    Opens a ``CircleMarker`` popup via the Leaflet API (fixture clusters may never
  un-cluster at max zoom). Asserts popup content + tip and minimum banner width.
    """
    url = streamlit_app_url
    dataset_label = "real" if os.environ.get("EXPLORER_E2E_DATASET_CSV") else "fixture"

    with launch_chromium_or_skip() as browser:
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )

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
            "no frame contained .marker-cluster; All-locations cluster path did not render"
        )

        result = map_frame.evaluate(
            """
            () => {
                const out = {found: 0, error: null,
                             popupCount: 0, popupContentCount: 0, popupTipCount: 0};
                const m = window.__pebirdLeafletMap || null;
                if (!m) { out.error = 'no __pebirdLeafletMap on window'; return out; }
                m.eachLayer((layer) => {
                    if (out.found > 0) return;
                    if (window.L && layer instanceof window.L.CircleMarker) {
                        try {
                            const ll = layer.getLatLng();
                            m.setView(ll, 12, {animate: false});
                            if (typeof layer.openPopup === 'function') {
                                layer.openPopup();
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
        assert result.get("found", 0) >= 1, f"could not open CircleMarker popup (result={result!r})"
        assert int(result.get("popupContentCount", 0)) >= 1
        assert int(result.get("popupTipCount", 0)) >= 1, (
            "missing .leaflet-popup-tip (detached popup shape)"
        )

        banner = map_frame.locator(".pebird-map-banner").first
        assert banner.count() >= 1
        banner_box = banner.bounding_box()
        assert banner_box is not None
        assert banner_box["width"] >= _PEBIRD_BANNER_MIN_WIDTH_PX, (
            f"pebird-map-banner width {banner_box['width']} < {_PEBIRD_BANNER_MIN_WIDTH_PX}px"
        )

        try:
            map_frame.locator(".leaflet-tile-loaded").first.wait_for(timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        out_dir = REPO_ROOT / "benchmarks" / "map_perf" / "snapshots" / "issue-222-cluster-popup-parity"
        out_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out_dir / f"all-locations-cluster-popup-{dataset_label}.png"), full_page=True)
