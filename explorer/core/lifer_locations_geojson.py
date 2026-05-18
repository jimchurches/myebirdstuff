"""GeoJSON + revision for the **Lifer locations** Leaflet component.

Mirrors :func:`~explorer.core.map_leaflet_viewport.build_lifer_overlay_map` data without Folium.
Structured ``lifer_popup_v1`` feeds the iframe TS template (parity with ``format_lifer_popup_lines``).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

from explorer.app.streamlit.defaults import MapMarkerColourScheme
from explorer.core.lifer_last_seen_prep import aggregate_lifer_sites
from explorer.core.map_marker_colour_resolve import resolve_lifer_overlay_pin_params
from explorer.core.map_overlay_lifer_popups import lifer_popup_line_structured_items
from explorer.core.map_overlay_types import BaseSpeciesFn


def build_lifer_locations_geojson_payload(
    *,
    full_location_data: pd.DataFrame,
    lifer_lookup_df: pd.DataFrame,
    true_lifer_locations: dict[str, Any],
    true_lifer_locations_taxon: dict[str, Any],
    show_subspecies_lifers: bool,
    base_species_fn: BaseSpeciesFn,
    visit_marker_scheme: MapMarkerColourScheme,
    revision_extra: str = "",
) -> tuple[str | None, dict[str, Any] | None, str | None, list[list[float]]]:
    """Return ``(revision, geojson_feature_collection, warning, framing_pairs_lat_lon)``.

    *framing_pairs_lat_lon* — base-species lifer coordinates only (viewport parity with Folium);
    empty when ``warning`` is set or no valid coordinates.
    """
    if full_location_data is None or full_location_data.empty:
        return None, None, "⚠️ Lifer map mode requires full location data.", []
    loc_to_species, _ = aggregate_lifer_sites(
        lifer_lookup_df,
        true_lifer_locations,
        true_lifer_locations_taxon,
    )
    if not loc_to_species:
        return None, None, "⚠️ No lifer locations found in your dataset.", []
    base_lifer_loc_ids = set(true_lifer_locations.values())
    loc_rows_framing = full_location_data[
        full_location_data["Location ID"].isin(base_lifer_loc_ids)
    ].drop_duplicates(subset=["Location ID"], keep="first")
    framing_pairs: list[list[float]] = []
    for _, row in loc_rows_framing.iterrows():
        la, lo = float(row["Latitude"]), float(row["Longitude"])
        if pd.isna(la) or pd.isna(lo):
            continue
        framing_pairs.append([la, lo])

    if show_subspecies_lifers:
        lifer_loc_ids = set(loc_to_species.keys())
    else:
        lifer_loc_ids = set(true_lifer_locations.values())
    loc_rows = full_location_data[full_location_data["Location ID"].isin(lifer_loc_ids)]
    if loc_rows.empty:
        return None, None, "⚠️ No lifer locations match your location table.", []

    le, lf, se, sp, r_lifer, r_species, stroke_w, fo_lif, fo_spec = resolve_lifer_overlay_pin_params(
        visit_marker_scheme
    )

    loc_kind_by_id: dict[Any, str] = {}
    if show_subspecies_lifers:

        def _loc_kind(entries: list[dict]) -> str:
            for e in entries:
                if e.get("is_base_lifer"):
                    return "lifer"
            return "subspecies"

        loc_kind_by_id = {lid: _loc_kind(entries) for lid, entries in loc_to_species.items()}

    features: list[dict[str, Any]] = []

    for _, row in loc_rows.iterrows():
        lid = row["Location ID"]
        entries = loc_to_species.get(lid, [])
        base_entries = [e for e in entries if e.get("is_base_lifer")]
        popup_entries = entries if show_subspecies_lifers else base_entries
        lines = lifer_popup_line_structured_items(
            entries=popup_entries,
            lifer_lookup_df=lifer_lookup_df,
            location_id=lid,
            base_species_fn=base_species_fn,
        )
        lid_s = str(lid)
        lat_f = float(row["Latitude"])
        lon_f = float(row["Longitude"])
        lifer_popup_v1: dict[str, Any] = {"v": 1, "lines": lines}
        if show_subspecies_lifers:
            lk = loc_kind_by_id.get(lid, "lifer")
            if lk == "subspecies":
                circle_pin = {
                    "stroke_hex": se,
                    "fill_hex": sp,
                    "radius_px": int(r_species),
                    "stroke_weight": int(stroke_w),
                    "fill_opacity": float(fo_spec),
                }
            else:
                circle_pin = {
                    "stroke_hex": le,
                    "fill_hex": lf,
                    "radius_px": int(r_lifer),
                    "stroke_weight": int(stroke_w),
                    "fill_opacity": float(fo_lif),
                }
        else:
            circle_pin = {
                "stroke_hex": le,
                "fill_hex": lf,
                "radius_px": int(r_lifer),
                "stroke_weight": int(stroke_w),
                "fill_opacity": float(fo_lif),
            }

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                "properties": {
                    "location_id": lid_s,
                    "name": str(row["Location"]),
                    "lifelist_url": f"https://ebird.org/lifelist/{lid_s}",
                    "lifer_popup_v1": lifer_popup_v1,
                    "circle_pin": circle_pin,
                    "pin_kind": (
                        "subspecies"
                        if show_subspecies_lifers
                        and loc_kind_by_id.get(lid, "lifer") == "subspecies"
                        else "lifer"
                    ),
                },
            }
        )

    rev_payload = json.dumps(features, separators=(",", ":")) + "|" + revision_extra
    revision = hashlib.sha256(rev_payload.encode("utf-8")).hexdigest()[:24]
    geojson: dict[str, Any] = {"type": "FeatureCollection", "features": features}
    return revision, geojson, None, framing_pairs
