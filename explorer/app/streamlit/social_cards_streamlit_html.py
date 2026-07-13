"""
**Social Cards** (Streamlit main tab): period-scoped stats wired from the session export.

Card preview, stat picker, and lazy PNG export live in
:mod:`explorer.app.streamlit.social_cards_streamlit_ui`.
All-time taxonomy denominators reuse the rankings/families prep bundle — not
:func:`~explorer.core.share_summary_compute.compute_share_summary_all_time_stats`.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_constants import RANKING_LISTS_FAMILIES_BUNDLE_KEY
from explorer.app.streamlit.app_social_cards_sidebar_ui import (
    SOCIAL_CARDS_DF_SCOPED_SESSION_KEY,
    SOCIAL_CARDS_GEO_SCOPE_SESSION_KEY,
    SOCIAL_CARDS_SIDEBAR_SELECTION_KEY,
    resolve_social_cards_period_from_session,
)
from explorer.app.streamlit.perf_instrumentation import perf_fragment, perf_span
from explorer.app.streamlit.social_cards_session_keys import APP_SOCIAL_CARDS_KEYS
from explorer.app.streamlit.social_cards_sidebar_ui import SocialCardsSidebarSelection
from explorer.app.streamlit.social_cards_streamlit_helpers import (
    card_stat_data_scope_from_session_export,
    period_has_checklist_data,
)
from explorer.app.streamlit.social_cards_streamlit_ui import (
    render_current_card_fragment,
)
from explorer.core.share_summary_compute import (
    ShareSummaryGeoScope,
    geo_scope_display_label,
    resolve_social_cards_stats,
    world_taxonomy_bundle_status,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_INSIGHT_FACT_DEFAULT,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
)
from explorer.core.share_summary_insight_facts import (
    ShareSummaryInsightFact,
    compute_insight_facts,
    species_common_names_in_period,
)
from explorer.presentation.share_summary_preview import summary_status_metrics


def render_social_cards_tab_content(
    *,
    df_full: pd.DataFrame,
    df_scoped: pd.DataFrame,
    geo_scope: ShareSummaryGeoScope,
    rankings_bundle: dict[str, Any] | None,
) -> None:
    """Social Cards main column — card preview, stat pickers, and lazy PNG export."""
    period = resolve_social_cards_period_from_session(df_scoped)
    if period is None:
        st.caption("No dated checklists in this export.")
        return

    with perf_span("social_cards.resolve_stats"):
        stats, all_time = resolve_social_cards_stats(
            df_full=df_full,
            df_scoped=df_scoped,
            period=period,
            geo_scope=geo_scope,
            rankings_bundle=rankings_bundle,
        )
    if stats is None:
        st.warning("Could not compute stats for this period.")
        return

    sidebar_raw = st.session_state.get(SOCIAL_CARDS_SIDEBAR_SELECTION_KEY)
    if not isinstance(sidebar_raw, SocialCardsSidebarSelection):
        st.caption("Use the sidebar to configure layout, format, and theme.")
        return
    sidebar_selection = sidebar_raw

    scope_label = geo_scope_display_label(geo_scope)

    if not period_has_checklist_data(stats):
        st.warning(
            f"No checklists in **{stats.period_label}** in this export. "
            "Try **Previous month** (or another range) in the sidebar, or pick a period that includes your data."
        )

    if geo_scope.is_world:
        tax_status = world_taxonomy_bundle_status(rankings_bundle)
        if tax_status == "pending":
            st.caption(
                "Taxonomy reference stats are still loading — wait for checklist and "
                "rankings prep to finish, then try again."
            )
        elif tax_status == "unavailable":
            st.caption(
                "Taxonomy reference stats unavailable (taxonomy data may not be loaded)."
            )

    keys = APP_SOCIAL_CARDS_KEYS
    if keys.spotlight_label not in st.session_state:
        st.session_state[keys.spotlight_label] = SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT
    if keys.insight_fact not in st.session_state:
        st.session_state[keys.insight_fact] = SHARE_SUMMARY_INSIGHT_FACT_DEFAULT

    # Insight facts are only used by the Interesting Insights layout — skip on tiles /
    # list / spotlight (~1.5s on a ~46k-row lifetime export; see #328 timing notes).
    insight_facts: list[ShareSummaryInsightFact] = []
    insight_species_options: tuple[str, ...] = ()
    if sidebar_selection.layout == "insight":
        with perf_span("social_cards.compute_insight_facts"):
            insight_facts = compute_insight_facts(df_scoped, period)
            insight_species_options = species_common_names_in_period(df_scoped, period)
        if insight_species_options and keys.insight_species not in st.session_state:
            st.session_state[keys.insight_species] = insight_species_options[0]

    card_stat_data_scope = card_stat_data_scope_from_session_export(
        period_kind=stats.period_kind,
        period_label=stats.period_label,
        geo_scope=geo_scope,
        fmt=sidebar_selection.fmt,
        tiles_presentation=sidebar_selection.tiles_presentation,
    )
    status_metrics = summary_status_metrics(
        stats, all_time=all_time, geo_scope=geo_scope
    )

    with perf_span("social_cards.render_preview"):
        render_current_card_fragment(
            stats=stats,
            all_time=all_time,
            selected_layout=sidebar_selection.layout,
            fmt=sidebar_selection.fmt,
            scale=sidebar_selection.scale,
            status_metrics=status_metrics,
            color_scheme_index=sidebar_selection.color_scheme_index,
            card_stat_data_scope=card_stat_data_scope,
            scope_label=scope_label,
            geo_scope=geo_scope,
            keys=keys,
            tiles_presentation=sidebar_selection.tiles_presentation,
            spotlight_presentation=sidebar_selection.spotlight_presentation,
            insight_facts=insight_facts,
            insight_species_options=insight_species_options,
            df_scoped=df_scoped,
            resolved_period=period,
            current_card_label="",
            lazy_png_export=True,
        )


@st.fragment
def run_social_cards_streamlit_tab_fragment(df_full: Any) -> None:
    """Partial reruns for in-tab Social Cards controls (stat picker, PNG export).

    Period / geo / layout / format / theme stay in the main-script sidebar so the
    chrome matches other explorer tabs. On current Streamlit, sidebar widgets still
    trigger a full app rerun; map prep is skipped while this tab is active (#328).
    """
    with perf_fragment("social_cards"):
        if df_full is None or not isinstance(df_full, pd.DataFrame) or df_full.empty:
            st.info("Load checklist data to use Social Cards.")
            return

        geo_scope = st.session_state.get(SOCIAL_CARDS_GEO_SCOPE_SESSION_KEY)
        if not isinstance(geo_scope, ShareSummaryGeoScope):
            geo_scope = ShareSummaryGeoScope()

        df_scoped = st.session_state.get(SOCIAL_CARDS_DF_SCOPED_SESSION_KEY)
        if df_scoped is None or not isinstance(df_scoped, pd.DataFrame):
            st.info("Load checklist data to use Social Cards.")
            return
        if df_scoped.empty:
            if not geo_scope.is_world:
                scope_label = geo_scope_display_label(geo_scope)
                st.info(
                    f"No checklists in this export match **{scope_label}**. "
                    "Try **World** or a different country/region in the sidebar."
                )
                return
            st.info("Load checklist data to use Social Cards.")
            return

        bundle = st.session_state.get(RANKING_LISTS_FAMILIES_BUNDLE_KEY)
        rankings_bundle = bundle if isinstance(bundle, dict) else None

        render_social_cards_tab_content(
            df_full=df_full,
            df_scoped=df_scoped,
            geo_scope=geo_scope,
            rankings_bundle=rankings_bundle,
        )
