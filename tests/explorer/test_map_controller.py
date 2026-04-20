"""Tests for :mod:`explorer.core.map_controller` / overlay map build."""

from collections import OrderedDict
from dataclasses import replace

import pandas as pd

from explorer.app.streamlit.defaults import (
    MAP_SPECIES_DEFAULT_CENTER_LAT,
    MAP_SPECIES_DEFAULT_CENTER_LON,
    MAP_SPECIES_DEFAULT_ZOOM,
    active_map_marker_colour_scheme,
)
from explorer.core.settings_schema_defaults import MAP_MARKER_COLOUR_SCHEME_DEFAULT
from explorer.core.lifer_last_seen_prep import prepare_lifer_last_seen
from explorer.core.map_controller import MapOverlayResult, build_species_overlay_map
from explorer.core.map_marker_colour_resolve import (
    normalize_marker_hex,
    resolve_lifer_overlay_pin_params,
    resolve_location_visit_colours,
    resolve_species_visit_pin,
)
from explorer.core.species_logic import base_species_for_lifer

from tests.colour_scheme_test_utils import (
    BUNDLED_COLOUR_SCHEME_INDICES,
    first_bundled_scheme_index_with_nine_cluster_tiers,
    leaflet_rgb_csv_from_hex_rrggbb,
)


def _minimal_map_df():
    return pd.DataFrame(
        {
            "Submission ID": ["S1"],
            "Date": [pd.Timestamp("2025-01-01")],
            "Time": ["06:15"],
            "datetime": [pd.Timestamp("2025-01-01 06:15")],
            "Count": [3],
            "Location ID": ["L1"],
            "Location": ["Test Location"],
            "Scientific Name": ["Anas gracilis"],
            "Common Name": ["Grey Teal"],
            "Latitude": [-35.0],
            "Longitude": [149.0],
            "Protocol": ["Traveling"],
            "Duration (Min)": [30],
            "Distance Traveled (km)": [1.5],
            "All Obs Reported": [1],
            "Number of Observers": [2],
        }
    )


def _common_kwargs(df, *, visit_marker_scheme=None):
    if visit_marker_scheme is None:
        visit_marker_scheme = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    location_data = df[["Location ID", "Location", "Latitude", "Longitude"]].drop_duplicates()
    records_by_loc = {lid: grp for lid, grp in df.groupby("Location ID")}
    prep = prepare_lifer_last_seen(df, base_species_fn=base_species_for_lifer)
    return dict(
        df=df,
        location_data=location_data,
        records_by_loc=records_by_loc,
        effective_location_data=location_data,
        effective_records_by_loc=records_by_loc,
        effective_totals=(df["Submission ID"].nunique(), 1, 3),
        effective_use_full=False,
        lifer_lookup_df=prep.lifer_lookup_df,
        true_lifer_locations=prep.true_lifer_locations,
        true_last_seen_locations=prep.true_last_seen_locations,
        true_lifer_locations_taxon=prep.true_lifer_locations_taxon,
        true_last_seen_locations_taxon=prep.true_last_seen_locations_taxon,
        popup_html_cache={},
        filtered_by_loc_cache=OrderedDict(),
        visit_marker_scheme=visit_marker_scheme,
    )


def test_no_sightings_returns_warning():
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="Xyz abcensis",
        selected_common_name="",
    )
    assert isinstance(r, MapOverlayResult)
    assert r.map is None
    assert r.warning is not None
    assert "No sightings" in r.warning
    assert "Xyz abcensis" in r.warning


def test_all_species_builds_map_with_banner():
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_()
    assert "All species" in html
    assert "1 checklist" in html
    assert "Date filter" not in html


def test_species_filter_visit_overlay_uses_scheme_hex():
    """Species-filtered map uses :class:`MapMarkerColourScheme` (no separate named-colour path).

    The minimal dataframe is both a species match and the lifer site for the taxon; visit-map code
    assigns **lifer** role first, so the rendered pin uses lifer stroke/fill from the scheme.
    """
    df = _minimal_map_df()
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="Anas gracilis",
        selected_common_name="Grey Teal",
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map.get_root().render().lower()
    stroke, _fill, _, _, _ = resolve_species_visit_pin(sch, "lifer")
    # Edge colour is reliably present in the rendered document; fill may be inlined differently.
    assert stroke.replace("#", "").lower() in html


def test_all_locations_visit_marker_scheme_uses_hex_from_scheme():
    df = _minimal_map_df()
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    vf, ve = resolve_location_visit_colours(sch)
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map.get_root().render().lower()
    for hx in (vf, ve):
        assert hx.replace("#", "").lower() in html


def test_all_locations_cluster_markers_use_scheme_cluster_tier_fills_when_present():
    idx = first_bundled_scheme_index_with_nine_cluster_tiers()
    assert idx is not None
    sch = active_map_marker_colour_scheme(idx)
    tier = sch.all_locations.cluster.tier_icon_hex
    assert tier is not None
    small_fill = normalize_marker_hex(str(tier[0]), channel="fill")
    expected_rgb = leaflet_rgb_csv_from_hex_rrggbb(small_fill)
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df, visit_marker_scheme=sch),
        selected_species="",
        cluster_all_locations=True,
    )
    assert r.warning is None
    assert r.map is not None
    # ``_repr_html_`` may omit iframe script bodies; full root includes cluster iconCreateFunction.
    full = r.map.get_root().render().lower()
    assert "marker-cluster" in full
    # Custom cluster icons use rgba(...) from hex + marker_cluster_*_opacity (not raw #hex in HTML).
    assert "rgba(" in full
    assert expected_rgb in full


