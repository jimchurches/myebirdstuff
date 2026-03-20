"""Tests for personal_ebird_explorer.maintenance_display (refs #69)."""

import pandas as pd

from personal_ebird_explorer.maintenance_display import (
    format_incomplete_checklists_maintenance_html,
    format_map_maintenance_html,
    format_sex_notation_maintenance_html,
)


def test_format_map_maintenance_html_contains_section():
    loc = pd.DataFrame(
        {
            "Location ID": ["L1"],
            "Location": ["Only"],
            "Latitude": [-35.0],
            "Longitude": [149.0],
        }
    )
    html = format_map_maintenance_html(loc, threshold_m=200)
    assert "Location Maintenance" in html
    assert "Exact duplicates" in html
    assert "Close locations" in html


def test_format_incomplete_empty():
    assert format_incomplete_checklists_maintenance_html({}) == ""


def test_format_sex_notation_empty():
    assert format_sex_notation_maintenance_html({}) == ""
