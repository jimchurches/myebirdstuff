"""Folium map build for **All locations** and **Selected species** overlay views."""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any, Dict, Hashable, Literal, MutableMapping, Optional, Tuple, cast

import folium
import pandas as pd
from branca.element import Element
from folium.plugins import MarkerCluster

from explorer.app.streamlit.defaults import (
    MAP_DEBUG_SHOW_ZOOM_LEVEL,
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT,
    MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT,
    MapMarkerColourScheme,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.core.map_marker_colour_resolve import (
    is_valid_hex_colour,
    normalize_marker_hex,
    resolve_location_visit_colours,
    resolve_species_visit_pin,
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
    build_species_map_location_popup_html,
    build_visit_info_html,
    classify_locations,
    create_map,
    format_visit_time,
    popup_scroll_script,
    resolve_lifer_last_seen,
)
from explorer.presentation.map_ui_constants import MAP_POPUP_MAX_WIDTH_PX
from explorer.core.species_logic import filter_species
from explorer.core.stats import safe_count


def _all_locations_marker_params_from_scheme(sch: MapMarkerColourScheme) -> tuple[str, str, int, int, float]:
    """Resolved fill, edge (stroke), radius (px), stroke weight, fill opacity for **All locations** view."""
    fill_c, edge = resolve_location_visit_colours(sch)
    g = sch.global_defaults
    al = sch.all_locations
    md = int(g.circle_radius_px)
    loc = al.radius_override_px
    radius_px = clamp_map_marker_circle_radius_px(loc if loc is not None else md)
    sw_raw = al.stroke_weight
    if sw_raw is None:
        sw_raw = g.base_stroke_weight
    sw = max(1, int(sw_raw))
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(g, "circle_fill_opacity", None),
        fallback=0.88,
    )
    legacy_fo = float(al.fill_opacity) if al.fill_opacity is not None else md_fo
    fo_override = al.fill_opacity_override
    fo = (
        clamp_map_marker_circle_fill_opacity(fo_override, fallback=legacy_fo)
        if fo_override is not None
        else legacy_fo
    )
    return fill_c, edge, radius_px, sw, fo


def _hex_to_rgba_css(hex_str: str, alpha: float, *, channel: str) -> str:
    """Convert ``#RRGGBB`` to ``rgba(r,g,b,a)`` for CSS (cluster icon inline styles)."""
    h = normalize_marker_hex(hex_str, channel=channel).lstrip("#")
    if len(h) < 6:
        h = (h + "000000")[:6]
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({r},{g},{b},{a})"


def _marker_cluster_root_background_reset_css() -> str:
    """CSS to clear default MarkerCluster *root* tier backgrounds.

    Leaflet.markercluster styles the **root** ``.marker-cluster-small|medium|large`` with a semi-transparent
    halo. Our ``iconCreateFunction`` must keep the stock DOM shape (**one** inner ``<div>`` wrapping
    ``<span>``) so ``.marker-cluster div`` rules still size/center the inner disc. We paint fill, border,
    and halo-like ring on that single inner div (``box-shadow`` ring) and make the root transparent so
    those defaults do not stack as a third offset circle.
    """
    return (
        "<style>"
        ".leaflet-marker-icon.marker-cluster.marker-cluster-small,"
        ".leaflet-marker-icon.marker-cluster.marker-cluster-medium,"
        ".leaflet-marker-icon.marker-cluster.marker-cluster-large"
        "{background:transparent!important;}"
        "</style>"
    )


