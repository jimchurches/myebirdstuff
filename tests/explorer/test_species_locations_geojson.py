"""Tests for :mod:`explorer.core.species_locations_geojson` + viewport helper."""

import pandas as pd

from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
from explorer.core.lifer_last_seen_prep import prepare_lifer_last_seen
from explorer.core.map_leaflet_viewport import species_leaflet_viewport_recipe
from explorer.core.map_prep import prepare_all_locations_map_context
from explorer.core.settings_schema_defaults import MAP_MARKER_COLOUR_SCHEME_DEFAULT
from explorer.core.species_locations_geojson import (
    build_species_locations_geojson_payload,
    compute_species_map_banner_fields,
)
from explorer.core.species_logic import base_species_for_lifer, filter_species


def test_species_leaflet_viewport_single_point():
    vp = species_leaflet_viewport_recipe([[10.0, 20.0]])
    assert vp["v"] == 1
    assert vp["mode"] == "fit_bounds"
    assert vp["single_point"] is True


def test_species_leaflet_viewport_blank_center_zoom():
    vp = species_leaflet_viewport_recipe(
        [],
        blank_viewport_recipe={"mode": "center_zoom", "center": [1.0, 2.0], "zoom": 5},
    )
    assert vp["mode"] == "center_zoom"
    assert vp["center"] == [1.0, 2.0]
    assert vp["zoom"] == 5


def test_build_species_geojson_with_match_and_background_pin():
    df = pd.DataFrame(
        {
            "Submission ID": ["S1", "S2"],
            "Date": [pd.Timestamp("2024-06-01"), pd.Timestamp("2024-07-01")],
            "Time": ["08:00", "09:00"],
            "datetime": [
                pd.Timestamp("2024-06-01 08:00"),
                pd.Timestamp("2024-07-01 09:00"),
            ],
            "Location ID": ["L1", "L2"],
            "Location": ["Patch A", "Patch B"],
            "Latitude": [-33.0, -34.0],
            "Longitude": [151.0, 152.0],
            "Scientific Name": ["Anas gracilis", "Corvus brachyrhynchos"],
            "Common Name": ["Grey Teal", "American Crow"],
            "Count": [2, 1],
        }
    )
    ctx = prepare_all_locations_map_context(df, full_df=df)
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    rev, gj, warn, framing, roles = build_species_locations_geojson_payload(
        df=ctx["df"],
        location_data=ctx["location_data"],
        records_by_loc=ctx["records_by_loc"],
        selected_species="Anas gracilis",
        true_lifer_locations=ctx["true_lifer_locations"],
        true_lifer_locations_taxon=ctx["true_lifer_locations_taxon"],
        true_last_seen_locations=ctx["true_last_seen_locations"],
        true_last_seen_locations_taxon=ctx["true_last_seen_locations_taxon"],
        hide_non_matching_locations=False,
        mark_lifer=False,
        mark_last_seen=False,
        base_species_fn=base_species_for_lifer,
        visit_marker_scheme=sch,
        popup_visit_dates_ascending=True,
        revision_extra="{}",
    )
    assert warn is None
    assert rev is not None
    assert gj is not None
    assert len(gj["features"]) == 2
    props_match = next(
        f["properties"]
        for f in gj["features"]
        if f["properties"]["location_id"] == "L1"
    )
    assert "species_popup_v1" in props_match
    assert props_match["species_popup_v1"]["v"] == 1
    assert "circle_pin" in props_match
    props_bg = next(
        f["properties"]
        for f in gj["features"]
        if f["properties"]["location_id"] == "L2"
    )
    assert "popup_v1" in props_bg
    assert "visited" in props_bg["popup_v1"]
    assert len(framing) == 1
    assert "Species" in roles
    assert "Locations" in roles


def _species_map_df() -> pd.DataFrame:
    """Three locations: Grey Teal at L1/L3, American Crow at L2 only."""
    return pd.DataFrame(
        {
            "Submission ID": ["S1", "S2", "S3"],
            "Date": [
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-06-15"),
                pd.Timestamp("2024-12-01"),
            ],
            "Time": ["08:00", "09:00", "10:00"],
            "datetime": [
                pd.Timestamp("2024-01-01 08:00"),
                pd.Timestamp("2024-06-15 09:00"),
                pd.Timestamp("2024-12-01 10:00"),
            ],
            "Location ID": ["L1", "L2", "L3"],
            "Location": ["Patch A", "Patch B", "Patch C"],
            "Latitude": [-33.0, -34.0, -35.0],
            "Longitude": [151.0, 152.0, 153.0],
            "Scientific Name": [
                "Anas gracilis",
                "Corvus brachyrhynchos",
                "Anas gracilis",
            ],
            "Common Name": ["Grey Teal", "American Crow", "Grey Teal"],
            "Count": [2, 5, 3],
        }
    )


