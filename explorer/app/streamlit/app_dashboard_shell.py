"""Primary ``st.tabs`` shell: Map prep embed + non-map fragments + Settings (R13 split)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from explorer.app.streamlit.app_bootstrap import TaxonomyPopupAssets
from explorer.app.streamlit.app_landing_ui import title_with_logo
from explorer.app.streamlit.app_main_tab_ui import notebook_main_tabs
from explorer.app.streamlit.app_prep_map_ui import render_prep_spinner_and_map_tab
from explorer.app.streamlit.app_settings_ui import render_settings_tab
from explorer.app.streamlit.bird_families_streamlit_html import (
    run_families_streamlit_tab_fragment,
)
from explorer.app.streamlit.checklist_stats_streamlit_html import (
    run_checklist_stats_streamlit_fragment,
)
from explorer.app.streamlit.country_stats_streamlit_html import (
    run_country_tab_streamlit_fragment,
)
from explorer.app.streamlit.maintenance_streamlit_html import (
    run_maintenance_streamlit_tab_fragment,
)
from explorer.app.streamlit.rankings_streamlit_html import (
    run_rankings_streamlit_tab_fragment,
)
from explorer.app.streamlit.social_cards_streamlit_html import (
    run_social_cards_streamlit_tab_fragment,
)
from explorer.app.streamlit.streamlit_theme import inject_main_tab_panel_top_compact_css
from explorer.app.streamlit.yearly_summary_streamlit_html import (
    run_yearly_summary_streamlit_fragment,
)

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
    """Checklist, Rankings, Bird Families, Yearly, Country, and Maintenance tab fragments."""
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
    map_working: MapWorkingContext,
    taxonomy_assets: TaxonomyPopupAssets,
) -> None:
    title_with_logo()

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_families,
        tab_yearly,
        tab_country,
        tab_social_cards,
        tab_maint,
        tab_settings,
    ) = notebook_main_tabs()

    inject_main_tab_panel_top_compact_css()

    render_prep_spinner_and_map_tab(
        tab_map=tab_map,
        work_df=map_working.work_df,
        df_full=df_full,
        provenance=provenance,
        data_abs_path=data_abs_path,
        tax_locale_effective=taxonomy_assets.tax_locale_effective,
        map_height=map_working.map_height,
        map_style=map_working.map_style,
        map_view_mode=map_working.map_view_mode,
        is_lifer_view=map_working.is_lifer_view,
        date_filter_banner=map_working.date_filter_banner,
        species_pick_common=map_working.species_pick_common,
        species_pick_sci=map_working.species_pick_sci,
        family_name=map_working.family_name,
        family_highlight_base=map_working.family_highlight_base,
        family_colour_scheme=map_working.family_colour_scheme,
        hide_non_matching_locations=map_working.hide_non_matching_locations,
        popup_sort_order=taxonomy_assets.popup_sort_order,
        popup_scroll_hint=taxonomy_assets.popup_scroll_hint,
        mark_lifer=taxonomy_assets.mark_lifer,
        mark_last_seen=taxonomy_assets.mark_last_seen,
        species_url_fn=taxonomy_assets.species_url_fn,
    )

    run_non_map_data_tab_fragments(
        tab_checklist,
        tab_rankings,
        tab_families,
        tab_yearly,
        tab_country,
        tab_maint,
    )

    with tab_social_cards:
        if tab_social_cards.open:
            run_social_cards_streamlit_tab_fragment(df_full)

    with tab_settings:
        render_settings_tab(
            data_basename=data_basename,
            data_abs_path=data_abs_path,
            source_label=source_label,
        )
