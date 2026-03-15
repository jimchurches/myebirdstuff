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
    build_visit_info_html,
    build_location_popup_html,
    resolve_lifer_last_seen,
    classify_locations,
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


# ---------------------------------------------------------------------------
# build_visit_info_html
# ---------------------------------------------------------------------------

def test_build_visit_info_html_basic():
    df = pd.DataFrame({
        "Submission ID": ["S100", "S200"],
        "Date": [pd.Timestamp("2025-01-15"), pd.Timestamp("2025-01-16")],
        "Time": ["08:00", "09:00"],
    })
    html = build_visit_info_html(df, format_visit_time)
    assert "S100" in html
    assert "S200" in html
    assert "ebird.org/checklist/S100" in html
    assert "<br>" in html


def test_build_visit_info_html_empty():
    df = pd.DataFrame({"Submission ID": [], "Date": [], "Time": []})
    assert build_visit_info_html(df, format_visit_time) == ""


def test_build_visit_info_html_single_record():
    df = pd.DataFrame({
        "Submission ID": ["S999"],
        "Date": [pd.Timestamp("2025-06-01")],
        "Time": ["12:00"],
    })
    html = build_visit_info_html(df, format_visit_time)
    assert "S999" in html
    assert "<br>" not in html.replace("</a>", "")  # no separator between items


# ---------------------------------------------------------------------------
# build_location_popup_html
# ---------------------------------------------------------------------------

def test_build_location_popup_html_visits_only():
    html = build_location_popup_html("My Park", "L12345", "<a>visit1</a>")
    assert "My Park" in html
    assert "ebird.org/lifelist/L12345" in html
    assert "Visited:" in html
    assert "Seen:" not in html
    assert "popup-scroll-wrapper" in html


def test_build_location_popup_html_with_sightings():
    html = build_location_popup_html(
        "My Park", "L12345", "<a>visit1</a>", "<br>sighting1"
    )
    assert "Visited:" in html
    assert "Seen:" in html
    assert "sighting1" in html


def test_build_location_popup_html_empty_visit_info():
    html = build_location_popup_html("Empty Spot", "L00000", "")
    assert "Empty Spot" in html
    assert "Visited:" in html


def test_build_location_popup_html_structure():
    html = build_location_popup_html("Loc", "L1", "visits")
    assert html.startswith('<div class="popup-scroll-wrapper"')
    assert html.endswith("</div></div>")


# ---------------------------------------------------------------------------
# resolve_lifer_last_seen
# ---------------------------------------------------------------------------

def _dummy_base(sci_name):
    """Minimal base-species extractor for tests."""
    parts = (sci_name or "").strip().split()
    return f"{parts[0]} {parts[1]}".lower() if len(parts) >= 2 else None


def test_resolve_lifer_last_seen_base_species():
    seen = {"L1", "L2", "L3"}
    lifer, last = resolve_lifer_last_seen(
        "Anas gracilis",
        seen,
        lifer_lookup={"anas gracilis": "L1"},
        last_seen_lookup={"anas gracilis": "L3"},
        lifer_lookup_taxon={},
        last_seen_lookup_taxon={},
        base_species_fn=_dummy_base,
    )
    assert lifer == "L1"
    assert last == "L3"


def test_resolve_lifer_last_seen_subspecies_taxon():
    seen = {"L1", "L2"}
    lifer, last = resolve_lifer_last_seen(
        "Anas gracilis rogersi",
        seen,
        lifer_lookup={"anas gracilis": "L1"},
        last_seen_lookup={"anas gracilis": "L2"},
        lifer_lookup_taxon={"anas gracilis rogersi": "L2"},
        last_seen_lookup_taxon={"anas gracilis rogersi": "L1"},
        base_species_fn=_dummy_base,
    )
    # Taxon-level should win for subspecies
    assert lifer == "L2"
    assert last == "L1"


def test_resolve_lifer_last_seen_taxon_fallback_to_base():
    seen = {"L1", "L2"}
    lifer, last = resolve_lifer_last_seen(
        "Anas gracilis rogersi",
        seen,
        lifer_lookup={"anas gracilis": "L1"},
        last_seen_lookup={"anas gracilis": "L2"},
        lifer_lookup_taxon={},  # no taxon entry
        last_seen_lookup_taxon={},
        base_species_fn=_dummy_base,
    )
    assert lifer == "L1"
    assert last == "L2"


