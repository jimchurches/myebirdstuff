"""GeoJSON + revision for the **Species locations** Leaflet component.

Mirrors :func:`~explorer.core.map_overlay_visit_map.build_visit_overlay_map` species branch without Folium.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

import pandas as pd

from explorer.app.streamlit.defaults import MapMarkerColourScheme
from explorer.core.map_marker_colour_resolve import resolve_species_visit_pin
from explorer.core.map_overlay_species_popups import (
    species_popup_v1_payload,
    visit_only_popup_v1_payload,
)
from explorer.core.map_overlay_types import BaseSpeciesFn
from explorer.core.species_logic import filter_species
from explorer.core.stats import safe_count
from explorer.presentation.map_renderer import (
    build_visit_popup_entry_rows,
    classify_locations,
    format_visit_time,
    resolve_lifer_last_seen,
)

VisitPinRole = Literal["lifer", "last_seen", "species", "default"]


def compute_species_map_banner_fields(
    *,
    filtered: pd.DataFrame,
    selected_species: str,
    selected_common_name: str,
    lifer_lookup_df: pd.DataFrame,
    base_species_fn: BaseSpeciesFn,
) -> dict[str, Any]:
    """Banner stats for :func:`~explorer.presentation.map_renderer.build_species_banner_html`."""
    n_checklists = int(filtered["Submission ID"].nunique())
    n_individuals = int(filtered["Count"].apply(safe_count).sum())
    high_count = int(filtered["Count"].apply(safe_count).max())

    def _banner_date(d: Any) -> str:
        return d.strftime("%d-%b-%Y") if pd.notna(d) else "?"

    first_seen_date = ""
    last_seen_date = ""
    high_count_date = ""
    first_seen_url: str | None = None
    last_seen_url: str | None = None
    high_count_url: str | None = None
    sci_parts = (selected_species or "").strip().split()
    is_subspecies = len(sci_parts) >= 3
    taxon_key = selected_species.strip().lower() if selected_species else None
    if is_subspecies and taxon_key:
        subset = lifer_lookup_df[lifer_lookup_df["_taxon"] == taxon_key]
    else:
        base = base_species_fn(selected_species)
        subset = lifer_lookup_df[lifer_lookup_df["_base"] == base] if base else pd.DataFrame()
    if not subset.empty:
        first_rec = subset.iloc[0]
        last_rec = subset.iloc[-1]
        first_seen_date = _banner_date(first_rec["Date"])
        last_seen_date = _banner_date(last_rec["Date"])
        fcid = first_rec.get("Submission ID", "")
        lcid = last_rec.get("Submission ID", "")
        if pd.notna(fcid) and str(fcid).strip():
            first_seen_url = f"https://ebird.org/checklist/{str(fcid).strip()}"
        if pd.notna(lcid) and str(lcid).strip():
            last_seen_url = f"https://ebird.org/checklist/{str(lcid).strip()}"

    high_count_rows = filtered[filtered["Count"].apply(safe_count) == high_count]
    if not high_count_rows.empty:
        high_count_row = high_count_rows.iloc[0]
        high_count_date = _banner_date(high_count_row["Date"])
        hc_id = high_count_row.get("Submission ID", "")
        if pd.notna(hc_id) and str(hc_id).strip():
            high_count_url = f"https://ebird.org/checklist/{str(hc_id).strip()}"

    display_name = (selected_common_name or "").strip() or selected_species
    return {
        "display_name": display_name,
        "n_checklists": n_checklists,
        "n_individuals": n_individuals,
        "high_count": high_count,
        "first_seen_date": first_seen_date,
        "last_seen_date": last_seen_date,
        "high_count_date": high_count_date,
        "first_seen_checklist_url": first_seen_url,
        "last_seen_checklist_url": last_seen_url,
        "high_count_checklist_url": high_count_url,
    }


def _visit_role_for_row(row: pd.Series) -> VisitPinRole:
    if bool(row.get("is_lifer")):
        return "lifer"
    if bool(row.get("is_last_seen")):
        return "last_seen"
    if bool(row.get("has_species_match")):
        return "species"
    return "default"


def build_species_locations_geojson_payload(
    *,
    df: pd.DataFrame,
    location_data: pd.DataFrame,
    records_by_loc: dict[Any, pd.DataFrame],
    selected_species: str,
    true_lifer_locations: dict[str, Any],
    true_lifer_locations_taxon: dict[str, Any],
    true_last_seen_locations: dict[str, Any],
    true_last_seen_locations_taxon: dict[str, Any],
    hide_non_matching_locations: bool,
    mark_lifer: bool,
    mark_last_seen: bool,
    base_species_fn: BaseSpeciesFn,
    visit_marker_scheme: MapMarkerColourScheme,
    popup_visit_dates_ascending: bool,
    revision_extra: str = "",
) -> tuple[str | None, dict[str, Any] | None, str | None, list[list[float]], set[str]]:
    """Return ``(revision, geojson, warning, framing_pairs_lat_lon, pin_roles_present)``.

    *framing_pairs* — coordinates of species-matching pins only (viewport parity with Folium).
    *pin_roles_present* — legend labels present: ``Species``, ``Locations``, ``Lifer``, ``Last seen``.
    """
    sci = (selected_species or "").strip()
    if not sci:
        return None, None, None, [], set()

    filtered = filter_species(df, sci)
    if filtered.empty:
        return (
            None,
            None,
            f"⚠️ No sightings of '{sci}' in current data — check date range or filters.",
            [],
            set(),
        )

    filtered_by_loc = {
        lid: grp for lid, grp in filtered.groupby("Location ID", sort=False)
    }
    seen_location_ids = set(filtered["Location ID"])
    lifer_location, last_seen_location = resolve_lifer_last_seen(
        sci,
        seen_location_ids,
        true_lifer_locations,
        true_last_seen_locations,
        true_lifer_locations_taxon,
        true_last_seen_locations_taxon,
        base_species_fn=base_species_fn,
        mark_lifer=mark_lifer,
        mark_last_seen=mark_last_seen,
    )
    location_data_local = classify_locations(
        location_data, seen_location_ids, lifer_location, last_seen_location
    )

    features: list[dict[str, Any]] = []
    framing_pairs: list[list[float]] = []
    pin_roles_present: set[str] = set()
    role_to_legend = {
        "species": "Species",
        "default": "Locations",
        "lifer": "Lifer",
        "last_seen": "Last seen",
    }

    for _, row in location_data_local.iterrows():
        if not bool(row.get("has_species_match")) and hide_non_matching_locations:
            continue

        loc_id = row["Location ID"]
        lat_f = float(row["Latitude"])
        lon_f = float(row["Longitude"])
        if pd.isna(lat_f) or pd.isna(lon_f):
            continue

        role = _visit_role_for_row(row)
        pin_roles_present.add(role_to_legend[role])

        base_records = records_by_loc.get(loc_id, pd.DataFrame())
        visit_records = base_records.drop_duplicates(subset=["Submission ID"])
        if not visit_records.empty:
            if "datetime" in visit_records.columns:
                visit_records = visit_records.sort_values(
                    "datetime", ascending=popup_visit_dates_ascending
                )
            elif "Date" in visit_records.columns:
                visit_records = visit_records.sort_values(
                    "Date", ascending=popup_visit_dates_ascending
                )
        visit_entries = build_visit_popup_entry_rows(visit_records, format_visit_time)
        n_visits = len(visit_records)

        if bool(row.get("has_species_match")):
            species_sightings = filtered_by_loc.get(loc_id, pd.DataFrame())
            if not species_sightings.empty and "datetime" in species_sightings.columns:
                species_sightings = species_sightings.sort_values(
                    "datetime", ascending=popup_visit_dates_ascending
                )
            popup_payload = species_popup_v1_payload(
                species_sightings=species_sightings,
                visit_entries=visit_entries,
                visit_record_count=n_visits,
                popup_ascending=popup_visit_dates_ascending,
            )
            framing_pairs.append([lat_f, lon_f])
        else:
            popup_payload = visit_only_popup_v1_payload(visit_entries=visit_entries)

        color, fill, radius_px, stroke_w, fill_opacity = resolve_species_visit_pin(
            visit_marker_scheme, role
        )
        lid_s = str(loc_id)
        props: dict[str, Any] = {
            "location_id": lid_s,
            "name": str(row["Location"]),
            "lifelist_url": f"https://ebird.org/lifelist/{lid_s}",
            "circle_pin": {
                "stroke_hex": color,
                "fill_hex": fill,
                "radius_px": int(radius_px),
                "stroke_weight": int(stroke_w),
                "fill_opacity": float(fill_opacity),
            },
            "pin_role": role,
        }
        if bool(row.get("has_species_match")):
            props["species_popup_v1"] = popup_payload
        else:
            props["popup_v1"] = popup_payload
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
    return revision, geojson, None, framing_pairs, pin_roles_present
