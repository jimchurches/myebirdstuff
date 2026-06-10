"""
Period-scoped stats for share-summary graphics (#157).

Computes the same headline metrics as yearly summary rows, but for an arbitrary
inclusive date window (year, month, ISO week, or custom trip range).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import pandas as pd

from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.species_family import build_base_species_to_family_map
from explorer.core.species_logic import countable_species_vectorized
from explorer.core.stats import checklist_country_keys, longest_streak, safe_count

PeriodKind = Literal["year", "month", "week", "custom"]


def _fmt_short_date(d: date) -> str:
    """Portable short date (e.g. ``5 Jan 2025``)."""
    return d.strftime("%d %b %Y").lstrip("0")


def format_us_date_range(start: date, end: date) -> str:
    """Long-form date range for weekly titles (e.g. ``May 31, 2026 - June 6, 2026``)."""
    if end < start:
        start, end = end, start
    if start == end:
        return _fmt_us_long_date(start)
    return f"{_fmt_us_long_date(start)} - {_fmt_us_long_date(end)}"


def _fmt_us_long_date(d: date) -> str:
    """``May 31, 2026`` — full month name, no zero-padded day."""
    return d.strftime("%B %d, %Y").replace(" 0", " ")


def format_custom_date_range(start: date, end: date) -> str:
    """Compact date range for trip cards (e.g. ``1 – 7 June 2025``, ``6 May – 12 May 2025``)."""
    if end < start:
        start, end = end, start
    if start == end:
        return _fmt_short_date(start)
    if start.year == end.year and start.month == end.month:
        month_year = start.strftime("%B %Y")
        return f"{start.day} – {end.day} {month_year}"
    if start.year == end.year:
        return f"{start.day} {start.strftime('%b')} – {end.day} {end.strftime('%b %Y')}"
    return f"{_fmt_short_date(start)} – {_fmt_short_date(end)}"


@dataclass(frozen=True)
class ShareSummaryPeriod:
    """Inclusive calendar period for share-summary stats."""

    kind: PeriodKind
    start: date
    end: date
    label: str
    trip_title: str | None = None

    @property
    def start_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.start)

    @property
    def end_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)


def period_for_year(year: int) -> ShareSummaryPeriod:
    start = date(int(year), 1, 1)
    end = date(int(year), 12, 31)
    return ShareSummaryPeriod(kind="year", start=start, end=end, label=str(year))


def period_for_month(year: int, month: int) -> ShareSummaryPeriod:
    start = date(int(year), int(month), 1)
    if month == 12:
        end = date(int(year), 12, 31)
    else:
        end = date(int(year), int(month) + 1, 1) - timedelta(days=1)
    label = start.strftime("%B %Y")
    return ShareSummaryPeriod(kind="month", start=start, end=end, label=label)


def _week_sun_sat_containing(day: date) -> tuple[date, date]:
    """Inclusive Sun–Sat week containing *day*."""
    days_since_sunday = (day.weekday() + 1) % 7
    start = day - timedelta(days=days_since_sunday)
    return start, start + timedelta(days=6)


def period_for_week_containing(day: date) -> ShareSummaryPeriod:
    """Calendar week Sun–Sat containing *day*; label is a long US-style date range."""
    start, end = _week_sun_sat_containing(day)
    return ShareSummaryPeriod(
        kind="week",
        start=start,
        end=end,
        label=format_us_date_range(start, end),
    )


def period_for_iso_week(year: int, week: int) -> ShareSummaryPeriod:
    """Deprecated alias — use :func:`period_for_week_containing` (Sun–Sat weeks)."""
    return period_for_week_containing(date.fromisocalendar(int(year), int(week), 1))


def period_for_custom(
    start: date,
    end: date,
    *,
    trip_title: str | None = None,
    label: str | None = None,
) -> ShareSummaryPeriod:
    """Custom inclusive date range; optional *trip_title* shown on the card above stats.

    *label* is a deprecated alias for *trip_title* (kept for callers that used the old name).
    """
    if end < start:
        start, end = end, start
    title = (trip_title or label or "").strip() or None
    date_label = format_custom_date_range(start, end)
    return ShareSummaryPeriod(
        kind="custom",
        start=start,
        end=end,
        label=date_label,
        trip_title=title,
    )


@dataclass(frozen=True)
class ShareSummaryStats:
    """Headline stats for one share-summary period."""

    period_label: str
    period_kind: PeriodKind
    trip_title: str | None = None
    species: int | None = None
    families: int | None = None
    individuals: int | None = None
    checklists: int | None = None
    locations: int | None = None
    lifers: int | None = None
    birding_hours: float | None = None
    days_with_checklist: int | None = None
    longest_streak: int | None = None
    countries: int | None = None


def _countries_in_period(cl: pd.DataFrame) -> int | None:
    """Distinct countries with checklists in *cl* (same keys as Country tab)."""
    if cl.empty:
        return None
    if "Country" not in cl.columns and "State/Province" not in cl.columns:
        return None
    keys = checklist_country_keys(cl)
    known = keys[(keys != "_UNKNOWN") & keys.notna()]
    if known.empty:
        return None
    return int(known.nunique())


def _mask_in_period(dates: pd.Series, period: ShareSummaryPeriod) -> pd.Series:
    ts = pd.to_datetime(dates, errors="coerce")
    return ts.notna() & (ts >= period.start_ts) & (ts <= period.end_ts)


def compute_share_summary_stats(
    df: pd.DataFrame,
    period: ShareSummaryPeriod,
    *,
    taxonomy_locale: str | None = None,
) -> ShareSummaryStats | None:
    """Compute headline share stats for *period* from a sighting-level export frame."""
    if df.empty or "Date" not in df.columns:
        return None

    cl = df.drop_duplicates(subset=["Submission ID"]).copy()
    cl["Date"] = pd.to_datetime(cl["Date"], errors="coerce")
    cl = cl.dropna(subset=["Date"])
    if cl.empty:
        return None

    in_period_cl = cl[_mask_in_period(cl["Date"], period)]
    if in_period_cl.empty:
        return ShareSummaryStats(
            period_label=period.label,
            period_kind=period.kind,
            trip_title=period.trip_title,
        )

    df_all = df.copy()
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
    in_period_df = df_all[_mask_in_period(df_all["Date"], period)]

    sp = countable_species_vectorized(in_period_df)
    in_period_df = in_period_df.assign(_base=sp, _count=in_period_df["Count"].apply(safe_count))

    species = int(in_period_df["_base"].dropna().nunique()) if not in_period_df.empty else 0
    individuals = int(in_period_df["_count"].sum()) if not in_period_df.empty else 0
    checklists = int(len(in_period_cl))
    locations = int(in_period_cl["Location ID"].nunique()) if "Location ID" in in_period_cl.columns else None

    # Lifers: first checklist date for each species in the full dataset falls in period.
    lifers = None
    base_all = countable_species_vectorized(df_all.dropna(subset=["Date"]))
    lifer_df = df_all.dropna(subset=["Date"]).assign(_base=base_all).dropna(subset=["_base"])
    if not lifer_df.empty:
        first_seen = lifer_df.groupby("_base")["Date"].min()
        first_in_period = first_seen[_mask_in_period(first_seen, period)]
        lifers = int(len(first_in_period))

    families = None
    loc = (taxonomy_locale or "").strip() or TAXONOMY_LOCALE_DEFAULT
    base_to_family = build_base_species_to_family_map(loc)
    if base_to_family and not in_period_df.empty:
        fam_df = in_period_df.dropna(subset=["_base"]).copy()
        fam_df["_family"] = fam_df["_base"].astype(str).str.strip().map(base_to_family)
        families = int(fam_df.dropna(subset=["_family"])["_family"].nunique())

    birding_hours = None
    dur_col = "Duration (Min)" if "Duration (Min)" in cl.columns else None
    if dur_col:
        timed = in_period_cl.dropna(subset=[dur_col]).copy()
        if "Protocol" in timed.columns:
            proto = timed["Protocol"].astype(str).str.strip().str.lower()
            excl = proto.str.contains("incidental|historical|casual observation", na=False, regex=True)
            timed = timed[~excl]
        if not timed.empty:
            mins = pd.to_numeric(timed[dur_col], errors="coerce").fillna(0).sum()
            birding_hours = float(mins) / 60.0

    days = int(in_period_cl["Date"].dt.normalize().nunique())

    longest_streak_days = None
    if period.kind in ("year", "month"):
        unique_dates = in_period_cl["Date"].dt.normalize().unique()
        streak_val, *_ = longest_streak(unique_dates, in_period_cl)
        longest_streak_days = int(streak_val)

    countries = _countries_in_period(in_period_cl)

    return ShareSummaryStats(
        period_label=period.label,
        period_kind=period.kind,
        trip_title=period.trip_title,
        species=species,
        lifers=lifers,
        checklists=checklists,
        locations=locations,
        families=families,
        individuals=individuals,
        days_with_checklist=days,
        birding_hours=birding_hours,
        longest_streak=longest_streak_days,
        countries=countries,
    )
