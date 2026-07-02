"""
Interesting Insights card facts for share-summary cards (#285).

Framework-neutral compute: species- and checklist-derived highlights beyond simple
stat + number pairs. Presentation reads :class:`ShareSummaryInsightFact` via
``explorer.presentation.share_summary_preview``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from explorer.core.share_summary_compute import ShareSummaryPeriod, _mask_in_period
from explorer.core.species_logic import countable_species_vectorized
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
]

INSIGHT_FACT_PICKER_LABELS: dict[InsightFactId, str] = {
    "most_common_checklist_species": "Most common checklist species",
    "most_individuals_species": "Most individuals of a single species",
    "biggest_checklist_count": "Biggest single-checklist count",
    "species_individuals": "Individuals of selected species",
}

INSIGHT_FACTS_REQUIRING_SPECIES: frozenset[InsightFactId] = frozenset({"species_individuals"})
# Card heading when the species name is the hero line (picker label stays descriptive).
INSIGHT_SPECIES_INDIVIDUALS_CARD_LABEL = "Species count"


@dataclass(frozen=True)
class ShareSummaryInsightFact:
    """One Interesting Insights highlight for a period."""

    fact_id: InsightFactId
    label: str
    primary_text: str
    metric_value: int | None = None
    metric_unit: str | None = None


def format_insight_fact_metric(fact: ShareSummaryInsightFact) -> str | None:
    """Formatted optional number line, e.g. ``3,999 checklists``."""
    if fact.metric_value is None:
        return None
    formatted = f"{fact.metric_value:,}"
    if fact.metric_unit:
        return f"{formatted} {fact.metric_unit}"
    return formatted


def insight_fact_requires_species(fact_id: InsightFactId) -> bool:
    return fact_id in INSIGHT_FACTS_REQUIRING_SPECIES


def species_common_names_in_period(df: pd.DataFrame, period: ShareSummaryPeriod) -> tuple[str, ...]:
    """Distinct countable-species common names with observations in *period*, sorted."""
    obs = _observations_in_period(df, period)
    if obs.empty or "Common Name" not in obs.columns:
        return ()
    frame = obs.copy()
    frame["_base"] = countable_species_vectorized(frame)
    countable = frame.dropna(subset=["_base"])
    if countable.empty:
        return ()
    names = (
        countable["Common Name"]
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

    return facts


def insight_fact_by_id(
    facts: list[ShareSummaryInsightFact],
    fact_id: InsightFactId,
) -> ShareSummaryInsightFact | None:
    for fact in facts:
        if fact.fact_id == fact_id:
            return fact
    return None


def _observations_in_period(df: pd.DataFrame, period: ShareSummaryPeriod) -> pd.DataFrame:
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


def _species_individuals_fact(obs: pd.DataFrame, species_common: str) -> ShareSummaryInsightFact | None:
    if obs.empty:
        return None
    target = species_common.casefold()
    frame = obs.copy()
    frame["_base"] = countable_species_vectorized(frame)
    frame = frame.dropna(subset=["_base"])
    if frame.empty or "Common Name" not in frame.columns:
        return None
    frame["_common_key"] = frame["Common Name"].fillna("").astype(str).str.strip().str.casefold()
    matched = frame[frame["_common_key"] == target]
    if matched.empty:
        return None
    display_name = (
        matched["Common Name"].dropna().astype(str).str.strip().value_counts().index[0]
    )
    total = int(matched["Count"].apply(safe_count).sum())
    return ShareSummaryInsightFact(
        fact_id="species_individuals",
        label=INSIGHT_SPECIES_INDIVIDUALS_CARD_LABEL,
        primary_text=str(display_name),
        metric_value=total,
        metric_unit="individuals",
    )
