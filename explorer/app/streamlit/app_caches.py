"""Streamlit ``@st.cache_*`` helpers shared by ``app.py`` (refs #98)."""

from __future__ import annotations

from collections.abc import Callable
import pandas as pd
import streamlit as st

from explorer.core.checklist_stats_compute import ChecklistStatsPayload, compute_checklist_stats_payload
from explorer.app.streamlit.defaults import CHECKLIST_STATS_TOP_N_TABLE_LIMIT


@st.cache_data(show_spinner=False)
def cached_checklist_stats_payload(df: pd.DataFrame) -> ChecklistStatsPayload | None:
    """Structured checklist stats for the Checklist Statistics tab (refs #68)."""
    return compute_checklist_stats_payload(df, CHECKLIST_STATS_TOP_N_TABLE_LIMIT)


@st.cache_data(show_spinner=False)
def cached_full_export_checklist_stats_payload(
    df: pd.DataFrame,
    top_n_limit: int,
    high_count_sort: str,
    high_count_tie_break: str,
) -> ChecklistStatsPayload | None:
    """Full-export stats payload shared by Maintenance + Rankings (one compute per cache key).

    *top_n_limit* and high-count options match **Settings → Tables & lists** and Rankings.
    """
    return compute_checklist_stats_payload(
        df,
        top_n_limit,
        high_count_sort=high_count_sort,
        high_count_tie_break=high_count_tie_break,
    )


@st.cache_data(show_spinner=False)
def cached_sex_notation_by_year(df: pd.DataFrame) -> dict:
    """Sex-notation maintenance scan on full export (refs #79)."""
    from explorer.core.stats import get_sex_notation_by_year

    return get_sex_notation_by_year(df)


def full_location_data_for_maintenance(df: pd.DataFrame) -> pd.DataFrame:
    """Unique locations for map maintenance (same columns as ``full_location_data``)."""
    cols = ["Location ID", "Location", "Latitude", "Longitude"]
    if not all(c in df.columns for c in cols):
        return pd.DataFrame(columns=cols)
    return df[cols].drop_duplicates()


@st.cache_resource(show_spinner="Loading eBird taxonomy…")
def cached_species_url_fn(locale_key: str) -> Callable[[str], str | None]:
    """One taxonomy fetch per session per locale; used for species links in map UI."""
    from explorer.core.taxonomy import get_species_url, load_taxonomy

    loc = locale_key.strip() if locale_key and locale_key.strip() else None
    if load_taxonomy(locale=loc):
        return get_species_url
    return lambda _: None


def static_map_cache_key(
    work_df: pd.DataFrame,
    map_view_mode: str,
    date_filter_banner: str,
    map_style: str,
    render_opts_sig: tuple = (),
    taxonomy_locale: str = "",
    *,
    species_selected_sci: str = "",
    species_selected_common: str = "",
    hide_non_matching_locations: bool = False,
) -> tuple:
    """Stable key for Folium map reuse (session holds one cached map; same key → skip rebuild).

    *species_* / *hide_non_matching* matter for **Selected species** view; pass empty / False for
    All / Lifers or Species with no selection (aligned with ``map_controller`` coercion).
    """
    n = len(work_df)
    sid0 = ""
    if n > 0 and "Submission ID" in work_df.columns:
        sid0 = str(work_df["Submission ID"].iloc[0])
    tax = (taxonomy_locale or "").strip()
    sci = (species_selected_sci or "").strip()
    common = (species_selected_common or "").strip()
    return (
        map_view_mode,
        date_filter_banner,
        map_style,
        render_opts_sig,
        n,
        sid0,
        tax,
        sci,
        common,
        bool(hide_non_matching_locations),
    )
