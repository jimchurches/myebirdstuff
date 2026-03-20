"""
Structured checklist / yearly / rankings prep for the Checklist Statistics UI.

Computes numeric summaries and ranking inputs without HTML (refs #68).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from personal_ebird_explorer.species_logic import countable_species_vectorized
from personal_ebird_explorer.stats import (
    compute_rankings,
    longest_streak,
    safe_count,
    yearly_summary_stats,
)


PROTOCOL_ORDER = ["Traveling", "Stationary", "Incidental", "Pelagic Protocol", "Historical", "Other"]
PROTOCOL_MAP = {
    "traveling": "Traveling",
    "travelling": "Traveling",
    "traveling count": "Traveling",
    "ebird - traveling count": "Traveling",
    "stationary": "Stationary",
    "stationary count": "Stationary",
    "ebird - stationary count": "Stationary",
    "incidental": "Incidental",
    "incidental observation": "Incidental",
    "ebird - casual observation": "Incidental",
    "casual observation": "Incidental",
    "pelagic": "Pelagic Protocol",
    "pelagic protocol": "Pelagic Protocol",
    "historical": "Historical",
    "historical checklist": "Historical",
}


@dataclass(frozen=True)
class ChecklistStatsPayload:
    """All values needed to render checklist stats, yearly summary, and rankings tables."""

    n_checklists: int
    n_species: int
    n_individuals: int
    n_completed_display: str
    protocol_rows: List[Tuple[str, str]]
    total_minutes: float
    total_hours: float
    total_days_dec: float
    total_months: float
    total_years: float
    n_days_with_checklist: int
    n_shared: int
    shared_minutes: float
    shared_hours: float
    n_days_birding_with_others: int
    total_km: float
    parkruns: float
    marathons: float
    times_equator: float
    times_godwit: float
    streak: int
    streak_start_date: str
    streak_start_loc: str
    streak_start_sid: str
    streak_end_date: str
    streak_end_loc: str
    streak_end_sid: str
    rankings: Dict[str, Any]
    years_list: List[Any]
    yearly_rows: List[Tuple[str, List[str]]]
    incomplete_by_year: Dict[Any, Any]


def compute_checklist_stats_payload(df: pd.DataFrame, top_n_limit: int) -> Optional[ChecklistStatsPayload]:
    """Build structured checklist statistics from a sighting-level DataFrame.

    Returns ``None`` when *df* is empty. *top_n_limit* caps ranking list lengths
    (same as notebook **Top N table limit**).
    """
    if df.empty:
        return None

    cl = df.drop_duplicates(subset=["Submission ID"]).copy()
    dur_col = "Duration (Min)" if "Duration (Min)" in df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in df.columns else None

    n_checklists = cl["Submission ID"].nunique()
    n_species = int(countable_species_vectorized(df).dropna().nunique())
    n_individuals = int(df["Count"].apply(safe_count).sum())

    n_completed = "—"
    if "All Obs Reported" in df.columns:
        a = cl["All Obs Reported"]
        reported = a.notna() & (
            (pd.to_numeric(a, errors="coerce") == 1)
            | (a.astype(str).str.strip().str.upper().isin(["TRUE", "YES", "Y"]))
        )
        n_completed = f"{reported.sum():,}"

    protocol_counts = {p: 0 for p in PROTOCOL_ORDER}
    if "Protocol" in df.columns:
        proto_df = cl.dropna(subset=["Protocol"])
        for _, row in proto_df.iterrows():
            p = str(row["Protocol"]).strip().lower()
            if not p:
                continue
            disp = PROTOCOL_MAP.get(p, "Other")
            protocol_counts[disp] = protocol_counts.get(disp, 0) + 1
    protocol_rows = [(k, f"{v:,}") for k, v in protocol_counts.items()]
    protocol_rows.append(("Completed checklists", n_completed))

    total_minutes = 0.0
    if dur_col:
        timed = cl.dropna(subset=[dur_col]).copy()
        if "Protocol" in timed.columns:
            excl = timed["Protocol"].str.strip().str.lower().str.contains(
                "incidental|historical|casual observation", na=False, regex=True
            )
            timed = timed[~excl]
        total_minutes = pd.to_numeric(timed[dur_col], errors="coerce").fillna(0).sum()
    total_hours = total_minutes / 60
    total_days_dec = total_minutes / (60 * 24)
    total_months = total_minutes / (60 * 24 * 30.44)
    total_years = total_minutes / (60 * 24 * 365.25)
    dates = cl.dropna(subset=["Date"])["Date"]
    unique_dates = dates.dt.normalize().unique()
    n_days_with_checklist = len(unique_dates)

    n_shared = 0
    shared_minutes = 0.0
    n_days_birding_with_others = 0
    if "Number of Observers" in df.columns:
        shared_cl = cl.dropna(subset=["Number of Observers"])
        shared_mask = shared_cl["Number of Observers"].astype(float) > 1
        n_shared = int(shared_mask.sum())
        if n_shared > 0:
            shared_ids = set(shared_cl.loc[shared_mask, "Submission ID"])
            shared_subset = cl[cl["Submission ID"].isin(shared_ids)]
            if "Date" in shared_subset.columns:
                n_days_birding_with_others = shared_subset["Date"].dt.normalize().nunique()
            if dur_col:
                shared_dur = shared_subset.dropna(subset=[dur_col])
                shared_minutes = pd.to_numeric(shared_dur[dur_col], errors="coerce").fillna(0).sum()
    shared_hours = shared_minutes / 60

    total_km = 0.0
    if dist_col:
        total_km = pd.to_numeric(cl[dist_col], errors="coerce").fillna(0).sum()
    parkruns = total_km / 5
    marathons = total_km / 42.195
    equator_km = 40_075
    times_equator = total_km / equator_km
    godwit_km = 13_560
    times_godwit = total_km / godwit_km

    streak, streak_start_date, streak_start_loc, streak_start_sid, streak_end_date, streak_end_loc, streak_end_sid = longest_streak(
        unique_dates, cl
    )

    rankings = compute_rankings(df, cl, top_n_limit, dur_col, dist_col)
    years_list, yearly_rows, incomplete_by_year = yearly_summary_stats(df, cl, dur_col, dist_col)

    return ChecklistStatsPayload(
        n_checklists=n_checklists,
        n_species=n_species,
        n_individuals=n_individuals,
        n_completed_display=n_completed,
        protocol_rows=protocol_rows,
        total_minutes=total_minutes,
        total_hours=total_hours,
        total_days_dec=total_days_dec,
        total_months=total_months,
        total_years=total_years,
        n_days_with_checklist=n_days_with_checklist,
        n_shared=n_shared,
        shared_minutes=shared_minutes,
        shared_hours=shared_hours,
        n_days_birding_with_others=n_days_birding_with_others,
        total_km=total_km,
        parkruns=parkruns,
        marathons=marathons,
        times_equator=times_equator,
        times_godwit=times_godwit,
        streak=streak,
        streak_start_date=streak_start_date,
        streak_start_loc=streak_start_loc,
        streak_start_sid=streak_start_sid,
        streak_end_date=streak_end_date,
        streak_end_loc=streak_end_loc,
        streak_end_sid=streak_end_sid,
        rankings=rankings,
        years_list=years_list,
        yearly_rows=yearly_rows,
        incomplete_by_year=incomplete_by_year,
    )
