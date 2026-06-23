"""Map tab embed, export recipe finalization, and post-map sidebar (R13)."""

from __future__ import annotations

import importlib
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_constants import (
    EXPLORER_MAP_HTML_BYTES_KEY,
    EXPORT_MAP_HTML_BTN_KEY,
    LEAFLET_EXPORT_BUILT_CACHE_KEY,
    LEAFLET_EXPORT_RECIPE_KEY,
    LEAFLET_MAP_MOUNT_NONCE_KEY,
)
from explorer.app.streamlit.app_map_ui import (
    inject_map_iframe_min_height_css,
    inject_sidebar_outline_download_button_css,
    sidebar_footer_links,
)
from explorer.app.streamlit.app_prep_map_leaflet_caches import (
    render_leaflet_export_map_html_download,
    sync_leaflet_export_recipe,
)
from explorer.app.streamlit.app_prep_map_types import LeafletMapPrepBundle
from explorer.app.streamlit.streamlit_ui_constants import (
    MAP_EXPORT_HTML_FILENAME,
    SIDEBAR_FOOTER_LINK_HEX,
)
from explorer.presentation.map_renderer import map_overlay_theme_stylesheet


def _prep_map_ui():
    return importlib.import_module("explorer.app.streamlit.app_prep_map_ui")


def finalize_leaflet_export_recipe(
    bundle: LeafletMapPrepBundle,
    map_height: int,
    map_style: str,
) -> str | None:
    """Sync session export recipe when embeddable; return warning text for the map tab."""
    if (
        bundle.has_embeddable_leaflet()
        and bundle.leaflet_cluster_opts is not None
        and bundle.leaflet_circle_style is not None
    ):
        sync_leaflet_export_recipe(
            leaflet_revision=bundle.leaflet_revision,
            leaflet_geojson=bundle.leaflet_geojson,
            map_height=int(map_height),
            map_style=map_style,
            leaflet_cluster_opts=bundle.leaflet_cluster_opts,
            leaflet_circle_style=bundle.leaflet_circle_style,
            leaflet_cluster_icon_style=bundle.leaflet_cluster_icon_style,
            leaflet_viewport=bundle.leaflet_viewport,
            banner_html=bundle.all_locations_leaflet_banner_html,
            legend_html=bundle.all_locations_leaflet_legend_html,
        )
        return None
    if bundle.result_warning:
        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
        st.session_state.pop(LEAFLET_EXPORT_RECIPE_KEY, None)
        st.session_state.pop(LEAFLET_EXPORT_BUILT_CACHE_KEY, None)
        return bundle.result_warning
    return None


def render_map_tab_leaflet_embed(
    tab_map: Any,
    bundle: LeafletMapPrepBundle,
    *,
    map_height: int,
    map_style: str,
    map_view_mode: str,
    map_hint_text: str | None,
    map_warning_text: str | None,
    popup_scroll_hint: str = "",
    popup_sort_order: str = "ascending",
) -> None:
    """Render map-tab warning, hint, and Leaflet component embed."""
    with tab_map:
        if map_warning_text is not None:
            st.warning(map_warning_text)
        elif (
            bundle.has_embeddable_leaflet()
            and bundle.leaflet_cluster_opts is not None
            and bundle.leaflet_circle_style is not None
        ):
            inject_map_iframe_min_height_css(map_height)
            if map_hint_text:
                st.info(map_hint_text)
            _embed_extra: dict[str, Any] = {
                "revision_prefix": (bundle.leaflet_revision or "")[:12],
                "n_features": len((bundle.leaflet_geojson or {}).get("features", [])),
                "cluster_enabled": bundle.leaflet_cluster_opts.get("enabled"),
            }
            if bundle.use_lifer_leaflet:
                _embed_extra["embed"] = "lifer_leaflet"
                _span_name = "map.lifer_leaflet.component_embed"
            elif bundle.use_species_leaflet:
                _embed_extra["embed"] = "species_leaflet"
                _span_name = "map.species_leaflet.component_embed"
            elif bundle.use_family_leaflet:
                _embed_extra["embed"] = "family_leaflet"
                _span_name = "map.family_leaflet.component_embed"
            else:
                _embed_extra["embed"] = "all_locations_leaflet"
                _embed_extra["map_view_mode"] = map_view_mode
                _span_name = "map.all_locations_leaflet.component_embed"
            _ui = _prep_map_ui()
            with _ui.perf_span(_span_name, extra=_embed_extra):
                _ui.render_all_locations_map_component(
                    revision=bundle.leaflet_revision,
                    geojson=bundle.leaflet_geojson,
                    height=int(map_height),
                    map_style=map_style,
                    cluster_options=bundle.leaflet_cluster_opts,
                    circle_marker_style=bundle.leaflet_circle_style,
                    cluster_icon_style=bundle.leaflet_cluster_icon_style or {},
                    viewport=bundle.leaflet_viewport or {},
                    map_theme_css=map_overlay_theme_stylesheet(),
                    popup_scroll_hint=str(popup_scroll_hint or ""),
                    popup_scroll_to_bottom=popup_sort_order == "ascending",
                    banner_html=bundle.all_locations_leaflet_banner_html,
                    legend_html=bundle.all_locations_leaflet_legend_html,
                    key=(
                        f"explorer_{'lifer' if bundle.use_lifer_leaflet else 'species' if bundle.use_species_leaflet else 'family' if bundle.use_family_leaflet else 'all_locations'}_leaflet_h{map_height}_"
                        f"n{int(st.session_state.get(LEAFLET_MAP_MOUNT_NONCE_KEY, 0))}"
                    ),
                )


def render_prep_sidebar_after_map(map_height: int) -> None:
    """Export-map HTML controls and sidebar footer links below the prep spinners."""
    _leaflet_recipe = st.session_state.get(LEAFLET_EXPORT_RECIPE_KEY)
    _export_html_bytes = st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY)
    _has_map_export = _leaflet_recipe is not None or _export_html_bytes is not None
    if _has_map_export:
        st.divider()
        _ex1, _ex2, _ex3 = st.columns([1, 3, 1])
        with _ex2:
            inject_sidebar_outline_download_button_css(SIDEBAR_FOOTER_LINK_HEX)
            if isinstance(_leaflet_recipe, dict):
                render_leaflet_export_map_html_download(_leaflet_recipe)
            elif isinstance(_export_html_bytes, (bytes, bytearray)):
                st.download_button(
                    "Export map HTML",
                    data=bytes(_export_html_bytes),
                    file_name=MAP_EXPORT_HTML_FILENAME,
                    mime="text/html",
                    key=EXPORT_MAP_HTML_BTN_KEY,
                    use_container_width=True,
                    type="secondary",
                )
    sidebar_footer_links(leading_divider=not _has_map_export)
