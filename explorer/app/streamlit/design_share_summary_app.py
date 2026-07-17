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

_REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd
import streamlit as st

from explorer.app.streamlit.social_cards_session_keys import DESIGN_SOCIAL_CARDS_KEYS
from explorer.app.streamlit.social_cards_sidebar_ui import (
    render_sidebar_card_controls,
    render_sidebar_geo_scope_controls,
)
from explorer.app.streamlit.social_cards_streamlit_helpers import (
    card_stat_data_scope_from_design_source,
    ordered_custom_date_range,
    period_has_checklist_data,
)
from explorer.app.streamlit.social_cards_streamlit_ui import (
    SOCIAL_CARDS_CURRENT_CARD_LABEL,
    render_current_card_fragment,
)
from explorer.core.data_loader import add_datetime_column, load_dataset
from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.share_summary_compute import (
    PeriodAnchor,
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
    compute_share_summary_all_time_stats,
    compute_share_summary_stats,
    filter_df_by_geo_scope,
    geo_scope_display_label,
    period_for_custom,
    period_for_lifetime,
    period_for_month,
    period_for_week_containing,
    period_for_year,
    resolve_period,
    suggest_period_anchor,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_INSIGHT_FACT_DEFAULT,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    SHARE_SUMMARY_STORY_MAX_STATS,
)
from explorer.core.share_summary_insight_facts import (
    ShareSummaryInsightFact,
    compute_insight_facts,
    species_common_names_in_period,
)
from explorer.presentation.share_summary_circle_layout_playground import (
    CIRCLE_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX,
    render_circle_layout_playground_html,
)
from explorer.presentation.share_summary_hex_preview import (
    HEX_GRID_EXPERIMENTAL_NOTICE,
    HEX_VARIANT_IDS,
    HEX_VARIANT_LABELS,
    HexVariantId,
    render_hex_grid_preview_html,
)
from explorer.presentation.share_summary_preview import (
    default_card_stat_labels,
    sample_share_summary_stats,
    summary_status_metrics,
)

_DESIGN_STUDIO_TITLE = "Social sharing design studio"
_SOCIAL_CARDS_TAB_LABEL = "Social Cards"
_HEX_EXPERIMENTS_TAB_LABEL = "Hex grid experiments (experimental)"
_CIRCLE_LAYOUT_TAB_LABEL = "Circle layout"
_CARD_HEADING_LABEL = "Card Heading (optional)"
_CARD_HEADING_PLACEHOLDER = "e.g. North Coast NSW Exploration"
_DESIGN_HEX_SELECTED_KEY = "design_hex_selected_variant"


def _card_heading_or_none(text: str) -> str | None:
    """Normalize sidebar card heading; maps to ``trip_title`` on stats/period objects."""
    stripped = (text or "").strip()
    return stripped or None


@st.cache_data
def _design_sample_dataset(sample_year: int) -> pd.DataFrame:
    """Small multi-region export for sample mode (AU NSW/QLD, India Goa)."""
    y = int(sample_year)
    checklists: list[tuple[str, str, str, str, float, float, list[tuple[str, str]]]] = [
        (
            "S9001",
            "AU-NSW",
            f"{y}-06-05",
            "Royal National Park",
            -34.07,
            151.08,
            [
                ("Superb Fairywren", "Malurus cyaneus"),
                ("Laughing Kookaburra", "Dacelo novaeguineae"),
                ("Australian Magpie", "Gymnorhina tibicen"),
            ],
        ),
        (
            "S9002",
            "AU-NSW",
            f"{y}-06-12",
            "Blue Mountains",
            -33.71,
            150.31,
            [
                ("Crimson Rosella", "Platycercus elegans"),
                ("Eastern Yellow Robin", "Eopsaltria australis"),
                ("Willie Wagtail", "Rhipidura leucophrys"),
            ],
        ),
        (
            "S9003",
            "AU-QLD",
            f"{y}-05-20",
            "Roma Street Parkland",
            -27.46,
            153.02,
            [
                ("Rainbow Lorikeet", "Trichoglossus moluccanus"),
                ("Sulphur-crested Cockatoo", "Cacatua galerita"),
                ("Australian Pelican", "Pelecanus conspicillatus"),
            ],
        ),
        (
            "S9004",
            "IN-GA",
            f"{y}-11-28",
            "Arambol Beach",
            15.688,
            73.703,
            [
                ("Indian Pond-Heron", "Ardeola grayii"),
                ("House Crow", "Corvus splendens"),
                ("White-throated Kingfisher", "Halcyon smyrnensis"),
            ],
        ),
    ]
    records: list[dict] = []
    for sid, state, dt, loc_name, lat, lon, species in checklists:
        for common, scientific in species:
            records.append(
                {
                    "Submission ID": sid,
                    "Date": dt,
                    "Time": "08:00 AM",
                    "State/Province": state,
                    "Location ID": f"L_{sid}",
                    "Location": loc_name,
                    "Latitude": lat,
                    "Longitude": lon,
                    "Common Name": common,
                    "Scientific Name": scientific,
                    "Count": 2,
                    "Protocol": "eBird - Traveling Count",
                    "All Obs Reported": 1,
                    "Duration (Min)": 60.0,
                    "Number of Observers": 1.0,
                }
            )
    return add_datetime_column(pd.DataFrame(records))


