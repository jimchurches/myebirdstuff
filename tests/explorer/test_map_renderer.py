"""Tests for explorer.presentation.map_renderer helpers."""

import folium
import pandas as pd

from explorer.app.streamlit.defaults import MAP_POPUP_MACAULAY_LINK_SYMBOL, MAP_POPUP_MAX_WIDTH_PX
from explorer.presentation.map_renderer import (
    build_species_map_location_popup_html,
    build_species_seen_sections_html,
    build_visit_info_html,
    build_all_species_banner_html,
    build_species_banner_html,
    build_legend_html,
    build_location_popup_html,
    classify_locations,
    create_map,
    format_species_map_sighting_row,
    format_sighting_row,
    format_visit_time,
    map_popup_width_fix_script,
    pin_legend_item,
    popup_scroll_script,
    resolve_lifer_last_seen,
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
    assert "pebird-map-popup__media-link" in html and MAP_POPUP_MACAULAY_LINK_SYMBOL in html
    assert 'title="media"' in html


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
# format_species_map_sighting_row / build_species_seen_sections_html (refs #145)
# ---------------------------------------------------------------------------

def test_format_species_map_sighting_row_omits_common_name():
    row = pd.Series({
        "Date": pd.Timestamp("2024-11-12"),
        "Time": "05:54",
        "Common Name": "Pacific Golden Plover",
        "Count": 1,
        "Submission ID": "SCHK1",
        "ML Catalog Numbers": None,
        "datetime": pd.Timestamp("2024-11-12 05:54"),
    })
    html = format_species_map_sighting_row(row)
    assert "Pacific Golden Plover" not in html
    assert "pebird-map-popup__obs-line" in html
    assert "2024-11-12 05:54" in html
    assert "(Observed: 1)" in html
    assert "ebird.org/checklist/SCHK1" in html


def test_format_species_map_sighting_row_media():
    row = pd.Series({
        "Date": pd.Timestamp("2024-11-12"),
        "Time": "05:54",
        "Common Name": "X",
        "Count": 2,
        "Submission ID": "S2",
        "ML Catalog Numbers": "ML999",
        "datetime": pd.Timestamp("2024-11-12 05:54"),
    })
    html = format_species_map_sighting_row(row)
    assert "pebird-map-popup__obs-line" in html
    assert "macaulaylibrary.org/asset/ML999" in html
    assert "pebird-map-popup__media-link" in html and MAP_POPUP_MACAULAY_LINK_SYMBOL in html
    assert 'title="media"' in html


def test_build_species_seen_sections_two_common_names():
    df = pd.DataFrame({
        "Common Name": ["Grey Teal", "Pacific Golden Plover", "Grey Teal"],
        "datetime": [
            pd.Timestamp("2025-01-01 08:00"),
            pd.Timestamp("2025-02-01 09:00"),
            pd.Timestamp("2025-01-02 10:00"),
        ],
        "Count": [1, 2, 3],
        "Submission ID": ["A", "B", "C"],
        "ML Catalog Numbers": [None, None, None],
    })
    html = build_species_seen_sections_html(df, ascending=True)
    assert html.count('<details class="pebird-map-popup__species-seen">') == 2
    assert '<details class="pebird-map-popup__species-seen" open>' not in html
    assert 'pebird-map-popup__section-label">Grey Teal:</summary>' in html
    assert 'pebird-map-popup__section-label">Pacific Golden Plover:</summary>' in html
    assert "pebird-map-popup__obs-list" in html
    assert html.index("Grey Teal") < html.index("Pacific Golden Plover")


def test_build_species_map_location_popup_html_collapsed_visits():
    species_df = pd.DataFrame({
        "Common Name": ["Bird X"],
        "datetime": [pd.Timestamp("2025-06-01 12:00")],
        "Count": [5],
        "Submission ID": ["SID1"],
        "ML Catalog Numbers": [None],
    })
    visit_fragment = '<a href="https://ebird.org/checklist/V1">2025-01-01</a>'
    html = build_species_map_location_popup_html(
        "Hotspot",
        "L99",
        species_df,
        visit_fragment,
        visit_record_count=3,
        popup_ascending=True,
    )
    assert '<details class="pebird-map-popup__species-seen" open>' in html
    assert "details" in html and "pebird-map-popup__all-visits" in html
    assert "Visited: (3)" in html
    assert visit_fragment in html
    # Species map uses <summary>, not the standalone Visited block from build_location_popup_html.
    assert '<div class="pebird-map-popup__section-label">Visited:</div>' not in html


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


def test_map_popup_width_fix_script_embeds_max_width():
    s = map_popup_width_fix_script()
    assert "<script>" in s and "shrinkPebirdPopups" in s
    assert f"var MAX_PX = {MAP_POPUP_MAX_WIDTH_PX}" in s


# ---------------------------------------------------------------------------
# create_map
# ---------------------------------------------------------------------------

def test_create_map_default():
    m = create_map([0.0, 0.0])
    assert isinstance(m, folium.Map)


def test_create_map_default_explicit():
    m = create_map([0.0, 0.0], "default")
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
    assert "1 checklist" in html
    assert "1 individual" in html


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
        first_seen_checklist_url="https://ebird.org/checklist/S1",
        last_seen_checklist_url="https://ebird.org/checklist/S2",
        high_count_checklist_url="https://ebird.org/checklist/S3",
    )
    assert "Grey Teal" in html
    assert "15 checklists" in html
    assert "42 individuals" in html
    assert 'First seen: <a href="https://ebird.org/checklist/S1"' in html
    assert "10-Jan-2024</a>" in html
    assert 'Last seen: <a href="https://ebird.org/checklist/S2"' in html
    assert "20-Feb-2026</a>" in html
    assert 'High count: <a href="https://ebird.org/checklist/S3"' in html
    assert "05-Mar-2025</a> (8)" in html
    assert "pebird-map-banner__stats-primary" in html
    assert html.count("pebird-map-banner__stats-secondary") == 2


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
    assert "1 checklist" in html
    assert "1 individual" in html


