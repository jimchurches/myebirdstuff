"""Tests for map_controller (refs #67)."""

from collections import OrderedDict

import pandas as pd

from personal_ebird_explorer.lifer_last_seen_prep import prepare_lifer_last_seen
from personal_ebird_explorer.map_controller import MapOverlayResult, build_species_overlay_map
from personal_ebird_explorer.species_logic import base_species_for_lifer


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
        date_filter_status="Date filter: Off",
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_()
    assert "All species" in html
    assert "1 checklist" in html


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
    assert "Sub-species included" in html
