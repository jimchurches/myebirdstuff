"""Tests for :mod:`explorer.core.map_controller` / overlay map build."""

from collections import OrderedDict
from dataclasses import replace

import pandas as pd

from explorer.app.streamlit.defaults import MAP_MARKER_COLOUR_SCHEME_1, MAP_MARKER_COLOUR_SCHEME_3
from explorer.core.lifer_last_seen_prep import prepare_lifer_last_seen
from explorer.core.map_controller import MapOverlayResult, build_species_overlay_map
from explorer.core.species_logic import base_species_for_lifer


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


def _common_kwargs(df):
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


def test_all_locations_visit_marker_scheme_uses_hex_from_scheme():
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
        visit_marker_scheme=MAP_MARKER_COLOUR_SCHEME_1,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_().lower()
    assert "008000" in html
    assert "d3d3d3" in html


def test_all_locations_cluster_markers_use_scheme_cluster_tier_fills_when_present():
    df = _minimal_map_df()
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
        cluster_all_locations=True,
        visit_marker_scheme=MAP_MARKER_COLOUR_SCHEME_3,
    )
    assert r.warning is None
    assert r.map is not None
    # ``_repr_html_`` may omit iframe script bodies; full root includes cluster iconCreateFunction.
    full = r.map.get_root().render().lower()
    assert "marker-cluster" in full
    # Custom cluster icons use rgba(...) from hex + marker_cluster_*_opacity (not raw #hex in HTML).
    assert "rgba(" in full
    # Scheme 3 small-tier fill is ``#DFCEDE`` → ``rgb(223,206,222)`` in the custom icon JS.
    assert "223,206,222" in full


def test_all_locations_cluster_markers_apply_tier_border_colours_when_present():
    df = _minimal_map_df()
    scheme_with_border = replace(
        MAP_MARKER_COLOUR_SCHEME_3,
        marker_cluster_colours_hex=(
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
    )
    r = build_species_overlay_map(
        **_common_kwargs(df),
        selected_species="",
        cluster_all_locations=True,
        visit_marker_scheme=scheme_with_border,
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


def test_species_view_no_selection_show_all_matches_all_locations_banner():
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
    assert "All species" in html
    assert "1 checklist" in html


def test_lifer_map_mode_uses_visit_marker_scheme_when_provided():
    df = _minimal_map_df()
    kwargs = _common_kwargs(df)
    full_loc = kwargs["location_data"]
    r = build_species_overlay_map(
        **kwargs,
        selected_species="",
        map_view_mode="lifers",
        full_location_data=full_loc,
        visit_marker_scheme=MAP_MARKER_COLOUR_SCHEME_1,
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_().lower()
    assert "800080" in html
    assert "ffff00" in html


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
    html = r.map._repr_html_()
    assert "Lifer locations" in html
    assert " lifer " in html or "1 lifer" in html
    assert "Sub-species included" not in html
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
    assert "separate pin only when no species lifer" in html2
    assert "Visited:" not in html2
