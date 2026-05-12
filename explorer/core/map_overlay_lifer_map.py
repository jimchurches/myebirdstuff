"""Folium map build for **Lifer locations** view (pins + popups + legend variants)."""

from __future__ import annotations

import time
from typing import Any, Dict, MutableMapping, Optional, Tuple

import folium
import pandas as pd
from branca.element import Element

from explorer.app.streamlit.defaults import (
    MAP_DEBUG_SHOW_ZOOM_LEVEL,
    MAP_LIFER_MAP_FIT_BOUNDS_MAX_ZOOM,
    MAP_LIFER_MAP_FIT_BOUNDS_PADDING_PX,
    MAP_LIFER_MAP_SINGLE_POINT_ZOOM,
    MapMarkerColourScheme,
)
from explorer.core.lifer_last_seen_prep import aggregate_lifer_sites, count_subspecies_lifer_taxa
from explorer.core.map_marker_colour_resolve import resolve_lifer_overlay_pin_params
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


def _epsilon_bounds_around_point(lat: float, lon: float, delta: float = 0.02) -> list[list[float]]:
    """Tiny bounding box so Leaflet ``fitBounds`` has non-zero extent for a single pin."""
    return [[lat - delta, lon - delta], [lat + delta, lon + delta]]


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
    date_filter_status: str,
    popup_html_cache: MutableMapping[Tuple[Any, ...], str],
    tax_loc_key: str,
    show_subspecies_lifers: bool,
    effective_use_full: bool,
    base_species_fn: BaseSpeciesFn,
    visit_marker_scheme: MapMarkerColourScheme,
    metrics_sink: Optional[Dict[str, Any]] = None,
    lite_map_popups: bool = False,
) -> MapOverlayResult:
    """Assemble the lifer-locations Folium map or return a user-facing *warning*.

    See :func:`explorer.core.map_controller.build_species_overlay_map` for *metrics_sink*
    semantics (#205 batch 4 I1/I2). Populated keys: ``view_path``, ``marker_count``,
    ``popup_build_count``, ``popup_cache_hit_count``, ``popup_build_total_ms``.

    *lite_map_popups* (#205 W2): location lifelist only — skips per-location lifer species HTML.
    """
    if full_location_data is None or full_location_data.empty:
        return MapOverlayResult(
            None,
            warning="⚠️ Lifer map mode requires full location data.",
        )
    loc_to_species, _ = aggregate_lifer_sites(
        lifer_lookup_df,
        true_lifer_locations,
        true_lifer_locations_taxon,
    )
    if not loc_to_species:
        return MapOverlayResult(
            None,
            warning="⚠️ No lifer locations found in your dataset.",
        )
    n_species_lifers = len(true_lifer_locations)
    n_subspecies_lifers = count_subspecies_lifer_taxa(lifer_lookup_df, true_lifer_locations_taxon)
    # Viewport framing: base-species lifer locations only (never subspecies-only sites).
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
        return MapOverlayResult(
            None,
            warning="⚠️ No lifer locations match your location table.",
        )
    if framing_pairs:
        map_center = [
            sum(p[0] for p in framing_pairs) / len(framing_pairs),
            sum(p[1] for p in framing_pairs) / len(framing_pairs),
        ]
    else:
        map_center = [loc_rows["Latitude"].mean(), loc_rows["Longitude"].mean()]
    species_map = create_map(map_center, map_style, height_px=map_height_px)
    inject_map_overlay_theme(species_map)
    add_zoom_level_debug_overlay(species_map, enabled=MAP_DEBUG_SHOW_ZOOM_LEVEL)
    popup_asc = popup_sort_order == "ascending"
    date_filter_status_line = date_filter_status or None
    n_locations = int(loc_rows["Location ID"].nunique())
    le, lf, se, sp, r_lifer, r_species, stroke_w, fo_lif, fo_spec = resolve_lifer_overlay_pin_params(
        visit_marker_scheme
    )
    species_map.get_root().html.add_child(
        Element(
            build_lifer_locations_banner_html(
                n_species_lifers,
                n_locations,
                date_filter_status_line,
                include_subspecies=bool(show_subspecies_lifers),
                n_subspecies_lifers=n_subspecies_lifers if show_subspecies_lifers else None,
            )
        )
    )
    loc_kind_by_id: dict[Any, str] = {}
    if not show_subspecies_lifers:
        species_map.get_root().html.add_child(Element(build_legend_html([(le, lf, "Lifer")])))
    else:

        def _loc_kind(entries: list[dict]) -> str:
            """``lifer`` = species first-seen (base lifer) at this location; ``subspecies`` = taxon lifer only.

            When base and taxon lifers coincide, use a single **Lifer** pin (no double ring).
            """
            for e in entries:
                if e.get("is_base_lifer"):
                    return "lifer"
            return "subspecies"

        loc_kind_by_id = {lid: _loc_kind(entries) for lid, entries in loc_to_species.items()}
        kinds_present = set(loc_kind_by_id.values())
        legend_items = []
        if "lifer" in kinds_present:
            legend_items.append((le, lf, "Lifer"))
        if "subspecies" in kinds_present:
            legend_items.append((se, sp, "Subspecies"))
        species_map.get_root().html.add_child(Element(build_legend_html(legend_items)))

    lite_b = bool(lite_map_popups)
    # I1/I2 counters (#205 batch 4); zero-cost when ``metrics_sink is None`` other than the
    # per-cache-miss ``time.perf_counter`` pair.
    _m_count = 0
    _p_built = 0
    _p_hit = 0
    _p_build_ms = 0.0
    for _, row in loc_rows.iterrows():
        lid = row["Location ID"]
        popup_key = (lid, "__lifer_map__", effective_use_full, tax_loc_key, bool(show_subspecies_lifers), lite_b)
        if popup_key not in popup_html_cache:
            _p_built += 1
            _t_p0 = time.perf_counter()
            if lite_b:
                popup_html_cache[popup_key] = build_location_popup_html(
                    row["Location"],
                    lid,
                    "",
                    show_visit_history=False,
                    lifer_heading_html="",
                    location_heading_margin_px=2,
                )
            else:
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
            _p_build_ms += (time.perf_counter() - _t_p0) * 1000.0
        else:
            _p_hit += 1
        popup_html = popup_html_cache[popup_key]
        if not show_subspecies_lifers:
            popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=r_lifer,
                color=le,
                weight=stroke_w,
                fill=True,
                fill_color=lf,
                fill_opacity=fo_lif,
                popup=popup,
            ).add_to(species_map)
            _m_count += 1
        else:
            latlng = [row["Latitude"], row["Longitude"]]
            loc_kind = loc_kind_by_id.get(lid, "lifer")
            if loc_kind == "subspecies":
                popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
                folium.CircleMarker(
                    location=latlng,
                    radius=r_species,
                    color=se,
                    weight=stroke_w,
                    fill=True,
                    fill_color=sp,
                    fill_opacity=fo_spec,
                    popup=popup,
                ).add_to(species_map)
                _m_count += 1
            else:
                popup = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)
                folium.CircleMarker(
                    location=latlng,
                    radius=r_lifer,
                    color=le,
                    weight=stroke_w,
                    fill=True,
                    fill_color=lf,
                    fill_opacity=fo_lif,
                    popup=popup,
                ).add_to(species_map)
                _m_count += 1

    if metrics_sink is not None:
        metrics_sink["view_path"] = "lifer"
        metrics_sink["marker_count"] = _m_count
        metrics_sink["popup_build_count"] = _p_built
        metrics_sink["popup_cache_hit_count"] = _p_hit
        metrics_sink["popup_build_total_ms"] = round(_p_build_ms, 3)

    # Initial viewport follows base lifer extent only; subspecies toggle does not change these bounds.
    if framing_pairs:
        pad = int(MAP_LIFER_MAP_FIT_BOUNDS_PADDING_PX)
        max_z = int(MAP_LIFER_MAP_FIT_BOUNDS_MAX_ZOOM)
        if len(framing_pairs) == 1:
            la, lo = float(framing_pairs[0][0]), float(framing_pairs[0][1])
            species_map.fit_bounds(
                _epsilon_bounds_around_point(la, lo),
                padding=(pad, pad),
                max_zoom=int(MAP_LIFER_MAP_SINGLE_POINT_ZOOM),
            )
        else:
            species_map.fit_bounds(framing_pairs, padding=(pad, pad), max_zoom=max_z)

    scroll_popup_script = popup_scroll_script(popup_scroll_hint, popup_asc)
    species_map.get_root().html.add_child(Element(scroll_popup_script))
    return MapOverlayResult(species_map, None)
