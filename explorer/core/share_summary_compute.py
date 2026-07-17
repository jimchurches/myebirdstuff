"""
Period-scoped stats for share-summary graphics (#157).

Computes the same headline metrics as yearly summary rows, but for an arbitrary
inclusive date window (year, month, ISO week, or custom trip range).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

import pandas as pd

from explorer.core.region_display import map_focus_key_for_display, state_for_display
from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.species_family import build_base_species_to_family_map
from explorer.core.species_logic import countable_species_vectorized
from explorer.core.stats import (
    checklist_country_keys,
    format_region_parts,
    incidental_checklist_mask,
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

    @property
    def is_country_only(self) -> bool:
        """True when scoped to a whole country (no state/province subdivision)."""
        return not self.is_world and not (self.region_code or "").strip()


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
    """Return sighting rows whose checklists fall in *scope*.

    Always returns a new frame — callers store the result in session caches, and
    aliasing the canonical export there would break the static-dataframe invariant.
    """
    if df.empty or scope.is_world:
        return df.copy()
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


def dataset_date_bounds(df: pd.DataFrame) -> tuple[date, date] | None:
    """Inclusive min/max checklist dates in *df*, or ``None`` when no usable dates."""
    if df.empty or "Date" not in df.columns:
        return None
    dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


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
    incidental_checklists: int | None = None
    locations: int | None = None
    lifers: int | None = None
    region_lifers: int | None = None
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


def geo_region_lifer_stat_label(scope: ShareSummaryGeoScope) -> str:
    """Display label for geo-scoped lifers, e.g. ``Australia Lifers`` or ``New South Wales Lifers``."""
    if scope.is_world:
        return ""
    rc = (scope.region_code or "").strip()
    if rc:
        cc = scope.country_key or ""
        cc_norm = cc[3:] if str(cc).startswith("_R:") else cc
        place = state_for_display(cc_norm, rc) or rc
    else:
        place = map_focus_key_for_display(scope.country_key or "")
    return f"{place} Lifers"


def _region_lifers_in_period(df: pd.DataFrame, period: ShareSummaryPeriod) -> int:
    """Species whose first sighting in *df* (geo-scoped export) falls in *period*."""
    frame = df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    base = countable_species_vectorized(frame.dropna(subset=["Date"]))
    obs = frame.dropna(subset=["Date"]).assign(_base=base).dropna(subset=["_base"])
    if obs.empty:
        return 0
    first_seen = obs.groupby("_base")["Date"].min()
    first_in_period = first_seen[_mask_in_period(first_seen, period)]
    return int(len(first_in_period))


def _lifers_in_period(
    df: pd.DataFrame,
    in_period_df: pd.DataFrame,
    period: ShareSummaryPeriod,
    *,
    lifer_reference_df: pd.DataFrame | None = None,
) -> int | None:
    """Count lifers whose global first sighting falls in *period*.

    When *lifer_reference_df* is set (geo-scoped stats), first-seen dates come from
    the full export while *in_period_df* restricts which species count (seen in scope
    during the period). Without it, first-seen uses *df* only (legacy / world scope).
    """
    if period.kind == "lifetime":
        return None
    ref = lifer_reference_df if lifer_reference_df is not None else df
    ref = ref.copy()
    ref["Date"] = pd.to_datetime(ref["Date"], errors="coerce")
    base_all = countable_species_vectorized(ref.dropna(subset=["Date"]))
    lifer_df = ref.dropna(subset=["Date"]).assign(_base=base_all).dropna(subset=["_base"])
    if lifer_df.empty:
        return 0
    first_seen = lifer_df.groupby("_base")["Date"].min()
    first_in_period = first_seen[_mask_in_period(first_seen, period)]
    if lifer_reference_df is not None:
        period_bases = in_period_df["_base"].dropna().unique()
        first_in_period = first_in_period[first_in_period.index.isin(period_bases)]
    return int(len(first_in_period))


def compute_share_summary_stats(
    df: pd.DataFrame,
    period: ShareSummaryPeriod,
    *,
    taxonomy_locale: str | None = None,
    lifer_reference_df: pd.DataFrame | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> ShareSummaryStats | None:
    """Compute headline share stats for *period* from a sighting-level export frame.

    Pass the unfiltered export as *lifer_reference_df* when *df* is geo-filtered so
    lifers use global first-seen dates but only count species seen in scope during
    the period. Pass *geo_scope* when *df* is geo-filtered to compute regional lifers
    (first sighting within the scope).
    """
    if df.empty or "Date" not in df.columns:
        return None

    cl = df.drop_duplicates(subset=["Submission ID"]).copy()
    cl["Date"] = pd.to_datetime(cl["Date"], errors="coerce")
    cl = cl.dropna(subset=["Date"])
    if cl.empty:
        return None

    in_period_cl = cl[_mask_in_period(cl["Date"], period)]
    geo_constrained = geo_scope is not None and not geo_scope.is_world
    if in_period_cl.empty:
        region_lifers = _region_lifers_in_period(df, period) if geo_constrained else None
        if period.kind == "lifetime":
            region_lifers = None
        # checklists=0 (not None) so the preview renders the dedicated
        # "No checklists in this period" card for genuinely empty periods.
        return ShareSummaryStats(
            period_label=period.label,
            period_kind=period.kind,
            trip_title=period.trip_title,
            checklists=0,
            region_lifers=region_lifers if geo_constrained else None,
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
    incidental_checklists = None
    incidental_mask = incidental_checklist_mask(in_period_cl)
    if incidental_mask is not None:
        incidental_checklists = int(incidental_mask.sum())
    locations = int(in_period_cl["Location ID"].nunique()) if "Location ID" in in_period_cl.columns else None

    # Lifers: global first checklist date per species; geo scope keeps period species only.
    lifers = _lifers_in_period(
        df_all,
        in_period_df,
        period,
        lifer_reference_df=lifer_reference_df,
    )

    region_lifers = None
    if geo_constrained and period.kind != "lifetime":
        region_lifers = _region_lifers_in_period(df_all, period)

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
        region_lifers=region_lifers,
        checklists=checklists,
        completed_checklists=completed_checklists,
        incidental_checklists=incidental_checklists,
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


# Rankings + Bird Families prep bundle keys (``attach_group_coverage_to_bundle``).
GROUP_COVERAGE_SUMMARY_KEY = "group_coverage_summary"
WORLD_SPECIES_COVERAGE_METRICS_KEY = "world_species_coverage_metrics"

WorldTaxonomyBundleStatus = Literal["ready", "pending", "unavailable"]


def all_time_stats_from_rankings_bundle(
    bundle: dict[str, Any] | None,
) -> ShareSummaryAllTimeStats | None:
    """Build taxonomy denominators from the rankings/families prep bundle (no re-merge)."""
    if not bundle:
        return None

    observed: int | None = None
    total_sp: int | None = None
    pct: float | None = None
    world = bundle.get(WORLD_SPECIES_COVERAGE_METRICS_KEY)
    if isinstance(world, tuple) and len(world) == 3:
        observed, total_sp, pct = world

    total_families: int | None = None
    observed_families: int | None = None
    summary = bundle.get(GROUP_COVERAGE_SUMMARY_KEY)
    if isinstance(summary, pd.DataFrame) and not summary.empty:
        total_families = int(summary["group_name"].nunique())
        if "seen_species" in summary.columns:
            seen = pd.to_numeric(summary["seen_species"], errors="coerce").fillna(0)
            observed_families = int((seen > 0).sum())

    if all(
        value is None
        for value in (
            observed,
            total_sp,
            pct,
            total_families,
            observed_families,
        )
    ):
        return None

    return ShareSummaryAllTimeStats(
        total_species_taxa=total_sp,
        total_families_taxa=total_families,
        observed_species_taxa=observed,
        observed_families=observed_families,
        world_bird_coverage_pct=pct,
    )


def world_taxonomy_bundle_status(
    bundle: dict[str, Any] | None,
) -> WorldTaxonomyBundleStatus:
    """Whether world-scope taxonomy reference rows can be read from the prep bundle."""
    if bundle is None:
        return "pending"
    if all_time_stats_from_rankings_bundle(bundle) is not None:
        return "ready"
    return "unavailable"


def resolve_social_cards_stats(
    *,
    df_full: pd.DataFrame,
    df_scoped: pd.DataFrame,
    period: ShareSummaryPeriod,
    geo_scope: ShareSummaryGeoScope,
    rankings_bundle: dict[str, Any] | None,
) -> tuple[ShareSummaryStats | None, ShareSummaryAllTimeStats | None]:
    """Period stats from scoped export; all-time taxonomy rows from the shared prep bundle."""
    lifer_ref = df_full if not geo_scope.is_world else None
    stats = compute_share_summary_stats(
        df_scoped,
        period,
        lifer_reference_df=lifer_ref,
        geo_scope=geo_scope,
    )
    all_time = (
        all_time_stats_from_rankings_bundle(rankings_bundle)
        if geo_scope.is_world
        else None
    )
    return stats, all_time
