"""
Framework-neutral map build pipeline for the species overlay map.

Streamlit (or any host) calls :func:`build_species_overlay_map` with data and options and receives
Folium HTML.

Implementation is split for readability:

- :mod:`explorer.core.map_overlay_types` — result type and callback aliases
- :mod:`explorer.core.map_overlay_theme` — shared popup/banner CSS injection
- :mod:`explorer.core.map_overlay_lifer_popups` — HTML for lifer popup lines
- :mod:`explorer.core.map_overlay_lifer_map` — **Lifer locations** map mode
- :mod:`explorer.core.map_overlay_visit_map` — **All locations** and **Selected species** modes

This module keeps the public entry point and normalises *map_view_mode*.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, Hashable, MutableMapping, Optional, Tuple

import pandas as pd

from explorer.app.streamlit.defaults import MAP_HEIGHT_PX_DEFAULT, MapMarkerColourScheme
from explorer.core.map_overlay_lifer_map import build_lifer_overlay_map
from explorer.core.map_overlay_types import (
    BaseSpeciesFn,
    MapOverlayResult,
    SpeciesUrlFn,
    VALID_MAP_VIEWS,
)
from explorer.core.all_locations_viewport import ALL_LOCATIONS_SCOPE_FOCUSED
from explorer.core.map_overlay_visit_map import build_visit_overlay_map
from explorer.core.species_logic import base_species_for_lifer

# Re-export for ``from explorer.core.map_controller import MapOverlayResult`` (tests, lazy barrel).
__all__ = ["MapOverlayResult", "build_species_overlay_map", "SpeciesUrlFn", "BaseSpeciesFn"]


def build_species_overlay_map(
    *,
    df: pd.DataFrame,
    location_data: pd.DataFrame,
    records_by_loc: Dict[Hashable, pd.DataFrame],
    effective_location_data: pd.DataFrame,
    effective_records_by_loc: Dict[Hashable, pd.DataFrame],
    effective_totals: Tuple[int, int, int],
    effective_use_full: bool,
    lifer_lookup_df: pd.DataFrame,
    true_lifer_locations: Dict[str, Any],
    true_last_seen_locations: Dict[str, Any],
    true_lifer_locations_taxon: Dict[str, Any],
    true_last_seen_locations_taxon: Dict[str, Any],
    selected_species: str,
    selected_common_name: str = "",
    map_style: str = "default",
    popup_sort_order: str = "ascending",
    popup_scroll_hint: str = "shading",
    mark_lifer: bool = True,
    mark_last_seen: bool = True,
    cluster_all_locations: bool = True,
    hide_non_matching_locations: bool = False,
    date_filter_status: str = "",
    species_url_fn: SpeciesUrlFn = None,
    base_species_fn: BaseSpeciesFn = base_species_for_lifer,
    popup_html_cache: MutableMapping[Tuple[Any, ...], str],
    filtered_by_loc_cache: OrderedDict,
    filtered_by_loc_cache_max: int = 60,
    map_view_mode: str = "all",
    full_location_data: Optional[pd.DataFrame] = None,
    taxonomy_locale: str = "",
    show_subspecies_lifers: bool = False,
    map_height_px: int = MAP_HEIGHT_PX_DEFAULT,
    visit_marker_scheme: MapMarkerColourScheme,
    all_locations_scope: str | None = None,
    all_locations_location_country: dict[Hashable, str] | None = None,
) -> MapOverlayResult:
    """Build the Folium map for all-species, one-species, or lifer-locations overlay.

    *map_view_mode*: ``"all"`` | ``"species"`` | ``"lifers"``. When
    ``"lifers"``, *selected_species* is ignored; *full_location_data* must be the
    full-export location table (same scope as lifer prep).

    *popup_html_cache* and *filtered_by_loc_cache* are mutated by this function
    (session caches; same contract as the UI). Popup cache keys include
    *taxonomy_locale* so eBird species links refresh when the locale changes (Streamlit Settings).

    *date_filter_status*: optional extra muted line on map banners (e.g. date range). The Streamlit
    app passes ``""`` so filter state stays in the sidebar only (refs #150); non-UI callers may
    still pass a string for export or notebooks.

    *cluster_all_locations*: when there is no species filter (All locations view),
    group nearby pins with Leaflet.markercluster. Ignored for species and lifer maps.

    *hide_non_matching_locations*: in **Species locations** view with no species selected, when
    ``True`` an empty map is shown until a species is chosen. When ``False`` and the view is still
    **All locations**, the full map is shown; **Species** view with no selection is always empty (refs #147).

    *map_height_px*: pixel height for the Folium map pane (match Streamlit **Map height** slider).

    *visit_marker_scheme*: active :class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme`
    (resolved via :mod:`explorer.core.map_marker_colour_resolve`) for **All locations**, **Species
    locations**, and **Lifer locations** pins (colours, radii, stroke weight, fill opacities, cluster
    tiers).
    """
    tax_loc_key = (taxonomy_locale or "").strip()
    mode = (map_view_mode or "all").strip().lower()
    if mode not in VALID_MAP_VIEWS:
        mode = "all"

    if mode == "lifers":
        return build_lifer_overlay_map(
            full_location_data=full_location_data,
            lifer_lookup_df=lifer_lookup_df,
            true_lifer_locations=true_lifer_locations,
            true_lifer_locations_taxon=true_lifer_locations_taxon,
            map_style=map_style,
            map_height_px=map_height_px,
            popup_sort_order=popup_sort_order,
            popup_scroll_hint=popup_scroll_hint,
            date_filter_status=date_filter_status,
            popup_html_cache=popup_html_cache,
            tax_loc_key=tax_loc_key,
            show_subspecies_lifers=show_subspecies_lifers,
            effective_use_full=effective_use_full,
            base_species_fn=base_species_fn,
            visit_marker_scheme=visit_marker_scheme,
        )

    # Species overlay is driven by a non-empty *selected_species* (same as legacy behaviour), not only
    # when *map_view_mode* is the string ``"species"`` (Streamlit may pass mode ``"all"`` with a pick).
    sel = (selected_species or "").strip()

    return build_visit_overlay_map(
        df=df,
        location_data=location_data,
        records_by_loc=records_by_loc,
        effective_location_data=effective_location_data,
        effective_records_by_loc=effective_records_by_loc,
        effective_totals=effective_totals,
        effective_use_full=effective_use_full,
        lifer_lookup_df=lifer_lookup_df,
        true_lifer_locations=true_lifer_locations,
        true_last_seen_locations=true_last_seen_locations,
        true_lifer_locations_taxon=true_lifer_locations_taxon,
        true_last_seen_locations_taxon=true_last_seen_locations_taxon,
        selected_species=sel,
        selected_common_name=selected_common_name,
        map_style=map_style,
        popup_sort_order=popup_sort_order,
        popup_scroll_hint=popup_scroll_hint,
        mark_lifer=mark_lifer,
        mark_last_seen=mark_last_seen,
        cluster_all_locations=cluster_all_locations,
        hide_non_matching_locations=hide_non_matching_locations,
        date_filter_status=date_filter_status,
        species_url_fn=species_url_fn,
        base_species_fn=base_species_fn,
        popup_html_cache=popup_html_cache,
        filtered_by_loc_cache=filtered_by_loc_cache,
        filtered_by_loc_cache_max=filtered_by_loc_cache_max,
        tax_loc_key=tax_loc_key,
        map_height_px=map_height_px,
        visit_marker_scheme=visit_marker_scheme,
        map_view_mode=mode,
        all_locations_scope=all_locations_scope or ALL_LOCATIONS_SCOPE_FOCUSED,
        all_locations_location_country=all_locations_location_country,
    )
