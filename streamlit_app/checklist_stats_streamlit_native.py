"""
Streamlit-native **Checklist Statistics** tab: :class:`~personal_ebird_explorer.checklist_stats_compute.ChecklistStatsPayload`
rendered with ``st.expander`` and ``st.dataframe`` (refs #70).

Hint strings are kept aligned with ``personal_ebird_explorer.checklist_stats_display`` where duplicated.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload

AUDUBON_4BBRW_URL = (
    "https://www.audubon.org/news/these-mighty-shorebirds-keep-breaking-flight-records-and-you-can-follow-along"
)

# Sync with checklist_stats_display.format_checklist_stats_bundle (time_hint / godwit_hint).
_TIME_EBIRDED_CAPTION = (
    "Incidental, historical and other untimed checklists don't count towards total time, "
    "but do count towards Days with a checklist."
)
_GODWIT_CAPTION = (
    "4BBRW: Bar-tailed Godwit, Alaska→Tasmania, ~13,560 km nonstop (2022). 11 days without landing."
)


def render_checklist_stats_streamlit_native(payload: ChecklistStatsPayload) -> None:
    """Render overview / protocols / distance / time / shared / streak using ``st.expander`` stacks."""

    def _metric_table(rows: list[tuple[str, str]]) -> None:
        # ``width`` replaces deprecated ``use_container_width`` (Streamlit ≥ ~1.40).
        st.dataframe(
            pd.DataFrame(rows, columns=["Metric", "Value"]),
            hide_index=True,
            width="stretch",
        )

    with st.expander("Overview", expanded=True):
        _metric_table(
            [
                ("Total checklists", f"{payload.n_checklists:,}"),
                ("Total species", f"{payload.n_species:,}"),
                ("Total individuals", f"{payload.n_individuals:,}"),
            ]
        )

    with st.expander("Checklist types"):
        _metric_table(list(payload.protocol_rows))

    with st.expander("Total distance"):
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

    with st.expander("Time eBirded"):
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

    with st.expander("eBirding with Others"):
        _metric_table(
            [
                ("Shared checklists", f"{payload.n_shared:,}"),
                ("Minutes eBirding with others", f"{payload.shared_minutes:,.0f}"),
                ("Hours eBirding with others", f"{payload.shared_hours:,.2f}"),
                ("Days birding with others", f"{payload.n_days_birding_with_others:,}"),
            ]
        )

    with st.expander("Checklist streak"):
        _metric_table(
            [
                ("Longest streak (consecutive days)", str(payload.streak)),
                ("Start date", payload.streak_start_date),
                ("Start location", payload.streak_start_loc),
                ("End date", payload.streak_end_date),
                ("End location", payload.streak_end_loc),
            ]
        )
        link_bits: list[str] = []
        if payload.streak_start_sid:
            u = f"https://ebird.org/checklist/{payload.streak_start_sid}"
            link_bits.append(f"[Start checklist]({u})")
        if payload.streak_end_sid:
            u = f"https://ebird.org/checklist/{payload.streak_end_sid}"
            link_bits.append(f"[End checklist]({u})")
        if link_bits:
            st.caption("eBird — " + " · ".join(link_bits))
