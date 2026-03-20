"""Tests for checklist stats compute + display bundle (refs #68)."""

import pandas as pd

from personal_ebird_explorer.checklist_stats_compute import compute_checklist_stats_payload
from personal_ebird_explorer.checklist_stats_display import format_checklist_stats_bundle


def test_compute_payload_empty():
    assert compute_checklist_stats_payload(pd.DataFrame(), top_n_limit=10) is None


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
