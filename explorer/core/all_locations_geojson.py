"""GeoJSON payload + revision string for the experimental All locations map (#221)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd


def _lifelist_url(location_id: str) -> str:
    lid = str(location_id).strip()
    if not lid:
        return ""
    return f"https://ebird.org/lifelist/{lid}"


def build_all_locations_geojson_payload(
    location_data: pd.DataFrame,
    *,
    checklist_counts_by_location: Mapping[Hashable, int] | None = None,
    pin_fill_hex: str = "#3388ff",
    omit_pin_colour: bool = False,
    revision_extra: str = "",
) -> tuple[str, dict[str, Any]]:
    """Return ``(revision, geojson_dict)`` for the Leaflet Streamlit component.

    *revision* changes when the sorted feature set (coordinates, ids, labels, visit counts) changes.
    Pass *revision_extra* (e.g. JSON of cluster options) so iframe behaviour can bump the revision
    without changing GeoJSON geometry.
    When *omit_pin_colour* is True, ``colour`` is omitted from features so the iframe applies
    ``circle_marker_style`` from Streamlit (resolved Folium-equivalent pin styling).
    """
    cols = {"Location ID", "Location", "Latitude", "Longitude"}
    if not cols.issubset(location_data.columns):
        missing = cols - set(location_data.columns)
        raise ValueError(f"location_data missing columns: {sorted(missing)}")

    ld = location_data[list(cols)].drop_duplicates(subset=["Location ID"]).copy()
    ld["_sort_key"] = ld["Location ID"].astype(str)
    ld = ld.sort_values("_sort_key")

    features: list[dict[str, Any]] = []
    for _, row in ld.iterrows():
        lid = str(row["Location ID"])
        lat_f = float(row["Latitude"])
        lon_f = float(row["Longitude"])
        name = str(row["Location"])
        visits_val: int | str = ""
        if checklist_counts_by_location is not None:
            visits_val = int(checklist_counts_by_location.get(row["Location ID"], 0))
        props: dict[str, Any] = {
            "location_id": lid,
            "name": name,
            "lifelist_url": _lifelist_url(lid),
            "visit_checklists": visits_val,
        }
        if not omit_pin_colour:
            props["colour"] = pin_fill_hex
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                "properties": props,
            }
        )

    rev_payload = json.dumps(features, separators=(",", ":")) + "|" + revision_extra
    revision = hashlib.sha256(rev_payload.encode("utf-8")).hexdigest()[:24]
    geojson: dict[str, Any] = {"type": "FeatureCollection", "features": features}
    return revision, geojson
