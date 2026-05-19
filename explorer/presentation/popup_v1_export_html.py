"""Render GeoJSON popup properties to HTML for standalone Leaflet map export (#222 §7).

Mirrors the component iframe templates in ``AllLocationsMap.tsx`` without a second Folium stack.
"""

from __future__ import annotations

from typing import Any

from explorer.presentation.map_popup_models import (
    LocationPopupModel,
    SpeciesMapLocationPopupModel,
    assemble_location_popup_html,
    assemble_species_map_location_popup_html,
)
from explorer.presentation.map_popup_heading_text import prevent_orphan_closing_punctuation
from explorer.presentation.map_renderer import MAP_POPUP_MACAULAY_LINK_SYMBOL, esc_attr, esc_text
from explorer.presentation.stats_html_helpers import safe_http_url

_HEADING_MARGIN_ALL = 4


def _location_heading_element(name: str, url: str | None) -> str:
    esc_name = esc_text(prevent_orphan_closing_punctuation(name))
    if url:
        return (
            f'<a class="pebird-map-popup__location-heading" href="{esc_attr(url)}" '
            f'target="_blank" rel="noopener noreferrer">{esc_name}</a>'
        )
    return f'<span class="pebird-map-popup__location-heading">{esc_name}</span>'


def _lifelist_href(lifelist_url: str, loc_id: str | None = None) -> str:
    u = safe_http_url(lifelist_url)
    if u:
        return u
    lid = str(loc_id or "").strip()
    if lid:
        return safe_http_url(f"https://ebird.org/lifelist/{lid}")
    return ""


def _loc_id_from_props(props: dict[str, Any]) -> str:
    for key in ("loc_id", "location_id", "Location ID"):
        v = props.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    url = str(props.get("lifelist_url") or "").strip()
    if "/lifelist/" in url:
        return url.rsplit("/lifelist/", 1)[-1].split("?")[0].strip()
    return ""


def _visited_trunc_hint_html(
    *,
    entries: list[Any],
    lifelist_url: str,
    loc_id: str,
    popup: dict[str, Any],
) -> str:
    """Mirror ``popupHtmlVisitedLayout`` trunc block in ``AllLocationsMap.tsx``."""
    if popup.get("visited_truncated") is not True:
        return ""
    try:
        omitted = int(popup.get("visited_omitted") or 0)
    except (TypeError, ValueError):
        omitted = 0
    if omitted <= 0:
        return ""
    href = _lifelist_href(lifelist_url, loc_id)
    if not href:
        return ""
    shown = len(entries)
    try:
        total = int(popup.get("visited_total"))
    except (TypeError, ValueError):
        total = shown + omitted
    return (
        f'<div class="pebird-map-popup__trunc-hint">'
        f"{esc_text(str(shown))} of {esc_text(str(total))} checklists shown. "
        f'<a href="{esc_attr(href)}" target="_blank" rel="noopener noreferrer">Open lifelist</a> '
        f"for full history ({esc_text(str(omitted))} more)."
        f"</div>"
    )


