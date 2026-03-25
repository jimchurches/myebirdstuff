"""
Framework-neutral map build pipeline for the species overlay map.

Extracted from the notebook so Streamlit or other UIs can call
``build_species_overlay_map`` with data + options and receive a Folium map
(no ipywidgets). Notebook keeps display double-buffering and widget I/O (refs #67).
"""

from __future__ import annotations

import html as html_module
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, List, MutableMapping, Optional, Tuple, cast

import folium
import pandas as pd
from branca.element import Element

from personal_ebird_explorer.lifer_last_seen_prep import aggregate_lifer_sites
from personal_ebird_explorer.map_renderer import (
    build_all_species_banner_html,
    build_legend_html,
    build_lifer_locations_banner_html,
    build_location_popup_html,
    build_species_banner_html,
    build_visit_info_html,
    classify_locations,
    create_map,
    format_sighting_row,
    format_visit_time,
    map_overlay_theme_stylesheet,
    popup_scroll_script,
    resolve_lifer_last_seen,
)
from streamlit_app.defaults import (
    MAP_CIRCLE_MARKER_RADIUS_PX,
    MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    MAP_PIN_FILL_OPACITY_EMPHASIS,
    MAP_POPUP_MAX_WIDTH_PX,
)
from personal_ebird_explorer.species_logic import base_species_for_lifer, filter_species
from personal_ebird_explorer.stats import safe_count

SpeciesUrlFn = Optional[Callable[[str], Optional[str]]]
BaseSpeciesFn = Callable[[str], Optional[str]]

_VALID_MAP_VIEWS = frozenset({"all", "species", "lifers"})


def _inject_map_popup_theme(map_obj: folium.Map) -> None:
    """Inject shared CSS: Leaflet popups + fixed banner/legend chrome (Streamlit theme; refs #70)."""
    map_obj.get_root().html.add_child(Element(map_overlay_theme_stylesheet()))


def _format_lifer_species_popup_lines(
    rows: List[Tuple[str, str]],
    species_url_fn: SpeciesUrlFn,
) -> str:
    """HTML fragment: one line per lifer species (optional eBird species links)."""
    parts: List[str] = []
    for sci, common in rows:
        label = common if common else sci
        esc_label = html_module.escape(label)
        url = None
        if species_url_fn:
            url = species_url_fn(common) if common else species_url_fn(sci)
        if url:
            esc_url = html_module.escape(url, quote=True)
            parts.append(
                f'<br><a href="{esc_url}" target="_blank" rel="noopener">{esc_label}</a>'
            )
        else:
            parts.append(f"<br>{esc_label}")
    return "".join(parts)


