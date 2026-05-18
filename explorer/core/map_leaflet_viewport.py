"""Leaflet map viewport recipes and All locations marker/cluster styling.

Used by production GeoJSON builders and Streamlit prep (no Folium).
"""

from __future__ import annotations

import json
import math
from typing import Any, Hashable

import pandas as pd

from explorer.app.streamlit.defaults import (
    MAP_ALL_LOCATIONS_CENTRE_OF_GRAVITY_ZOOM,
    MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM,
    MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX,
    MAP_ALL_LOCATIONS_FOCUSED_MIN_OBSERVATIONS_PER_COUNTRY,
    MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_HIGH,
    MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_LOW,
    MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM,
    MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM,
    MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM_HIGHLIGHT,
    MAP_FAMILY_MAP_FIT_BOUNDS_PADDING_PX,
    MAP_GO_TO_GPS_MAX_ZOOM,
    MAP_LIFER_MAP_FIT_BOUNDS_MAX_ZOOM,
    MAP_LIFER_MAP_FIT_BOUNDS_PADDING_PX,
    MAP_LIFER_MAP_SINGLE_POINT_ZOOM,
    MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT,
    MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT,
    MAP_SPECIES_DEFAULT_CENTER_LAT,
    MAP_SPECIES_DEFAULT_CENTER_LON,
    MAP_SPECIES_DEFAULT_ZOOM,
    MAP_SPECIES_FIT_BOUNDS_MAX_ZOOM,
    MAP_SPECIES_FIT_BOUNDS_PADDING_PX,
    MAP_SPECIES_SINGLE_POINT_ZOOM,
    MapMarkerColourScheme,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    coordinate_pairs_focused_viewport,
    coordinate_pairs_for_viewport,
    mean_center_from_pairs,
    observation_row_counts_by_country_key,
)
from explorer.core.map_marker_colour_resolve import (
    is_valid_hex_colour,
    normalize_marker_hex,
    resolve_location_visit_colours,
)

def lifer_leaflet_viewport_recipe(framing_pairs: list[list[float]]) -> dict[str, Any]:
    """Camera recipe ``v1`` for the Lifer Leaflet iframe — matches ``build_lifer_overlay_map`` fit."""
    if not framing_pairs:
        return {
            "v": 1,
            "mode": "center_zoom",
            "center": [20.0, 0.0],
            "zoom": 2,
        }
    pad = int(MAP_LIFER_MAP_FIT_BOUNDS_PADDING_PX)
    max_z = int(MAP_LIFER_MAP_FIT_BOUNDS_MAX_ZOOM)
    if len(framing_pairs) == 1:
        la, lo = float(framing_pairs[0][0]), float(framing_pairs[0][1])
        return {
            "v": 1,
            "mode": "fit_bounds",
            "single_point": True,
            "lat": la,
            "lon": lo,
            "epsilon_delta": 0.02,
            "padding_px": pad,
            "max_zoom": int(MAP_LIFER_MAP_SINGLE_POINT_ZOOM),
        }
    return {
        "v": 1,
        "mode": "fit_bounds",
        "single_point": False,
        "pairs": [[float(p[0]), float(p[1])] for p in framing_pairs],
        "padding_px": pad,
        "max_zoom": max_z,
    }



