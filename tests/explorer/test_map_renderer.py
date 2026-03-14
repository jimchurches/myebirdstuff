"""Tests for personal_ebird_explorer.map_renderer helpers."""

import math
from datetime import datetime

import folium
import pandas as pd

from personal_ebird_explorer.map_renderer import (
    create_map,
    format_visit_time,
    format_sighting_row,
    popup_scroll_script,
)


# ---------------------------------------------------------------------------
# format_visit_time
# ---------------------------------------------------------------------------

def test_format_visit_time_with_datetime_column():
    row = pd.Series({"Date": pd.Timestamp("2025-01-15"), "Time": "08:30", "datetime": pd.Timestamp("2025-01-15 08:30")})
    assert format_visit_time(row) == "2025-01-15 08:30"


def test_format_visit_time_without_datetime_column():
    row = pd.Series({"Date": pd.Timestamp("2025-01-15"), "Time": "08:30"})
    assert format_visit_time(row) == "2025-01-15 08:30"


def test_format_visit_time_missing_date():
    row = pd.Series({"Date": pd.NaT, "Time": "08:30"})
    assert format_visit_time(row) == "? 08:30"


def test_format_visit_time_missing_time():
    row = pd.Series({"Date": pd.Timestamp("2025-01-15"), "Time": None})
    assert format_visit_time(row) == "2025-01-15 unknown"


def test_format_visit_time_datetime_nan_falls_back():
    row = pd.Series({"Date": pd.Timestamp("2025-01-15"), "Time": "09:00", "datetime": pd.NaT})
    assert format_visit_time(row) == "2025-01-15 09:00"


# ---------------------------------------------------------------------------
# format_sighting_row
# ---------------------------------------------------------------------------

def test_format_sighting_row_basic():
    row = pd.Series({
        "Date": pd.Timestamp("2025-03-10"),
        "Time": "07:00",
        "Common Name": "Grey Teal",
        "Count": 3,
        "Submission ID": "S123456",
        "ML Catalog Numbers": None,
    })
    html = format_sighting_row(row)
    assert "Grey Teal" in html
    assert "S123456" in html
    assert "ebird.org/checklist/S123456" in html
    assert html.startswith("<br>")


def test_format_sighting_row_with_media():
    row = pd.Series({
        "Date": pd.Timestamp("2025-03-10"),
        "Time": "07:00",
        "Common Name": "Grey Teal",
        "Count": 3,
        "Submission ID": "S123456",
        "ML Catalog Numbers": "ML12345 ML67890",
    })
    html = format_sighting_row(row)
    assert "macaulaylibrary.org/asset/ML12345" in html
    assert "📷" in html


def test_format_sighting_row_no_submission_id():
    row = pd.Series({
        "Date": pd.Timestamp("2025-03-10"),
        "Time": "07:00",
        "Common Name": "Grey Teal",
        "Count": 1,
        "ML Catalog Numbers": None,
    })
    html = format_sighting_row(row)
    assert 'href="#"' in html


def test_format_sighting_row_with_datetime():
    row = pd.Series({
        "Date": pd.Timestamp("2025-03-10"),
        "Time": "07:00",
        "Common Name": "Grey Teal",
        "Count": 2,
        "Submission ID": "S999",
        "ML Catalog Numbers": None,
        "datetime": pd.Timestamp("2025-03-10 07:00"),
    })
    html = format_sighting_row(row)
    assert "2025-03-10 07:00" in html


# ---------------------------------------------------------------------------
# popup_scroll_script
# ---------------------------------------------------------------------------

def test_popup_scroll_script_returns_script_tag():
    result = popup_scroll_script("chevron", False)
    assert "<script>" in result
    assert "</script>" in result


def test_popup_scroll_script_chevron_mode():
    result = popup_scroll_script("chevron", False)
    assert "'chevron'" in result
    assert "SCROLL_TO_BOTTOM = false" in result


def test_popup_scroll_script_scroll_to_bottom():
    result = popup_scroll_script("both", True)
    assert "SCROLL_TO_BOTTOM = true" in result


def test_popup_scroll_script_none_hint():
    result = popup_scroll_script(None, False)
    assert "None" in result


# ---------------------------------------------------------------------------
# create_map
# ---------------------------------------------------------------------------

def test_create_map_default():
    m = create_map([0.0, 0.0])
    assert isinstance(m, folium.Map)


def test_create_map_default_explicit():
    m = create_map([0.0, 0.0], "default")
    assert isinstance(m, folium.Map)


def test_create_map_satellite():
    m = create_map([-33.8, 151.2], "satellite")
    assert isinstance(m, folium.Map)


def test_create_map_google():
    m = create_map([-33.8, 151.2], "google")
    assert isinstance(m, folium.Map)


def test_create_map_carto():
    m = create_map([-33.8, 151.2], "carto")
    assert isinstance(m, folium.Map)


def test_create_map_unknown_style_falls_back():
    m = create_map([0.0, 0.0], "unknown_style")
    assert isinstance(m, folium.Map)
