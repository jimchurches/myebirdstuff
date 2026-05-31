"""Primary ``st.tabs`` shell: Map prep embed + non-map fragments + Settings (R13 split)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import streamlit as st

from explorer.app.streamlit.app_bootstrap import TaxonomyPopupAssets
from explorer.app.streamlit.app_landing_ui import title_with_logo
from explorer.app.streamlit.app_prep_map_ui import render_prep_spinner_and_map_tab
from explorer.app.streamlit.app_settings_ui import render_settings_tab
from explorer.app.streamlit.checklist_stats_streamlit_html import run_checklist_stats_streamlit_fragment
from explorer.app.streamlit.country_stats_streamlit_html import run_country_tab_streamlit_fragment
from explorer.app.streamlit.maintenance_streamlit_html import run_maintenance_streamlit_tab_fragment
from explorer.app.streamlit.bird_families_streamlit_html import run_families_streamlit_tab_fragment
from explorer.app.streamlit.rankings_streamlit_html import run_rankings_streamlit_tab_fragment
from explorer.app.streamlit.streamlit_theme import inject_main_tab_panel_top_compact_css
from explorer.app.streamlit.streamlit_ui_constants import NOTEBOOK_MAIN_TAB_LABELS
from explorer.app.streamlit.yearly_summary_streamlit_html import run_yearly_summary_streamlit_fragment

if TYPE_CHECKING:
    from explorer.app.streamlit.app_map_working_ui import MapWorkingContext


def run_non_map_data_tab_fragments(
    tab_checklist: Any,
    tab_rankings: Any,
    tab_families: Any,
    tab_yearly: Any,
    tab_country: Any,
    tab_maint: Any,
) -> None:
    """Checklist, Rankings, Bird Families, Yearly, Country, Maintenance tabs (refs #118)."""
    with tab_checklist:
        run_checklist_stats_streamlit_fragment()

    with tab_rankings:
        run_rankings_streamlit_tab_fragment()

    with tab_families:
        run_families_streamlit_tab_fragment()

    with tab_yearly:
        run_yearly_summary_streamlit_fragment()

    with tab_country:
        run_country_tab_streamlit_fragment()

    with tab_maint:
        run_maintenance_streamlit_tab_fragment()


def render_dashboard_shell(
    *,
    df_full: Any,
    provenance: Any,
    source_label: str | None,
    data_abs_path: str | None,
    data_basename: str | None,
    mw: MapWorkingContext,
    tax: TaxonomyPopupAssets,
) -> None:
    title_with_logo()

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_families,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    inject_main_tab_panel_top_compact_css()

    render_prep_spinner_and_map_tab(
        tab_map=tab_map,
        work_df=mw.work_df,
        df_full=df_full,
        provenance=provenance,
        data_abs_path=data_abs_path,
        tax_locale_effective=tax.tax_locale_effective,
        map_height=mw.map_height,
        map_style=mw.map_style,
        map_view_mode=mw.map_view_mode,
        is_lifer_view=mw.is_lifer_view,
        date_filter_banner=mw.date_filter_banner,
        species_pick_common=mw.species_pick_common,
        species_pick_sci=mw.species_pick_sci,
        family_name=mw.family_name,
        family_highlight_base=mw.family_highlight_base,
        family_colour_scheme=mw.family_colour_scheme,
        hide_non_matching_locations=mw.hide_non_matching_locations,
        popup_sort_order=tax.popup_sort_order,
        popup_scroll_hint=tax.popup_scroll_hint,
        mark_lifer=tax.mark_lifer,
        mark_last_seen=tax.mark_last_seen,
        species_url_fn=tax.species_url_fn,
    )

    run_non_map_data_tab_fragments(
        tab_checklist,
        tab_rankings,
        tab_families,
        tab_yearly,
        tab_country,
        tab_maint,
    )

    with tab_settings:
        render_settings_tab(
            data_basename=data_basename,
            data_abs_path=data_abs_path,
            source_label=source_label,
        )
