"""Unit tests for family map aggregation (refs #138)."""

import pandas as pd
import pytest

from explorer.core.family_map_compute import (
    DENSITY_BAND_LABELS,
    FamilyMapBannerMetrics,
    FamilyLocationPin,
    base_species_to_common_from_taxonomy,
    build_family_location_pins,
    compute_family_map_banner_metrics,
    families_recorded_alphabetically,
    family_density_band_index,
    family_density_band_label,
    filter_work_to_family,
    format_family_location_popup_html,
    highlight_species_choices_alphabetical,
    merge_taxonomy_detail_for_family_map,
    prepare_family_map_work_frame,
    taxonomy_species_count_for_family,
)


def _tiny_export_rows():
    """Two whistler species + subspecies at two locations; one duck elsewhere."""
    return pd.DataFrame(
        {
            "Submission ID": ["A", "A", "B", "C", "C"],
            "Location ID": ["L1", "L1", "L1", "L2", "L2"],
            "Location": ["Alpha", "Alpha", "Alpha", "Beta", "Beta"],
            "Latitude": [-35.0, -35.0, -35.0, -34.0, -34.0],
            "Longitude": [149.0, 149.0, 149.0, 150.0, 150.0],
            "Scientific Name": [
                "Pachycephala olivacea",
                "Pachycephala pectoralis glaucura",
                "Anas gracilis",
                "Pachycephala rufiventris",
                "Pachycephala rufiventris",
            ],
            "Common Name": [
                "Olive Whistler",
                "Golden Whistler (Eastern)",
                "Grey Teal",
                "Rufous Whistler",
                "Rufous Whistler",
            ],
            "Count": [1, 1, 2, 1, 1],
        }
    )


def _base_to_family_stub():
    return {
        "pachycephala olivacea": "Whistlers and Allies",
        "pachycephala pectoralis": "Whistlers and Allies",
        "anas gracilis": "Ducks, Geese, and Swans",
        "pachycephala rufiventris": "Whistlers and Allies",
    }


def test_density_bands_and_labels():
    assert family_density_band_index(0) == 0
    assert family_density_band_index(1) == 0
    assert family_density_band_index(2) == 1
    assert family_density_band_index(3) == 1
    assert family_density_band_index(4) == 2
    assert family_density_band_index(5) == 2
    assert family_density_band_index(6) == 3
    assert family_density_band_index(99) == 3
    assert family_density_band_label(1) == DENSITY_BAND_LABELS[0]
    assert family_density_band_label(4) == DENSITY_BAND_LABELS[2]


def test_prepare_work_frame_and_families_alphabetical():
    df = _tiny_export_rows()
    m = _base_to_family_stub()
    work = prepare_family_map_work_frame(df, m)
    assert not work.empty
    assert set(work["_family"].unique()) == {"Whistlers and Allies", "Ducks, Geese, and Swans"}
    fams = families_recorded_alphabetically(work)
    assert fams == ("Ducks, Geese, and Swans", "Whistlers and Allies")


def test_filter_work_to_family():
    df = _tiny_export_rows()
    work = prepare_family_map_work_frame(df, _base_to_family_stub())
    w = filter_work_to_family(work, "Whistlers and Allies")
    assert w["Location ID"].nunique() == 2
    assert w["_base"].nunique() == 3


def test_taxonomy_species_count_for_family():
    tax = pd.DataFrame(
        {
            "base_species": ["a a", "b b", "c c", "d d"],
            "group_name": ["G1", "G1", "G1", "G2"],
        }
    )
    assert taxonomy_species_count_for_family(tax, "G1") == 3
    assert taxonomy_species_count_for_family(tax, "G2") == 1
    assert taxonomy_species_count_for_family(tax, "None") == 0


def test_banner_metrics():
    df = _tiny_export_rows()
    work = prepare_family_map_work_frame(df, _base_to_family_stub())
    tax = pd.DataFrame(
        {
            "base_species": ["pachycephala olivacea", "pachycephala pectoralis", "pachycephala rufiventris", "x x"],
            "group_name": ["Whistlers and Allies"] * 4,
        }
    )
    m = compute_family_map_banner_metrics(work, "Whistlers and Allies", tax)
    assert isinstance(m, FamilyMapBannerMetrics)
    assert m.total_species_taxonomy == 4
    assert m.species_recorded_user == 3
    assert m.locations_with_records == 2


