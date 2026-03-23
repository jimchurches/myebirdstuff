"""Tests for checklist stats compute + display bundle (refs #68)."""

import pandas as pd

from personal_ebird_explorer.checklist_stats_compute import (
    compute_checklist_stats_payload,
    protocol_display_name,
)
from personal_ebird_explorer.checklist_stats_display import (
    build_yearly_summary_streamlit_tab_html_dict,
    format_checklist_stats_bundle,
    strip_yearly_stats_info_icons,
)


def test_compute_payload_empty():
    assert compute_checklist_stats_payload(pd.DataFrame(), top_n_limit=10) is None


def test_protocol_display_name_ebird_export_strings():
    assert protocol_display_name("eBird - Traveling Count") == "Traveling"
    assert protocol_display_name("eBird - Stationary Count") == "Stationary"
    assert protocol_display_name("eBird - Casual Observation") == "Incidental"
    assert protocol_display_name("  ebird - travelling count  ") == "Traveling"


def test_protocol_display_name_unknown_unchanged():
    assert protocol_display_name("Banding") == "Banding"
    assert protocol_display_name("") == ""
    assert protocol_display_name(float("nan")) == ""


def test_format_bundle_empty_dataframe():
    out = format_checklist_stats_bundle(
        None,
        link_urls_fn=None,
        scroll_hint=400,
        visible_rows=8,
    )
    assert "stats_html" in out
    assert "No data." in out["stats_html"]
    assert out["rankings_sections_top_n"] == []
    assert out["incomplete_by_year"] == {}


def test_incomplete_checklists_excludes_incidental_and_historical():
    """Incomplete row counts not-all-reported checklists except Incidental/Historical/casual."""
    df = pd.DataFrame(
        {
            "Submission ID": ["a", "b", "c", "d"],
            "Common Name": ["X", "X", "X", "X"],
            "Scientific Name": ["Sp", "Sp", "Sp", "Sp"],
            "Count": [1, 1, 1, 1],
            "Date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]),
            "Location": ["L1", "L2", "L3", "L4"],
            "Location ID": ["1", "2", "3", "4"],
            "Latitude": [-33.0, -33.0, -34.0, -34.0],
            "Longitude": [151.0, 151.0, 150.0, 150.0],
            "Protocol": ["Traveling", "Incidental", "Historical", "Traveling"],
            "Duration (Min)": [10, 10, 10, 10],
            "Distance Traveled (km)": [0.0, 0.0, 0.0, 0.0],
            "All Obs Reported": [0, 0, 0, 1],
        }
    )
    payload = compute_checklist_stats_payload(df, top_n_limit=5)
    assert payload is not None
    rows = dict(payload.protocol_rows)
    assert rows["Incomplete checklists"] == "1"
    assert rows["Completed checklists"] == "1"
    keys = [k for k, _ in payload.protocol_rows]
    assert keys.index("Incomplete checklists") < keys.index("Completed checklists")


def test_compute_and_format_smoke():
    df = pd.DataFrame(
        {
            "Submission ID": ["s1", "s1", "s2"],
            "Common Name": ["Robin", "Duck", "Duck"],
            "Scientific Name": ["Turdus migratorius", "Anas platyrhynchos", "Anas platyrhynchos"],
            "Count": [1, 2, 1],
            "Date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01"]),
            "Location": ["L1", "L1", "L2"],
            "Location ID": ["1", "1", "2"],
            "Latitude": [-33.0, -33.0, -34.0],
            "Longitude": [151.0, 151.0, 150.0],
            "Protocol": ["Traveling", "Traveling", "Stationary"],
            "Duration (Min)": [30, 30, 20],
            "Distance Traveled (km)": [1.0, 1.0, 0.0],
            "All Obs Reported": [1, 1, 1],
        }
    )
    payload = compute_checklist_stats_payload(df, top_n_limit=5)
    assert payload is not None
    assert payload.n_checklists == 2
    assert payload.streak >= 1
    bundle = format_checklist_stats_bundle(
        payload,
        link_urls_fn=lambda _: (None, None),
        scroll_hint=400,
        visible_rows=8,
    )
    assert "<table" in bundle["stats_html"]
    assert len(bundle["rankings_sections_top_n"]) == 7
    assert len(bundle["rankings_sections_other"]) == 4


def test_strip_yearly_stats_info_icons_removes_span():
    raw = (
        'Traveling checklists <span class="stats-info-icon">'
        '<span class="stats-info-glyph">&#9432;</span>'
        "<span class=\"stats-info-tooltip\">hint</span></span>"
    )
    out = strip_yearly_stats_info_icons(raw)
    assert "stats-info-icon" not in out
    assert out == "Traveling checklists"


def test_build_yearly_summary_streamlit_tab_html_dict_smoke():
    """Streamlit yearly tabs: three bodies, no inline info icons, yearly table class (refs #85)."""
    df = pd.DataFrame(
        {
            "Submission ID": ["s1", "s1", "s2"],
            "Common Name": ["Robin", "Duck", "Duck"],
            "Scientific Name": ["Turdus migratorius", "Anas platyrhynchos", "Anas platyrhynchos"],
            "Count": [1, 2, 1],
            "Date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01"]),
            "Location": ["L1", "L1", "L2"],
            "Location ID": ["1", "1", "2"],
            "Latitude": [-33.0, -33.0, -34.0],
            "Longitude": [151.0, 151.0, 150.0],
            "Protocol": ["Traveling", "Traveling", "Stationary"],
            "Duration (Min)": [30, 30, 20],
            "Distance Traveled (km)": [1.0, 1.0, 0.0],
            "All Obs Reported": [1, 1, 1],
        }
    )
    payload = compute_checklist_stats_payload(df, top_n_limit=5)
    assert payload is not None
    bodies = build_yearly_summary_streamlit_tab_html_dict(payload)
    assert bodies is not None
    assert set(bodies) == {"all", "travelling", "stationary"}
    assert "stats-tbl-yearly" in bodies["all"]
    assert "stats-info-icon" not in bodies["all"]
    assert "stats-info-icon" not in bodies["travelling"]
    assert "stats-info-icon" not in bodies["stationary"]
    assert "Travelling and Stationary checklist counts" in bodies["all"]
    assert "Incomplete checklists are excluded" in bodies["travelling"]
