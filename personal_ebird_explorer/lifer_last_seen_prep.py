"""
Lifer and last-seen lookup preparation from the full (unfiltered) dataset.

Used for map pin highlighting and species-banner dates. Pure data prep — no
widgets or HTML (refs #68, Streamlit migration prep).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

import pandas as pd

from personal_ebird_explorer.species_logic import base_species_for_lifer as _default_base_species_for_lifer


@dataclass(frozen=True)
class LiferLastSeenPrep:
    """Chronologically sorted rows with taxon/base columns and location lookups."""

    lifer_lookup_df: pd.DataFrame
    true_lifer_locations: Dict[str, object]
    true_last_seen_locations: Dict[str, object]
    true_lifer_locations_taxon: Dict[str, object]
    true_last_seen_locations_taxon: Dict[str, object]


def prepare_lifer_last_seen(
    full_df: pd.DataFrame,
    base_species_fn: Callable[[object], object] | None = None,
) -> LiferLastSeenPrep:
    """Build lifer / last-seen tables from a full export DataFrame (already scoped as needed).

    *full_df* must include ``datetime``, ``Scientific Name``, ``Location ID``, and ``Date``.
    Rows should represent the same checklist filter as the main map (e.g. locations with
    checklists only), but must **not** be date-filtered if lifers are to match eBird-style
    first/last across all time.

    Subspecies roll up to base species (genus + species) for nominate-style lifers; full
    scientific string (lowercased) is used as taxon key for subspecies-level selection.
    """
    fn = base_species_fn or _default_base_species_for_lifer
    lifer_lookup_df = (
        full_df.sort_values("datetime")
        .dropna(subset=["Scientific Name", "Location ID", "datetime"])
        .assign(
            _base=lambda x: x["Scientific Name"].apply(fn),
            _taxon=lambda x: x["Scientific Name"].str.strip().str.lower(),
        )
    )
    lifer_lookup_df = lifer_lookup_df[lifer_lookup_df["_base"].notna()]
    true_lifer_locations = lifer_lookup_df.groupby("_base").first()["Location ID"].to_dict()
    true_last_seen_locations = lifer_lookup_df.groupby("_base").last()["Location ID"].to_dict()
    true_lifer_locations_taxon = lifer_lookup_df.groupby("_taxon").first()["Location ID"].to_dict()
    true_last_seen_locations_taxon = lifer_lookup_df.groupby("_taxon").last()["Location ID"].to_dict()
    return LiferLastSeenPrep(
        lifer_lookup_df=lifer_lookup_df,
        true_lifer_locations=true_lifer_locations,
        true_last_seen_locations=true_last_seen_locations,
        true_lifer_locations_taxon=true_lifer_locations_taxon,
        true_last_seen_locations_taxon=true_last_seen_locations_taxon,
    )