st.set_page_config(page_title=_DESIGN_STUDIO_TITLE, layout="wide")
st.title(_DESIGN_STUDIO_TITLE)
st.caption(
    "Exploratory tool only. Compare HTML mockups before choosing layouts for the main app."
)

keys = DESIGN_SOCIAL_CARDS_KEYS
df: pd.DataFrame | None = None
geo_scope = ShareSummaryGeoScope()

with st.sidebar:
    st.header("Data")
    use_sample = st.toggle("Use sample data", value=True)
    uploaded = (
        None if use_sample else st.file_uploader("eBird CSV export", type=["csv"])
    )
    if use_sample:
        df = _design_sample_dataset(date.today().year)
    elif uploaded is not None:
        with st.spinner("Loading CSV…"):
            df = load_dataset(uploaded)

    st.header("Scope")
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
    )
    period_anchor: PeriodAnchor | None = None
    selected_year: int | None = None
    if period_mode == "year":
        selected_year = int(
            st.number_input(
                "Year",
                min_value=2000,
                max_value=2100,
                value=date.today().year,
                step=1,
                key="design_period_year",
            )
        )
    elif period_mode in ("month", "week"):
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
        sample_start, sample_end, sample_swapped = ordered_custom_date_range(
            st.session_state.get("design_sample_custom_start"),
            st.session_state.get("design_sample_custom_end"),
            default_start=date(2025, 6, 1),
            default_end=date(2025, 6, 7),
        )
        st.session_state["design_sample_custom_start"] = sample_start
        st.session_state["design_sample_custom_end"] = sample_end
        if sample_swapped:
            st.caption(
                "Start and end dates were swapped so the range runs forwards."
            )
        sample_custom_start = st.date_input(
            "Start date",
            value=sample_start,
            max_value=sample_end,
            key="design_sample_custom_start",
        )
        sample_custom_end = st.date_input(
            "End date",
            value=sample_end,
            min_value=sample_start,
            key="design_sample_custom_end",
        )
        sample_card_heading = st.text_input(
            _CARD_HEADING_LABEL,
            value="",
            placeholder=_CARD_HEADING_PLACEHOLDER,
            key="design_sample_card_heading",
        )

    if df is not None and not df.empty:
        geo_scope = render_sidebar_geo_scope_controls(df, keys)
    elif not use_sample and uploaded is None:
        st.caption("Upload a CSV to choose country and region.")
    elif df is not None and df.empty:
        st.caption("No data in file.")

    sidebar_selection = render_sidebar_card_controls(keys)

resolved_period = None
stats: ShareSummaryStats = sample_share_summary_stats()
all_time: ShareSummaryAllTimeStats | None = ShareSummaryAllTimeStats(
    total_species_taxa=10_800,
    total_families_taxa=248,
)

if not use_sample:
    if uploaded is None:
        st.info("Upload an eBird CSV in the sidebar, or enable **Use sample data**.")
        st.stop()
    if df is None or df.empty:
        st.warning("No data found in this file.")
        st.stop()

