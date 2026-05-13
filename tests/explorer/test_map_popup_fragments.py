"""Tests for popup fragment keys and HTML assembly models (#205 Batch A)."""

from __future__ import annotations

import pandas as pd

from explorer.presentation.map_popup_fragments import (
    get_or_set_popup_fragment,
    visit_list_fragment_key,
)
from explorer.presentation.map_popup_models import LocationPopupModel, assemble_location_popup_html


def test_visit_list_fragment_key_stable_under_row_order():
    a = pd.DataFrame(
        {
            "Submission ID": ["S2", "S1"],
            "datetime": pd.to_datetime(["2024-02-01", "2024-01-01"]),
        }
    )
    b = a.sort_values("datetime", ascending=True)
    assert visit_list_fragment_key(a) != visit_list_fragment_key(b)
    assert visit_list_fragment_key(b) == visit_list_fragment_key(b.reset_index(drop=True))


def test_get_or_set_popup_fragment_dedupes():
    cache: dict[tuple, str] = {}
    calls = {"n": 0}

    def factory() -> str:
        calls["n"] += 1
        return "<br>x"

    k: tuple = ("visit", (("S1", 1),))
    assert get_or_set_popup_fragment(cache, k, factory) == "<br>x"
    assert get_or_set_popup_fragment(cache, k, factory) == "<br>x"
    assert calls["n"] == 1


def test_assemble_location_popup_escapes_title_and_keeps_structure():
    m = LocationPopupModel(
        loc_name="Place & <tag>",
        loc_id="L99",
        visit_info_html='<a href="https://ebird.org/checklist/S1">2024-01-01</a>',
        sightings_html="",
        lifer_species_html="",
        show_visit_history=True,
        lifer_heading_html="",
        location_heading_margin_px=4,
    )
    html = assemble_location_popup_html(m)
    assert "pebird-map-popup" in html
    assert "https://ebird.org/lifelist/L99" in html
    assert "Place &amp; &lt;tag&gt;" in html
    assert "Visited:" in html