def test_highlight_choices_sorted_by_common_name():
    df = _tiny_export_rows()
    work = prepare_family_map_work_frame(df, _base_to_family_stub())
    wf = filter_work_to_family(work, "Whistlers and Allies")
    common = {
        "pachycephala olivacea": "Olive Whistler",
        "pachycephala pectoralis": "Golden Whistler",
        "pachycephala rufiventris": "Rufous Whistler",
    }
    pairs = highlight_species_choices_alphabetical(wf, common)
    labels = [p[0] for p in pairs]
    assert labels == ["Golden Whistler", "Olive Whistler", "Rufous Whistler"]


def test_build_family_location_pins_richness_and_popup_lines():
    df = _tiny_export_rows()
    work = prepare_family_map_work_frame(df, _base_to_family_stub())
    wf = filter_work_to_family(work, "Whistlers and Allies")
    pins = build_family_location_pins(wf, highlight_base_species=None)
    assert len(pins) == 2
    by_id = {p.location_id: p for p in pins}
    p1 = by_id["L1"]
    # Olive + Golden (Eastern) subspecies row → two base species
    assert p1.distinct_base_species_count == 2
    assert p1.density_band_index == 1
    assert "Golden Whistler (Eastern)" in p1.common_name_lines
    assert "Olive Whistler" in p1.common_name_lines
    p2 = by_id["L2"]
    assert p2.distinct_base_species_count == 1
    assert p2.density_band_index == 0


def test_build_family_location_pins_highlight():
    df = _tiny_export_rows()
    work = prepare_family_map_work_frame(df, _base_to_family_stub())
    wf = filter_work_to_family(work, "Whistlers and Allies")
    pins = build_family_location_pins(
        wf,
        highlight_base_species="pachycephala rufiventris",
    )
    by_id = {p.location_id: p for p in pins}
    assert by_id["L1"].highlight_match is False
    assert by_id["L2"].highlight_match is True


def test_build_family_location_pins_missing_columns():
    wf = pd.DataFrame({"Location ID": ["x"]})
    with pytest.raises(ValueError, match="missing columns"):
        build_family_location_pins(wf)


def test_merge_taxonomy_detail_for_family_map_smoke():
    tax = pd.DataFrame(
        {
            "scientific_name": ["Aa bb", "Cc dd"],
            "common_name": ["A b", "C d"],
            "species_code": ["aabb", "ccdd"],
            "taxon_order": [100.0, 200.0],
            "base_species": ["aa bb", "cc dd"],
        }
    )
    groups = [
        {
            "group_name": "G",
            "group_order": 1,
            "bounds": [(50.0, 250.0)],
        }
    ]
    merged = merge_taxonomy_detail_for_family_map(tax, groups)
    assert "group_name" in merged.columns
    assert merged["group_name"].iloc[0] == "G"


def test_base_species_to_common_from_taxonomy():
    tax = pd.DataFrame(
        {
            "base_species": ["aa bb", "cc dd"],
            "common_name": ["A", "C"],
        }
    )
    d = base_species_to_common_from_taxonomy(tax)
    assert d["aa bb"] == "A"
    assert d["cc dd"] == "C"


def test_format_family_location_popup_html_links():
    pin = FamilyLocationPin(
        location_id="L1",
        location_name="Test & Park",
        latitude=-35.0,
        longitude=149.0,
        distinct_base_species_count=2,
        density_band_index=1,
        common_name_lines=("Bird A", "Bird B"),
        highlight_match=False,
    )
    html = format_family_location_popup_html(
        pin,
        location_page_url="https://ebird.org/hotspot/L1",
        species_url_by_common={"Bird A": "https://ebird.org/species/foo"},
    )
    assert "Test &amp; Park" in html
    assert "hotspot" in html
    assert "Bird A" in html
    assert "species/foo" in html
    assert "Bird B" in html