@dataclass
class MapOverlayResult:
    """Outcome of :func:`build_species_overlay_map`."""

    map: Optional[folium.Map]
    """Folium map when build succeeds; ``None`` when *warning* is set."""

    warning: Optional[str] = None
    """User-facing message (e.g. no sightings for species in current data)."""


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
    lifer_color: str = "purple",
    lifer_fill: str = "yellow",
    last_seen_color: str = "purple",
    last_seen_fill: str = "lightgreen",
    species_color: str = "purple",
    species_fill: str = "red",
    default_color: str = "green",
    default_fill: str = "lightgreen",
    mark_lifer: bool = True,
    mark_last_seen: bool = True,
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
) -> MapOverlayResult:
    """Build the Folium map for all-species, one-species, or lifer-locations overlay.

    *map_view_mode*: ``"all"`` | ``"species"`` | ``"lifers"`` (refs #71). When
    ``"lifers"``, *selected_species* is ignored; *full_location_data* must be the
    full-export location table (same scope as lifer prep).

    *popup_html_cache* and *filtered_by_loc_cache* are mutated by this function
    (session caches; same contract as the notebook). Popup cache keys include
    *taxonomy_locale* so eBird species links refresh when the locale changes (Streamlit Settings).

    *date_filter_status* is shown in banners (e.g. ``Date filter: Off``); pass
    ``""`` to omit the extra line.
    """
    tax_loc_key = (taxonomy_locale or "").strip()
    mode = (map_view_mode or "all").strip().lower()
    if mode not in _VALID_MAP_VIEWS:
        mode = "all"
    if mode == "species" and not (selected_species or "").strip():
        mode = "all"

    if mode == "lifers":
        if full_location_data is None or full_location_data.empty:
            return MapOverlayResult(
                None,
                warning="⚠️ Lifer map mode requires full location data.",
            )
        loc_to_species, n_lifer_species = aggregate_lifer_sites(
            lifer_lookup_df,
            true_lifer_locations,
            true_lifer_locations_taxon,
        )
        if not loc_to_species:
            return MapOverlayResult(
                None,
                warning="⚠️ No lifer locations found in your dataset.",
            )
        lifer_loc_ids = set(loc_to_species.keys())
        loc_rows = full_location_data[full_location_data["Location ID"].isin(lifer_loc_ids)]
        if loc_rows.empty:
            return MapOverlayResult(
                None,
                warning="⚠️ No lifer locations match your location table.",
            )
        map_center = [loc_rows["Latitude"].mean(), loc_rows["Longitude"].mean()]
        species_map = create_map(map_center, map_style)
        _inject_map_popup_theme(species_map)
        popup_asc = popup_sort_order == "ascending"
        dfs = date_filter_status or None
        n_locations = int(loc_rows["Location ID"].nunique())
        species_map.get_root().html.add_child(
            Element(build_lifer_locations_banner_html(n_lifer_species, n_locations, dfs))
        )
        species_map.get_root().html.add_child(
            Element(build_legend_html([(lifer_color, lifer_fill, "Lifer")]))
        )
        for _, row in loc_rows.iterrows():
            lid = row["Location ID"]
            popup_key = (lid, "__lifer_map__", effective_use_full, tax_loc_key)
            if popup_key not in popup_html_cache:
                base_records = effective_records_by_loc.get(lid, pd.DataFrame())
                visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values(
                    "datetime", ascending=popup_asc
                )
                visit_info = build_visit_info_html(visit_records, format_visit_time)
                lifer_lines = _format_lifer_species_popup_lines(
                    loc_to_species.get(lid, []),
                    species_url_fn,
                )
                popup_html_cache[popup_key] = build_location_popup_html(
                    row["Location"],
                    lid,
                    visit_info,
                    lifer_species_html=lifer_lines,
                )
            popup_html = popup_html_cache[popup_key]
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=MAP_CIRCLE_MARKER_RADIUS_PX,
                color=lifer_color,
                weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
                fill=True,
                fill_color=lifer_fill,
                fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
                popup=folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX),
            ).add_to(species_map)
        scroll_popup_script = popup_scroll_script(popup_scroll_hint, popup_sort_order == "ascending")
        species_map.get_root().html.add_child(Element(scroll_popup_script))
        return MapOverlayResult(species_map, None)

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
        map_center = [
            effective_location_data["Latitude"].mean(),
            effective_location_data["Longitude"].mean(),
        ]

    species_map = create_map(map_center, map_style)
    _inject_map_popup_theme(species_map)
    popup_asc = popup_sort_order == "ascending"
    dfs = date_filter_status or None

    if not selected_species:
        tc, ts, ti = effective_totals
        species_map.get_root().html.add_child(
            Element(build_all_species_banner_html(tc, ts, ti, dfs))
        )
        species_map.get_root().html.add_child(
            Element(build_legend_html([(default_color, default_fill, "All locations")]))
        )

        for _, row in effective_location_data.iterrows():
            popup_key = (row["Location ID"], "", effective_use_full, tax_loc_key)
            if popup_key not in popup_html_cache:
                base_records = effective_records_by_loc.get(row["Location ID"], pd.DataFrame())
                visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values(
                    "datetime", ascending=popup_asc
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
            ).add_to(species_map)

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

        high_count_rows = filtered[filtered["Count"].apply(safe_count) == high_count]
        if not high_count_rows.empty:
            high_count_date = _banner_date(high_count_rows.iloc[0]["Date"])

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
                    date_filter_status=dfs,
                    species_url=species_url,
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
                    "datetime", ascending=popup_asc
                )
                visit_info = build_visit_info_html(visit_records, format_visit_time)
                sightings_html = ""
                if row["has_species_match"]:
                    sub = filtered_by_loc.get(loc_id, pd.DataFrame()).sort_values(
                        "datetime", ascending=popup_asc
                    )
                    sightings_html = "".join(format_sighting_row(r) for _, r in sub.iterrows())
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
