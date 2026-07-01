"""Sidebar prep spinners (map-first, then checklist / rankings / tab sync) and Map tab embed.

All four Map-tab modes use the Leaflet Streamlit custom component. Session LRU helpers live in
:mod:`explorer.app.streamlit.app_prep_map_leaflet_caches`; non-map tab prep in
:mod:`explorer.app.streamlit.app_prep_map_tab_prep`. Per-mode payload builders in
:mod:`explorer.app.streamlit.app_prep_map_leaflet_modes`; map tab embed in
:mod:`explorer.app.streamlit.app_prep_map_map_tab`.
"""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from explorer.app.streamlit.app_constants import (
    EXPLORER_MAP_HTML_BYTES_KEY,
    LEAFLET_EXPORT_BUILT_CACHE_KEY,
    LEAFLET_EXPORT_RECIPE_KEY,
)
from explorer.app.streamlit.app_main_tab_ui import is_social_cards_main_tab
from explorer.app.streamlit.app_map_ui import (
    place_spinner_emoji_strip,
    sidebar_bottom_slot_end,
    sidebar_bottom_slot_start,
    sidebar_footer_links,
)
from explorer.app.streamlit.app_prep_map_blank_viewport import (
    seed_blank_map_default_viewport_recipe,
)
from explorer.app.streamlit.app_prep_map_leaflet_caches import (
    apply_dataset_signature_for_map_caches,
)
from explorer.app.streamlit.app_prep_map_leaflet_modes import (
    prep_family_leaflet_mode,
    prep_standard_map_leaflet_modes,
)
from explorer.app.streamlit.app_prep_map_map_tab import (
    finalize_leaflet_export_recipe,
    render_map_tab_leaflet_embed,
    render_prep_sidebar_after_map,
)
from explorer.app.streamlit.app_prep_map_tab_prep import run_tab_prep_spinner_and_sync
from explorer.app.streamlit.app_prep_map_types import LeafletMapPrepBundle
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.app.streamlit.streamlit_ui_constants import MAP_PREP_SPINNER_TEXT
from explorer.components.all_locations_map import (
    render_all_locations_map_component,  # noqa: F401 — re-export for integration tests
)
from explorer.core.map_prep import prepare_all_locations_map_context

__all__ = [
    "render_prep_spinner_and_map_tab",
    "render_all_locations_map_component",
    "apply_dataset_signature_for_map_caches",
    "perf_span",
]


def render_prep_spinner_and_map_tab(
    *,
    tab_map: Any,
    work_df: Any,
    df_full: Any,
    provenance: str | None,
    data_abs_path: str | None = None,
    tax_locale_effective: str,
    map_height: int,
    map_style: str,
    map_view_mode: str,
    is_lifer_view: bool,
    date_filter_banner: str,
    species_pick_common: str | None,
    species_pick_sci: str,
    family_name: str,
    family_highlight_base: str,
    family_colour_scheme: int,
    hide_non_matching_locations: bool,
    popup_sort_order: Any,
    popup_scroll_hint: Any,
    mark_lifer: bool,
    mark_last_seen: bool,
    species_url_fn: Callable[..., str],
) -> None:
    """Run map prep first (spinner), then heavy tab caches + session sync (second spinner)."""
    with st.sidebar:
        sidebar_bottom_slot_start()
        with st.spinner(MAP_PREP_SPINNER_TEXT):
            _spinner_emoji_placeholder = place_spinner_emoji_strip()
            with perf_span("prep.data_signature"):
                apply_dataset_signature_for_map_caches(
                    df_full, provenance, data_abs_path=data_abs_path
                )

            map_warning_text: str | None = None
            map_hint_text: str | None = None
            prep_bundle = LeafletMapPrepBundle()
            try:
                with perf_span("prep.map_context_prepare"):
                    ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
            except ValueError as e:
                map_warning_text = str(e)
                st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                st.session_state.pop(LEAFLET_EXPORT_RECIPE_KEY, None)
                st.session_state.pop(LEAFLET_EXPORT_BUILT_CACHE_KEY, None)
            else:
                blank_viewport_recipe = seed_blank_map_default_viewport_recipe(
                    ctx, map_view_mode=map_view_mode
                )

                if map_view_mode == "families":
                    prep_bundle, map_hint_text = prep_family_leaflet_mode(
                        work_df=work_df,
                        df_full=df_full,
                        tax_locale_effective=tax_locale_effective,
                        date_filter_banner=date_filter_banner,
                        map_style=map_style,
                        map_height=map_height,
                        map_view_mode=map_view_mode,
                        family_name=family_name,
                        family_highlight_base=family_highlight_base,
                        family_colour_scheme=family_colour_scheme,
                        blank_viewport_recipe=blank_viewport_recipe,
                        species_url_fn=species_url_fn,
                    )
                else:
                    prep_bundle, map_hint_text = prep_standard_map_leaflet_modes(
                        ctx=ctx,
                        work_df=work_df,
                        tax_locale_effective=tax_locale_effective,
                        map_view_mode=map_view_mode,
                        date_filter_banner=date_filter_banner,
                        map_style=map_style,
                        map_height=map_height,
                        species_pick_common=species_pick_common,
                        species_pick_sci=species_pick_sci,
                        hide_non_matching_locations=hide_non_matching_locations,
                        popup_sort_order=popup_sort_order,
                        popup_scroll_hint=popup_scroll_hint,
                        mark_lifer=mark_lifer,
                        mark_last_seen=mark_last_seen,
                        family_colour_scheme=family_colour_scheme,
                        blank_viewport_recipe=blank_viewport_recipe,
                        species_url_fn=species_url_fn,
                    )

                export_warning = finalize_leaflet_export_recipe(
                    prep_bundle, map_height, map_style
                )
                if export_warning:
                    map_warning_text = export_warning

            render_map_tab_leaflet_embed(
                tab_map,
                prep_bundle,
                map_height=map_height,
                map_style=map_style,
                map_view_mode=map_view_mode,
                map_hint_text=map_hint_text,
                map_warning_text=map_warning_text,
                popup_scroll_hint=str(popup_scroll_hint or ""),
                popup_sort_order=str(popup_sort_order or "ascending"),
            )

        run_tab_prep_spinner_and_sync(
            work_df=work_df,
            df_full=df_full,
            tax_locale_effective=tax_locale_effective,
        )

        _spinner_emoji_placeholder.empty()
        if is_social_cards_main_tab():
            sidebar_footer_links(leading_divider=True)
        else:
            render_prep_sidebar_after_map(map_height)
        sidebar_bottom_slot_end()