def test_all_locations_cluster_markers_apply_tier_border_colours_when_present():
    df = _minimal_map_df()
    base = active_map_marker_colour_scheme(BUNDLED_COLOUR_SCHEME_INDICES[-1])
    scheme_with_border = replace(
        base,
        all_locations=replace(
            base.all_locations,
            cluster=replace(
                base.all_locations.cluster,
                tier_icon_hex=(
                    "#EFE6EE",
                    "#4b2e46",
                    "#e0ccdd",
                    "#E0CCDD",
                    "#5b3655",
                    "#cfb4cc",
                    "#CFB4CC",
                    "#6a3f64",
                    "#b78fb3",
                ),
            ),
        ),
    )
    r = build_species_overlay_map(
        **_common_kwargs(df, visit_marker_scheme=scheme_with_border),
        selected_species="",
        cluster_all_locations=True,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_().lower()
    assert "border:2px solid" in html
    assert "rgba(" in html
    assert "75,46,70" in html


def test_species_view_no_selection_hide_only_empty_map():
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
        map_view_mode="species",
        hide_non_matching_locations=True,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_()
    assert "Select a species in the sidebar" in html
    assert "All species" not in html
    assert "All locations" not in html


def test_species_view_no_selection_empty_even_when_hide_filter_off():
    """Species tab with no pick is empty — no fallback to the all-locations map (refs #147)."""
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
        map_view_mode="species",
        hide_non_matching_locations=False,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_()
    assert "Select a species in the sidebar" in html
    assert "All species" not in html


def test_species_view_no_selection_uses_fixed_default_center_and_zoom():
    df = _minimal_map_df()
    # Deliberately offset dataset from default blank-map centre to verify fixed viewport values are used.
    df["Latitude"] = [-10.0]
    df["Longitude"] = [110.0]
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
        map_view_mode="species",
        hide_non_matching_locations=False,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map.get_root().render()
    assert f"center: [{float(MAP_SPECIES_DEFAULT_CENTER_LAT)}, {float(MAP_SPECIES_DEFAULT_CENTER_LON)}]" in html
    assert f"\"zoom\": {int(MAP_SPECIES_DEFAULT_ZOOM)}" in html


def test_species_selection_applies_fit_bounds_to_species_extent():
    df = pd.DataFrame(
        {
            "Submission ID": ["S1", "S2", "S3"],
            "Date": [pd.Timestamp("2025-01-01")] * 3,
            "Time": ["06:15", "06:20", "06:25"],
            "datetime": [
                pd.Timestamp("2025-01-01 06:15"),
                pd.Timestamp("2025-01-01 06:20"),
                pd.Timestamp("2025-01-01 06:25"),
            ],
            "Count": [1, 2, 3],
            "Location ID": ["L1", "L2", "L3"],
            "Location": ["A", "B", "C"],
            "Scientific Name": ["Anas gracilis", "Anas gracilis", "Cygnus atratus"],
            "Common Name": ["Grey Teal", "Grey Teal", "Black Swan"],
            "Latitude": [-35.0, -33.0, -12.0],
            "Longitude": [149.0, 151.0, 131.0],
            "Protocol": ["Traveling"] * 3,
            "Duration (Min)": [30, 30, 30],
            "Distance Traveled (km)": [1.5, 1.5, 1.5],
            "All Obs Reported": [1, 1, 1],
            "Number of Observers": [2, 2, 2],
        }
    )
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="Anas gracilis",
        selected_common_name="Grey Teal",
        map_view_mode="species",
        hide_non_matching_locations=False,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map.get_root().render()
    assert "fitBounds(" in html


def test_lifer_map_mode_uses_visit_marker_scheme_when_provided():
    df = _minimal_map_df()
    kwargs = _common_kwargs(df)
    sch = kwargs["visit_marker_scheme"]
    full_loc = kwargs["location_data"]
    r = build_species_overlay_map(
        **kwargs,
        selected_species="",
        map_view_mode="lifers",
        full_location_data=full_loc,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map.get_root().render().lower()
    lf_stroke, lf_fill, *_ = resolve_lifer_overlay_pin_params(sch)
    assert lf_stroke.replace("#", "").lower() in html
    assert lf_fill.replace("#", "").lower() in html


def test_lifer_map_mode_builds_banner():
    df = _minimal_map_df()
    kwargs = _common_kwargs(df)
    full_loc = kwargs["location_data"]
    r = build_species_overlay_map(
        **kwargs,
        selected_species="",
        map_view_mode="lifers",
        full_location_data=full_loc,
    )
    assert r.warning is None
    assert r.map is not None
    html_root = r.map.get_root().render()
    assert "fitBounds(" in html_root
    html = r.map._repr_html_()
    assert "Lifer locations" in html
    assert "+ subspecies" not in html
    assert " lifer " in html or "1 lifer" in html
    # refs #104: lifer popup should be simplified (no visit history noise).
    assert "Visited:" not in html
    assert "Lifers (first recorded here):" not in html
    assert "Grey Teal : 2025-01-01" in html
    assert "ebird.org/checklist/S1" in html

    r2 = build_species_overlay_map(
        **kwargs,
        selected_species="",
        map_view_mode="lifers",
        full_location_data=full_loc,
        show_subspecies_lifers=True,
    )
    assert r2.warning is None
    assert r2.map is not None
    html2 = r2.map.get_root().render()
    assert "fitBounds(" in html2
    # Subspecies toggle does not change framing (base lifer extent only); bounds call should match.
    assert html_root.split("fitBounds(", 1)[1].split(");", 1)[0] == html2.split("fitBounds(", 1)[1].split(");", 1)[0]
    assert "Lifer locations + subspecies" in html2
    assert "0 subspecies lifers" in html2.lower()
    assert "Visited:" not in html2
