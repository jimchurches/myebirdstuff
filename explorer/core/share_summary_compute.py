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

from explorer.core.region_display import map_focus_key_for_display, state_for_display
from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.species_family import build_base_species_to_family_map
from explorer.core.species_logic import countable_species_vectorized
from explorer.core.stats import (
    checklist_country_keys,
    format_region_parts,
    longest_streak,
    safe_count,
    shared_checklist_stats,
    sum_timed_birding_minutes,
    timed_checklists_excl_incidental,
)

PeriodAnchor = Literal["current", "previous"]
PeriodKind = Literal["year", "month", "week", "custom", "lifetime"]

LIFETIME_PERIOD_LABEL = "Lifetime"


def _completed_checklist_mask(cl: pd.DataFrame) -> pd.Series | None:
    """True for checklists with all observations reported (matches main app stats)."""
    if "All Obs Reported" not in cl.columns:
        return None
    a = cl["All Obs Reported"]
    return a.notna() & (
        (pd.to_numeric(a, errors="coerce") == 1)
        | (a.astype(str).str.strip().str.upper().isin(["TRUE", "YES", "Y"]))
    )


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


@dataclass(frozen=True)
class ShareSummaryGeoScope:
    """Geographic filter for share-summary stats.

    *country_key* ``None`` means **World** (no geographic filter).
    *region_code* is the state/province subdivision code within *country_key*
    (e.g. ``NSW`` for ``AU-NSW``); ``None`` means all regions in that country.
    """

    country_key: str | None = None
    region_code: str | None = None

    @property
    def is_world(self) -> bool:
        return not (self.country_key or "").strip()

    def scope_token(self) -> str:
        """Stable token for session keys (world, country, or country+region)."""
        if self.is_world:
            return "world"
        ck = str(self.country_key).strip()
        rc = (self.region_code or "").strip()
        return f"{ck}|{rc}" if rc else ck


def _checklist_region_code(country_key: str, state_province: object) -> str | None:
    """State/province code for one checklist row, aligned with *country_key*."""
    ck = str(country_key or "").strip()
    if not ck or ck == "_UNKNOWN":
        return None
    if state_province is None or (isinstance(state_province, float) and pd.isna(state_province)):
        return None
    cc, st = format_region_parts(state_province)
    st_s = str(st).strip() if st else ""
    if ck.startswith("_R:"):
        tail = ck[3:].strip()
        if not st_s:
            return tail or None
        return st_s
    if cc and str(cc).strip().upper() == ck.upper():
        return st_s or None
    if not cc and st_s:
        return st_s
    return None


def _checklist_geo_frame(cl: pd.DataFrame) -> pd.DataFrame:
    """Per-checklist country key and optional region code (one row per Submission ID)."""
    if cl.empty or "Submission ID" not in cl.columns:
        return pd.DataFrame(columns=["Submission ID", "_country_key", "_region_code"])
    frame = cl.drop_duplicates(subset=["Submission ID"]).copy()
    frame["_country_key"] = checklist_country_keys(frame)
    sp_col = "State/Province" if "State/Province" in frame.columns else None
    if sp_col:
        frame["_region_code"] = [
            _checklist_region_code(ck, sp)
            for ck, sp in zip(frame["_country_key"], frame[sp_col], strict=True)
        ]
    else:
        frame["_region_code"] = None
    return frame[["Submission ID", "_country_key", "_region_code"]]


def geo_country_keys_from_df(df: pd.DataFrame) -> list[str]:
    """Distinct country keys in *df*, sorted by display name (excludes ``_UNKNOWN``)."""
    if df.empty:
        return []
    geo = _checklist_geo_frame(df.drop_duplicates(subset=["Submission ID"]))
    keys = {str(k) for k in geo["_country_key"].dropna().unique() if k and str(k) != "_UNKNOWN"}
    return sorted(keys, key=lambda k: map_focus_key_for_display(k).lower())


def geo_region_options_for_country(
    df: pd.DataFrame,
    country_key: str,
) -> list[tuple[str, str]]:
    """``(region_code, display_label)`` pairs for *country_key*, sorted by label."""
    ck = str(country_key or "").strip()
    if not ck or df.empty:
        return []
    geo = _checklist_geo_frame(df.drop_duplicates(subset=["Submission ID"]))
    sub = geo[geo["_country_key"] == ck]
    codes = {str(c).strip() for c in sub["_region_code"].dropna() if str(c).strip()}
    cc = ck[3:] if ck.startswith("_R:") else ck
    pairs = [
        (code, state_for_display(cc, code) or code)
        for code in codes
    ]
    return sorted(pairs, key=lambda p: p[1].lower())


