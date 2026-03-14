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
    pin_legend_item,
    build_all_species_banner_html,
    build_species_banner_html,
    build_legend_html,
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


# ---------------------------------------------------------------------------
# pin_legend_item
# ---------------------------------------------------------------------------

def test_pin_legend_item_contains_color_and_label():
    html = pin_legend_item("red", "#ff0000", "Lifer")
    assert "red" in html
    assert "#ff0000" in html
    assert "Lifer" in html


def test_pin_legend_item_is_single_span():
    html = pin_legend_item("green", "#00ff00", "All locations")
    assert html.startswith("<span")
    assert html.endswith("</span>")


# ---------------------------------------------------------------------------
# build_all_species_banner_html
# ---------------------------------------------------------------------------

def test_build_all_species_banner_html_content():
    html = build_all_species_banner_html(42, 100, 5000)
    assert "All species" in html
    assert "42 checklists" in html
    assert "100 species" in html
    assert "5000 individuals" in html


def test_build_all_species_banner_html_singular():
    html = build_all_species_banner_html(1, 1, 1)
    assert "1 checklist " in html or "1 checklist&" in html
    assert "1 individual<" in html or "1 individual&" in html


def test_build_all_species_banner_html_is_div():
    html = build_all_species_banner_html(10, 20, 30)
    assert html.startswith("<div")
    assert html.endswith("</div>")


# ---------------------------------------------------------------------------
# build_legend_html
# ---------------------------------------------------------------------------

def test_build_legend_html_single_item():
    html = build_legend_html([("green", "#0f0", "All locations")])
    assert "All locations" in html
    assert html.startswith("<div")


def test_build_legend_html_multiple_items():
    items = [
        ("blue", "#00f", "Lifer"),
        ("red", "#f00", "Species"),
        ("green", "#0f0", "Other"),
    ]
    html = build_legend_html(items)
    assert "Lifer" in html
    assert "Species" in html
    assert "Other" in html


def test_build_legend_html_empty_list():
    html = build_legend_html([])
    assert html.startswith("<div")
    assert html.endswith("</div>")


# ---------------------------------------------------------------------------
# build_species_banner_html
# ---------------------------------------------------------------------------

def test_build_species_banner_html_full():
    html = build_species_banner_html(
        display_name="Grey Teal",
        n_checklists=15,
        n_individuals=42,
        high_count=8,
        first_seen_date="10-Jan-2024",
        last_seen_date="20-Feb-2026",
        high_count_date="05-Mar-2025",
    )
    assert "Grey Teal" in html
    assert "15 checklists" in html
    assert "42 individuals" in html
    assert "First seen: 10-Jan-2024" in html
    assert "Last seen: 20-Feb-2026" in html
    assert "High count: 05-Mar-2025 (8)" in html


def test_build_species_banner_html_no_dates():
    html = build_species_banner_html(
        display_name="Superb Fairywren",
        n_checklists=3,
        n_individuals=7,
        high_count=4,
    )
    assert "Superb Fairywren" in html
    assert "3 checklists" in html
    assert "First seen:" not in html
    assert "Last seen:" not in html
    assert "High count:" in html


def test_build_species_banner_html_singular():
    html = build_species_banner_html(
        display_name="Common Ostrich",
        n_checklists=1,
        n_individuals=1,
        high_count=1,
        first_seen_date="01-Jan-2026",
    )
    assert "1 checklist " in html or "1 checklist&" in html
    assert "1 individual<" in html or "1 individual&" in html


def test_build_species_banner_html_is_div():
    html = build_species_banner_html("Test", 1, 1, 1)
    assert html.startswith("<div")
    assert html.endswith("</div>")
