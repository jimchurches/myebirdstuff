"""
Rebuild the explorer's filtered working DataFrame and derived map/search structures.

Lives outside the Streamlit layer so the same filtering and aggregates can be tested and reused
without importing UI widgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Any, Dict, List, MutableMapping, Optional, Tuple

import pandas as pd

from explorer.core.species_logic import countable_species_vectorized
from explorer.core.stats import safe_count


@dataclass
class WorkingSet:
    """Active working dataset and aggregates after applying the date filter (or full range)."""

    df: pd.DataFrame
    location_data: pd.DataFrame
    records_by_loc: Dict[Any, pd.DataFrame]
    species_list: List[str]
    total_checklists: int
    total_individuals: int
    total_species: int
    name_map: Dict[str, str]
    records_by_loc_full: Dict[Any, pd.DataFrame]
    total_checklists_full: int
    total_species_full: int
    total_individuals_full: int


def rebuild_working_set_from_date_filter(
    df_full: pd.DataFrame,
    location_ids_with_checklists: AbstractSet[Any],
    *,
    filter_by_date: bool,
    filter_start_date: str,
    filter_end_date: str,
    whoosh_index: Any = None,
    map_caches: Optional[Tuple[dict, MutableMapping[Any, Any]]] = None,
) -> Optional[WorkingSet]:
    """
    Recompute the working ``df`` and derived structures from ``df_full``.

    Mirrors the former ``_apply_date_filter_and_build_map_data`` behaviour:
    invalid date range leaves everything unchanged (returns ``None``).
    On success, optionally clears map popup/filter caches and rebuilds the Whoosh
    species index when ``whoosh_index`` is provided.

    Parameters
    ----------
    df_full
        Full export dataframe (not the working slice).
    location_ids_with_checklists
        Location IDs that have at least one checklist.
    filter_by_date, filter_start_date, filter_end_date
        Same semantics as ``FILTER_*`` variables.
    whoosh_index
        If set, the Whoosh index is cleared and repopulated with ``species_list``.
    map_caches
        If set, ``(popup_html_cache, filtered_by_loc_cache)``; both are ``.clear()`` on success.

    Returns
    -------
    WorkingSet or None
        ``None`` if date filter is on but start/end are invalid; otherwise a populated ``WorkingSet``.
    """
    start, end = None, None
    if filter_by_date:
        try:
            start = datetime.strptime(filter_start_date, "%Y-%m-%d")
            end = datetime.strptime(filter_end_date, "%Y-%m-%d")
            assert start <= end, "Start date must be before end date"
        except Exception:
            return None

    # Keep "full" groupings consistent: only locations that
    # have checklists are eligible for both working + full views.
    df_full_filtered = df_full[df_full["Location ID"].isin(location_ids_with_checklists)].copy()

    df_new = df_full_filtered
    if filter_by_date and start is not None and end is not None:
        df_new = df_new[(df_new["Date"] >= start) & (df_new["Date"] <= end)]

    df = df_new
    location_data = df[["Location ID", "Location", "Latitude", "Longitude"]].drop_duplicates()
    records_by_loc = {lid: grp for lid, grp in df.groupby("Location ID")}
    species_list = sorted(df["Common Name"].dropna().unique().tolist())
    total_checklists = df["Submission ID"].nunique()
    total_individuals = int(df["Count"].apply(safe_count).sum())
    total_species = int(countable_species_vectorized(df).dropna().nunique())
    name_map = (
        df[["Common Name", "Scientific Name"]]
        .dropna()
        .drop_duplicates()
        .set_index("Common Name")["Scientific Name"]
        .to_dict()
    )

    if filter_by_date:
        records_by_loc_full = {lid: grp for lid, grp in df_full_filtered.groupby("Location ID")}
        total_checklists_full = df_full_filtered["Submission ID"].nunique()
        total_species_full = int(countable_species_vectorized(df_full_filtered).dropna().nunique())
        total_individuals_full = int(df_full_filtered["Count"].apply(safe_count).sum())
    else:
        records_by_loc_full = {}
        total_checklists_full = total_checklists
        total_species_full = total_species
        total_individuals_full = total_individuals

    if map_caches is not None:
        popup_cache, filtered_cache = map_caches
        popup_cache.clear()
        filtered_cache.clear()

    if whoosh_index is not None:
        from whoosh.query import Every

        w = whoosh_index.writer()
        w.delete_by_query(Every())
        for common in species_list:
            sci = str(name_map.get(common, "") or "")
            w.add_document(common_name=common, scientific_name=sci, kind="species")
        w.commit()

    return WorkingSet(
        df=df,
        location_data=location_data,
        records_by_loc=records_by_loc,
        species_list=species_list,
        total_checklists=total_checklists,
        total_individuals=total_individuals,
        total_species=total_species,
        name_map=name_map,
        records_by_loc_full=records_by_loc_full,
        total_checklists_full=total_checklists_full,
        total_species_full=total_species_full,
        total_individuals_full=total_individuals_full,
    )