def filter_df_by_geo_scope(df: pd.DataFrame, scope: ShareSummaryGeoScope) -> pd.DataFrame:
    """Return sighting rows whose checklists fall in *scope*."""
    if df.empty or scope.is_world:
        return df
    if "Submission ID" not in df.columns:
        return df.iloc[0:0].copy()
    ck = str(scope.country_key or "").strip()
    geo = _checklist_geo_frame(df)
    mask = geo["_country_key"] == ck
    rc = (scope.region_code or "").strip()
    if rc:
        mask = mask & (geo["_region_code"].astype(str).str.strip() == rc)
    sids = set(geo.loc[mask, "Submission ID"])
    return df[df["Submission ID"].isin(sids)].copy()


def geo_scope_display_label(scope: ShareSummaryGeoScope) -> str:
    """Human-readable scope for card footer debug text."""
    if scope.is_world:
        return "World"
    country = map_focus_key_for_display(scope.country_key or "")
    rc = (scope.region_code or "").strip()
    if not rc:
        return country
    cc = scope.country_key or ""
    cc_norm = cc[3:] if str(cc).startswith("_R:") else cc
    region = state_for_display(cc_norm, rc) or rc
    return f"{country} · {region}"


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


def period_for_previous_month(year: int, month: int) -> ShareSummaryPeriod:
    """Calendar month immediately before *year*/*month*."""
    if int(month) == 1:
        return period_for_month(int(year) - 1, 12)
    return period_for_month(int(year), int(month) - 1)


def period_for_previous_week_containing(day: date) -> ShareSummaryPeriod:
    """Sun–Sat week immediately before the week containing *day*."""
    start, _ = _week_sun_sat_containing(day)
    return period_for_week_containing(start - timedelta(days=1))


def resolve_period(
    kind: Literal["year", "month", "week"],
    *,
    anchor: PeriodAnchor,
    reference: date,
) -> ShareSummaryPeriod:
    """Resolve year/month/week period from *reference* date and current/previous anchor."""
    if kind == "year":
        y = reference.year if anchor == "current" else reference.year - 1
        return period_for_year(y)
    if kind == "month":
        if anchor == "current":
            return period_for_month(reference.year, reference.month)
        return period_for_previous_month(reference.year, reference.month)
    # week
    if anchor == "current":
        return period_for_week_containing(reference)
    return period_for_previous_week_containing(reference)


def suggest_period_anchor(kind: Literal["year", "month", "week"], reference: date) -> PeriodAnchor:
    """Heuristic default for current vs previous (social-posting context).

    Examples: early in a new month → previous month; weekend → current week.
    """
    if kind == "month":
        return "previous" if reference.day <= 7 else "current"
    if kind == "year":
        if reference.month == 1 and reference.day <= 14:
            return "previous"
        return "current"
    if kind == "week":
        if reference.weekday() >= 5:  # Saturday or Sunday
            return "current"
        if reference.weekday() <= 1:  # Monday or Tuesday
            return "previous"
        return "current"
    return "current"


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


