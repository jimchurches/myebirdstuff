"""Tests for :mod:`explorer.core.family_locations_geojson` + viewport helper."""

from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
from explorer.core.family_map_compute import FamilyLocationPin
from explorer.core.family_map_overlays import family_map_marker_style
from explorer.core.family_locations_geojson import build_family_locations_geojson_payload
from explorer.core.map_leaflet_viewport import family_leaflet_viewport_recipe
from explorer.core.settings_schema_defaults import MAP_MARKER_COLOUR_SCHEME_DEFAULT


def _sample_pins():
    return (
        FamilyLocationPin(
            location_id="L1",
            location_name="Site One",
            latitude=-35.0,
            longitude=149.0,
            distinct_base_species_count=2,
            density_band_index=1,
            common_name_lines=("A", "B"),
            highlight_match=False,
        ),
        FamilyLocationPin(
            location_id="L2",
            location_name="Site Two",
            latitude=-34.0,
            longitude=150.0,
            distinct_base_species_count=1,
            density_band_index=0,
            common_name_lines=("C",),
            highlight_match=True,
        ),
    )


def test_family_leaflet_viewport_single_point():
    vp = family_leaflet_viewport_recipe([[10.0, 20.0]])
    assert vp["v"] == 1
    assert vp["mode"] == "fit_bounds"
    assert vp["single_point"] is True


def test_family_leaflet_viewport_highlight_max_zoom():
    vp = family_leaflet_viewport_recipe([[10.0, 20.0], [11.0, 21.0]], highlight_framed=True)
    from explorer.app.streamlit.defaults import MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM_HIGHLIGHT

    assert vp["max_zoom"] == int(MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM_HIGHLIGHT)


def test_build_family_geojson_uses_species_url_by_common():
    pins = _sample_pins()
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    _rev, gj, _framing, _hl = build_family_locations_geojson_payload(
        pins,
        visit_marker_scheme=sch,
        location_page_url_fn=lambda lid: f"https://ebird.org/lifelist/{lid}",
        species_url_fn=lambda _c: None,
        species_url_by_common={"A": "https://ebird.org/species/aaa", "C": "https://ebird.org/species/ccc"},
        fit_bounds_highlight_only=False,
        revision_extra="{}",
    )
    feat_a = next(f for f in gj["features"] if f["properties"]["location_id"] == "L1")
    lines = feat_a["properties"]["family_popup_v1"]["species_lines"]
    by_name = {ln["name"]: ln["species_href"] for ln in lines}
    assert by_name["A"] == "https://ebird.org/species/aaa"
    assert by_name["B"] == ""
    feat_c = next(f for f in gj["features"] if f["properties"]["location_id"] == "L2")
    assert feat_c["properties"]["family_popup_v1"]["species_lines"][0]["species_href"] == "https://ebird.org/species/ccc"


def test_build_family_geojson_pins_and_highlight_framing():
    pins = _sample_pins()
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    rev, gj, framing, hl_framed = build_family_locations_geojson_payload(
        pins,
        visit_marker_scheme=sch,
        location_page_url_fn=lambda lid: f"https://ebird.org/lifelist/{lid}",
        species_url_fn=lambda _c: None,
        fit_bounds_highlight_only=True,
        revision_extra="{}",
    )
    assert rev is not None
    assert gj is not None
    assert len(gj["features"]) == 2
    assert hl_framed is True
    assert len(framing) == 1
    hl_feat = next(f for f in gj["features"] if f["properties"]["location_id"] == "L2")
    assert "family_popup_v1" in hl_feat["properties"]
    assert hl_feat["properties"]["family_popup_v1"]["v"] == 1
    assert len(hl_feat["properties"]["family_popup_v1"]["species_lines"]) == 1
    fill, stroke, _sw = family_map_marker_style(pins[1], style=sch)
    assert hl_feat["properties"]["circle_pin"]["fill_hex"] == fill
    assert hl_feat["properties"]["circle_pin"]["stroke_hex"] == stroke
    # Highlight pin drawn after normal (later feature = on top in Leaflet order).
    assert gj["features"][-1]["properties"]["location_id"] == "L2"
