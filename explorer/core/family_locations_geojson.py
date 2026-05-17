"""GeoJSON + revision for the **Family locations** Leaflet component.

Mirrors :func:`~explorer.core.family_map_folium.build_family_composition_folium_map` without Folium.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from explorer.app.streamlit.defaults import MapMarkerColourScheme
from explorer.core.family_map_compute import DENSITY_BAND_LABELS, FamilyLocationPin
from explorer.core.family_map_folium import family_map_marker_style
from explorer.core.map_marker_colour_resolve import (
    family_map_has_highlight_halo,
    family_map_resolved_circle_radius_px,
    family_map_resolved_fill_opacity,
    family_map_resolved_highlight_halo_fill_opacity,
    family_map_resolved_highlight_halo_radius_px,
    family_map_resolved_highlight_halo_stroke_opacity,
    family_map_resolved_highlight_halo_stroke_weight,
    resolve_family_highlight_halo_fill_hex,
    resolve_family_highlight_halo_stroke_hex,
)
from explorer.core.map_overlay_family_popups import family_popup_v1_payload


def _species_url_map_for_pin(
    pin: FamilyLocationPin,
    species_url_fn: Callable[[str], str | None],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in pin.common_name_lines:
        u = species_url_fn(line)
        if u:
            out[line] = u
    return out


def _circle_pin_for_family_pin(
    pin: FamilyLocationPin,
    *,
    scheme: MapMarkerColourScheme,
) -> dict[str, Any]:
    fill, stroke, sw = family_map_marker_style(pin, style=scheme)
    return {
        "stroke_hex": stroke,
        "fill_hex": fill,
        "radius_px": int(family_map_resolved_circle_radius_px(scheme)),
        "stroke_weight": int(sw),
        "fill_opacity": float(family_map_resolved_fill_opacity(scheme)),
    }


def _highlight_halo_circle_for_pin(
    pin: FamilyLocationPin,
    *,
    scheme: MapMarkerColourScheme,
) -> dict[str, Any] | None:
    if not pin.highlight_match or not family_map_has_highlight_halo(scheme):
        return None
    return {
        "stroke_hex": resolve_family_highlight_halo_stroke_hex(scheme),
        "fill_hex": resolve_family_highlight_halo_fill_hex(scheme),
        "radius_px": int(family_map_resolved_highlight_halo_radius_px(scheme)),
        "stroke_weight": int(family_map_resolved_highlight_halo_stroke_weight(scheme)),
        "fill_opacity": float(family_map_resolved_highlight_halo_fill_opacity(scheme)),
        "stroke_opacity": float(family_map_resolved_highlight_halo_stroke_opacity(scheme)),
    }


def build_family_locations_geojson_payload(
    pins: tuple[FamilyLocationPin, ...] | list[FamilyLocationPin],
    *,
    visit_marker_scheme: MapMarkerColourScheme,
    location_page_url_fn: Callable[[str], str | None],
    species_url_fn: Callable[[str], str | None],
    fit_bounds_highlight_only: bool,
    revision_extra: str = "",
) -> tuple[str | None, dict[str, Any] | None, list[list[float]], bool]:
    """Return ``(revision, geojson, framing_pairs_lat_lon, highlight_framed)``.

    *highlight_framed* — viewport uses highlight max-zoom when true (parity with Folium).
    """
    pin_list = list(pins)
    normal = sorted(
        (p for p in pin_list if not p.highlight_match),
        key=lambda p: int(p.density_band_index),
    )
    highlighted = sorted(
        (p for p in pin_list if p.highlight_match),
        key=lambda p: int(p.density_band_index),
    )
    ordered = normal + highlighted

    if fit_bounds_highlight_only:
        hl_only = [p for p in pin_list if p.highlight_match]
        bounds_src = hl_only if hl_only else pin_list
        highlight_framed = bool(hl_only)
    else:
        bounds_src = pin_list
        highlight_framed = False

    framing_pairs: list[list[float]] = [
        [float(p.latitude), float(p.longitude)] for p in bounds_src
    ]

    features: list[dict[str, Any]] = []
    for pin in ordered:
        lid_s = str(pin.location_id)
        loc_url = location_page_url_fn(lid_s) if location_page_url_fn else None
        url_map = _species_url_map_for_pin(pin, species_url_fn)
        props: dict[str, Any] = {
            "location_id": lid_s,
            "name": pin.location_name or lid_s,
            "lifelist_url": (
                str(loc_url).strip()
                if loc_url and str(loc_url).strip()
                else f"https://ebird.org/lifelist/{lid_s}"
            ),
            "family_popup_v1": family_popup_v1_payload(
                pin,
                species_url_by_common=url_map or None,
            ),
            "circle_pin": _circle_pin_for_family_pin(pin, scheme=visit_marker_scheme),
            "density_band_index": int(pin.density_band_index),
        }
        halo = _highlight_halo_circle_for_pin(pin, scheme=visit_marker_scheme)
        if halo is not None:
            props["highlight_halo_circle"] = halo
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(pin.longitude), float(pin.latitude)],
                },
                "properties": props,
            }
        )

    rev_payload = json.dumps(features, separators=(",", ":")) + "|" + revision_extra
    revision = hashlib.sha256(rev_payload.encode("utf-8")).hexdigest()[:24]
    geojson: dict[str, Any] = {"type": "FeatureCollection", "features": features}
    return revision, geojson, framing_pairs, highlight_framed


def density_band_labels_present(
    pins: tuple[FamilyLocationPin, ...] | list[FamilyLocationPin],
) -> tuple[int, ...]:
    """Sorted band indices present on the map (for legend rows)."""
    pin_list = list(pins)
    bands = sorted({int(p.density_band_index) for p in pin_list}) if pin_list else []
    return tuple(i for i in bands if 0 <= i < len(DENSITY_BAND_LABELS))
