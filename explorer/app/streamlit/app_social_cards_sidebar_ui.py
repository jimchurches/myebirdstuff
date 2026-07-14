"""Social Cards sidebar for the main explorer app (tab-aware)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_constants import EBIRD_DATA_SIG_KEY
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.app.streamlit.social_cards_session_keys import (
    APP_SOCIAL_CARDS_KEYS,
    SocialCardsSessionKeys,
)
from explorer.app.streamlit.social_cards_sidebar_ui import (
    render_sidebar_card_controls,
    render_sidebar_geo_scope_controls,
)
from explorer.app.streamlit.social_cards_streamlit_helpers import (
    ordered_custom_date_range,
    peek_geo_scoped_dataframe_cache,
    resolve_geo_scoped_dataframe,
    social_cards_dataframe_signature,
)
from explorer.core.share_summary_compute import (
    PeriodAnchor,
    ShareSummaryGeoScope,
    ShareSummaryPeriod,
    dataset_date_bounds,
    period_for_custom,
    period_for_lifetime,
    period_for_year,
    resolve_period,
    suggest_period_anchor,
)

SOCIAL_CARDS_DF_SCOPED_SESSION_KEY = "_social_cards_df_scoped"
SOCIAL_CARDS_GEO_SCOPE_SESSION_KEY = "_social_cards_geo_scope"
SOCIAL_CARDS_SIDEBAR_SELECTION_KEY = "_social_cards_sidebar_selection"
SOCIAL_CARDS_GEO_FILTER_CACHE_KEY = "_social_cards_geo_filter_cache"


def _card_heading_or_none(text: str) -> str | None:
    stripped = (text or "").strip()
    return stripped or None


SOCIAL_CARDS_DEFAULT_PERIOD_MODE = "lifetime"
# Longest → shortest fixed period; custom trip range last.
SOCIAL_CARDS_PERIOD_MODE_OPTIONS: tuple[str, ...] = (
    "lifetime",
    "year",
    "month",
    "week",
    "custom",
)


def _render_period_controls(
    df: pd.DataFrame,
    keys: SocialCardsSessionKeys,
) -> None:
    """Period pickers for session export (no sample-data toggle)."""
    bounds = dataset_date_bounds(df)
    if bounds is None:
        st.caption("No dated checklists in this export.")
        return

    min_d, max_d = bounds
    reference = date.today()

    period_mode = st.selectbox(
        "Range",
        options=list(SOCIAL_CARDS_PERIOD_MODE_OPTIONS),
        index=SOCIAL_CARDS_PERIOD_MODE_OPTIONS.index(SOCIAL_CARDS_DEFAULT_PERIOD_MODE),
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
        start, end, swapped = ordered_custom_date_range(
            st.session_state.get(keys.custom_start),
            st.session_state.get(keys.custom_end),
            default_start=min_d,
            default_end=max_d,
        )
        st.session_state[keys.custom_start] = start
        st.session_state[keys.custom_end] = end
        if swapped:
            st.caption(
                "Start and end dates were swapped so the range runs forwards."
            )
        st.date_input(
            "Start date",
            value=start,
            min_value=min_d,
            max_value=end,
            key=keys.custom_start,
        )
        st.date_input(
            "End date",
            value=end,
            min_value=start,
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

        dataset_sig = social_cards_dataframe_signature(
            df_full,
            session_sig=st.session_state.get(EBIRD_DATA_SIG_KEY),
        )
        cached_entry = st.session_state.get(SOCIAL_CARDS_GEO_FILTER_CACHE_KEY)
        if not isinstance(cached_entry, dict):
            cached_entry = None
        scoped = peek_geo_scoped_dataframe_cache(
            dataset_sig=dataset_sig,
            geo_scope=geo_scope,
            cache_entry=cached_entry,
        )
        if scoped is None:
            with perf_span("social_cards.filter_geo_scope"):
                scoped, cache_entry, _ = resolve_geo_scoped_dataframe(
                    df_full,
                    geo_scope,
                    dataset_sig=dataset_sig,
                    cache_entry=None,
                )
            st.session_state[SOCIAL_CARDS_GEO_FILTER_CACHE_KEY] = cache_entry
        st.session_state[SOCIAL_CARDS_DF_SCOPED_SESSION_KEY] = scoped


def resolve_social_cards_period_from_session(
    df_scoped: pd.DataFrame | None,
    keys: SocialCardsSessionKeys = APP_SOCIAL_CARDS_KEYS,
) -> ShareSummaryPeriod | None:
    """Resolve the selected period object from sidebar session keys."""
    if df_scoped is None or df_scoped.empty:
        return None
    bounds = dataset_date_bounds(df_scoped)
    if bounds is None:
        return None

    min_d, max_d = bounds
    reference = date.today()
    period_mode = st.session_state.get(keys.period_mode, SOCIAL_CARDS_DEFAULT_PERIOD_MODE)

    if period_mode == "year":
        selected_year = int(st.session_state.get(keys.period_year, date.today().year))
        return period_for_year(selected_year)
    if period_mode in ("month", "week"):
        anchor: PeriodAnchor = st.session_state.get(keys.period_anchor, "current")
        return resolve_period(period_mode, anchor=anchor, reference=reference)
    if period_mode == "lifetime":
        return period_for_lifetime(min_d, max_d)
    if period_mode == "custom":
        start, end, swapped = ordered_custom_date_range(
            st.session_state.get(keys.custom_start, min_d),
            st.session_state.get(keys.custom_end, max_d),
            default_start=min_d,
            default_end=max_d,
        )
        if swapped:
            st.session_state[keys.custom_start] = start
            st.session_state[keys.custom_end] = end
        heading = _card_heading_or_none(
            st.session_state.get(keys.custom_card_heading, "")
        )
        return period_for_custom(start, end, trip_title=heading)

    return period_for_year(
        int(st.session_state.get(keys.period_year, date.today().year))
    )
