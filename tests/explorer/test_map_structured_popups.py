"""Tests for #205 Batch C — structured All-locations popup payloads."""

from __future__ import annotations

import pandas as pd
import pytest

from explorer.presentation.map_renderer import (
    build_location_popup_html,
    build_visit_info_html,
    format_visit_time,
)
from explorer.presentation.map_structured_popups import (
    ALL_LOCATIONS_POPUP_PAYLOAD_KIND,
    all_locations_popup_payload_to_html,
    build_all_locations_popup_payload,
)


def _visit_records():
    return pd.DataFrame(
        {
            "Submission ID": ["S1", "S2"],
            "datetime": pd.to_datetime(["2024-01-01 08:00", "2024-02-01 09:30"]),
            "Common Name": ["A", "B"],
            "Count": [1, 2],
        }
    )


def test_build_all_locations_popup_payload_round_trip_matches_rich_popup():
    rec = _visit_records().sort_values("datetime", ascending=True)
    loc_name = "Ripple Swamp"
    loc_id = "L77"
    visit_info = build_visit_info_html(rec, format_visit_time)
    expected = build_location_popup_html(loc_name, loc_id, visit_info)
    payload = build_all_locations_popup_payload(loc_name, loc_id, rec, format_visit_time)
    assert payload["k"] == ALL_LOCATIONS_POPUP_PAYLOAD_KIND
    assert all_locations_popup_payload_to_html(payload) == expected


def test_empty_visits_match_rich_popup():
    empty = pd.DataFrame()
    expected = build_location_popup_html("X", "L9", "")
    payload = build_all_locations_popup_payload("X", "L9", empty, format_visit_time)
    assert all_locations_popup_payload_to_html(payload) == expected


def test_payload_to_html_rejects_unknown_kind():
    with pytest.raises(ValueError):
        all_locations_popup_payload_to_html({"k": "nope"})