def period_for_lifetime(start: date, end: date) -> ShareSummaryPeriod:
    """Full export span — inclusive dates from first to last checklist in the CSV."""
    if end < start:
        start, end = end, start
    return ShareSummaryPeriod(
        kind="lifetime",
        start=start,
        end=end,
        label=LIFETIME_PERIOD_LABEL,
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
    completed_checklists: int | None = None
    locations: int | None = None
    lifers: int | None = None
    birding_hours: float | None = None
    distance_km: float | None = None
    days_with_checklist: int | None = None
    longest_streak: int | None = None
    countries: int | None = None
    shared_checklists: int | None = None
    days_birding_with_others: int | None = None


@dataclass(frozen=True)
class ShareSummaryAllTimeStats:
    """eBird/Clements taxonomy denominators for share-summary coverage stats.

    ``total_species_taxa`` and ``total_families_taxa`` are exposed on cards.
    ``observed_species_taxa``, ``observed_families``, and ``world_bird_coverage_pct``
    are all-time coverage values from the Bird Families pipeline (internal / tests).
    Card ``Observed species (%)`` uses period ``ShareSummaryStats.species`` instead.
    """

    total_species_taxa: int | None = None
    total_families_taxa: int | None = None
    observed_species_taxa: int | None = None
    observed_families: int | None = None
    world_bird_coverage_pct: float | None = None


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


def period_species_common_names(df: pd.DataFrame, period: ShareSummaryPeriod) -> list[str]:
    """Distinct common names from sightings in *period* (picker scope for favourite birds)."""
    if df.empty or "Date" not in df.columns or "Common Name" not in df.columns:
        return []
    frame = df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    in_period = frame[_mask_in_period(frame["Date"], period)]
    if in_period.empty:
        return []
    names = in_period["Common Name"].dropna().astype(str).str.strip()
    return sorted({n for n in names if n})


def period_species_name_map(df: pd.DataFrame, period: ShareSummaryPeriod) -> dict[str, str]:
    """First scientific name per common name in *period* (Whoosh index for species search)."""
    if df.empty or "Date" not in df.columns or "Common Name" not in df.columns:
        return {}
    frame = df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    in_period = frame[_mask_in_period(frame["Date"], period)]
    if in_period.empty:
        return {}
    sci_col = "Scientific Name" if "Scientific Name" in in_period.columns else None
    out: dict[str, str] = {}
    for common in period_species_common_names(df, period):
        rows = in_period[in_period["Common Name"].astype(str).str.strip() == common]
        if rows.empty:
            continue
        sci = ""
        if sci_col:
            sci_vals = rows[sci_col].dropna().astype(str).str.strip()
            sci = next((s for s in sci_vals if s), "")
        out[common] = sci
    return out


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
    completed_checklists = None
    completed_mask = _completed_checklist_mask(in_period_cl)
    if completed_mask is not None:
        completed_checklists = int(completed_mask.sum())
    locations = int(in_period_cl["Location ID"].nunique()) if "Location ID" in in_period_cl.columns else None

    # Lifers: first checklist date for each species in the full dataset falls in period.
    lifers = None
    if period.kind != "lifetime":
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
    dur_col = "Duration (Min)" if "Duration (Min)" in in_period_cl.columns else None
    if dur_col:
        timed = timed_checklists_excl_incidental(in_period_cl, dur_col)
        if not timed.empty:
            birding_hours = sum_timed_birding_minutes(in_period_cl, dur_col) / 60.0

    distance_km = None
    if period.kind in ("year", "lifetime"):
        dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in in_period_cl.columns else None
        if dist_col:
            distance_km = float(
                pd.to_numeric(in_period_cl[dist_col], errors="coerce").fillna(0).sum()
            )

    days = int(in_period_cl["Date"].dt.normalize().nunique())

    longest_streak_days = None
    if period.kind in ("year", "month", "lifetime"):
        unique_dates = in_period_cl["Date"].dt.normalize().unique()
        streak_val, *_ = longest_streak(unique_dates, in_period_cl)
        longest_streak_days = int(streak_val)

    countries = _countries_in_period(in_period_cl)
    shared_checklists, days_birding_with_others = shared_checklist_stats(
        in_period_cl, absent_column="none"
    )

    return ShareSummaryStats(
        period_label=period.label,
        period_kind=period.kind,
        trip_title=period.trip_title,
        species=species,
        lifers=lifers,
        checklists=checklists,
        completed_checklists=completed_checklists,
        locations=locations,
        families=families,
        individuals=individuals,
        days_with_checklist=days,
        birding_hours=birding_hours,
        distance_km=distance_km,
        longest_streak=longest_streak_days,
        countries=countries,
        shared_checklists=shared_checklists,
        days_birding_with_others=days_birding_with_others,
    )


def compute_share_summary_all_time_stats(
    df: pd.DataFrame,
    *,
    taxonomy_locale: str | None = None,
) -> ShareSummaryAllTimeStats | None:
    """All-time taxonomy metrics via Bird Families coverage tables."""
    if df.empty:
        return None
    loc = (taxonomy_locale or "").strip() or TAXONOMY_LOCALE_DEFAULT
    try:
        from explorer.app.streamlit.bird_families_streamlit_html import (
            build_group_coverage_tables,
            compute_world_species_coverage,
        )
    except ImportError:
        return None

    try:
        summary, detail = build_group_coverage_tables(df, loc)
    except Exception:
        return None
    if detail.empty:
        return None

    observed, total_sp, pct = compute_world_species_coverage(detail)
    total_families = int(summary["group_name"].nunique()) if not summary.empty else None
    observed_families = None
    if not summary.empty and "seen_species" in summary.columns:
        seen = pd.to_numeric(summary["seen_species"], errors="coerce").fillna(0)
        observed_families = int((seen > 0).sum())
    return ShareSummaryAllTimeStats(
        total_species_taxa=total_sp,
        total_families_taxa=total_families,
        observed_species_taxa=observed,
        observed_families=observed_families,
        world_bird_coverage_pct=pct,
    )
