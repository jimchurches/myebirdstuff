"""
Interesting Insights card facts for share-summary cards (#285, #334).

Framework-neutral compute: species- and checklist-derived highlights beyond simple
stat + number pairs, plus period-gated peak calendar facts (best year / month / day).
Presentation reads :class:`ShareSummaryInsightFact` via
``explorer.presentation.share_summary_preview``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd

from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryPeriod,
    _completed_checklist_mask,
    _fmt_short_date,
    _mask_in_period,
)
from explorer.core.species_logic import (
    countable_species_vectorized,
    most_frequent_parent_common,
    parent_common_name,
)
from explorer.core.stats import (
    rankings_by_checklists,
    rankings_by_individuals,
    rankings_high_counts,
    safe_count,
)

InsightFactId = Literal[
    "most_common_checklist_species",
    "most_individuals_species",
    "biggest_checklist_count",
    "species_individuals",
    "year_most_checklists",
    "year_most_completed_checklists",
    "year_most_species",
    "year_most_individuals",
    "month_most_checklists",
    "month_most_completed_checklists",
    "month_most_species",
    "month_most_individuals",
    "day_most_checklists",
    "day_most_completed_checklists",
    "day_most_species",
    "day_most_individuals",
]

# Peak card headings — also used as Insights picker labels (keep in sync by sharing).
INSIGHT_FACT_CARD_LABELS: dict[InsightFactId, str] = {
    "year_most_checklists": "Most checklists in a year",
    "year_most_completed_checklists": "Most completed checklists in a year",
    "year_most_species": "Most species in a year",
    "year_most_individuals": "Most individual birds in a year",
    "month_most_checklists": "Most checklists in a month",
    "month_most_completed_checklists": "Most completed checklists in a month",
    "month_most_species": "Most species in a month",
    "month_most_individuals": "Most individual birds in a month",
    "day_most_checklists": "Most checklists in a day",
    "day_most_completed_checklists": "Most completed checklists in a day",
    "day_most_species": "Most species in a day",
    "day_most_individuals": "Most individual birds in a day",
}

INSIGHT_FACT_PICKER_LABELS: dict[InsightFactId, str] = {
    "most_common_checklist_species": "Species seen on the most checklists",
    "most_individuals_species": "Most-recorded species",
    "biggest_checklist_count": "Biggest single-checklist count",
    "species_individuals": "Individuals of selected species",
    **INSIGHT_FACT_CARD_LABELS,
}

INSIGHT_FACTS_REQUIRING_SPECIES: frozenset[InsightFactId] = frozenset(
    {"species_individuals"}
)
# Card heading when the species name is the hero line (picker label stays descriptive).
INSIGHT_SPECIES_INDIVIDUALS_CARD_LABEL = "Species count"

# Existing auto facts first; species_individuals stays with them; peaks follow (#334).
INSIGHT_LEGACY_AUTO_FACT_IDS: tuple[InsightFactId, ...] = (
    "most_common_checklist_species",
    "most_individuals_species",
    "biggest_checklist_count",
)
INSIGHT_PEAK_FACT_IDS: tuple[InsightFactId, ...] = (
    "year_most_checklists",
    "year_most_completed_checklists",
    "year_most_species",
    "year_most_individuals",
    "month_most_checklists",
    "month_most_completed_checklists",
    "month_most_species",
    "month_most_individuals",
    "day_most_checklists",
    "day_most_completed_checklists",
    "day_most_species",
    "day_most_individuals",
)

_YEAR_PEAK_FACT_IDS: frozenset[InsightFactId] = frozenset(
    {
        "year_most_checklists",
        "year_most_completed_checklists",
        "year_most_species",
        "year_most_individuals",
    }
)
_MONTH_PEAK_FACT_IDS: frozenset[InsightFactId] = frozenset(
    {
        "month_most_checklists",
        "month_most_completed_checklists",
        "month_most_species",
        "month_most_individuals",
    }
)
_DAY_PEAK_FACT_IDS: frozenset[InsightFactId] = frozenset(
    {
        "day_most_checklists",
        "day_most_completed_checklists",
        "day_most_species",
        "day_most_individuals",
    }
)

# Lifetime → year + day; Yearly → month + day; Monthly → day; Week/Custom → none.
_PEAK_FACT_IDS_BY_PERIOD_KIND: dict[PeriodKind, frozenset[InsightFactId]] = {
    "lifetime": _YEAR_PEAK_FACT_IDS | _DAY_PEAK_FACT_IDS,
    "year": _MONTH_PEAK_FACT_IDS | _DAY_PEAK_FACT_IDS,
    "month": _DAY_PEAK_FACT_IDS,
    "week": frozenset(),
    "custom": frozenset(),
}


@dataclass(frozen=True)
class ShareSummaryInsightFact:
    """One Interesting Insights highlight for a period."""

    fact_id: InsightFactId
    label: str
    primary_text: str
    metric_value: int | None = None
    metric_unit: str | None = None
    peak_tied: bool = False
    # Total calendar units sharing the peak (including the shown earliest). Soft note uses N-1.
    peak_tie_count: int = 0


def format_insight_fact_metric(fact: ShareSummaryInsightFact) -> str | None:
    """Format the optional metric line, e.g. ``3,999 checklists``."""
    if fact.metric_value is None:
        return None
    formatted = f"{fact.metric_value:,}"
    if fact.metric_unit:
        return f"{formatted} {fact.metric_unit}"
    return formatted


def format_insight_peak_tie_note(fact: ShareSummaryInsightFact) -> str | None:
    """Soft note when a peak unit ties, e.g. ``Tied with 2 other days``."""
    if not fact.peak_tied or fact.peak_tie_count < 2:
        return None
    if fact.fact_id not in INSIGHT_PEAK_FACT_IDS:
        return None
    others = fact.peak_tie_count - 1
    unit = _peak_unit_for_fact(fact.fact_id)
    if unit == "year":
        noun = "year" if others == 1 else "years"
    elif unit == "month":
        noun = "month" if others == 1 else "months"
    else:
        noun = "day" if others == 1 else "days"
    return f"Tied with {others} other {noun}"


def insight_fact_requires_species(fact_id: InsightFactId) -> bool:
    """Return whether the picker must show a species selectbox."""
    return fact_id in INSIGHT_FACTS_REQUIRING_SPECIES


def peak_fact_ids_for_period_kind(period_kind: PeriodKind) -> frozenset[InsightFactId]:
    """Peak fact ids allowed for *period_kind* (empty for week/custom)."""
    return _PEAK_FACT_IDS_BY_PERIOD_KIND.get(period_kind, frozenset())


def species_common_names_in_period(
    df: pd.DataFrame, period: ShareSummaryPeriod
) -> tuple[str, ...]:
    """Distinct parent-species common names with observations in *period*, sorted.

    Subspecies rows roll up to the parent name (same rule as Bird Families tab).
    """
    obs = _observations_in_period(df, period)
    if obs.empty or "Common Name" not in obs.columns:
        return ()
    frame = obs.copy()
    frame["_base"] = countable_species_vectorized(frame)
    countable = frame.dropna(subset=["_base"])
    if countable.empty:
        return ()
    countable = countable.copy()
    countable["_parent_common"] = countable["Common Name"].map(parent_common_name)
    names = (
        countable.groupby("_base", sort=False)["_parent_common"]
        .agg(most_frequent_parent_common)
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .unique()
        .tolist()
    )
    return tuple(sorted(names, key=str.lower))


def compute_insight_facts(
    df: pd.DataFrame,
    period: ShareSummaryPeriod,
    *,
    species_common: str | None = None,
) -> list[ShareSummaryInsightFact]:
    """Compute auto insight facts for *period*; optional species fact when *species_common* set."""
    obs = _observations_in_period(df, period)
    facts: list[ShareSummaryInsightFact] = []

    checklist_rows = rankings_by_checklists(obs, limit=1)
    if checklist_rows:
        name, _, count_str = checklist_rows[0]
        count = _parse_int(count_str)
        facts.append(
            ShareSummaryInsightFact(
                fact_id="most_common_checklist_species",
                label=INSIGHT_FACT_PICKER_LABELS["most_common_checklist_species"],
                primary_text=name,
                metric_value=count,
                metric_unit="checklists",
            )
        )

    individual_rows = rankings_by_individuals(obs, limit=1)
    if individual_rows:
        name, _, count_str = individual_rows[0]
        count = _parse_int(count_str)
        facts.append(
            ShareSummaryInsightFact(
                fact_id="most_individuals_species",
                label=INSIGHT_FACT_PICKER_LABELS["most_individuals_species"],
                primary_text=name,
                metric_value=count,
                metric_unit="individuals",
            )
        )

    high_count_rows = rankings_high_counts(obs)
    if high_count_rows:
        name, *_rest, count_str = high_count_rows[0]
        count = _parse_int(count_str)
        facts.append(
            ShareSummaryInsightFact(
                fact_id="biggest_checklist_count",
                label=INSIGHT_FACT_PICKER_LABELS["biggest_checklist_count"],
                primary_text=name,
                metric_value=count,
                metric_unit="on one checklist",
            )
        )

    cleaned_species = (species_common or "").strip()
    if cleaned_species:
        species_fact = _species_individuals_fact(obs, cleaned_species)
        if species_fact is not None:
            facts.append(species_fact)

    facts.extend(_compute_peak_facts(obs, period))
    return facts


def insight_fact_by_id(
    facts: list[ShareSummaryInsightFact],
    fact_id: InsightFactId,
) -> ShareSummaryInsightFact | None:
    """Return the first fact matching *fact_id*, or None."""
    for fact in facts:
        if fact.fact_id == fact_id:
            return fact
    return None


def species_individuals_insight_fact(
    df: pd.DataFrame,
    period: ShareSummaryPeriod,
    species_common: str,
) -> ShareSummaryInsightFact | None:
    """Individuals total for one species in *period* — avoids recomputing all auto facts."""
    cleaned = (species_common or "").strip()
    if not cleaned:
        return None
    return _species_individuals_fact(_observations_in_period(df, period), cleaned)


def _observations_in_period(
    df: pd.DataFrame, period: ShareSummaryPeriod
) -> pd.DataFrame:
    if df.empty or "Date" not in df.columns:
        return df.iloc[0:0].copy()
    frame = df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    return frame.dropna(subset=["Date"]).loc[_mask_in_period(frame["Date"], period)]


def _parse_int(text: str) -> int | None:
    cleaned = str(text).replace(",", "").strip()
    if not cleaned or cleaned == "—":
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _species_individuals_fact(
    obs: pd.DataFrame, species_common: str
) -> ShareSummaryInsightFact | None:
    if obs.empty:
        return None
    target = parent_common_name(species_common).casefold()
    if not target:
        return None
    frame = obs.copy()
    frame["_base"] = countable_species_vectorized(frame)
    frame = frame.dropna(subset=["_base"])
    if frame.empty or "Common Name" not in frame.columns:
        return None
    frame["_parent_common"] = (
        frame["Common Name"].map(parent_common_name).str.casefold()
    )
    matched = frame[frame["_parent_common"] == target]
    if matched.empty:
        return None
    canonical_common = (
        matched["Common Name"].dropna().astype(str).str.strip().value_counts().index[0]
    )
    display_name = parent_common_name(canonical_common)
    total = int(matched["Count"].apply(safe_count).sum())
    return ShareSummaryInsightFact(
        fact_id="species_individuals",
        label=INSIGHT_SPECIES_INDIVIDUALS_CARD_LABEL,
        primary_text=str(display_name),
        metric_value=total,
        metric_unit="individuals",
    )


def _compute_peak_facts(
    obs: pd.DataFrame, period: ShareSummaryPeriod
) -> list[ShareSummaryInsightFact]:
    """Period-gated peak year/month/day facts (#334)."""
    allowed = peak_fact_ids_for_period_kind(period.kind)
    if not allowed or obs.empty:
        return []

    checklists = _checklists_frame(obs)
    species_by_unit = _prepare_species_obs(obs)

    facts: list[ShareSummaryInsightFact] = []
    for fact_id in INSIGHT_PEAK_FACT_IDS:
        if fact_id not in allowed:
            continue
        fact = _build_peak_fact(
            fact_id,
            checklists=checklists,
            species_obs=species_by_unit,
        )
        if fact is not None:
            facts.append(fact)
    return facts


def _checklists_frame(obs: pd.DataFrame) -> pd.DataFrame:
    if obs.empty or "Submission ID" not in obs.columns:
        return obs.iloc[0:0].copy()
    return obs.drop_duplicates(subset=["Submission ID"]).copy()


def _prepare_species_obs(obs: pd.DataFrame) -> pd.DataFrame:
    if obs.empty:
        return obs.iloc[0:0].copy()
    frame = obs.copy()
    frame["_base"] = countable_species_vectorized(frame)
    frame["_count"] = (
        frame["Count"].apply(safe_count) if "Count" in frame.columns else 0
    )
    return frame


def _build_peak_fact(
    fact_id: InsightFactId,
    *,
    checklists: pd.DataFrame,
    species_obs: pd.DataFrame,
) -> ShareSummaryInsightFact | None:
    unit = _peak_unit_for_fact(fact_id)
    fmt = _primary_formatter(unit)
    if fact_id.endswith("_completed_checklists"):
        return _peak_from_series(
            fact_id,
            _checklist_counts_by_unit(checklists, unit, completed_only=True),
            metric_unit="checklists",
            format_key=fmt,
        )
    if fact_id.endswith("_checklists"):
        return _peak_from_series(
            fact_id,
            _checklist_counts_by_unit(checklists, unit, completed_only=False),
            metric_unit="checklists",
            format_key=fmt,
        )
    if fact_id.endswith("_individuals"):
        return _peak_from_series(
            fact_id,
            _individual_counts_by_unit(species_obs, unit),
            metric_unit="individual birds",
            format_key=fmt,
        )
    if fact_id.endswith("_species"):
        return _peak_from_series(
            fact_id,
            _species_counts_by_unit(species_obs, unit),
            metric_unit="species",
            format_key=fmt,
        )
    return None


def _peak_unit_for_fact(fact_id: InsightFactId) -> Literal["year", "month", "day"]:
    if fact_id in _YEAR_PEAK_FACT_IDS:
        return "year"
    if fact_id in _MONTH_PEAK_FACT_IDS:
        return "month"
    return "day"


def _primary_formatter(
    unit: Literal["year", "month", "day"],
) -> Callable[[object], str]:
    if unit == "year":

        def _fmt_year(key: object) -> str:
            return str(int(key))

        return _fmt_year
    if unit == "month":

        def _fmt_month(key: object) -> str:
            period = pd.Period(key, freq="M")
            return period.strftime("%b %Y")

        return _fmt_month

    def _fmt_day(key: object) -> str:
        if isinstance(key, pd.Timestamp):
            day = key.date()
        elif isinstance(key, date):
            day = key
        else:
            day = pd.Timestamp(key).date()
        return _fmt_short_date(day)

    return _fmt_day


def _unit_keys(dates: pd.Series, unit: Literal["year", "month", "day"]) -> pd.Series:
    if unit == "year":
        return dates.dt.year
    if unit == "month":
        return dates.dt.to_period("M")
    return dates.dt.normalize()


def _checklist_counts_by_unit(
    checklists: pd.DataFrame,
    unit: Literal["year", "month", "day"],
    *,
    completed_only: bool,
) -> pd.Series:
    if checklists.empty or "Date" not in checklists.columns:
        return pd.Series(dtype="int64")
    frame = checklists
    if completed_only:
        mask = _completed_checklist_mask(frame)
        if mask is None:
            return pd.Series(dtype="int64")
        frame = frame.loc[mask]
        if frame.empty:
            return pd.Series(dtype="int64")
    keys = _unit_keys(frame["Date"], unit)
    return frame.groupby(keys, sort=True)["Submission ID"].nunique()


def _species_counts_by_unit(
    species_obs: pd.DataFrame, unit: Literal["year", "month", "day"]
) -> pd.Series:
    if species_obs.empty or "Date" not in species_obs.columns:
        return pd.Series(dtype="int64")
    countable = species_obs.dropna(subset=["_base"])
    if countable.empty:
        return pd.Series(dtype="int64")
    keys = _unit_keys(countable["Date"], unit)
    return countable.groupby(keys, sort=True)["_base"].nunique()


def _individual_counts_by_unit(
    species_obs: pd.DataFrame, unit: Literal["year", "month", "day"]
) -> pd.Series:
    if species_obs.empty or "Date" not in species_obs.columns:
        return pd.Series(dtype="int64")
    # Individuals include counts on countable taxa only (same spirit as share stats).
    countable = species_obs.dropna(subset=["_base"])
    if countable.empty:
        return pd.Series(dtype="int64")
    keys = _unit_keys(countable["Date"], unit)
    return countable.groupby(keys, sort=True)["_count"].sum().astype(int)


def _peak_from_series(
    fact_id: InsightFactId,
    counts: pd.Series,
    *,
    metric_unit: str,
    format_key: Callable[[object], str],
) -> ShareSummaryInsightFact | None:
    if counts.empty:
        return None
    max_val = int(counts.max())
    if max_val <= 0:
        return None
    winners = counts[counts == max_val].sort_index()
    winner_key = winners.index[0]
    tie_count = len(winners)
    return ShareSummaryInsightFact(
        fact_id=fact_id,
        label=INSIGHT_FACT_CARD_LABELS[fact_id],
        primary_text=format_key(winner_key),
        metric_value=max_val,
        metric_unit=metric_unit,
        peak_tied=tie_count > 1,
        peak_tie_count=tie_count,
    )