if df is not None:
    df_scoped = filter_df_by_geo_scope(df, geo_scope)
    dates = pd.to_datetime(df_scoped["Date"], errors="coerce").dropna()
    if dates.empty:
        st.warning("No dated checklists in this file.")
        st.stop()
    min_d = dates.min().date()
    max_d = dates.max().date()

    reference = date.today()
    if period_mode == "year":
        if selected_year is None:
            st.warning("Select a year in the sidebar.")
            st.stop()
        period = period_for_year(selected_year)
    elif period_mode == "month":
        if period_anchor is not None:
            period = resolve_period("month", anchor=period_anchor, reference=reference)
        else:
            month_options = sorted(
                {(int(r.year), int(r.month)) for r in dates.dt.to_pydatetime()}
            )
            labels = [date(y, m, 1).strftime("%B %Y") for y, m in month_options]
            pick = st.sidebar.selectbox(
                "Month", options=range(len(labels)), format_func=lambda i: labels[i]
            )
            y, m = month_options[pick]
            period = period_for_month(y, m)
    elif period_mode == "week":
        if period_anchor is not None:
            period = resolve_period("week", anchor=period_anchor, reference=reference)
        else:
            week_starts = sorted(
                {period_for_week_containing(d).start for d in dates.dt.date}
            )
            week_labels = [period_for_week_containing(ws).label for ws in week_starts]
            pick = st.sidebar.selectbox(
                "Week",
                options=range(len(week_labels)),
                format_func=lambda i: week_labels[i],
            )
            period = period_for_week_containing(week_starts[pick])
    elif period_mode == "lifetime":
        period = period_for_lifetime(min_d, max_d)
    elif period_mode == "custom":
        if use_sample:
            start, end = sample_custom_start, sample_custom_end
            if start is None or end is None:
                st.warning("Choose custom dates in the sidebar.")
                st.stop()
            start, end, _swapped = ordered_custom_date_range(
                start,
                end,
                default_start=date(2025, 6, 1),
                default_end=date(2025, 6, 7),
            )
            period = period_for_custom(
                start,
                end,
                trip_title=_card_heading_or_none(sample_card_heading),
            )
        else:
            csv_start, csv_end, csv_swapped = ordered_custom_date_range(
                st.session_state.get("design_csv_custom_start"),
                st.session_state.get("design_csv_custom_end"),
                default_start=min_d,
                default_end=max_d,
            )
            st.session_state["design_csv_custom_start"] = csv_start
            st.session_state["design_csv_custom_end"] = csv_end
            if csv_swapped:
                st.sidebar.caption(
                    "Start and end dates were swapped so the range runs forwards."
                )
            start = st.sidebar.date_input(
                "Start date",
                value=csv_start,
                min_value=min_d,
                max_value=csv_end,
                key="design_csv_custom_start",
            )
            end = st.sidebar.date_input(
                "End date",
                value=csv_end,
                min_value=csv_start,
                max_value=max_d,
                key="design_csv_custom_end",
            )
            card_heading = st.sidebar.text_input(
                _CARD_HEADING_LABEL,
                value="",
                placeholder=_CARD_HEADING_PLACEHOLDER,
                key="design_csv_card_heading",
            )
            period = period_for_custom(
                start, end, trip_title=_card_heading_or_none(card_heading)
            )

    resolved_period = period
    lifer_ref = df if not geo_scope.is_world else None
    computed = compute_share_summary_stats(
        df_scoped, period, lifer_reference_df=lifer_ref, geo_scope=geo_scope
    )
    if computed is None:
        st.warning("Could not compute stats for this period.")
        st.stop()
    stats = computed
    all_time = (
        compute_share_summary_all_time_stats(
            df_scoped, taxonomy_locale=TAXONOMY_LOCALE_DEFAULT
        )
        if geo_scope.is_world
        else None
    )

upload_name = uploaded.name if uploaded is not None else None
card_stat_data_scope = card_stat_data_scope_from_design_source(
    use_sample=use_sample,
    period_kind=stats.period_kind,
    period_label=stats.period_label,
    upload_name=upload_name,
    geo_scope=geo_scope,
    fmt=sidebar_selection.fmt,
    tiles_presentation=sidebar_selection.tiles_presentation,
)
scope_label = geo_scope_display_label(geo_scope)

status_metrics = summary_status_metrics(stats, all_time=all_time, geo_scope=geo_scope)

if keys.spotlight_label not in st.session_state:
    st.session_state[keys.spotlight_label] = SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT
if keys.insight_fact not in st.session_state:
    st.session_state[keys.insight_fact] = SHARE_SUMMARY_INSIGHT_FACT_DEFAULT

