"""
Prepare kwargs for :func:`map_controller.build_species_overlay_map` in **all locations** mode.

Used by Streamlit so map + popups match the shared pipeline (refs #70).
When a date filter exists later, pass the **filtered** working frame as *df* and the
**full** export as *full_df* for lifer / last-seen prep.
"""

from __future__ import annotations

from typing import Any, Dict, Hashable, Tuple

import pandas as pd

from explorer.core.lifer_last_seen_prep import prepare_lifer_last_seen
from explorer.core.species_logic import base_species_for_lifer, countable_species_vectorized
from explorer.core.stats import safe_count


def prepare_all_locations_map_context(
    df: pd.DataFrame,
    *,
    full_df: pd.DataFrame | None = None,
) -> Dict[str, Any]:
    """Return keyword arguments (except caches and UI hooks) for ``map_view_mode='all'``.

    *df* — rows shown on the map (checklists / observations).
    *full_df* — if given, used only for :func:`prepare_lifer_last_seen` (e.g. unfiltered
    export). Defaults to *df* when omitted.
    """
    if df.empty:
        raise ValueError("Cannot build map context from an empty DataFrame.")

    work = df.copy()
    full = (full_df if full_df is not None else df).copy()

    location_ids_with_checklists = set(full.dropna(subset=["Submission ID"])["Location ID"].unique())
    work = work[work["Location ID"].isin(location_ids_with_checklists)].copy()
    full = full[full["Location ID"].isin(location_ids_with_checklists)].copy()
    if work.empty:
        raise ValueError("No rows with checklist locations to map.")

    cols = ["Location ID", "Location", "Latitude", "Longitude"]
    location_data = work[cols].drop_duplicates()
    full_location_data = full[cols].drop_duplicates()
    records_by_loc: Dict[Hashable, pd.DataFrame] = {lid: grp for lid, grp in work.groupby("Location ID")}

    total_checklists = int(work["Submission ID"].nunique())
    total_individuals = int(work["Count"].apply(safe_count).sum())
    total_species = int(countable_species_vectorized(work).dropna().nunique())

    prep = prepare_lifer_last_seen(full, base_species_fn=base_species_for_lifer)

    return {
        "df": work,
        "location_data": location_data,
        "records_by_loc": records_by_loc,
        "effective_location_data": location_data,
        "effective_records_by_loc": records_by_loc,
        "effective_totals": (total_checklists, total_species, total_individuals),
        "effective_use_full": False,
        "lifer_lookup_df": prep.lifer_lookup_df,
        "true_lifer_locations": prep.true_lifer_locations,
        "true_last_seen_locations": prep.true_last_seen_locations,
        "true_lifer_locations_taxon": prep.true_lifer_locations_taxon,
        "true_last_seen_locations_taxon": prep.true_last_seen_locations_taxon,
        "full_location_data": full_location_data,
    }


def data_signature_for_caches(df: pd.DataFrame, provenance: str) -> Tuple[str, int, str]:
    """Stable tuple to detect a new dataset and clear popup / filter caches."""
    first_sid = ""
    if len(df) > 0 and "Submission ID" in df.columns:
        first_sid = str(df["Submission ID"].iloc[0])
    return (provenance, len(df), first_sid)