def all_locations_leaflet_viewport_recipe(
    *,
    effective_location_data: pd.DataFrame,
    df: pd.DataFrame,
    all_locations_scope: str,
    all_locations_location_country: dict[Hashable, str] | None,
    go_to_gps_pin: tuple[float, float] | None,
) -> dict[str, Any]:
    """Serializable camera recipe for the All locations Leaflet component (Folium ``build_visit_overlay_map`` parity).

    Keys are JSON-stable for ``revision_extra`` hashing. ``v`` is ``1`` for forward compatibility.
    """
    loc_c = all_locations_location_country or {}
    scope = (all_locations_scope or ALL_LOCATIONS_SCOPE_FOCUSED).strip()

    def _mean_center() -> list[float]:
        lat = float(effective_location_data["Latitude"].mean())
        lon = float(effective_location_data["Longitude"].mean())
        if not (math.isfinite(lat) and math.isfinite(lon)):
            return [float(MAP_SPECIES_DEFAULT_CENTER_LAT), float(MAP_SPECIES_DEFAULT_CENTER_LON)]
        return [lat, lon]

    if go_to_gps_pin is not None and len(go_to_gps_pin) == 2:
        lat, lon = float(go_to_gps_pin[0]), float(go_to_gps_pin[1])
        return {
            "v": 1,
            "mode": "go_to_gps",
            "lat": lat,
            "lon": lon,
            "padding_px": int(MAP_SPECIES_FIT_BOUNDS_PADDING_PX),
            "epsilon_delta": 0.02,
            "max_zoom": int(MAP_GO_TO_GPS_MAX_ZOOM),
        }

    all_loc_pairs: list[list[float]] = []
    if scope == ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY:
        all_loc_pairs = coordinate_pairs_for_viewport(
            effective_location_data,
            location_id_to_country=loc_c,
            focus_country="",
        )
        mc = mean_center_from_pairs(all_loc_pairs)
        center = [float(mc[0]), float(mc[1])] if mc else _mean_center()
        return {
            "v": 1,
            "mode": "center_zoom",
            "center": center,
            "zoom": int(MAP_ALL_LOCATIONS_CENTRE_OF_GRAVITY_ZOOM),
        }

    if scope == ALL_LOCATIONS_SCOPE_FOCUSED:
        _min_c = int(MAP_ALL_LOCATIONS_FOCUSED_MIN_OBSERVATIONS_PER_COUNTRY)
        _obs_by_c = (
            observation_row_counts_by_country_key(df)
            if _min_c > 0
            else {}
        )
        all_loc_pairs = coordinate_pairs_focused_viewport(
            effective_location_data,
            location_id_to_country=loc_c,
            observation_counts_by_country=_obs_by_c,
            quantile_low=MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_LOW,
            quantile_high=MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_HIGH,
            min_observations_full_country=_min_c,
        )
    else:
        fc = "" if scope == ALL_LOCATIONS_FRAMING_FIT_ALL else scope
        all_loc_pairs = coordinate_pairs_for_viewport(
            effective_location_data,
            location_id_to_country=loc_c,
            focus_country=fc,
        )
        if fc and not all_loc_pairs:
            all_loc_pairs = coordinate_pairs_for_viewport(
                effective_location_data,
                location_id_to_country=loc_c,
                focus_country="",
            )

    should_fit = scope != ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY and bool(all_loc_pairs)
    if not should_fit:
        c = _mean_center()
        return {"v": 1, "mode": "center_zoom", "center": c, "zoom": 5}

    pad = int(MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX)
    max_z = int(MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM)
    if len(all_loc_pairs) == 1:
        la, lo = float(all_loc_pairs[0][0]), float(all_loc_pairs[0][1])
        return {
            "v": 1,
            "mode": "fit_bounds",
            "single_point": True,
            "lat": la,
            "lon": lo,
            "epsilon_delta": 0.02,
            "padding_px": pad,
            "max_zoom": int(MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM),
        }
    return {
        "v": 1,
        "mode": "fit_bounds",
        "single_point": False,
        "pairs": [[float(p[0]), float(p[1])] for p in all_loc_pairs],
        "padding_px": pad,
        "max_zoom": max_z,
    }