def _visit_entries_html(entries: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for e in entries:
        href = safe_http_url(str(e.get("href") or ""))
        label = esc_text(str(e.get("label") or href or "—"))
        if href:
            parts.append(
                f'<a href="{esc_attr(href)}" target="_blank" rel="noopener noreferrer">{label}</a>'
            )
        else:
            parts.append(f'<span class="pebird-map-popup__visit-link-text">{label}</span>')
    return "<br>".join(parts)


def _species_obs_line(obs: dict[str, Any]) -> str:
    dt = esc_text(str(obs.get("datetime_label") or "—").strip())
    href = safe_http_url(str(obs.get("checklist_href") or ""))
    count = esc_text(str(obs.get("observed_count") or "").strip())
    media = safe_http_url(str(obs.get("media_href") or ""))
    if href:
        line = (
            f'<a href="{esc_attr(href)}" target="_blank" rel="noopener noreferrer">{dt}</a>'
        )
    else:
        line = f"<span>{dt}</span>"
    line += f' <span class="pebird-map-popup__obs-count">(Observed: {count})</span>'
    if media:
        line += (
            f' <a class="pebird-map-popup__media-link" href="{esc_attr(media)}" '
            f'target="_blank" rel="noopener noreferrer" title="media">'
            f"{MAP_POPUP_MACAULAY_LINK_SYMBOL}</a>"
        )
    return f'<div class="pebird-map-popup__obs-line">{line}</div>'


def _species_sections_html(sections: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for sec in sections:
        name = esc_text(str(sec.get("common_name") or ""))
        n_obs = int(sec.get("observation_count") or 0)
        open_attr = " open" if sec.get("open_by_default") else ""
        rows = "".join(_species_obs_line(o) for o in (sec.get("observations") or []))
        parts.append(
            f'<details class="pebird-map-popup__species-seen"{open_attr}>'
            f'<summary class="pebird-map-popup__section-label">{name}: ({n_obs})</summary>'
            f'<div class="pebird-map-popup__obs-list">{rows}</div>'
            f"</details>"
        )
    return "".join(parts)


def _lifer_popup_html(name: str, lifelist_url: str, payload: dict[str, Any]) -> str:
    lines = payload.get("lines") if isinstance(payload.get("lines"), list) else []
    inner_parts: list[str] = []
    for i, row in enumerate(lines):
        if not isinstance(row, dict):
            continue
        label = esc_text(str(row.get("label") or "—"))
        date_s = esc_text(str(row.get("date") or "?"))
        href = safe_http_url(str(row.get("checklist_href") or ""))
        prefix = "<br>" if i else ""
        if href:
            inner_parts.append(
                f'{prefix}<a href="{esc_attr(href)}" target="_blank" rel="noopener noreferrer">'
                f"{label} : {date_s}</a>"
            )
        else:
            inner_parts.append(f"{prefix}<span>{label} : {date_s}</span>")
    loc_id = _loc_id_from_props({"lifelist_url": lifelist_url})
    model = LocationPopupModel(
        loc_name=name,
        loc_id=loc_id or "0",
        visit_info_html="".join(inner_parts),
        sightings_html="",
        lifer_species_html="",
        show_visit_history=True,
        lifer_heading_html="",
        location_heading_margin_px=_HEADING_MARGIN_ALL,
    )
    return assemble_location_popup_html(model)


def _family_popup_html(name: str, lifelist_url: str, payload: dict[str, Any]) -> str:
    species_lines = payload.get("species_lines") if isinstance(payload.get("species_lines"), list) else []
    line_html: list[str] = []
    for row in species_lines:
        if not isinstance(row, dict):
            continue
        n = esc_text(str(row.get("name") or "").strip())
        if not n:
            continue
        href = safe_http_url(str(row.get("species_href") or ""))
        if href:
            line_html.append(
                f'<div class="pebird-map-popup__species-line"><a href="{esc_attr(href)}" '
                f'target="_blank" rel="noopener noreferrer">{n}</a></div>'
            )
        else:
            line_html.append(f'<div class="pebird-map-popup__species-line">{n}</div>')
    body = (
        "".join(line_html)
        if line_html
        else '<div class="pebird-map-popup__summary-line">No species lines</div>'
    )
    loc_id = _loc_id_from_props({"lifelist_url": lifelist_url})
    url = _lifelist_href(lifelist_url, loc_id)
    head = _location_heading_element(name, url or None)
    return (
        f'<div class="pebird-map-popup popup-scroll-wrapper">'
        f'<div class="pebird-map-popup__heading-row" style="margin-bottom:{_HEADING_MARGIN_ALL}px;">{head}</div>'
        f'<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">{body}</div>'
        f"</div>"
    )


def _species_popup_html(name: str, lifelist_url: str, payload: dict[str, Any]) -> str:
    sections = payload.get("species_sections") if isinstance(payload.get("species_sections"), list) else []
    visits = payload.get("visits") if isinstance(payload.get("visits"), dict) else {}
    visit_entries = visits.get("entries") if isinstance(visits.get("entries"), list) else []
    visit_count = len(visit_entries)
    margin = int(payload.get("location_heading_margin_px") or 6)
    loc_id = _loc_id_from_props({"lifelist_url": lifelist_url})
    return assemble_species_map_location_popup_html(
        SpeciesMapLocationPopupModel(
            loc_name=name,
            loc_id=loc_id or "0",
            species_sections_html=_species_sections_html(sections),
            visit_info_html=_visit_entries_html(visit_entries),
            visit_record_count=visit_count,
            location_heading_margin_px=margin,
        )
    )


def _popup_v1_html(name: str, lifelist_url: str, popup: dict[str, Any]) -> str:
    visited = popup.get("visited")
    if isinstance(visited, dict):
        entries = visited.get("entries") if isinstance(visited.get("entries"), list) else []
        loc_id = _loc_id_from_props({"lifelist_url": lifelist_url})
        trunc_hint = _visited_trunc_hint_html(
            entries=entries,
            lifelist_url=lifelist_url,
            loc_id=loc_id,
            popup=popup,
        )
        return assemble_location_popup_html(
            LocationPopupModel(
                loc_name=name,
                loc_id=loc_id or "0",
                visit_info_html=_visit_entries_html(entries),
                sightings_html="",
                lifer_species_html="",
                show_visit_history=True,
                lifer_heading_html="",
                location_heading_margin_px=_HEADING_MARGIN_ALL,
                visit_trunc_hint_html=trunc_hint,
            )
        )
    summary_lines = popup.get("summary_lines") if isinstance(popup.get("summary_lines"), list) else []
    links = popup.get("links") if isinstance(popup.get("links"), list) else []
    loc_id = _loc_id_from_props({"lifelist_url": lifelist_url})
    url = _lifelist_href(lifelist_url, loc_id)
    head = _location_heading_element(name, url or None)
    body_parts = [
        f'<span class="pebird-map-popup__summary-line">{esc_text(str(ln))}</span>'
        for ln in summary_lines
        if str(ln).strip()
    ]
    for link in links:
        if not isinstance(link, dict):
            continue
        href = safe_http_url(str(link.get("href") or ""))
        label = esc_text(str(link.get("label") or "Link"))
        if href:
            body_parts.append(
                f'<span class="pebird-map-popup__summary-line"><a href="{esc_attr(href)}" '
                f'target="_blank" rel="noopener noreferrer">{label}</a></span>'
            )
    return (
        f'<div class="pebird-map-popup">'
        f'<div class="pebird-map-popup__heading-row" style="margin-bottom:{_HEADING_MARGIN_ALL}px;">{head}</div>'
        f"{''.join(body_parts)}</div>"
    )


def popup_export_html_from_properties(props: dict[str, Any] | None) -> str:
    """Build popup HTML for one GeoJSON feature (export / offline HTML)."""
    props = props or {}
    name = str(props.get("name") or props.get("Location") or "Location")
    lifelist_url = str(props.get("lifelist_url") or "")
    lifer = props.get("lifer_popup_v1")
    if isinstance(lifer, dict) and lifer.get("v") == 1:
        return _lifer_popup_html(name, lifelist_url, lifer)
    family = props.get("family_popup_v1")
    if isinstance(family, dict) and family.get("v") == 1:
        return _family_popup_html(name, lifelist_url, family)
    species = props.get("species_popup_v1")
    if isinstance(species, dict) and species.get("v") == 1:
        return _species_popup_html(name, lifelist_url, species)
    popup = props.get("popup_v1")
    if isinstance(popup, dict) and popup.get("v") == 1:
        return _popup_v1_html(name, lifelist_url, popup)
    loc_id = _loc_id_from_props(props)
    url = _lifelist_href(lifelist_url, loc_id)
    head = _location_heading_element(name, url or None)
    visits = props.get("visit_checklists")
    extra = (
        f'<span class="pebird-map-popup__summary-line">Checklists: {esc_text(str(visits))}</span>'
        if visits not in (None, "")
        else ""
    )
    return (
        f'<div class="pebird-map-popup">'
        f'<div class="pebird-map-popup__heading-row" style="margin-bottom:{_HEADING_MARGIN_ALL}px;">{head}</div>'
        f"{extra}</div>"
    )


def enrich_geojson_for_export(geojson: dict[str, Any]) -> dict[str, Any]:
    """Copy GeoJSON and add ``export_popup_html`` on each feature for the export viewer."""
    features_in = geojson.get("features") if isinstance(geojson.get("features"), list) else []
    features_out: list[dict[str, Any]] = []
    for feat in features_in:
        if not isinstance(feat, dict):
            continue
        props = dict(feat.get("properties") or {})
        props["export_popup_html"] = popup_export_html_from_properties(props)
        features_out.append({**feat, "properties": props})
    return {**geojson, "type": geojson.get("type") or "FeatureCollection", "features": features_out}
