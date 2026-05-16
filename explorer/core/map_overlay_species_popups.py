"""Structured species-map popup payloads for the Leaflet component (#222).

Parallels :func:`~explorer.presentation.map_renderer.build_species_map_location_popup_html` and
:func:`~explorer.presentation.map_renderer.build_species_seen_sections_html` without pre-rendered HTML.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from explorer.core.stats import format_observed_count_for_map_popup
from explorer.presentation.map_renderer import esc_attr, esc_text
from explorer.presentation.map_ui_constants import (
    SPECIES_MAP_POPUP_OPEN_SPECIES_SECTION_MAX_OBSERVATIONS,
    SPECIES_MAP_POPUP_OPEN_VISIT_LIST_MAX_CHECKLISTS,
)


def _macaulay_media_href(r: pd.Series) -> str:
    ml = r.get("ML Catalog Numbers")
    if pd.isna(ml) or not str(ml).strip():
        return ""
    first_ml = str(ml).strip().split()[0]
    if not first_ml:
        return ""
    return f"https://macaulaylibrary.org/asset/{esc_attr(first_ml)}"


def species_map_sighting_row_structured(r: pd.Series) -> dict[str, str]:
    """One observation row inside a species ``<details>`` block (no species name in line)."""
    if "datetime" in r.index and pd.notna(r.get("datetime")):
        dt = r["datetime"]
        datetime_label = dt.strftime("%Y-%m-%d %H:%M")
    else:
        date_str = r["Date"].strftime("%Y-%m-%d") if pd.notna(r.get("Date")) else "unknown"
        time_str = str(r["Time"]) if pd.notna(r.get("Time")) else "unknown"
        datetime_label = f"{date_str} {time_str}"
    cid = str(r.get("Submission ID", "") or "").strip()
    checklist_href = f"https://ebird.org/checklist/{esc_attr(cid)}" if cid else ""
    return {
        "datetime_label": datetime_label,
        "checklist_href": checklist_href,
        "observed_count": esc_text(format_observed_count_for_map_popup(r.get("Count"))),
        "media_href": _macaulay_media_href(r),
    }


def species_seen_sections_structured(
    species_sightings: pd.DataFrame,
    *,
    ascending: bool,
) -> list[dict[str, Any]]:
    """Grouped species sections — parallel to :func:`build_species_seen_sections_html`."""
    if species_sightings.empty or "Common Name" not in species_sightings.columns:
        return []
    work = species_sightings.copy()
    work["Common Name"] = work["Common Name"].fillna("Unknown")
    names = sorted(work["Common Name"].unique(), key=lambda x: str(x).lower())
    sections: list[dict[str, Any]] = []
    for common_name in names:
        sub = work[work["Common Name"] == common_name]
        if "datetime" in sub.columns:
            sub = sub.sort_values("datetime", ascending=ascending)
        n_obs = len(sub)
        observations = [species_map_sighting_row_structured(r) for _, r in sub.iterrows()]
        sections.append(
            {
                "common_name": esc_text(str(common_name)),
                "observation_count": int(n_obs),
                "open_by_default": n_obs <= SPECIES_MAP_POPUP_OPEN_SPECIES_SECTION_MAX_OBSERVATIONS,
                "observations": observations,
            }
        )
    return sections


def species_popup_v1_payload(
    *,
    species_sightings: pd.DataFrame,
    visit_entries: list[dict[str, str]],
    visit_record_count: int,
    popup_ascending: bool,
) -> dict[str, Any]:
    """Structured popup for a species-matching map pin."""
    return {
        "v": 1,
        "location_heading_margin_px": 6,
        "species_sections": species_seen_sections_structured(
            species_sightings, ascending=popup_ascending
        ),
        "visits": {
            "summary_label": f"Visited: ({visit_record_count})",
            "entries": visit_entries,
            "open_by_default": visit_record_count <= SPECIES_MAP_POPUP_OPEN_VISIT_LIST_MAX_CHECKLISTS,
        },
    }


def visit_only_popup_v1_payload(*, visit_entries: list[dict[str, str]]) -> dict[str, Any]:
    """Non-matching species-map pin — visit list only (:func:`build_location_popup_html` shape)."""
    return {
        "v": 1,
        "visited": {"label": "Visited:", "entries": visit_entries},
    }
