"""Structured All-locations popup payloads (#205 Batch C / C1).

Field-level JSON carried in the deferred-popup bridge replaces per-visit HTML strings in the
embedded map data when ``EXPLORER_MAP_STRUCTURED_POPUPS`` is on. A small client renderer turns each
payload into the same card as :func:`~explorer.presentation.map_renderer.build_location_popup_html`
(Visited list + lifelist heading only — **All locations** scope).

Default remains full server-built HTML per marker (flags off).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from explorer.presentation.map_popup_models import LocationPopupModel, assemble_location_popup_html
from explorer.presentation.stats_html_helpers import esc_attr, esc_text

ALL_LOCATIONS_POPUP_PAYLOAD_KIND = "al1"


def build_all_locations_popup_payload(
    loc_name: str,
    loc_id: Any,
    visit_records: pd.DataFrame,
    format_time_fn: Any,
    *,
    location_heading_margin_px: int = 4,
) -> dict[str, Any]:
    """Build a compact JSON-serializable payload for one All-locations marker.

    *visit_records* must be deduplicated by ``Submission ID`` and sorted (same contract as
    :func:`~explorer.presentation.map_renderer.build_visit_info_html`).
    """
    visits: list[list[str]] = []
    if not visit_records.empty:
        for _, r in visit_records.iterrows():
            sid = str(r.get("Submission ID", "") or "").strip()
            label = str(format_time_fn(r))
            visits.append([sid, label])
    return {
        "k": ALL_LOCATIONS_POPUP_PAYLOAD_KIND,
        "n": str(loc_name),
        "i": str(loc_id),
        "m": int(location_heading_margin_px),
        "v": visits,
    }


def all_locations_popup_payload_to_html(payload: dict[str, Any]) -> str:
    """Reference HTML assembler for tests — must stay aligned with the client ``al1`` renderer."""
    if payload.get("k") != ALL_LOCATIONS_POPUP_PAYLOAD_KIND:
        raise ValueError("unsupported structured popup payload")
    visit_parts: list[str] = []
    for pair in payload.get("v") or []:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        sid, text = pair[0], pair[1]
        visit_parts.append(
            f'<a href="https://ebird.org/checklist/{esc_attr(sid)}" '
            f'target="_blank" rel="noopener noreferrer">{esc_text(text)}</a>'
        )
    visit_inner = "<br>".join(visit_parts)
    m = LocationPopupModel(
        loc_name=str(payload.get("n", "")),
        loc_id=str(payload.get("i", "")),
        visit_info_html=visit_inner,
        sightings_html="",
        lifer_species_html="",
        show_visit_history=True,
        lifer_heading_html="",
        location_heading_margin_px=int(payload.get("m", 4)),
    )
    return assemble_location_popup_html(m)
