"""Structured inputs for final map popup HTML assembly (#205 Batch A).

Keeps a single string-assembly path for location-style popups so future lazy / on-click
work can render from the same model.
"""

from __future__ import annotations

import html as html_module
from dataclasses import dataclass

from explorer.presentation.map_ui_constants import SPECIES_MAP_POPUP_OPEN_VISIT_LIST_MAX_CHECKLISTS
from explorer.presentation.stats_html_helpers import esc_text


@dataclass(frozen=True)
class LocationPopupModel:
    """Pre-rendered inner fragments for :func:`assemble_location_popup_html`."""

    loc_name: str
    loc_id: str
    visit_info_html: str
    sightings_html: str
    lifer_species_html: str
    show_visit_history: bool
    lifer_heading_html: str
    location_heading_margin_px: int


def assemble_location_popup_html(m: LocationPopupModel) -> str:
    """Build the full popup card HTML from a :class:`LocationPopupModel`."""
    loc_url = f"https://ebird.org/lifelist/{m.loc_id}"
    esc_loc = html_module.escape(str(m.loc_name), quote=False)
    loc_link = (
        f'<a class="pebird-map-popup__location-heading" href="{loc_url}" '
        f'target="_blank" rel="noopener noreferrer">{esc_loc}</a>'
    )
    if m.lifer_species_html:
        extra_section = (
            f"{m.lifer_heading_html}{m.lifer_species_html}"
            if m.lifer_heading_html
            else m.lifer_species_html
        )
    elif m.sightings_html:
        extra_section = f'<div class="pebird-map-popup__section-label">Seen:</div>{m.sightings_html}'
    else:
        extra_section = ""
    visited_section = (
        '<div class="pebird-map-popup__visited-block">'
        '<div class="pebird-map-popup__section-label">Visited:</div>'
        f'<div class="pebird-map-popup__visit-dates">{m.visit_info_html}</div>'
        "</div>"
        if m.show_visit_history
        else ""
    )
    if visited_section and extra_section:
        inner_html = visited_section + "<br>" + extra_section
    else:
        inner_html = visited_section + extra_section
    return (
        f'<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">'
        f'<div class="pebird-map-popup__heading-row" style="margin-bottom:{int(m.location_heading_margin_px)}px;">{loc_link}</div>'
        f'<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">'
        f"{inner_html}"
        f"</div></div>"
    )


@dataclass(frozen=True)
class SpeciesMapLocationPopupModel:
    """Heading + pre-built species sections + visit-details wrapper."""

    loc_name: str
    loc_id: str
    species_sections_html: str
    visit_info_html: str
    visit_record_count: int
    location_heading_margin_px: int = 6


def assemble_species_map_location_popup_html(m: SpeciesMapLocationPopupModel) -> str:
    """Species-map matching pin: species ``<details>`` + collapsed visit list."""
    loc_url = f"https://ebird.org/lifelist/{m.loc_id}"
    esc_loc = html_module.escape(str(m.loc_name), quote=False)
    loc_link = (
        f'<a class="pebird-map-popup__location-heading" href="{loc_url}" '
        f'target="_blank" rel="noopener noreferrer">{esc_loc}</a>'
    )
    summary_text = f"Visited: ({m.visit_record_count})"
    esc_summary = esc_text(summary_text)
    inner_visits = m.visit_info_html if (m.visit_info_html and str(m.visit_info_html).strip()) else ""
    visits_open = (
        " open"
        if m.visit_record_count <= SPECIES_MAP_POPUP_OPEN_VISIT_LIST_MAX_CHECKLISTS
        else ""
    )
    details_block = (
        f'<details class="pebird-map-popup__all-visits"{visits_open}>'
        f'<summary class="pebird-map-popup__section-label">{esc_summary}</summary>'
        f'<div class="pebird-map-popup__visit-list-inner">{inner_visits}</div>'
        f"</details>"
    )
    inner_html = m.species_sections_html + details_block
    return (
        f'<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">'
        f'<div class="pebird-map-popup__heading-row" style="margin-bottom:{int(m.location_heading_margin_px)}px;">{loc_link}</div>'
        f'<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">'
        f"{inner_html}"
        f"</div></div>"
    )
