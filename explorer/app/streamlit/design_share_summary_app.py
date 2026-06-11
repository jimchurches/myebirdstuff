"""
Social summary **design** utility — prototype layouts for #157.

No integration with the main explorer app. Run from repo root::

    pip install -r requirements.txt
    streamlit run explorer/app/streamlit/design_share_summary_app.py

Upload an eBird CSV or use sample data; compare layout mockups at square post,
portrait post, and story aspect ratios. PNG export uses Playwright (headless Chromium).
"""

from __future__ import annotations

import os
import sys
from datetime import date

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd
import streamlit as st

from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.data_loader import load_dataset
from explorer.core.share_summary_compute import (
    PeriodAnchor,
    ShareSummaryAllTimeStats,
    ShareSummaryStats,
    compute_share_summary_all_time_stats,
    format_custom_date_range,
    resolve_period,
    suggest_period_anchor,
)
from explorer.presentation.share_summary_png_export import (
    share_summary_png_filename,
    share_summary_to_png_bytes,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
    SpotlightStatId,
    _FORMAT_LABELS,
    all_layout_previews_html,
    compute_share_summary_stats,
    period_for_custom,
    period_for_month,
    period_for_week_containing,
    period_for_year,
    render_share_summary_preview_html,
    sample_share_summary_stats,
    spotlight_stat_label,
    summary_status_metrics,
)


@st.cache_data(show_spinner="Generating PNG…")
def _cached_share_summary_png(
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    spotlight_stat: SpotlightStatId,
) -> bytes:
    return share_summary_to_png_bytes(
        stats,
        layout=layout,
        fmt=fmt,
        spotlight_stat=spotlight_stat,
    )

_DESIGN_STUDIO_TITLE = "Social sharing design studio"
_SOCIAL_CARDS_TAB_LABEL = "Social Cards"
_STATS_EXPANDER_LABEL = "Available statistics"
_CURRENT_CARD_LABEL = "Current card"
_CARD_HEADING_LABEL = "Card Heading (optional)"
_CARD_HEADING_PLACEHOLDER = "e.g. North Coast NSW Exploration"


def _card_heading_or_none(text: str) -> str | None:
    """Normalize sidebar card heading; maps to ``trip_title`` on stats/period objects."""
    stripped = (text or "").strip()
    return stripped or None


st.set_page_config(page_title=_DESIGN_STUDIO_TITLE, layout="wide")
st.title(_DESIGN_STUDIO_TITLE)
st.caption(
    "Exploratory tool only. Compare HTML mockups before choosing layouts for the main app."
)

with st.sidebar:
    st.header("Data")
    use_sample = st.toggle("Use sample data", value=True)
    uploaded = None if use_sample else st.file_uploader("eBird CSV export", type=["csv"])

    st.header("Period")
    period_mode = st.selectbox(
        "Range",
        options=["year", "month", "week", "custom"],
        format_func=lambda x: {
            "year": "Yearly",
            "month": "Monthly",
            "week": "Weekly",
            "custom": "Custom date range (trip)",
        }[x],
    )
    period_anchor: PeriodAnchor | None = None
    if period_mode in ("year", "month", "week"):
        default_anchor = suggest_period_anchor(period_mode, date.today())
        period_anchor = st.radio(
            "Period",
            options=["current", "previous"],
            index=0 if default_anchor == "current" else 1,
            format_func=lambda x: {
                "current": f"Current {period_mode}",
                "previous": f"Previous {period_mode}",
            }[x],
            help="Current vs previous calendar period (e.g. post May results on 2 June → previous month).",
        )

    sample_custom_start: date | None = None
    sample_custom_end: date | None = None
    sample_card_heading = ""
    if period_mode == "custom" and use_sample:
        sample_custom_start = st.date_input(
            "Start date",
            value=date(2025, 6, 1),
            key="design_sample_custom_start",
        )
        sample_custom_end = st.date_input(
            "End date",
            value=date(2025, 6, 7),
            key="design_sample_custom_end",
        )
        sample_card_heading = st.text_input(
            _CARD_HEADING_LABEL,
            value="",
            placeholder=_CARD_HEADING_PLACEHOLDER,
            key="design_sample_card_heading",
        )

    st.header(_CURRENT_CARD_LABEL)
    fmt: FormatId = st.selectbox(
        "Aspect ratio",
        options=["square", "portrait_post", "story"],
        format_func=lambda x: _FORMAT_LABELS[x],
    )
    scale = st.slider("Preview scale", min_value=0.22, max_value=0.55, value=0.36, step=0.01)
    selected_layout: LayoutId = st.selectbox(
        "Layout",
        options=["hero", "tiles", "minimal", "spotlight"],
        format_func=lambda x: {
            "hero": "Hero grid (4 stats)",
            "tiles": "Stat tiles (6)",
            "minimal": "Minimal list",
            "spotlight": "Single stat spotlight",
        }[x],
    )
    spotlight_stat: SpotlightStatId = st.selectbox(
        "Spotlight stat",
        options=["species", "lifers", "checklists", "locations"],
        format_func=lambda x: spotlight_stat_label(x, period_mode),
        disabled=selected_layout != "spotlight",
        help="Choose which stat to highlight when the Spotlight layout is selected.",
    )

df: pd.DataFrame | None = None
stats: ShareSummaryStats = sample_share_summary_stats()
all_time: ShareSummaryAllTimeStats | None = ShareSummaryAllTimeStats(
    total_species_taxa=10_800,
    total_families_taxa=248,
    observed_species_taxa=847,
    world_bird_coverage_pct=6.8,
)

if not use_sample:
    if uploaded is None:
        st.info("Upload an eBird CSV in the sidebar, or enable **Use sample data**.")
        st.stop()
    with st.spinner("Loading CSV…"):
        df = load_dataset(uploaded)
    if df is None or df.empty:
        st.warning("No data found in this file.")
        st.stop()
