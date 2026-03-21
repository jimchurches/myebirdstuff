"""
Streamlit-native **Checklist Statistics** tab: :class:`~personal_ebird_explorer.checklist_stats_compute.ChecklistStatsPayload`
rendered with nested ``st.tabs`` (one section visible at a time, like a single-open accordion) and
``st.dataframe`` key/value tables (refs #70).

All subtabs use ``st.dataframe`` with visible headers **Metric** and **Value** (and **eBird link** for the
streak table’s link column). **Streak:** optional eBird URL via ``LinkColumn`` with column-level
``display_text`` **⧉** (same glyph as country / rankings HTML). Hint strings stay aligned with
``personal_ebird_explorer.checklist_stats_display`` where duplicated.
"""

from __future__ import annotations

from urllib.parse import quote as url_quote

import pandas as pd
import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload

AUDUBON_4BBRW_URL = (
    "https://www.audubon.org/news/these-mighty-shorebirds-keep-breaking-flight-records-and-you-can-follow-along"
)

# Sync with checklist_stats_display.format_checklist_stats_bundle (time_hint / incomplete_hint / godwit_hint).
_CHECKLIST_TYPES_INCOMPLETE_CAPTION = (
    "Incidental, historical and other untimed checklists don't count towards the incomplete checklist total."
)
_TIME_EBIRDED_CAPTION = (
    "Incidental, historical and other untimed checklists don't count towards total time, "
    "but do count towards Days with a checklist."
)
_GODWIT_CAPTION = (
    "4BBRW: Bar-tailed Godwit, Alaska→Tasmania, ~13,560 km nonstop (2022). 11 days without landing."
)

# Same “open external resource” glyph as ``rankings_display`` / country stats HTML (not a webfont icon).
_EBIRD_LINK_GLYPH = "⧉"
# Link column: tighter than ``LinkColumn``’s ``"small"`` (75px); just room for ⧉.
_STREAK_LINK_COL_PX = 52


def render_checklist_stats_streamlit_native(payload: ChecklistStatsPayload) -> None:
    """Render stats subsections in nested ``st.tabs`` (only one panel visible at a time)."""

    def _metric_table(rows: list[tuple[str, str]]) -> None:
        st.dataframe(
            pd.DataFrame(rows, columns=["Metric", "Value"]),
            hide_index=True,
            width="stretch",
            column_config={
                "Metric": st.column_config.TextColumn("Metric"),
                "Value": st.column_config.TextColumn("Value"),
            },
        )

    def _checklist_href(sid: str) -> str:
        """Return checklist URL or empty string (``LinkColumn`` shows literal \"none\" for Python ``None``)."""
        s = str(sid).strip() if sid is not None else ""
        if not s:
            return ""
        return f"https://ebird.org/checklist/{url_quote(s, safe='')}"

    def _lifelist_href(lid: str) -> str:
        s = str(lid).strip() if lid is not None else ""
        if not s:
            return ""
        return f"https://ebird.org/lifelist/{url_quote(s, safe='')}"

    def _streak_table() -> None:
        rows: list[tuple[str, str, str]] = [
            ("Longest streak (consecutive days)", str(payload.streak), ""),
            ("Start date", str(payload.streak_start_date), _checklist_href(payload.streak_start_sid)),
            ("Start location", str(payload.streak_start_loc), _lifelist_href(payload.streak_start_lid)),
            ("End date", str(payload.streak_end_date), _checklist_href(payload.streak_end_sid)),
            ("End location", str(payload.streak_end_loc), _lifelist_href(payload.streak_end_lid)),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["Metric", "Value", "eBird link"]),
            hide_index=True,
            width="stretch",
            column_config={
                "Metric": st.column_config.TextColumn("Metric"),
                "Value": st.column_config.TextColumn("Value"),
                "eBird link": st.column_config.LinkColumn(
                    "eBird link",
                    display_text=_EBIRD_LINK_GLYPH,
                    width=_STREAK_LINK_COL_PX,
                ),
            },
        )

    # ``st.expander`` cannot be grouped “only one open”; nested ``st.tabs`` is the native pattern
    # for mutually exclusive panels (similar to a single-open accordion).
    t_overview, t_types, t_dist, t_time, t_others, t_streak = st.tabs(
        [
            "Overview",
            "Checklist types",
            "Total distance",
            "Time eBirded",
            "eBirding with Others",
            "Checklist streak",
        ]
    )

    with t_overview:
        _metric_table(
            [
                ("Total checklists", f"{payload.n_checklists:,}"),
                ("Total species", f"{payload.n_species:,}"),
                ("Total individuals", f"{payload.n_individuals:,}"),
            ]
        )

    with t_types:
        _metric_table(list(payload.protocol_rows))
        st.caption(_CHECKLIST_TYPES_INCOMPLETE_CAPTION)

    with t_dist:
        _metric_table(
            [
                ("Kilometers traveled", f"{payload.total_km:,.2f}"),
                ("Parkruns (5 km)", f"{payload.parkruns:,.2f}"),
                ("Marathons (42.195 km)", f"{payload.marathons:,.2f}"),
                ("Longest Flight (4BBRW)", f"{payload.times_godwit:,.2f}"),
                ("Times around the equator", f"{payload.times_equator:,.2f}"),
            ]
        )
        st.caption(
            f"{_GODWIT_CAPTION} [Audubon article]({AUDUBON_4BBRW_URL})."
        )

    with t_time:
        _metric_table(
            [
                ("Total minutes", f"{payload.total_minutes:,.2f}"),
                ("Total hours", f"{payload.total_hours:,.2f}"),
                ("Total days", f"{payload.total_days_dec:,.2f}"),
                ("Months", f"{payload.total_months:,.2f}"),
                ("Total years", f"{payload.total_years:,.2f}"),
                ("Days with a checklist", f"{payload.n_days_with_checklist:,}"),
            ]
        )
        st.caption(_TIME_EBIRDED_CAPTION)

    with t_others:
        _metric_table(
            [
                ("Shared checklists", f"{payload.n_shared:,}"),
                ("Minutes eBirding with others", f"{payload.shared_minutes:,.0f}"),
                ("Hours eBirding with others", f"{payload.shared_hours:,.2f}"),
                ("Days birding with others", f"{payload.n_days_birding_with_others:,}"),
            ]
        )

    with t_streak:
        _streak_table()