def test_resolve_lifer_last_seen_not_in_seen():
    seen = {"L1"}
    lifer, last = resolve_lifer_last_seen(
        "Anas gracilis",
        seen,
        lifer_lookup={"anas gracilis": "L99"},  # not in seen
        last_seen_lookup={"anas gracilis": "L1"},
        lifer_lookup_taxon={},
        last_seen_lookup_taxon={},
        base_species_fn=_dummy_base,
    )
    assert lifer is None
    assert last == "L1"


def test_resolve_lifer_last_seen_same_location():
    """last_seen should be None when it matches lifer."""
    seen = {"L1"}
    lifer, last = resolve_lifer_last_seen(
        "Anas gracilis",
        seen,
        lifer_lookup={"anas gracilis": "L1"},
        last_seen_lookup={"anas gracilis": "L1"},
        lifer_lookup_taxon={},
        last_seen_lookup_taxon={},
        base_species_fn=_dummy_base,
    )
    assert lifer == "L1"
    assert last is None


def test_resolve_lifer_last_seen_disabled():
    seen = {"L1"}
    lifer, last = resolve_lifer_last_seen(
        "Anas gracilis",
        seen,
        lifer_lookup={"anas gracilis": "L1"},
        last_seen_lookup={"anas gracilis": "L1"},
        lifer_lookup_taxon={},
        last_seen_lookup_taxon={},
        base_species_fn=_dummy_base,
        mark_lifer=False,
        mark_last_seen=False,
    )
    assert lifer is None
    assert last is None


def test_resolve_lifer_last_seen_empty_species():
    lifer, last = resolve_lifer_last_seen(
        "",
        set(),
        lifer_lookup={},
        last_seen_lookup={},
        lifer_lookup_taxon={},
        last_seen_lookup_taxon={},
        base_species_fn=_dummy_base,
    )
    assert lifer is None
    assert last is None


# ---------------------------------------------------------------------------
# classify_locations
# ---------------------------------------------------------------------------

def test_classify_locations_basic():
    loc_df = pd.DataFrame({
        "Location ID": ["L1", "L2", "L3"],
        "Location": ["Park", "Beach", "Lake"],
        "Latitude": [-33.0, -34.0, -35.0],
        "Longitude": [151.0, 150.0, 149.0],
    })
    result = classify_locations(loc_df, seen_location_ids={"L1", "L3"}, lifer_location="L1", last_seen_location="L3")
    assert {"has_species_match", "is_lifer", "is_last_seen"}.issubset(result.columns)
    l1 = result[result["Location ID"] == "L1"].iloc[0]
    assert l1["has_species_match"] == True
    assert l1["is_lifer"] == True
    assert l1["is_last_seen"] == False
    l2 = result[result["Location ID"] == "L2"].iloc[0]
    assert l2["has_species_match"] == False
    l3 = result[result["Location ID"] == "L3"].iloc[0]
    assert l3["has_species_match"] == True
    assert l3["is_last_seen"] == True


def test_classify_locations_sort_order():
    """Lifer should be last row (drawn on top)."""
    loc_df = pd.DataFrame({
        "Location ID": ["L1", "L2", "L3"],
        "Location": ["A", "B", "C"],
        "Latitude": [0, 0, 0],
        "Longitude": [0, 0, 0],
    })
    result = classify_locations(loc_df, {"L1", "L3"}, lifer_location="L3", last_seen_location="L1")
    assert result.iloc[-1]["Location ID"] == "L3"  # lifer last


def test_classify_locations_no_special():
    loc_df = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["A", "B"],
        "Latitude": [0, 0],
        "Longitude": [0, 0],
    })
    result = classify_locations(loc_df, {"L1"}, lifer_location=None, last_seen_location=None)
    assert not result["is_lifer"].any()
    assert not result["is_last_seen"].any()


def test_classify_locations_does_not_mutate_input():
    loc_df = pd.DataFrame({
        "Location ID": ["L1"],
        "Location": ["A"],
        "Latitude": [0],
        "Longitude": [0],
    })
    original_cols = list(loc_df.columns)
    classify_locations(loc_df, {"L1"}, "L1", None)
    assert list(loc_df.columns) == original_cols