insight_facts: list[ShareSummaryInsightFact] = []
insight_species_options: tuple[str, ...] = ()
if (
    df is not None
    and resolved_period is not None
    and sidebar_selection.layout == "insight"
):
    insight_facts = compute_insight_facts(df_scoped, resolved_period)
    insight_species_options = species_common_names_in_period(df_scoped, resolved_period)
    if insight_species_options and keys.insight_species not in st.session_state:
        st.session_state[keys.insight_species] = insight_species_options[0]

tab_social_cards, tab_hex_experiments, tab_circle_layout = st.tabs(
    [
        _SOCIAL_CARDS_TAB_LABEL,
        _HEX_EXPERIMENTS_TAB_LABEL,
        _CIRCLE_LAYOUT_TAB_LABEL,
    ]
)

hex_card_stat_labels = default_card_stat_labels(
    "tiles",
    status_metrics,
    period_kind=stats.period_kind,
    geo_scope=geo_scope,
)
if (
    sidebar_selection.fmt == "story"
    and len(hex_card_stat_labels) < SHARE_SUMMARY_STORY_MAX_STATS
):
    picked = set(hex_card_stat_labels)
    extra: list[str] = []
    for label, _ in status_metrics:
        if label in picked:
            continue
        extra.append(label)
        if len(hex_card_stat_labels) + len(extra) >= SHARE_SUMMARY_STORY_MAX_STATS:
            break
    hex_card_stat_labels = hex_card_stat_labels + tuple(extra)
hex_preview_scale = min(sidebar_selection.scale, 0.32)

with tab_social_cards:
    if not use_sample and not period_has_checklist_data(stats):
        st.warning(
            f"No checklists in **{stats.period_label}** in this export. "
            "Try **Previous month** (or another range) in the sidebar, or pick a period that includes your data."
        )

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
        resolved_period=resolved_period,
        current_card_label=SOCIAL_CARDS_CURRENT_CARD_LABEL,
    )

with tab_circle_layout:
    st.caption(
        "Dev-only circle tuner — Statistics Tiles and Spotlight at all export sizes. "
        "Copy output into ``share_summary_circles_preview.py``."
    )
    st.iframe(
        render_circle_layout_playground_html(),
        height=CIRCLE_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX,
    )

with tab_hex_experiments:
    st.info(HEX_GRID_EXPERIMENTAL_NOTICE)
    st.markdown(
        "Uniform **hexicons** for Statistics Tiles. **Organic hive** samples (bottom half) "
        "use edge-to-edge tessellation in irregular, jagged clusters — like a natural honeycomb "
        "blob, not balanced rows or a dashboard grid. Legacy overlapping-row samples are kept "
        "for comparison only."
    )
    if _DESIGN_HEX_SELECTED_KEY not in st.session_state:
        st.session_state[_DESIGN_HEX_SELECTED_KEY] = HEX_VARIANT_IDS[0]
    selected_hex: HexVariantId = st.selectbox(
        "Enlarged preview",
        options=HEX_VARIANT_IDS,
        format_func=lambda v: HEX_VARIANT_LABELS[v],
        key=_DESIGN_HEX_SELECTED_KEY,
    )
    hex_cols = st.columns(2)
    for i, variant in enumerate(HEX_VARIANT_IDS):
        with hex_cols[i % 2]:
            title = HEX_VARIANT_LABELS[variant]
            if variant == selected_hex:
                title = f"{title} · selected"
            st.markdown(f"**{title}**")
            st.markdown(
                render_hex_grid_preview_html(
                    stats,
                    variant=variant,
                    fmt=sidebar_selection.fmt,
                    scale=hex_preview_scale,
                    card_stat_labels=hex_card_stat_labels,
                    all_time=all_time,
                    color_scheme_index=sidebar_selection.color_scheme_index,
                    geo_scope=geo_scope,
                    scope_label=scope_label,
                ),
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("Selected preview (larger)")
    st.caption(
        f"{HEX_VARIANT_LABELS[selected_hex]} — use **Preview scale** in the sidebar "
        f"(currently {sidebar_selection.scale:.0%} of export size)."
    )
    st.markdown(
        render_hex_grid_preview_html(
            stats,
            variant=selected_hex,
            fmt=sidebar_selection.fmt,
            scale=sidebar_selection.scale,
            card_stat_labels=hex_card_stat_labels,
            all_time=all_time,
            color_scheme_index=sidebar_selection.color_scheme_index,
            geo_scope=geo_scope,
            scope_label=scope_label,
        ),
        unsafe_allow_html=True,
    )
