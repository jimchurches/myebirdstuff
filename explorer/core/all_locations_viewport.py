"""Helpers for All locations map viewport: focus by country, bounds points, framing modes.

Pure functions — no Streamlit imports. Used by :mod:`explorer.core.map_overlay_visit_map`
and tests.
"""

from __future__ import annotations

from typing import Hashable

import pandas as pd

from explorer.core.region_display import map_focus_key_for_display
from explorer.core.stats import checklist_country_keys

# Map area / viewport mode (Streamlit session values and map overlay API).
ALL_LOCATIONS_FRAMING_FIT_ALL = "fit_all"
ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY = "centre_of_gravity"

# Focus: empty string means all locations (no country filter).
ALL_LOCATIONS_FOCUS_ALL = ""


def location_id_to_country_map(df: pd.DataFrame) -> dict[Hashable, str]:
    """Map each ``Location ID`` to a region key for Focus (same logic as the Country tab).

    Uses :func:`~explorer.core.stats.checklist_country_keys`: prefer ``Country`` when present;
    otherwise derive from ``State/Province`` (e.g. ``AU-NSW`` → ``AU``). Rows mapped to
    ``_UNKNOWN`` are skipped. Returns ``{}`` if neither column exists.
    """
    if df is None or df.empty or "Location ID" not in df.columns:
        return {}
    if "Country" not in df.columns and "State/Province" not in df.columns:
        return {}
    keys = checklist_country_keys(df)
    work = df.loc[df["Location ID"].notna()].copy()
    work["_map_focus_key"] = keys
    work = work[work["_map_focus_key"].astype(str) != "_UNKNOWN"]
    work = work[work["_map_focus_key"].notna()]
    if work.empty:
        return {}
    out: dict[Hashable, str] = {}
    for lid, grp in work.groupby("Location ID", sort=False):
        if lid is None or (isinstance(lid, float) and pd.isna(lid)):
            continue
        first = grp["_map_focus_key"].iloc[0]
        s = str(first).strip()
        if s and s != "_UNKNOWN":
            out[lid] = s
    return out


def sorted_country_labels_from_work(df: pd.DataFrame) -> list[str]:
    """Unique region keys from *df* (excluding ``_UNKNOWN``), sorted by display name."""
    return sorted_country_keys_by_display_name(df)


def sorted_country_keys_by_display_name(df: pd.DataFrame) -> list[str]:
    """Distinct map-focus keys from *df*, sorted by :func:`map_focus_key_for_display` (case-insensitive)."""
    keys = set(location_id_to_country_map(df).values())
    if not keys:
        return []
    return sorted(keys, key=lambda k: map_focus_key_for_display(k).lower())


def all_locations_scope_option_values(df: pd.DataFrame) -> list[str]:
    """Selectbox options: All locations, My centre, then countries/regions from *df* (filtered data)."""
    return [
        ALL_LOCATIONS_FRAMING_FIT_ALL,
        ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ] + sorted_country_keys_by_display_name(df)


def filter_location_rows_by_focus_country(
    effective_location_data: pd.DataFrame,
    *,
    location_id_to_country: dict[Hashable, str],
    focus_country: str | None,
) -> pd.DataFrame:
    """Return rows whose Location ID maps to *focus_country*.

    If *focus_country* is falsy (all locations), return *effective_location_data* unchanged.
    If no rows match, returns an empty DataFrame.
    """
    if effective_location_data is None or effective_location_data.empty:
        return effective_location_data
    fc = (focus_country or "").strip()
    if not fc:
        return effective_location_data
    if not location_id_to_country:
        return pd.DataFrame(columns=effective_location_data.columns)
    mask = effective_location_data["Location ID"].map(
        lambda lid: location_id_to_country.get(lid, "") == fc
    )
    return effective_location_data.loc[mask].copy()


def coordinate_pairs_for_viewport(
    effective_location_data: pd.DataFrame,
    *,
    location_id_to_country: dict[Hashable, str] | None,
    focus_country: str | None,
) -> list[list[float]]:
    """Lat/lng pairs for fit-bounds or centre-of-gravity (same subset as Focus)."""
    loc_id_country = location_id_to_country or {}
    sub = filter_location_rows_by_focus_country(
        effective_location_data,
        location_id_to_country=loc_id_country,
        focus_country=focus_country,
    )
    if sub.empty:
        return []
    out: list[list[float]] = []
    for _, row in sub.iterrows():
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        if pd.isna(lat) or pd.isna(lon):
            continue
        out.append([lat, lon])
    return out


def mean_center_from_pairs(pairs: list[list[float]]) -> tuple[float, float] | None:
    """Mean (lat, lon) for centre-of-gravity framing."""
    if not pairs:
        return None
    s_lat = sum(p[0] for p in pairs)
    s_lon = sum(p[1] for p in pairs)
    n = len(pairs)
    return (s_lat / n, s_lon / n)
