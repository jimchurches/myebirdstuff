"""Minimal browser E2E smoke tests for Streamlit map defaults.

- launch the real Streamlit app in a subprocess,
- point it at a fixture CSV via temporary ``config/config.yaml``,
- assert high-value map UI contracts (``st_folium`` iframe / frames, not ``srcdoc``).

If Playwright is not installed locally, this module is skipped.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect

from tests.explorer.e2e_support import launch_chromium_or_skip, wait_for_pebird_map_markup

pytestmark = pytest.mark.e2e


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
