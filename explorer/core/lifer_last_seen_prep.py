"""
Lifer and last-seen lookup preparation from the full (unfiltered) dataset.

Feeds map pin highlighting and species-banner “first/last seen” dates. Pure data prep — no widgets
or HTML — so the same logic works in Streamlit and tests.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple, TypedDict

import pandas as pd

from explorer.core.species_logic import (
    base_species_for_lifer as _default_base_species_for_lifer,
    countable_species_vectorized,
)


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
    # Lifer pins should match the app's "countable species" rules:
    # exclude spuhs/hybrids/domestics and species-level slashes.
    # Keep subspecies (including slash later in the scientific name) intact.
    if "Common Name" not in lifer_lookup_df.columns:
        lifer_lookup_df = lifer_lookup_df.assign(**{"Common Name": pd.NA})
    countable_mask = countable_species_vectorized(lifer_lookup_df).notna()
    lifer_lookup_df = lifer_lookup_df[countable_mask]
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


class LiferSiteEntry(TypedDict):
    """One species line in a lifer-location popup (base and/or subspecies lifer semantics).

    - base-level lifer: first record for the base species
    - taxon-level lifer: first record for the specific taxon (subspecies)
    - both: same underlying record satisfied both
    """

    scientific_name: str
    common_name: str
    is_base_lifer: bool
    is_taxon_lifer: bool


def aggregate_lifer_sites(
    lifer_lookup_df: pd.DataFrame,
    true_lifer_locations: Dict[str, Any],
    true_lifer_locations_taxon: Dict[str, Any],
) -> Tuple[Dict[Any, List[LiferSiteEntry]], int]:
    """Map each location ID to lifer species entries and count unique lifer taxa.

    Uses the same first-row-per-base and first-row-per-taxon rules as
    :func:`prepare_lifer_last_seen`. Each scientific name appears at most once per
    location; taxon-level entries dedupe with base-level when the first row matches.

    Returns:
        ``(location_id -> [entry, ...], n_distinct_lifer_taxa)``
    """
    by_loc: Dict[Any, List[LiferSiteEntry]] = defaultdict(list)
    entry_by_loc_sci: Dict[Any, Dict[str, LiferSiteEntry]] = defaultdict(dict)
    global_sci: set[str] = set()

    def _valid_lid(lid: Any) -> bool:
        if lid is None:
            return False
        try:
            if pd.isna(lid):
                return False
        except TypeError:
            pass
        return True

    def _add(lid: Any, sci: str, common: str, *, is_base: bool, is_taxon: bool) -> None:
        if not _valid_lid(lid) or not sci:
            return
        existing = entry_by_loc_sci[lid].get(sci)
        if existing is None:
            entry: LiferSiteEntry = {
                "scientific_name": sci,
                "common_name": common,
                "is_base_lifer": bool(is_base),
                "is_taxon_lifer": bool(is_taxon),
            }
            entry_by_loc_sci[lid][sci] = entry
            by_loc[lid].append(entry)
        else:
            existing["is_base_lifer"] = existing["is_base_lifer"] or bool(is_base)
            existing["is_taxon_lifer"] = existing["is_taxon_lifer"] or bool(is_taxon)
        global_sci.add(sci)

    for _base, lid in true_lifer_locations.items():
        subset = lifer_lookup_df[lifer_lookup_df["_base"] == _base]
        if subset.empty:
            continue
        r = subset.iloc[0]
        sci = str(r["Scientific Name"])
        com = "" if pd.isna(r.get("Common Name")) else str(r["Common Name"])
        _add(lid, sci, com, is_base=True, is_taxon=False)

    for _taxon, lid in true_lifer_locations_taxon.items():
        subset = lifer_lookup_df[lifer_lookup_df["_taxon"] == _taxon]
        if subset.empty:
            continue
        r = subset.iloc[0]
        sci = str(r["Scientific Name"])
        # Only treat taxon-level lifers as "subspecies lifers" when the scientific name has 3+ parts.
        # A 2-part name duplicates the base-species lifer and must not create a spurious "Both" pin.
        if len(sci.strip().split()) < 3:
            continue
        com = "" if pd.isna(r.get("Common Name")) else str(r["Common Name"])
        _add(lid, sci, com, is_base=False, is_taxon=True)

    sorted_by_loc = {
        k: sorted(
            v,
            key=lambda e: (
                ((e["common_name"] or e["scientific_name"]).lower()),
                e["scientific_name"].lower(),
            ),
        )
        for k, v in by_loc.items()
    }
    return sorted_by_loc, len(global_sci)