def _species_payload_kwargs(ctx, *, hide_non_matching_locations=False, **overrides):
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    base = {
        "df": ctx["df"],
        "location_data": ctx["location_data"],
        "records_by_loc": ctx["records_by_loc"],
        "selected_species": "Anas gracilis",
        "true_lifer_locations": ctx["true_lifer_locations"],
        "true_lifer_locations_taxon": ctx["true_lifer_locations_taxon"],
        "true_last_seen_locations": ctx["true_last_seen_locations"],
        "true_last_seen_locations_taxon": ctx["true_last_seen_locations_taxon"],
        "hide_non_matching_locations": hide_non_matching_locations,
        "mark_lifer": False,
        "mark_last_seen": False,
        "base_species_fn": base_species_for_lifer,
        "visit_marker_scheme": sch,
        "popup_visit_dates_ascending": True,
        "revision_extra": "{}",
    }
    base.update(overrides)
    return base


def test_compute_species_map_banner_fields():
    df = _species_map_df()
    prep = prepare_lifer_last_seen(df, base_species_fn=base_species_for_lifer)
    filtered = filter_species(df, "Anas gracilis")

    fields = compute_species_map_banner_fields(
        filtered=filtered,
        selected_species="Anas gracilis",
        selected_common_name="Grey Teal",
        lifer_lookup_df=prep.lifer_lookup_df,
        base_species_fn=base_species_for_lifer,
    )

    assert fields["display_name"] == "Grey Teal"
    assert fields["n_checklists"] == 2
    assert fields["n_individuals"] == 5
    assert fields["high_count"] == 3
    assert fields["first_seen_date"] == "01-Jan-2024"
    assert fields["last_seen_date"] == "01-Dec-2024"
    assert fields["high_count_date"] == "01-Dec-2024"
    assert fields["first_seen_checklist_url"] == "https://ebird.org/checklist/S1"
    assert fields["last_seen_checklist_url"] == "https://ebird.org/checklist/S3"
    assert fields["high_count_checklist_url"] == "https://ebird.org/checklist/S3"


def test_build_species_geojson_hide_non_matching_locations():
    ctx = prepare_all_locations_map_context(_species_map_df(), full_df=_species_map_df())
    _, gj_show, _, framing_show, roles_show = build_species_locations_geojson_payload(
        **_species_payload_kwargs(ctx, hide_non_matching_locations=False)
    )
    _, gj_hide, _, framing_hide, roles_hide = build_species_locations_geojson_payload(
        **_species_payload_kwargs(ctx, hide_non_matching_locations=True)
    )

    assert len(gj_show["features"]) == 3
    assert {f["properties"]["location_id"] for f in gj_show["features"]} == {"L1", "L2", "L3"}
    assert len(framing_show) == 2
    assert "Locations" in roles_show

    assert len(gj_hide["features"]) == 2
    assert {f["properties"]["location_id"] for f in gj_hide["features"]} == {"L1", "L3"}
    assert len(framing_hide) == 2
    assert "Locations" not in roles_hide


def test_build_species_geojson_lifer_and_last_seen_pin_roles():
    df = pd.DataFrame(
        {
            "Submission ID": ["S1", "S2", "S3", "S4"],
            "Date": [
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-06-01"),
                pd.Timestamp("2024-12-01"),
                pd.Timestamp("2024-03-01"),
            ],
            "Time": ["08:00"] * 4,
            "datetime": [
                pd.Timestamp("2024-01-01 08:00"),
                pd.Timestamp("2024-06-01 08:00"),
                pd.Timestamp("2024-12-01 08:00"),
                pd.Timestamp("2024-03-01 08:00"),
            ],
            "Location ID": ["L1", "L2", "L3", "L4"],
            "Location": ["Patch A", "Patch B", "Patch C", "Patch D"],
            "Latitude": [-33.0, -34.0, -35.0, -36.0],
            "Longitude": [151.0, 152.0, 153.0, 154.0],
            "Scientific Name": [
                "Anas gracilis",
                "Anas gracilis",
                "Anas gracilis",
                "Corvus brachyrhynchos",
            ],
            "Common Name": ["Grey Teal"] * 3 + ["American Crow"],
            "Count": [1, 2, 3, 1],
        }
    )
    ctx = prepare_all_locations_map_context(df, full_df=df)
    _, gj, warn, framing, roles = build_species_locations_geojson_payload(
        **_species_payload_kwargs(
            ctx,
            hide_non_matching_locations=False,
            mark_lifer=True,
            mark_last_seen=True,
        )
    )
    assert warn is None
    by_loc = {f["properties"]["location_id"]: f["properties"] for f in gj["features"]}

    assert by_loc["L1"]["pin_role"] == "lifer"
    assert "species_popup_v1" in by_loc["L1"]
    assert by_loc["L2"]["pin_role"] == "species"
    assert by_loc["L3"]["pin_role"] == "last_seen"
    assert by_loc["L4"]["pin_role"] == "default"
    assert "popup_v1" in by_loc["L4"]
    assert "species_popup_v1" not in by_loc["L4"]

    assert roles == {"Lifer", "Last seen", "Species", "Locations"}
    assert len(framing) == 3