def species_leaflet_viewport_recipe(
    framing_pairs: list[list[float]],
    *,
    go_to_gps_pin: tuple[float, float] | None = None,
    blank_viewport_recipe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Camera recipe ``v1`` for Species locations Leaflet iframe.

    *blank_viewport_recipe* — session recipe when no species is selected (parity with Folium blank map).
    *framing_pairs* — species-matching pin coordinates when a species is selected.
    """
    if go_to_gps_pin is not None and len(go_to_gps_pin) == 2:
        lat, lon = float(go_to_gps_pin[0]), float(go_to_gps_pin[1])
        return {
            "v": 1,
            "mode": "go_to_gps",
            "lat": lat,
            "lon": lon,
            "padding_px": int(MAP_SPECIES_FIT_BOUNDS_PADDING_PX),
            "epsilon_delta": 0.02,
            "max_zoom": int(MAP_GO_TO_GPS_MAX_ZOOM),
        }

    if not framing_pairs:
        recipe = blank_viewport_recipe if isinstance(blank_viewport_recipe, dict) else {}
        mode = str(recipe.get("mode", "")).strip().lower()
        if mode == "fit_bounds":
            pairs_raw = recipe.get("pairs")
            pairs_list = pairs_raw if isinstance(pairs_raw, list) else []
            pairs = [
                [float(p[0]), float(p[1])]
                for p in pairs_list
                if isinstance(p, (list, tuple)) and len(p) == 2
            ]
            if pairs:
                pad = int(recipe.get("padding_px", MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX))
                max_z = int(recipe.get("max_zoom", MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM))
                if len(pairs) == 1:
                    la, lo = float(pairs[0][0]), float(pairs[0][1])
                    return {
                        "v": 1,
                        "mode": "fit_bounds",
                        "single_point": True,
                        "lat": la,
                        "lon": lo,
                        "epsilon_delta": 0.02,
                        "padding_px": pad,
                        "max_zoom": int(
                            recipe.get("single_point_zoom", MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM)
                        ),
                    }
                return {
                    "v": 1,
                    "mode": "fit_bounds",
                    "single_point": False,
                    "pairs": pairs,
                    "padding_px": pad,
                    "max_zoom": max_z,
                }
        center = recipe.get("center")
        if isinstance(center, (list, tuple)) and len(center) == 2:
            c_lat, c_lon = float(center[0]), float(center[1])
        else:
            c_lat = float(MAP_SPECIES_DEFAULT_CENTER_LAT)
            c_lon = float(MAP_SPECIES_DEFAULT_CENTER_LON)
        zoom = int(recipe.get("zoom", MAP_SPECIES_DEFAULT_ZOOM))
        return {
            "v": 1,
            "mode": "center_zoom",
            "center": [c_lat, c_lon],
            "zoom": zoom,
        }

    pad = int(MAP_SPECIES_FIT_BOUNDS_PADDING_PX)
    max_z = int(MAP_SPECIES_FIT_BOUNDS_MAX_ZOOM)
    if len(framing_pairs) == 1:
        la, lo = float(framing_pairs[0][0]), float(framing_pairs[0][1])
        return {
            "v": 1,
            "mode": "fit_bounds",
            "single_point": True,
            "lat": la,
            "lon": lo,
            "epsilon_delta": 0.02,
            "padding_px": pad,
            "max_zoom": int(MAP_SPECIES_SINGLE_POINT_ZOOM),
        }
    return {
        "v": 1,
        "mode": "fit_bounds",
        "single_point": False,
        "pairs": [[float(p[0]), float(p[1])] for p in framing_pairs],
        "padding_px": pad,
        "max_zoom": max_z,
    }


def family_leaflet_viewport_recipe(
    framing_pairs: list[list[float]],
    *,
    blank_viewport_recipe: dict[str, Any] | None = None,
    highlight_framed: bool = False,
) -> dict[str, Any]:
    """Camera recipe ``v1`` for Family locations Leaflet iframe.

    *blank_viewport_recipe* — session recipe when no family is selected or map is empty.
    *highlight_framed* — use closer max zoom when framing highlight-only pins (Folium parity).
    """
    if not framing_pairs:
        recipe = blank_viewport_recipe if isinstance(blank_viewport_recipe, dict) else {}
        mode = str(recipe.get("mode", "")).strip().lower()
        if mode == "fit_bounds":
            pairs_raw = recipe.get("pairs")
            pairs_list = pairs_raw if isinstance(pairs_raw, list) else []
            pairs = [
                [float(p[0]), float(p[1])]
                for p in pairs_list
                if isinstance(p, (list, tuple)) and len(p) == 2
            ]
            if pairs:
                pad = int(recipe.get("padding_px", MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX))
                max_z = int(recipe.get("max_zoom", MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM))
                if len(pairs) == 1:
                    la, lo = float(pairs[0][0]), float(pairs[0][1])
                    return {
                        "v": 1,
                        "mode": "fit_bounds",
                        "single_point": True,
                        "lat": la,
                        "lon": lo,
                        "epsilon_delta": 0.02,
                        "padding_px": pad,
                        "max_zoom": int(
                            recipe.get("single_point_zoom", MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM)
                        ),
                    }
                return {
                    "v": 1,
                    "mode": "fit_bounds",
                    "single_point": False,
                    "pairs": pairs,
                    "padding_px": pad,
                    "max_zoom": max_z,
                }
        center = recipe.get("center")
        if isinstance(center, (list, tuple)) and len(center) == 2:
            c_lat, c_lon = float(center[0]), float(center[1])
        else:
            c_lat = float(MAP_SPECIES_DEFAULT_CENTER_LAT)
            c_lon = float(MAP_SPECIES_DEFAULT_CENTER_LON)
        zoom = int(recipe.get("zoom", MAP_SPECIES_DEFAULT_ZOOM))
        return {
            "v": 1,
            "mode": "center_zoom",
            "center": [c_lat, c_lon],
            "zoom": zoom,
        }

    pad = int(MAP_FAMILY_MAP_FIT_BOUNDS_PADDING_PX)
    max_z = int(
        MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM_HIGHLIGHT
        if highlight_framed
        else MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM
    )
    if len(framing_pairs) == 1:
        la, lo = float(framing_pairs[0][0]), float(framing_pairs[0][1])
        return {
            "v": 1,
            "mode": "fit_bounds",
            "single_point": True,
            "lat": la,
            "lon": lo,
            "epsilon_delta": 0.02,
            "padding_px": pad,
            "max_zoom": max_z,
        }
    return {
        "v": 1,
        "mode": "fit_bounds",
        "single_point": False,
        "pairs": [[float(p[0]), float(p[1])] for p in framing_pairs],
        "padding_px": pad,
        "max_zoom": max_z,
    }



def _all_locations_marker_params_from_scheme(sch: MapMarkerColourScheme) -> tuple[str, str, int, int, float]:
    """Resolved fill, edge (stroke), radius (px), stroke weight, fill opacity for **All locations** view."""
    fill_c, edge = resolve_location_visit_colours(sch)
    g = sch.global_defaults
    al = sch.all_locations
    md = int(g.radius_px)
    loc = al.radius_px
    radius_px = clamp_map_marker_circle_radius_px(loc if loc is not None else md)
    sw_raw = al.stroke_weight
    if sw_raw is None:
        sw_raw = g.stroke_weight
    sw = max(1, int(sw_raw))
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(g, "fill_opacity", None),
        fallback=0.88,
    )
    legacy_fo = float(al.fill_opacity) if al.fill_opacity is not None else md_fo
    fo_override = al.fill_opacity_override
    fo = (
        clamp_map_marker_circle_fill_opacity(fo_override, fallback=legacy_fo)
        if fo_override is not None
        else legacy_fo
    )
    return fill_c, edge, radius_px, sw, fo


def _hex_to_rgba_css(hex_str: str, alpha: float, *, channel: str) -> str:
    """Convert ``#RRGGBB`` to ``rgba(r,g,b,a)`` for CSS (cluster icon inline styles)."""
    h = normalize_marker_hex(hex_str, channel=channel).lstrip("#")
    if len(h) < 6:
        h = (h + "000000")[:6]
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({r},{g},{b},{a})"


def _marker_cluster_root_background_reset_css() -> str:
    """CSS to clear default MarkerCluster *root* tier backgrounds.

    Leaflet.markercluster styles the **root** ``.marker-cluster-small|medium|large`` with a semi-transparent
    halo. Our ``iconCreateFunction`` must keep the stock DOM shape (**one** inner ``<div>`` wrapping
    ``<span>``) so ``.marker-cluster div`` rules still size/center the inner disc. We paint fill, border,
    and halo-like ring on that single inner div (``box-shadow`` ring) and make the root transparent so
    those defaults do not stack as a third offset circle.
    """
    return (
        "<style>"
        ".leaflet-marker-icon.marker-cluster.marker-cluster-small,"
        ".leaflet-marker-icon.marker-cluster.marker-cluster-medium,"
        ".leaflet-marker-icon.marker-cluster.marker-cluster-large"
        "{background:transparent!important;}"
        "</style>"
    )


def all_locations_cluster_icon_style_payload(sch: Any) -> dict[str, Any] | None:
    """JSON-serialisable cluster icon colours for Leaflet.markercluster (Folium ``iconCreateFunction`` parity).

    Returns ``fills_rgba``, ``borders_rgba``, ``halos_rgba`` (length-3 lists for small/medium/large tiers),
    ``border_width_px``, and ``halo_spread_px``. ``None`` when the scheme has no valid nine-tier hex tuple
    (caller falls back to plugin default green/orange styling).
    """

    def _cluster_colours_tuple() -> tuple[str, ...] | None:
        if sch is None:
            return None
        al = getattr(sch, "all_locations", None)
        if al is not None:
            cl = getattr(al, "cluster", None)
            if cl is not None:
                v = getattr(cl, "tier_icon_hex", None)
                if v is not None:
                    t = tuple(v) if isinstance(v, (tuple, list)) else None
                    if t is not None and len(t) == 9:
                        return t
        vals = getattr(sch, "marker_cluster_tier_icon_hex", None)
        if vals is None:
            return None
        t = tuple(vals) if isinstance(vals, (tuple, list)) else None
        return t if t is not None and len(t) == 9 else None

    def _resolve_cluster_colours() -> tuple[list[str], list[str], list[str]] | None:
        raw_tuple = _cluster_colours_tuple()
        if raw_tuple is None:
            return None
        vals = raw_tuple
        try:
            raw = tuple(str(vals[i]) for i in range(9))
        except Exception:
            return None
        if not all(is_valid_hex_colour(x) for x in raw):
            return None
        fills = [
            normalize_marker_hex(raw[0], channel="fill"),
            normalize_marker_hex(raw[3], channel="fill"),
            normalize_marker_hex(raw[6], channel="fill"),
        ]
        borders = [
            normalize_marker_hex(raw[1], channel="edge"),
            normalize_marker_hex(raw[4], channel="edge"),
            normalize_marker_hex(raw[7], channel="edge"),
        ]
        halos = [
            normalize_marker_hex(raw[2], channel="fill"),
            normalize_marker_hex(raw[5], channel="fill"),
            normalize_marker_hex(raw[8], channel="fill"),
        ]
        return fills, borders, halos

    if sch is None:
        return None
    col = _resolve_cluster_colours()
    if col is None:
        return None
    fills, borders, halos = col

    def _o(nested_attr: str, flat_attr: str, default: float) -> float:
        al = getattr(sch, "all_locations", None)
        if al is not None:
            cl = getattr(al, "cluster", None)
            if cl is not None:
                v = getattr(cl, nested_attr, None)
                if v is not None:
                    try:
                        return max(0.0, min(1.0, float(v)))
                    except (TypeError, ValueError):
                        pass
        v = getattr(sch, flat_attr, None)
        if v is None:
            return default
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return default

    def _oi(nested_attr: str, flat_attr: str, default: int, *, hi: int) -> int:
        al = getattr(sch, "all_locations", None)
        if al is not None:
            cl = getattr(al, "cluster", None)
            if cl is not None:
                v = getattr(cl, nested_attr, None)
                if v is not None:
                    try:
                        return max(0, min(hi, int(v)))
                    except (TypeError, ValueError):
                        pass
        v = getattr(sch, flat_attr, None)
        if v is None:
            return default
        try:
            return max(0, min(hi, int(v)))
        except (TypeError, ValueError):
            return default

    inner_a = _o("inner_fill_opacity", "marker_cluster_inner_fill_opacity", MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT)
    halo_a = _o("halo_opacity", "marker_cluster_halo_opacity", MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT)
    border_a = _o("border_opacity", "marker_cluster_border_opacity", MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT)
    spread = _oi("halo_spread_px", "marker_cluster_halo_spread_px", MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT, hi=24)
    bw = _oi("border_width_px", "marker_cluster_border_width_px", MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT, hi=8)

    fills_rgba = [_hex_to_rgba_css(fills[i], inner_a, channel="fill") for i in range(3)]
    borders_rgba = [_hex_to_rgba_css(borders[i], border_a, channel="edge") for i in range(3)]
    halos_rgba = [_hex_to_rgba_css(halos[i], halo_a, channel="fill") for i in range(3)]
    return {
        "fills_rgba": fills_rgba,
        "borders_rgba": borders_rgba,
        "halos_rgba": halos_rgba,
        "border_width_px": int(bw),
        "halo_spread_px": int(spread),
    }


def _marker_cluster_icon_create_function_from_scheme(
    sch: Any,
) -> str | None:
    """Return Leaflet.markercluster ``iconCreateFunction`` for configured cluster icon tier colours.

    Duck-typed: ``MapMarkerColourScheme`` (reads ``all_locations.cluster.*``),
    :class:`~explorer.presentation.design_map_preview.DesignMapPreviewConfig` (flat ``marker_cluster_*`` fields),
    or any object exposing the same attributes.

    Expects nine cluster tier colours (``tier_icon_hex`` or flat ``marker_cluster_tier_icon_hex``) with nine values
    ``(small_fill, small_border, small_halo, medium_fill, medium_border, medium_halo, large_fill, large_border, large_halo)``.
    If unset or invalid, returns ``None`` so Folium / Leaflet.markercluster defaults apply.
    """
    p = all_locations_cluster_icon_style_payload(sch)
    if p is None:
        return None
    fills_js = json.dumps(p["fills_rgba"])
    borders_js = json.dumps(p["borders_rgba"])
    halos_js = json.dumps(p["halos_rgba"])
    bw = int(p["border_width_px"])
    spread = int(p["halo_spread_px"])
    # One inner <div> only (same as plugin default HTML). Halo is a box-shadow ring; nested divs break
    # .marker-cluster div { width/height/margin } and look offset / triple-stacked.
    return (
        "function(cluster) {"
        "var count = cluster.getChildCount();"
        "var i = (count < 10) ? 0 : (count < 100) ? 1 : 2;"
        f"var fillsRgba = {fills_js};"
        f"var bordersRgba = {borders_js};"
        f"var halosRgba = {halos_js};"
        f"var bw = {bw};"
        f"var spread = {spread};"
        "var style = 'background-color:' + fillsRgba[i] + ';border:' + bw + 'px solid ' + bordersRgba[i] + ';"
        "box-shadow:0 0 0 ' + spread + 'px ' + halosRgba[i] + ';';"
        "var sizeClass = (count < 10) ? 'marker-cluster-small' : (count < 100) ? 'marker-cluster-medium' : 'marker-cluster-large';"
        "return new L.DivIcon({"
        "html: '<div style=\"' + style + '\"><span>' + count + '</span></div>',"
        "className: 'marker-cluster ' + sizeClass,"
        "iconSize: new L.Point(40, 40)"
        "});"
        "}"
    )

