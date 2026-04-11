"""Folium map build for **All locations** and **Selected species** overlay views."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, Hashable, MutableMapping, Optional, Tuple, cast

import folium
import pandas as pd
from branca.element import Element
from folium.plugins import MarkerCluster

from explorer.app.streamlit.defaults import (
    MAP_CIRCLE_MARKER_RADIUS_PX,
    MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    MAP_DEBUG_SHOW_ZOOM_LEVEL,
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    MAP_PIN_FILL_OPACITY_EMPHASIS,
)
from explorer.core.map_overlay_theme import inject_map_overlay_theme
from explorer.core.map_overlay_types import BaseSpeciesFn, MapOverlayResult, SpeciesUrlFn
from explorer.presentation.map_renderer import (
    add_zoom_level_debug_overlay,
    build_all_species_banner_html,
    build_legend_html,
    build_location_popup_html,
    build_species_banner_html,
    build_species_locations_awaiting_selection_banner_html,
    build_visit_info_html,
    classify_locations,
    create_map,
    format_sighting_row,
    format_visit_time,
    popup_scroll_script,
    resolve_lifer_last_seen,
)
from explorer.presentation.map_ui_constants import MAP_POPUP_MAX_WIDTH_PX
from explorer.core.species_logic import filter_species
from explorer.core.stats import safe_count


def build_visit_overlay_map(
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
    selected_common_name: str,
    map_style: str,
    popup_sort_order: str,
    popup_scroll_hint: str,
    lifer_color: str,
    lifer_fill: str,
    last_seen_color: str,
    last_seen_fill: str,
    species_color: str,
    species_fill: str,
    default_color: str,
    default_fill: str,
    mark_lifer: bool,
    mark_last_seen: bool,
    cluster_all_locations: bool,
    hide_non_matching_locations: bool,
    date_filter_status: str,
    species_url_fn: SpeciesUrlFn,
    base_species_fn: BaseSpeciesFn,
    popup_html_cache: MutableMapping[Tuple[Any, ...], str],
    filtered_by_loc_cache: OrderedDict,
    filtered_by_loc_cache_max: int,
    tax_loc_key: str,
    map_height_px: int,
) -> MapOverlayResult:
    """Build all-locations or species-filtered overlay (not lifer-locations mode)."""
    if selected_species:
        filtered = filter_species(df, selected_species)
        if filtered.empty:
            return MapOverlayResult(
                None,
                warning=(
                    f"⚠️ No sightings of '{selected_species}' in current data — "
                    "check date range or filters."
                ),
            )
        seen_location_ids = set(filtered["Location ID"])
        species_locations = location_data[location_data["Location ID"].isin(seen_location_ids)]
        map_center = [species_locations["Latitude"].mean(), species_locations["Longitude"].mean()]
    else:
        seen_location_ids = set()
        filtered = pd.DataFrame()
        map_center = [
            effective_location_data["Latitude"].mean(),
            effective_location_data["Longitude"].mean(),
        ]

    popup_ascending = popup_sort_order == "ascending"
    date_filter_status_line = date_filter_status or None

    if not selected_species and hide_non_matching_locations:
        if effective_location_data.empty:
            lat, lon = -25.0, 134.0
        else:
            lat = float(effective_location_data["Latitude"].mean())
            lon = float(effective_location_data["Longitude"].mean())
            if pd.isna(lat) or pd.isna(lon):
                lat, lon = -25.0, 134.0
        map_center_empty = [lat, lon]
        species_map = create_map(map_center_empty, map_style, height_px=map_height_px)
        inject_map_overlay_theme(species_map)
        add_zoom_level_debug_overlay(species_map, enabled=MAP_DEBUG_SHOW_ZOOM_LEVEL)
        species_map.get_root().html.add_child(
            Element(build_species_locations_awaiting_selection_banner_html(date_filter_status_line))
        )
        scroll_popup_script = popup_scroll_script(
            popup_scroll_hint, popup_sort_order == "ascending"
        )
        species_map.get_root().html.add_child(Element(scroll_popup_script))
        return MapOverlayResult(species_map, None)

    species_map = create_map(map_center, map_style, height_px=map_height_px)
    inject_map_overlay_theme(species_map)
    add_zoom_level_debug_overlay(species_map, enabled=MAP_DEBUG_SHOW_ZOOM_LEVEL)

    if not selected_species:
        tc, ts, ti = effective_totals
        species_map.get_root().html.add_child(
            Element(build_all_species_banner_html(tc, ts, ti, date_filter_status_line))
        )
        species_map.get_root().html.add_child(
            Element(build_legend_html([(default_color, default_fill, "All locations")]))
        )

        marker_cluster: Optional[MarkerCluster] = None
        if cluster_all_locations:
            marker_cluster = MarkerCluster(
                name="All locations",
                options={
                    "maxClusterRadius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
                    "disableClusteringAtZoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
                    "spiderfyOnMaxZoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
                    "zoomToBoundsOnClick": True,
                },
            )
        pin_parent: folium.Map | MarkerCluster = marker_cluster if marker_cluster is not None else species_map

        for _, row in effective_location_data.iterrows():
            popup_key = (row["Location ID"], "", effective_use_full, tax_loc_key)
            if popup_key not in popup_html_cache:
                base_records = effective_records_by_loc.get(row["Location ID"], pd.DataFrame())
                visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values(
                    "datetime", ascending=popup_ascending
                )
                visit_info = build_visit_info_html(visit_records, format_visit_time)
                popup_html_cache[popup_key] = build_location_popup_html(
                    row["Location"], row["Location ID"], visit_info
                )
            popup_html = popup_html_cache[popup_key]
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                color=default_color,
                weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                fill=True,
                fill_color=default_fill,
                fill_opacity=MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
                popup=folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX),
            ).add_to(pin_parent)

        if marker_cluster is not None:
            marker_cluster.add_to(species_map)

    else:
        if selected_species not in filtered_by_loc_cache:
            if len(filtered_by_loc_cache) >= filtered_by_loc_cache_max:
                filtered_by_loc_cache.popitem(last=False)
            filtered_by_loc_cache[selected_species] = {
                lid: grp for lid, grp in filtered.groupby("Location ID")
            }
        else:
            filtered_by_loc_cache.move_to_end(selected_species)
        filtered_by_loc = cast(Dict[Hashable, pd.DataFrame], filtered_by_loc_cache[selected_species])

        n_checklists = filtered["Submission ID"].nunique()
        n_individuals = int(filtered["Count"].apply(safe_count).sum())
        high_count = int(filtered["Count"].apply(safe_count).max())

        def _banner_date(d):
            return d.strftime("%d-%b-%Y") if pd.notna(d) else "?"

        first_seen_date = ""
        last_seen_date = ""
        high_count_date = ""
        first_seen_url: str | None = None
        last_seen_url: str | None = None
        high_count_url: str | None = None
        sci_parts_banner = (selected_species or "").strip().split()
        is_subspecies_banner = len(sci_parts_banner) >= 3
        taxon_key_banner = selected_species.strip().lower() if selected_species else None
        if is_subspecies_banner and taxon_key_banner:
            subset = lifer_lookup_df[lifer_lookup_df["_taxon"] == taxon_key_banner]
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
            high_count_checklist_id = high_count_row.get("Submission ID", "")
            if pd.notna(high_count_checklist_id) and str(high_count_checklist_id).strip():
                high_count_url = (
                    f"https://ebird.org/checklist/{str(high_count_checklist_id).strip()}"
                )

        display_name = selected_common_name or selected_species
        species_url = species_url_fn(display_name) if species_url_fn else None

        species_map.get_root().html.add_child(
            Element(
                build_species_banner_html(
                    display_name=display_name,
                    n_checklists=n_checklists,
                    n_individuals=n_individuals,
                    high_count=high_count,
                    first_seen_date=first_seen_date,
                    last_seen_date=last_seen_date,
                    high_count_date=high_count_date,
                    date_filter_status=date_filter_status_line,
                    species_url=species_url,
                    first_seen_checklist_url=first_seen_url,
                    last_seen_checklist_url=last_seen_url,
                    high_count_checklist_url=high_count_url,
                )
            )
        )

        lifer_location, last_seen_location = resolve_lifer_last_seen(
            selected_species,
            seen_location_ids,
            lifer_lookup=true_lifer_locations,
            last_seen_lookup=true_last_seen_locations,
            lifer_lookup_taxon=true_lifer_locations_taxon,
            last_seen_lookup_taxon=true_last_seen_locations_taxon,
            base_species_fn=base_species_fn,
            mark_lifer=mark_lifer,
            mark_last_seen=mark_last_seen,
        )
        location_data_local = classify_locations(
            location_data, seen_location_ids, lifer_location, last_seen_location
        )

        pin_types_present = set()
        for _, row in location_data_local.iterrows():
            if not row["has_species_match"] and hide_non_matching_locations:
                continue
            if row["is_lifer"]:
                pin_types_present.add("Lifer")
            elif row["is_last_seen"]:
                pin_types_present.add("Last seen")
            elif row["has_species_match"]:
                pin_types_present.add("Species")
            else:
                pin_types_present.add("Other")
        legend_order = [
            ("Lifer", lifer_color, lifer_fill),
            ("Last seen", last_seen_color, last_seen_fill),
            ("Species", species_color, species_fill),
            ("Other", default_color, default_fill),
        ]
        legend_items = [(c, f, label) for label, c, f in legend_order if label in pin_types_present]
        species_map.get_root().html.add_child(Element(build_legend_html(legend_items)))

        for _, row in location_data_local.iterrows():
            loc_id = row["Location ID"]

            if not row["has_species_match"] and hide_non_matching_locations:
                continue

            popup_key = (loc_id, selected_species, tax_loc_key)
            if popup_key not in popup_html_cache:
                base_records = records_by_loc.get(loc_id, pd.DataFrame())
                visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values(
                    "datetime", ascending=popup_ascending
                )
                visit_info = build_visit_info_html(visit_records, format_visit_time)
                sightings_html = ""
                if row["has_species_match"]:
                    species_sightings = filtered_by_loc.get(loc_id, pd.DataFrame()).sort_values(
                        "datetime", ascending=popup_ascending
                    )
                    sightings_html = "".join(
                        format_sighting_row(r) for _, r in species_sightings.iterrows()
                    )
                popup_html_cache[popup_key] = build_location_popup_html(
                    row["Location"], loc_id, visit_info, sightings_html
                )
            popup_html = popup_html_cache[popup_key]
            popup_content = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)

            if row["is_lifer"]:
                color, fill, fill_opacity = lifer_color, lifer_fill, MAP_PIN_FILL_OPACITY_EMPHASIS
            elif row["is_last_seen"]:
                color, fill, fill_opacity = last_seen_color, last_seen_fill, MAP_PIN_FILL_OPACITY_EMPHASIS
            elif row["has_species_match"]:
                color, fill, fill_opacity = species_color, species_fill, MAP_PIN_FILL_OPACITY_EMPHASIS
            else:
                color, fill, fill_opacity = default_color, default_fill, MAP_PIN_FILL_OPACITY_EMPHASIS

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                color=color,
                weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                fill=True,
                fill_color=fill,
                fill_opacity=fill_opacity,
                popup=popup_content,
            ).add_to(species_map)

    scroll_popup_script = popup_scroll_script(popup_scroll_hint, popup_sort_order == "ascending")
    species_map.get_root().html.add_child(Element(scroll_popup_script))

    return MapOverlayResult(species_map, None)
