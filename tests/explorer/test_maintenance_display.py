"""Tests for explorer.presentation.maintenance_display (refs #69)."""

import pandas as pd

from explorer.core.duplicate_checks import get_map_maintenance_data
from explorer.presentation.maintenance_display import (
    format_incomplete_checklists_maintenance_html,
    format_map_maintenance_html,
    map_maintenance_close_locations_body_html,
    format_sex_notation_maintenance_html,
)


def test_close_locations_one_table_per_pair():
    """Close locations: separate tables + stack wrapper."""
    loc = pd.DataFrame(
        {
            "Location ID": ["L1", "L2", "L3", "L4"],
            "Location": ["A", "B", "C", "D"],
            "Latitude": [-35.0, -35.000045, -35.02, -35.020045],
            "Longitude": [149.0, 149.0, 149.0, 149.0],
        }
    )
    _, near = get_map_maintenance_data(loc, threshold_m=100)
    assert len(near) == 2
    html = map_maintenance_close_locations_body_html(near, 100)
    assert html.count("<thead>") == 2
    assert html.count("<tbody>") == 2
    assert "maint-close-pair-stack" in html
    assert "maint-spacer" not in html


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
    assert "Update locations in eBird with caution." in html
    assert "particular use cases related to his own location data" in html
    assert "maint-caution-symbol" in html


def test_format_incomplete_empty():
    assert format_incomplete_checklists_maintenance_html({}) == ""


def test_format_sex_notation_empty():
    assert format_sex_notation_maintenance_html({}) == ""
