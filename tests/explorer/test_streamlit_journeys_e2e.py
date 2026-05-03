"""Browser E2E coverage for scripted map **user journeys** (sidebar flows).

Complements smoke tests in :mod:`~tests.explorer.test_streamlit_map_e2e` with multi-step scenarios.
Requires Playwright (module skipped otherwise).
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.explorer.e2e_support import (
    choose_map_view_mode,
    launch_chromium_or_skip,
    wait_for_pebird_map_markup,
)

pytestmark = pytest.mark.e2e


def test_journey_switch_all_locations_to_lifers_and_back(streamlit_app_url: str):
    """Map view → *Lifer locations* → banner title → switch back → *All locations* banner."""

    def _banner_all(html: str) -> None:
        assert 'class="pebird-map-banner__title">All locations</span>' in html

    def _banner_lifer(html: str) -> None:
        assert 'class="pebird-map-banner__title">Lifer locations</span>' in html

    with launch_chromium_or_skip() as browser:
        page = browser.new_page()
        page.goto(streamlit_app_url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        html0 = wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )
        _banner_all(html0)

        choose_map_view_mode(page, "Lifer locations")
        html1 = wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">Lifer locations</span>'],
        )
        _banner_lifer(html1)

        choose_map_view_mode(page, "All locations")
        html2 = wait_for_pebird_map_markup(
            page,
            must_contain=['class="pebird-map-banner__title">All locations</span>'],
        )
        _banner_all(html2)
