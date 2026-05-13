"""GeoJSON payload + revision string for the experimental All locations map (#221).

Per-pin ``popup_v1`` is structured data for one TS template (not HTML×N). With ``records_by_location``,
``visited.entries`` mirrors classic visit-list rows (parallel to ``build_visit_info_html``).

Optional ``visits_inline_max`` trims inlined checklist rows per pin (lifelist link remains); pairs with
env ``EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP`` from Streamlit (see experimental tab).

Streamlit-side payload caching (#221) avoids rebuilding GeoJSON on warm reruns when the Folium map
cache key and revision extras match — see ``EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd

from explorer.presentation.map_renderer import build_visit_popup_entry_rows, format_visit_time


def _lifelist_url(location_id: str) -> str:
    lid = str(location_id).strip()
    if not lid:
        return ""
    return f"https://ebird.org/lifelist/{lid}"


def _popup_payload_v1_compact(
    *,
    visit_checklists: int | str,
    lifelist_url: str,
) -> dict[str, Any]:
    """Fallback popup when per-location visit rows are unavailable (tests / minimal callers)."""
    summary_lines: list[str] = []
    if visit_checklists != "":
        summary_lines.append(f"Checklists: {visit_checklists}")
    links: list[dict[str, str]] = []
    url = lifelist_url.strip()
    if url:
        links.append({"label": "Lifelist", "href": url})
    return {"v": 1, "summary_lines": summary_lines, "links": links}


def _popup_payload_v1_all_locations(
    *,
    visit_entries: list[dict[str, str]],
    visits_inline_max: int | None = None,
) -> dict[str, Any]:
    """Classic All locations shape: heading uses lifelist URL in TS; ``Visited:`` checklist links.

    When *visits_inline_max* is a positive int and there are more rows, entries are truncated and
    ``visited_truncated`` metadata explains the omission (lifelist remains the exhaustive tie-back).
    """
    total = len(visit_entries)
    if (
        visits_inline_max is not None
        and visits_inline_max > 0
        and total > visits_inline_max
    ):
        return {
            "v": 1,
            "visited": {"label": "Visited:", "entries": visit_entries[:visits_inline_max]},
            "visited_truncated": True,
            "visited_total": total,
            "visited_omitted": total - visits_inline_max,
        }
    return {"v": 1, "visited": {"label": "Visited:", "entries": visit_entries}}


def _visit_entries_for_location(
    records_by_location: Mapping[Hashable, pd.DataFrame] | None,
    location_id: Hashable,
    *,
    popup_visit_dates_ascending: bool,
) -> list[dict[str, str]] | None:
    """Return structured visit rows, or ``None`` to fall back to compact popup."""
    if records_by_location is None:
        return None
    base = records_by_location.get(location_id, pd.DataFrame())
    if base.empty or "Submission ID" not in base.columns:
        return []
    vr = base.drop_duplicates(subset=["Submission ID"])
    if vr.empty:
        return []
    ascending = popup_visit_dates_ascending
    if "datetime" in vr.columns:
        vr = vr.sort_values("datetime", ascending=ascending)
    elif "Date" in vr.columns:
        vr = vr.sort_values("Date", ascending=ascending)
    return build_visit_popup_entry_rows(vr, format_visit_time)


def build_all_locations_geojson_payload(
    location_data: pd.DataFrame,
    *,
    checklist_counts_by_location: Mapping[Hashable, int] | None = None,
    records_by_location: Mapping[Hashable, pd.DataFrame] | None = None,
    popup_visit_dates_ascending: bool = True,
    visits_inline_max: int | None = None,
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

    When *records_by_location* is set (same mapping as Folium **All locations**), each feature's
    ``popup_v1`` includes a ``visited`` section mirroring :func:`build_location_popup_html` content.

    *visits_inline_max* caps how many checklist links appear under ``visited.entries`` per pin;
    ``None`` keeps full parity with classic (all visits inlined).
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
        lifelist_href = _lifelist_url(lid)
        visit_entries = _visit_entries_for_location(
            records_by_location,
            row["Location ID"],
            popup_visit_dates_ascending=popup_visit_dates_ascending,
        )
        if visit_entries is None:
            popup_v1: dict[str, Any] = _popup_payload_v1_compact(
                visit_checklists=visits_val,
                lifelist_url=lifelist_href,
            )
        else:
            popup_v1 = _popup_payload_v1_all_locations(
                visit_entries=visit_entries,
                visits_inline_max=visits_inline_max,
            )
        props: dict[str, Any] = {
            "location_id": lid,
            "name": name,
            "lifelist_url": lifelist_href,
            "visit_checklists": visits_val,
            "popup_v1": popup_v1,
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