def _marker_cluster_icon_create_function_from_scheme(
    sch: Any,
) -> str | None:
    """Return Leaflet.markercluster ``iconCreateFunction`` for configured cluster icon tier colours.

    Duck-typed: ``MapMarkerColourScheme`` (reads ``all_locations.cluster.*``),
    :class:`~explorer.presentation.design_map_preview.DesignMapPreviewConfig` (flat ``marker_cluster_*`` fields),
    or any object exposing the same attributes.

    Expects nine cluster tier colours (``colours_hex`` or legacy ``marker_cluster_colours_hex``) with nine values
    ``(small_fill, small_border, small_halo, medium_fill, medium_border, medium_halo, large_fill, large_border, large_halo)``.
    If unset or invalid, returns ``None`` so Folium / Leaflet.markercluster defaults apply.
    """

    def _cluster_colours_tuple() -> tuple[str, ...] | None:
        if sch is None:
            return None
        al = getattr(sch, "all_locations", None)
        if al is not None:
            cl = getattr(al, "cluster", None)
            if cl is not None:
                v = getattr(cl, "colours_hex", None)
                if v is not None:
                    t = tuple(v) if isinstance(v, (tuple, list)) else None
                    if t is not None and len(t) == 9:
                        return t
        vals = getattr(sch, "marker_cluster_colours_hex", None)
        if vals is None:
            return None
        t = tuple(vals) if isinstance(vals, (tuple, list)) else None
        return t if t is not None and len(t) == 9 else None

    def _resolve_cluster_colours() -> tuple[list[str], list[str], list[str]] | None:
        raw_tuple = _cluster_colours_tuple()
        if raw_tuple is None:
            return None
        vals = raw_tuple
        try:
            raw = tuple(str(vals[i]) for i in range(9))
        except Exception:
            return None
        if not all(is_valid_hex_colour(x) for x in raw):
            return None
        fills = [
            normalize_marker_hex(raw[0], channel="fill"),
            normalize_marker_hex(raw[3], channel="fill"),
            normalize_marker_hex(raw[6], channel="fill"),
        ]
        borders = [
            normalize_marker_hex(raw[1], channel="edge"),
            normalize_marker_hex(raw[4], channel="edge"),
            normalize_marker_hex(raw[7], channel="edge"),
        ]
        halos = [
            normalize_marker_hex(raw[2], channel="fill"),
            normalize_marker_hex(raw[5], channel="fill"),
            normalize_marker_hex(raw[8], channel="fill"),
        ]
        return fills, borders, halos

    if sch is None:
        return None
    col = _resolve_cluster_colours()
    if col is None:
        return None
    fills, borders, halos = col

    def _o(nested_attr: str, flat_attr: str, default: float) -> float:
        al = getattr(sch, "all_locations", None)
        if al is not None:
            cl = getattr(al, "cluster", None)
            if cl is not None:
                v = getattr(cl, nested_attr, None)
                if v is not None:
                    try:
                        return max(0.0, min(1.0, float(v)))
                    except (TypeError, ValueError):
                        pass
        v = getattr(sch, flat_attr, None)
        if v is None:
            return default
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return default

    def _oi(nested_attr: str, flat_attr: str, default: int, *, hi: int) -> int:
        al = getattr(sch, "all_locations", None)
        if al is not None:
            cl = getattr(al, "cluster", None)
            if cl is not None:
                v = getattr(cl, nested_attr, None)
                if v is not None:
                    try:
                        return max(0, min(hi, int(v)))
                    except (TypeError, ValueError):
                        pass
        v = getattr(sch, flat_attr, None)
        if v is None:
            return default
        try:
            return max(0, min(hi, int(v)))
        except (TypeError, ValueError):
            return default

    inner_a = _o("inner_fill_opacity", "marker_cluster_inner_fill_opacity", MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT)
    halo_a = _o("halo_opacity", "marker_cluster_halo_opacity", MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT)
    border_a = _o("border_opacity", "marker_cluster_border_opacity", MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT)
    spread = _oi("halo_spread_px", "marker_cluster_halo_spread_px", MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT, hi=24)
    bw = _oi("border_width_px", "marker_cluster_border_width_px", MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT, hi=8)

    fills_rgba = [_hex_to_rgba_css(fills[i], inner_a, channel="fill") for i in range(3)]
    borders_rgba = [_hex_to_rgba_css(borders[i], border_a, channel="edge") for i in range(3)]
    halos_rgba = [_hex_to_rgba_css(halos[i], halo_a, channel="fill") for i in range(3)]
    fills_js = json.dumps(fills_rgba)
    borders_js = json.dumps(borders_rgba)
    halos_js = json.dumps(halos_rgba)
    # One inner <div> only (same as plugin default HTML). Halo is a box-shadow ring; nested divs break
    # .marker-cluster div { width/height/margin } and look offset / triple-stacked.
    return (
        "function(cluster) {"
        "var count = cluster.getChildCount();"
        "var i = (count < 10) ? 0 : (count < 100) ? 1 : 2;"
        f"var fillsRgba = {fills_js};"
        f"var bordersRgba = {borders_js};"
        f"var halosRgba = {halos_js};"
        f"var bw = {int(bw)};"
        f"var spread = {int(spread)};"
        "var style = 'background-color:' + fillsRgba[i] + ';border:' + bw + 'px solid ' + bordersRgba[i] + ';"
        "box-shadow:0 0 0 ' + spread + 'px ' + halosRgba[i] + ';';"
        "var sizeClass = (count < 10) ? 'marker-cluster-small' : (count < 100) ? 'marker-cluster-medium' : 'marker-cluster-large';"
        "return new L.DivIcon({"
        "html: '<div style=\"' + style + '\"><span>' + count + '</span></div>',"
        "className: 'marker-cluster ' + sizeClass,"
        "iconSize: new L.Point(40, 40)"
        "});"
        "}"
    )


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
    visit_marker_scheme: MapMarkerColourScheme,
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
        _fill, _edge, _radius_px, _stroke_w, _fill_op = _all_locations_marker_params_from_scheme(
            visit_marker_scheme
        )
        legend_pair = (_edge, _fill)
        species_map.get_root().html.add_child(
            Element(build_legend_html([(legend_pair[0], legend_pair[1], "All locations")]))
        )

        marker_cluster: Optional[MarkerCluster] = None
        if cluster_all_locations:
            icon_fn = _marker_cluster_icon_create_function_from_scheme(visit_marker_scheme)
            if icon_fn is not None:
                species_map.get_root().html.add_child(Element(_marker_cluster_root_background_reset_css()))
            marker_cluster = MarkerCluster(
                name="All locations",
                icon_create_function=icon_fn,
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
                radius=_radius_px,
                color=_edge,
                weight=_stroke_w,
                fill=True,
                fill_color=_fill,
                fill_opacity=_fill_op,
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
        _legend_roles: list[tuple[str, Literal["lifer", "last_seen", "species", "default"]]] = [
            ("Lifer", "lifer"),
            ("Last seen", "last_seen"),
            ("Species", "species"),
            ("Other", "default"),
        ]
        legend_items = []
        for label, role in _legend_roles:
            if label not in pin_types_present:
                continue
            e, f, _, _, _ = resolve_species_visit_pin(visit_marker_scheme, role)
            legend_items.append((e, f, label))
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
                n_visits = int(len(visit_records))
                if row["has_species_match"]:
                    species_sightings = filtered_by_loc.get(loc_id, pd.DataFrame()).sort_values(
                        "datetime", ascending=popup_ascending
                    )
                    popup_html_cache[popup_key] = build_species_map_location_popup_html(
                        row["Location"],
                        loc_id,
                        species_sightings,
                        visit_info,
                        visit_record_count=n_visits,
                        popup_ascending=popup_ascending,
                    )
                else:
                    popup_html_cache[popup_key] = build_location_popup_html(
                        row["Location"], loc_id, visit_info, ""
                    )
            popup_html = popup_html_cache[popup_key]
            popup_content = folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX)

            visit_role: Literal["lifer", "last_seen", "species", "default"]
            if row["is_lifer"]:
                visit_role = "lifer"
            elif row["is_last_seen"]:
                visit_role = "last_seen"
            elif row["has_species_match"]:
                visit_role = "species"
            else:
                visit_role = "default"
            color, fill, radius_px, stroke_w, fill_opacity = resolve_species_visit_pin(
                visit_marker_scheme, visit_role
            )

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius_px,
                color=color,
                weight=stroke_w,
                fill=True,
                fill_color=fill,
                fill_opacity=fill_opacity,
                popup=popup_content,
            ).add_to(species_map)

    scroll_popup_script = popup_scroll_script(popup_scroll_hint, popup_sort_order == "ascending")
    species_map.get_root().html.add_child(Element(scroll_popup_script))

    return MapOverlayResult(species_map, None)
