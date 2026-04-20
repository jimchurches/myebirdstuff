"""Helpers for All locations map viewport: focus by country, bounds points, framing modes.

Pure functions — no Streamlit imports. Used by :mod:`explorer.core.map_overlay_visit_map`
and tests.
"""

from __future__ import annotations

from typing import Hashable

import pandas as pd

from explorer.core.region_display import map_focus_key_for_display
from explorer.core.stats import checklist_country_keys

# Map focust / viewport mode (Streamlit session values and map overlay API).
ALL_LOCATIONS_FRAMING_FIT_ALL = "fit_all"
# Default scope: quantile-trimmed bounds plus optional full inclusion of well-sampled countries.
ALL_LOCATIONS_SCOPE_FOCUSED = "focused"
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
    """Selectbox order: All locations, Focused (trimmed), My activity centre, then countries."""
    return [
        ALL_LOCATIONS_FRAMING_FIT_ALL,
        ALL_LOCATIONS_SCOPE_FOCUSED,
        ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ] + sorted_country_keys_by_display_name(df)


def trim_coordinate_pairs_to_central_extent(
    pairs: list[list[float]],
    *,
    quantile_low: float = 0.025,
    quantile_high: float = 0.975,
    min_points_to_trim: int = 4,
) -> list[list[float]]:
    """Keep points whose lat/lon fall inside independent quantile bands (central ~95% by default).

    If there are fewer than *min_points_to_trim* pairs, returns a copy of *pairs* unchanged.
    If trimming would remove everything, returns a copy of *pairs*.
    """
    if len(pairs) < min_points_to_trim:
        return [p[:] for p in pairs]
    lats = [float(p[0]) for p in pairs]
    lons = [float(p[1]) for p in pairs]
    lat_lo = float(pd.Series(lats).quantile(quantile_low))
    lat_hi = float(pd.Series(lats).quantile(quantile_high))
    lon_lo = float(pd.Series(lons).quantile(quantile_low))
    lon_hi = float(pd.Series(lons).quantile(quantile_high))
    if lat_lo >= lat_hi or lon_lo >= lon_hi:
        return [p[:] for p in pairs]
    out = [
        [la, lo]
        for la, lo in pairs
        if lat_lo <= float(la) <= lat_hi and lon_lo <= float(lo) <= lon_hi
    ]
    return out if out else [p[:] for p in pairs]


def observation_row_counts_by_country_key(df: pd.DataFrame) -> dict[str, int]:
    """Count species/checklist rows per map country key (same keys as :func:`location_id_to_country_map`).

    Uses :func:`~explorer.core.stats.checklist_country_keys` per row; excludes ``_UNKNOWN``.
    """
    if df is None or df.empty:
        return {}
    keys = checklist_country_keys(df)
    s = keys[keys.astype(str) != "_UNKNOWN"]
    if s.empty:
        return {}
    vc = s.value_counts()
    return {str(k): int(v) for k, v in vc.items()}


def _lat_lon_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(float(lat), 5), round(float(lon), 5))


def coordinate_pairs_focused_viewport(
    effective_location_data: pd.DataFrame,
    *,
    location_id_to_country: dict[Hashable, str],
    observation_counts_by_country: dict[str, int],
    quantile_low: float,
    quantile_high: float,
    min_observations_full_country: int,
) -> list[list[float]]:
    """Bounds points for **Focused**: quantile band on all pins, plus every pin in countries with enough rows.

    Rows counted in *observation_counts_by_country* should match the same export scope as *df*
    passed to :func:`observation_row_counts_by_country_key`. Country keys must align with
    *location_id_to_country* values. When *min_observations_full_country* is ``<= 0``, only
    quantile trimming applies.
    """
    triples: list[tuple[float, float, str]] = []
    loc_c = location_id_to_country or {}
    for _, row in effective_location_data.iterrows():
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        if pd.isna(lat) or pd.isna(lon):
            continue
        lid = row["Location ID"]
        c_raw = loc_c.get(lid, "")
        c = str(c_raw).strip() if c_raw is not None and str(c_raw).strip() else ""
        triples.append((lat, lon, c))
    if not triples:
        return []
    full_pairs = [[t[0], t[1]] for t in triples]
    trimmed = trim_coordinate_pairs_to_central_extent(
        full_pairs,
        quantile_low=quantile_low,
        quantile_high=quantile_high,
    )
    if min_observations_full_country <= 0 or not observation_counts_by_country:
        return trimmed

    high = {
        k
        for k, n in observation_counts_by_country.items()
        if n >= min_observations_full_country and str(k).strip() and str(k) != "_UNKNOWN"
    }
    if not high:
        return trimmed

    seen: set[tuple[float, float]] = {_lat_lon_key(p[0], p[1]) for p in trimmed}
    out: list[list[float]] = [p[:] for p in trimmed]
    for la, lo, c in triples:
        if c in high:
            key = _lat_lon_key(la, lo)
            if key not in seen:
                seen.add(key)
                out.append([la, lo])
    return out


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
