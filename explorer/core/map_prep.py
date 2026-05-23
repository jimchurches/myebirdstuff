"""
Prepare shared map context (locations, records-by-location, lifer prep) for Leaflet GeoJSON builders.

Centralises the same dataframe signatures the Streamlit app uses so the embedded map and popups stay
in sync with checklist prep. When a date filter applies, pass the **filtered** working frame as
*df* and the **full** export as *full_df* for lifer / last-seen prep.

Lifer / last-seen lookups in ``prepare_lifer_last_seen`` intentionally ignore the date filter;
only map pins and banner first/last dates use that full-time data.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, Hashable, Tuple

import pandas as pd

from explorer.core.lifer_last_seen_prep import prepare_lifer_last_seen
from explorer.core.species_logic import base_species_for_lifer, countable_species_vectorized
from explorer.core.stats import safe_count


def mean_center_from_location_data(location_data: pd.DataFrame | None) -> tuple[float, float] | None:
    """Mean ``(latitude, longitude)`` for default map centre (same idea as visit overlay empty map).

    Returns ``None`` when *location_data* is missing, empty, or means are non-finite — callers fall back
    to a regional default (e.g. family blank map).
    """
    if location_data is None or location_data.empty:
        return None
    if not {"Latitude", "Longitude"}.issubset(location_data.columns):
        return None
    lat = float(location_data["Latitude"].mean())
    lon = float(location_data["Longitude"].mean())
    if pd.isna(lat) or pd.isna(lon):
        return None
    return (lat, lon)


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
    n_locations = int(location_data["Location ID"].nunique())

    prep = prepare_lifer_last_seen(full, base_species_fn=base_species_for_lifer)

    return {
        "df": work,
        "location_data": location_data,
        "records_by_loc": records_by_loc,
        "effective_location_data": location_data,
        "effective_records_by_loc": records_by_loc,
        "effective_totals": (n_locations, total_checklists, total_species, total_individuals),
        "effective_use_full": False,
        "lifer_lookup_df": prep.lifer_lookup_df,
        "true_lifer_locations": prep.true_lifer_locations,
        "true_last_seen_locations": prep.true_last_seen_locations,
        "true_lifer_locations_taxon": prep.true_lifer_locations_taxon,
        "true_last_seen_locations_taxon": prep.true_last_seen_locations_taxon,
        "full_location_data": full_location_data,
    }


def _dataset_content_fingerprint(df: pd.DataFrame) -> str:
    """Hash submission-id set so two exports with the same row count do not share caches."""
    if df.empty:
        return "empty"
    digest = hashlib.sha256()
    digest.update(str(len(df)).encode())
    if "Submission ID" not in df.columns:
        return digest.hexdigest()[:16]
    sids = df["Submission ID"].dropna().astype(str).str.strip()
    if sids.empty:
        return digest.hexdigest()[:16]
    for sid in sorted(sids.unique()):
        digest.update(sid.encode("utf-8", errors="replace"))
        digest.update(b"\n")
    return digest.hexdigest()[:16]


def _disk_file_identity(data_abs_path: str) -> str:
    """``mtime_ns:size`` when the export path is stat-able (disk load)."""
    try:
        st = os.stat(data_abs_path)
        return f"{int(st.st_mtime_ns)}:{int(st.st_size)}"
    except OSError:
        return data_abs_path


def data_signature_for_caches(
    df: pd.DataFrame,
    provenance: str,
    *,
    data_abs_path: str | None = None,
) -> Tuple[str, int, str]:
    """Stable tuple to detect a new dataset and clear Leaflet session caches.

    Tuple is ``(provenance, row_count, fingerprint)``. The fingerprint hashes all
    unique submission IDs (not only the first row) and, for disk loads, includes
    file ``mtime_ns`` and size when *data_abs_path* is provided.
    """
    fingerprint = _dataset_content_fingerprint(df)
    if data_abs_path:
        fingerprint = f"{_disk_file_identity(data_abs_path)}|{fingerprint}"
    return (provenance, len(df), fingerprint)
