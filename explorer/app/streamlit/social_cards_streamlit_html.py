"""
**Social Cards** (Streamlit main tab): period-scoped stats wired from the session export.

Card preview, stat picker, and PNG export are batch 4 (:mod:`explorer.app.streamlit.social_cards_streamlit_ui`).
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
    resolve_social_cards_period_from_session,
)
from explorer.app.streamlit.perf_instrumentation import perf_fragment
from explorer.app.streamlit.social_cards_streamlit_helpers import (
    period_has_checklist_data,
)
from explorer.app.streamlit.streamlit_ui_constants import SOCIAL_CARDS_TAB_LABEL
from explorer.core.share_summary_compute import (
    ShareSummaryGeoScope,
    geo_scope_display_label,
    resolve_social_cards_stats,
    world_taxonomy_bundle_status,
)
from explorer.presentation.share_summary_preview import summary_status_metrics


def render_social_cards_status_metrics(
    status_metrics: list[tuple[str, str]],
) -> None:
    """Compact read-only metrics grid (batch 3 wiring; replaced by card preview in batch 4)."""
    if not status_metrics:
        st.caption("No statistics available for this period.")
        return
    cols = st.columns(min(4, len(status_metrics)))
    for index, (label, value) in enumerate(status_metrics):
        with cols[index % len(cols)]:
            st.metric(label, value)


def render_social_cards_tab_content(
    *,
    df_full: pd.DataFrame,
    df_scoped: pd.DataFrame,
    geo_scope: ShareSummaryGeoScope,
    rankings_bundle: dict[str, Any] | None,
) -> None:
    """Social Cards main column — period stats and empty-period handling."""
    st.subheader(SOCIAL_CARDS_TAB_LABEL)

    period = resolve_social_cards_period_from_session(df_scoped)
    if period is None:
        st.caption("No dated checklists in this export.")
        return

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

    scope_label = geo_scope_display_label(geo_scope)
    st.caption(f"**{stats.period_label}** · {scope_label}")

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

    status_metrics = summary_status_metrics(
        stats, all_time=all_time, geo_scope=geo_scope
    )
    with st.expander("Computed statistics", expanded=True):
        render_social_cards_status_metrics(status_metrics)

    st.caption(
        "Card preview and export are wired in batch 4. "
        "Use the sidebar to configure period, layout, and theme."
    )


@st.fragment
def run_social_cards_streamlit_tab_fragment(df_full: Any) -> None:
    """Partial reruns when Social Cards sidebar controls change."""
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