def test_build_species_banner_html_is_div():
    html = build_species_banner_html("Test", 1, 1, 1)
    assert html.startswith("<div")
    assert html.endswith("</div>")


def test_build_species_banner_html_with_species_url():
    """When species_url is provided, display_name is wrapped in a link (refs #56)."""
    html = build_species_banner_html(
        "Grey Teal",
        2,
        5,
        3,
        species_url="https://ebird.org/species/grtea",
    )
    assert "Grey Teal" in html
    assert 'href="https://ebird.org/species/grtea"' in html
    assert "target=\"_blank\"" in html


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
    assert "pebird-map-popup__visited-block" in html
    assert "pebird-map-popup__visit-dates" in html
    assert "Seen:" not in html
    assert "popup-scroll-wrapper" in html


def test_build_location_popup_html_with_sightings():
    html = build_location_popup_html(
        "My Park", "L12345", "<a>visit1</a>", "<br>sighting1"
    )
    assert "Visited:" in html
    assert "Seen:" in html
    assert "sighting1" in html


def test_build_location_popup_html_with_lifer_species_section():
    html = build_location_popup_html(
        "My Park",
        "L12345",
        "<a>visit1</a>",
        sightings_html="<br>should_not_show",
        lifer_species_html="<br>Grey Teal",
    )
    assert "Visited:" in html
    assert "Lifers (first recorded here):" in html
    assert "Grey Teal" in html
    assert "Seen:" not in html
    assert "should_not_show" not in html


def test_build_location_popup_html_empty_visit_info():
    html = build_location_popup_html("Empty Spot", "L00000", "")
    assert "Empty Spot" in html
    assert "Visited:" in html


def test_build_location_popup_html_structure():
    html = build_location_popup_html("Loc", "L1", "visits")
    assert html.startswith('<div class="pebird-map-popup popup-scroll-wrapper"')
    assert html.endswith("</div></div>")
    assert "pebird-map-popup__location-heading" in html


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
    assert l1["has_species_match"]
    assert l1["is_lifer"]
    assert not l1["is_last_seen"]
    l2 = result[result["Location ID"] == "L2"].iloc[0]
    assert not l2["has_species_match"]
    l3 = result[result["Location ID"] == "L3"].iloc[0]
    assert l3["has_species_match"]
    assert l3["is_last_seen"]


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
