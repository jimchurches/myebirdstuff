"""Social Cards main-column UI — stat pickers, preview fragment, PNG export.

Implementation split across:

- ``social_cards_stat_picker_ui`` — card / spotlight / insight pickers
- ``social_cards_png_export_ui`` — PNG cache and lazy export controls

This module keeps the fragment orchestrator and re-exports the public surface.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from explorer.app.streamlit.social_cards_png_export_ui import (
    cached_share_summary_png,
    centered_card_download_button,
    render_lazy_png_export_controls,
)
from explorer.app.streamlit.social_cards_session_keys import SocialCardsSessionKeys
from explorer.app.streamlit.social_cards_stat_picker_ui import (
    render_card_stat_picker_ui,
    render_insight_fact_picker_ui,
    render_spotlight_stat_picker,
    spotlight_label_from_session,
)
from explorer.app.streamlit.streamlit_ui_constants import INSIGHT_PEAK_TIE_INFO
from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryPeriod,
    ShareSummaryStats,
)
from explorer.core.share_summary_defaults import share_summary_color_scheme_fingerprint
from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact
from explorer.presentation.share_summary_png_export import share_summary_png_filename
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
    render_share_summary_preview_html,
)

SOCIAL_CARDS_STATISTICS_LABEL = "Card statistics"
SOCIAL_CARDS_CURRENT_CARD_LABEL = "Current card"


@st.fragment
def render_current_card_fragment(
    *,
    stats: ShareSummaryStats,
    all_time: ShareSummaryAllTimeStats | None,
    selected_layout: LayoutId,
    fmt: FormatId,
    scale: float,
    status_metrics: list[tuple[str, str]],
    color_scheme_index: int,
    card_stat_data_scope: str,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    keys: SocialCardsSessionKeys,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    insight_facts: list[ShareSummaryInsightFact],
    insight_species_options: tuple[str, ...],
    df_scoped: pd.DataFrame,
    resolved_period: ShareSummaryPeriod,
    statistics_label: str = SOCIAL_CARDS_STATISTICS_LABEL,
    current_card_label: str = SOCIAL_CARDS_CURRENT_CARD_LABEL,
    export_button_label: str = "Export card",
    lazy_png_export: bool = False,
) -> None:
    """Card statistics controls, live preview, and PNG export."""
    card_stat_labels: tuple[str, ...] = ()
    resolved_fact: ShareSummaryInsightFact | None = None
    with st.expander(statistics_label, expanded=False):
        if selected_layout == "spotlight":
            render_spotlight_stat_picker(status_metrics, keys)
        elif selected_layout == "insight":
            resolved_fact = render_insight_fact_picker_ui(
                insight_facts,
                insight_species_options,
                df=df_scoped,
                period=resolved_period,
                keys=keys,
            )
        else:
            card_stat_labels = render_card_stat_picker_ui(
                selected_layout,
                status_metrics,
                fmt,
                stats.period_kind,
                data_scope=card_stat_data_scope,
                geo_scope=geo_scope,
                tiles_presentation=tiles_presentation,
                keys=keys,
            )

    spotlight_label = spotlight_label_from_session(status_metrics, keys)

    if selected_layout == "insight" and resolved_fact is None:
        if (current_card_label or "").strip():
            st.subheader(current_card_label)
        st.info(
            "No Interesting Insights fact is available for this period and selection."
        )
        return

    if (current_card_label or "").strip():
        st.subheader(current_card_label)
    st.markdown(
        render_share_summary_preview_html(
            stats,
            layout=selected_layout,
            fmt=fmt,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
            scale=scale,
            spotlight_label=spotlight_label,
            insight_fact=resolved_fact,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            geo_scope=geo_scope,
            scope_label=scope_label,
        ),
        unsafe_allow_html=True,
    )
    if selected_layout == "insight" and resolved_fact is not None and resolved_fact.peak_tied:
        st.info(INSIGHT_PEAK_TIE_INFO)

    png_filename = share_summary_png_filename(stats, layout=selected_layout, fmt=fmt)
    if lazy_png_export:
        render_lazy_png_export_controls(
            stats=stats,
            layout=selected_layout,
            fmt=fmt,
            card_stat_labels=card_stat_labels,
            spotlight_label=spotlight_label,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            scope_label=scope_label,
            geo_scope=geo_scope,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
            resolved_fact=resolved_fact,
            export_button_label=export_button_label,
            png_filename=png_filename,
        )
        return

    try:
        png_bytes = cached_share_summary_png(
            stats,
            selected_layout,
            fmt,
            card_stat_labels,
            spotlight_label,
            all_time,
            color_scheme_index,
            share_summary_color_scheme_fingerprint(color_scheme_index),
            scope_label,
            geo_scope,
            tiles_presentation,
            spotlight_presentation,
            resolved_fact,
        )
    except RuntimeError as exc:
        st.warning(str(exc))
    else:
        centered_card_download_button(
            label=export_button_label,
            data=png_bytes,
            file_name=png_filename,
            mime="image/png",
            help_text="PNG of the current card above.",
        )
