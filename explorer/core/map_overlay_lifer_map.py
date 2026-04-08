"""Folium map build for **Lifer locations** view (pins + popups + legend variants)."""

from __future__ import annotations

from typing import Any, MutableMapping, Optional, Tuple

import folium
import pandas as pd
from branca.element import Element

from explorer.app.streamlit.defaults import (
    MAP_CIRCLE_MARKER_RADIUS_PX,
    MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    MAP_DEBUG_SHOW_ZOOM_LEVEL,
    MAP_PIN_FILL_OPACITY_EMPHASIS,
)
from explorer.core.lifer_last_seen_prep import aggregate_lifer_sites
from explorer.core.map_overlay_lifer_popups import format_lifer_popup_lines
from explorer.core.map_overlay_theme import inject_map_overlay_theme
from explorer.core.map_overlay_types import BaseSpeciesFn, MapOverlayResult
from explorer.presentation.map_renderer import (
    add_zoom_level_debug_overlay,
    build_legend_html,
    build_lifer_locations_banner_html,
    build_location_popup_html,
    create_map,
    popup_scroll_script,
)
from explorer.presentation.map_ui_constants import MAP_POPUP_MAX_WIDTH_PX


def build_lifer_overlay_map(
    *,
    full_location_data: Optional[pd.DataFrame],
    lifer_lookup_df: pd.DataFrame,
    true_lifer_locations: dict[str, Any],
    true_lifer_locations_taxon: dict[str, Any],
    map_style: str,
    map_height_px: int,
    popup_sort_order: str,
    popup_scroll_hint: str,
    lifer_color: str,
    lifer_fill: str,
    species_color: str,
    species_fill: str,
    date_filter_status: str,
    popup_html_cache: MutableMapping[Tuple[Any, ...], str],
    tax_loc_key: str,
    show_subspecies_lifers: bool,
    effective_use_full: bool,
    base_species_fn: BaseSpeciesFn,
) -> MapOverlayResult:
    """Assemble the lifer-locations Folium map or return a user-facing *warning*."""
    if full_location_data is None or full_location_data.empty:
        return MapOverlayResult(
            None,
            warning="⚠️ Lifer map mode requires full location data.",
        )
    loc_to_species, n_lifer_taxa = aggregate_lifer_sites(
        lifer_lookup_df,
        true_lifer_locations,
        true_lifer_locations_taxon,
    )
    if not loc_to_species:
        return MapOverlayResult(
            None,
            warning="⚠️ No lifer locations found in your dataset.",
        )
    if show_subspecies_lifers:
        lifer_loc_ids = set(loc_to_species.keys())
        n_lifer_count = n_lifer_taxa
    else:
        lifer_loc_ids = set(true_lifer_locations.values())
        n_lifer_count = len(true_lifer_locations)
    loc_rows = full_location_data[full_location_data["Location ID"].isin(lifer_loc_ids)]
    if loc_rows.empty:
        return MapOverlayResult(
            None,
            warning="⚠️ No lifer locations match your location table.",
        )
    map_center = [loc_rows["Latitude"].mean(), loc_rows["Longitude"].mean()]
    species_map = create_map(map_center, map_style, height_px=map_height_px)
    inject_map_overlay_theme(species_map)
    add_zoom_level_debug_overlay(species_map, enabled=MAP_DEBUG_SHOW_ZOOM_LEVEL)
    popup_asc = popup_sort_order == "ascending"
    dfs = date_filter_status or None
    n_locations = int(loc_rows["Location ID"].nunique())
    species_map.get_root().html.add_child(
        Element(
            build_lifer_locations_banner_html(
                n_lifer_count,
                n_locations,
                dfs,
                include_subspecies=bool(show_subspecies_lifers),
            )
        )
    )
    loc_kind_by_id: dict[Any, str] = {}
    if not show_subspecies_lifers:
        species_map.get_root().html.add_child(
            Element(build_legend_html([(lifer_color, lifer_fill, "Lifer")]))
        )
    else:

        def _loc_kind(entries: list[dict]) -> str:
            for e in entries:
                if e.get("is_base_lifer") and e.get("is_taxon_lifer"):
                    return "both"
            for e in entries:
                if e.get("is_base_lifer"):
                    return "lifer"
            return "subspecies"

        loc_kind_by_id = {lid: _loc_kind(entries) for lid, entries in loc_to_species.items()}
        kinds_present = set(loc_kind_by_id.values())
        legend_items = []
        if "lifer" in kinds_present:
            legend_items.append((lifer_color, lifer_fill, "Lifer"))
        if "subspecies" in kinds_present:
            legend_items.append((species_color, species_fill, "Subspecies"))
        if "both" in kinds_present:
            legend_items.append((lifer_color, lifer_fill, "Both"))
        species_map.get_root().html.add_child(Element(build_legend_html(legend_items)))

    for _, row in loc_rows.iterrows():
        lid = row["Location ID"]
        popup_key = (lid, "__lifer_map__", effective_use_full, tax_loc_key, bool(show_subspecies_lifers))
        if popup_key not in popup_html_cache:
            entries = loc_to_species.get(lid, [])
            base_entries = [e for e in entries if e.get("is_base_lifer")]
            popup_entries = entries if show_subspecies_lifers else base_entries
            lifer_lines = format_lifer_popup_lines(
                entries=popup_entries,
                lifer_lookup_df=lifer_lookup_df,
                location_id=lid,
                base_species_fn=base_species_fn,
            )
            popup_html_cache[popup_key] = build_location_popup_html(
                row["Location"],
                lid,
                "",
                lifer_species_html=lifer_lines,
                show_visit_history=False,
                lifer_heading_html="",
                location_heading_margin_px=2,
            )
        popup_html = popup_html_cache[popup_key]
        if not show_subspecies_lifers:
            popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                color=lifer_color,
                weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                fill=True,
                fill_color=lifer_fill,
                fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
                popup=popup,
            ).add_to(species_map)
        else:
            latlng = [row["Latitude"], row["Longitude"]]
            loc_kind = loc_kind_by_id.get(lid, "lifer")
            if loc_kind == "both":
                outer_popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
                folium.CircleMarker(
                    location=latlng,
                    radius=MAP_CIRCLE_MARKER_RADIUS_PX + 2,
                    color=species_color,
                    weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                    fill=False,
                    popup=outer_popup,
                ).add_to(species_map)
                inner_popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
                folium.CircleMarker(
                    location=latlng,
                    radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                    color=lifer_color,
                    weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                    fill=True,
                    fill_color=lifer_fill,
                    fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
                    popup=inner_popup,
                ).add_to(species_map)
            elif loc_kind == "subspecies":
                popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
                folium.CircleMarker(
                    location=latlng,
                    radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                    color=species_color,
                    weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                    fill=True,
                    fill_color=species_fill,
                    fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
                    popup=popup,
                ).add_to(species_map)
            else:
                popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
                folium.CircleMarker(
                    location=latlng,
                    radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                    color=lifer_color,
                    weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                    fill=True,
                    fill_color=lifer_fill,
                    fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
                    popup=popup,
                ).add_to(species_map)

    scroll_popup_script = popup_scroll_script(popup_scroll_hint, popup_asc)
    species_map.get_root().html.add_child(Element(scroll_popup_script))
    return MapOverlayResult(species_map, None)