else:
    st.sidebar.markdown("---")
    if period_mode == "year":
        y = st.sidebar.number_input("Sample year", min_value=2000, max_value=2100, value=2025)
        stats = sample_share_summary_stats(period_label=str(int(y)), period_kind="year")
    elif period_mode == "month":
        y = st.sidebar.number_input("Sample year", min_value=2000, max_value=2100, value=2025)
        m = st.sidebar.number_input("Sample month", min_value=1, max_value=12, value=6)
        stats = sample_share_summary_stats(
            period_label=date(int(y), int(m), 1).strftime("%B %Y"),
            period_kind="month",
        )
    elif period_mode == "week":
        stats = sample_share_summary_stats(
            period_label="May 31, 2025 - June 6, 2025",
            period_kind="week",
        )
    elif sample_custom_start is not None and sample_custom_end is not None:
        start, end = sample_custom_start, sample_custom_end
        if end < start:
            start, end = end, start
        stats = sample_share_summary_stats(
            period_label=format_custom_date_range(start, end),
            period_kind="custom",
            trip_title=_card_heading_or_none(sample_card_heading),
        )

if df is not None:
    dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
    if dates.empty:
        st.warning("No dated checklists in this file.")
        st.stop()
    min_d = dates.min().date()
    max_d = dates.max().date()

    reference = date.today()
    if period_mode == "year":
        if period_anchor is not None:
            period = resolve_period("year", anchor=period_anchor, reference=reference)
        else:
            years = sorted({int(y) for y in dates.dt.year.unique()})
            year = st.sidebar.selectbox("Year", options=years, index=len(years) - 1)
            period = period_for_year(year)
    elif period_mode == "month":
        if period_anchor is not None:
            period = resolve_period("month", anchor=period_anchor, reference=reference)
        else:
            month_options = sorted({(int(r.year), int(r.month)) for r in dates.dt.to_pydatetime()})
            labels = [date(y, m, 1).strftime("%B %Y") for y, m in month_options]
            pick = st.sidebar.selectbox("Month", options=range(len(labels)), format_func=lambda i: labels[i])
            y, m = month_options[pick]
            period = period_for_month(y, m)
    elif period_mode == "week":
        if period_anchor is not None:
            period = resolve_period("week", anchor=period_anchor, reference=reference)
        else:
            week_starts = sorted({period_for_week_containing(d).start for d in dates.dt.date})
            week_labels = [
                period_for_week_containing(ws).label for ws in week_starts
            ]
            pick = st.sidebar.selectbox("Week", options=range(len(week_labels)), format_func=lambda i: week_labels[i])
            period = period_for_week_containing(week_starts[pick])
    else:
        start = st.sidebar.date_input(
            "Start date",
            value=min_d,
            min_value=min_d,
            max_value=max_d,
            key="design_csv_custom_start",
        )
        end = st.sidebar.date_input(
            "End date",
            value=max_d,
            min_value=min_d,
            max_value=max_d,
            key="design_csv_custom_end",
        )
        card_heading = st.sidebar.text_input(
            _CARD_HEADING_LABEL,
            value="",
            placeholder=_CARD_HEADING_PLACEHOLDER,
            key="design_csv_card_heading",
        )
        period = period_for_custom(start, end, trip_title=_card_heading_or_none(card_heading))

    computed = compute_share_summary_stats(df, period)
    if computed is None:
        st.warning("Could not compute stats for this period.")
        st.stop()
    stats = computed
    all_time = compute_share_summary_all_time_stats(df, taxonomy_locale=TAXONOMY_LOCALE_DEFAULT)

status_metrics = summary_status_metrics(stats, all_time=all_time)

png_filename = share_summary_png_filename(stats, layout=selected_layout, fmt=fmt)
png_bytes: bytes | None = None
try:
    png_bytes = _cached_share_summary_png(stats, selected_layout, fmt, spotlight_stat)
except RuntimeError as exc:
    png_export_error = str(exc)
else:
    png_export_error = None

st.sidebar.markdown("---")
st.sidebar.header("Export")
if png_export_error:
    st.sidebar.warning(png_export_error)
elif png_bytes is not None:
    st.sidebar.download_button(
        "Export current card",
        data=png_bytes,
        file_name=png_filename,
        mime="image/png",
        use_container_width=True,
        help="PNG of the current card — not the all-layouts comparison below.",
    )

tab_social_cards, = st.tabs([_SOCIAL_CARDS_TAB_LABEL])

with tab_social_cards:
    with st.expander(_STATS_EXPANDER_LABEL, expanded=False):
        cols = st.columns(4)
        for i, (label, value) in enumerate(status_metrics):
            cols[i % 4].metric(label, value)

    st.subheader(_CURRENT_CARD_LABEL)
    st.markdown(
        render_share_summary_preview_html(
            stats,
            layout=selected_layout,
            fmt=fmt,
            scale=scale,
            spotlight_stat=spotlight_stat,
        ),
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("All layouts")
    previews = all_layout_previews_html(stats, fmt=fmt, scale=scale, spotlight_stat=spotlight_stat)
    layout_cols = st.columns(4)
    labels = {
        "hero": "Hero grid",
        "tiles": "Stat tiles",
        "minimal": "Minimal list",
        "spotlight": "Spotlight",
    }
    for col, (layout_id, html) in zip(layout_cols, previews.items()):
        with col:
            st.markdown(f"**{labels[layout_id]}**")
            st.markdown(html, unsafe_allow_html=True)

    st.divider()
    st.caption(
        "Living design notes: `docs/explorer/issue-157-share-summary-tracker.md`"
    )
