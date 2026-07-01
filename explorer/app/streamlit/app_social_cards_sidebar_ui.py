"""Social Cards sidebar for the main explorer app (tab-aware)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from explorer.app.streamlit.social_cards_session_keys import (
    APP_SOCIAL_CARDS_KEYS,
    SocialCardsSessionKeys,
)
from explorer.app.streamlit.social_cards_sidebar_ui import (
    render_sidebar_card_controls,
    render_sidebar_geo_scope_controls,
)
from explorer.core.share_summary_compute import (
    PeriodAnchor,
    ShareSummaryGeoScope,
    filter_df_by_geo_scope,
    period_for_custom,
    period_for_lifetime,
    period_for_year,
    resolve_period,
    suggest_period_anchor,
)

SOCIAL_CARDS_GEO_SCOPE_SESSION_KEY = "_social_cards_geo_scope"
SOCIAL_CARDS_SIDEBAR_SELECTION_KEY = "_social_cards_sidebar_selection"


def _card_heading_or_none(text: str) -> str | None:
    stripped = (text or "").strip()
    return stripped or None


def _render_period_controls(
    df: pd.DataFrame,
    keys: SocialCardsSessionKeys,
) -> None:
    """Period pickers for session export (no sample-data toggle)."""
    dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
    if dates.empty:
        st.caption("No dated checklists in this export.")
        return

    min_d = dates.min().date()
    max_d = dates.max().date()
    reference = date.today()

    period_mode = st.selectbox(
        "Range",
        options=["year", "month", "week", "custom", "lifetime"],
        format_func=lambda x: {
            "year": "Yearly",
            "month": "Monthly",
            "week": "Weekly",
            "custom": "Custom date range",
            "lifetime": "Lifetime",
        }[x],
        key=keys.period_mode,
    )

    if period_mode == "year":
        st.number_input(
            "Year",
            min_value=2000,
            max_value=2100,
            value=date.today().year,
            step=1,
            key=keys.period_year,
        )
    elif period_mode in ("month", "week"):
        default_anchor = suggest_period_anchor(period_mode, reference)
        st.radio(
            "Period",
            options=["current", "previous"],
            index=0 if default_anchor == "current" else 1,
            format_func=lambda x: {
                "current": f"Current {period_mode}",
                "previous": f"Previous {period_mode}",
            }[x],
            help="Current vs previous calendar period (e.g. post May results on 2 June → previous month).",
            key=keys.period_anchor,
        )
    elif period_mode == "custom":
        st.date_input(
            "Start date",
            value=min_d,
            min_value=min_d,
            max_value=max_d,
            key=keys.custom_start,
        )
        st.date_input(
            "End date",
            value=max_d,
            min_value=min_d,
            max_value=max_d,
            key=keys.custom_end,
        )
        st.text_input(
            "Card Heading (optional)",
            value="",
            placeholder="e.g. North Coast NSW Exploration",
            key=keys.custom_card_heading,
        )


def render_social_cards_main_sidebar(df_full: Any) -> None:
    """Social Cards sidebar block — period, geo scope, layout/format/theme."""
    with st.sidebar:
        keys = APP_SOCIAL_CARDS_KEYS
        st.header("Social Cards")

        st.subheader("Scope")
        _render_period_controls(df_full, keys)

        geo_scope = ShareSummaryGeoScope()
        if df_full is not None and not df_full.empty:
            geo_scope = render_sidebar_geo_scope_controls(df_full, keys)
        st.session_state[SOCIAL_CARDS_GEO_SCOPE_SESSION_KEY] = geo_scope

        selection = render_sidebar_card_controls(keys)
        st.session_state[SOCIAL_CARDS_SIDEBAR_SELECTION_KEY] = selection

        # Batch 3 will resolve period + stats from session keys and scoped export.
        scoped = filter_df_by_geo_scope(df_full, geo_scope)
        st.session_state["_social_cards_df_scoped"] = scoped


def resolve_social_cards_period_from_session(
    df_scoped: pd.DataFrame,
    keys: SocialCardsSessionKeys = APP_SOCIAL_CARDS_KEYS,
) -> Any | None:
    """Resolve the selected period object from sidebar session keys (for batch 3 wiring)."""
    if df_scoped is None or df_scoped.empty:
        return None
    dates = pd.to_datetime(df_scoped["Date"], errors="coerce").dropna()
    if dates.empty:
        return None

    min_d = dates.min().date()
    max_d = dates.max().date()
    reference = date.today()
    period_mode = st.session_state.get(keys.period_mode, "year")

    if period_mode == "year":
        selected_year = int(st.session_state.get(keys.period_year, date.today().year))
        return period_for_year(selected_year)
    if period_mode == "month":
        anchor: PeriodAnchor = st.session_state.get(keys.period_anchor, "current")
        return resolve_period("month", anchor=anchor, reference=reference)
    if period_mode == "week":
        anchor = st.session_state.get(keys.period_anchor, "current")
        return resolve_period("week", anchor=anchor, reference=reference)
    if period_mode == "lifetime":
        return period_for_lifetime(min_d, max_d)
    if period_mode == "custom":
        start = st.session_state.get(keys.custom_start, min_d)
        end = st.session_state.get(keys.custom_end, max_d)
        if end < start:
            start, end = end, start
        heading = _card_heading_or_none(st.session_state.get(keys.custom_card_heading, ""))
        return period_for_custom(start, end, trip_title=heading)

    return period_for_year(int(st.session_state.get(keys.period_year, date.today().year)))
