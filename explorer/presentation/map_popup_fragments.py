"""Content-keyed fragments for map popup HTML (#205 Batch A).

Reuses expensive substrings (visit lists, species ``<details>`` blocks, lifer lines) across
full-popup cache misses when the underlying rows are unchanged — e.g. map rebuild after a
non–data-affecting rerun or when switching views that share the same visit rows.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

import pandas as pd


def _dt_key(val: object) -> int | float | str | None:
    """Stable token for a timestamp cell (for cache keys only)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if hasattr(val, "value"):
        try:
            return int(val.value)  # pandas Timestamp .value is ns
        except (TypeError, ValueError):
            pass
    return str(val)


def visit_list_fragment_key(visit_records: pd.DataFrame) -> tuple[Any, ...]:
    """Key for :func:`~explorer.presentation.map_renderer.build_visit_info_html` output."""
    if visit_records.empty:
        return ("visit", ())
    sids = visit_records["Submission ID"].astype(str).map(str.strip)
    if "datetime" in visit_records.columns:
        dtoks = tuple(_dt_key(x) for x in visit_records["datetime"].tolist())
        return ("visit", tuple(zip(sids.tolist(), dtoks)))
    dates = visit_records["Date"].tolist() if "Date" in visit_records.columns else []
    times = visit_records["Time"].tolist() if "Time" in visit_records.columns else []
    return ("visit", tuple(zip(sids.tolist(), map(str, dates), map(str, times))))


def species_sections_fragment_key(
    species_sightings: pd.DataFrame, *, ascending: bool
) -> tuple[Any, ...]:
    """Key for :func:`~explorer.presentation.map_renderer.build_species_seen_sections_html` output."""
    if species_sightings.empty or "Common Name" not in species_sightings.columns:
        return ("ss", (), ascending)
    work = species_sightings.copy()
    work["_cn"] = work["Common Name"].fillna("Unknown")
    sort_cols: list[str] = []
    asc: list[bool] = []
    if "datetime" in work.columns:
        sort_cols.append("datetime")
        asc.append(ascending)
    sort_cols.extend(["_cn", "Submission ID"])
    asc.extend([True, True])
    work = work.sort_values(sort_cols, ascending=asc, kind="mergesort")
    rows: list[tuple[Any, ...]] = []
    for _, r in work.iterrows():
        rows.append(
            (
                str(r["_cn"]),
                str(r.get("Submission ID", "")).strip(),
                _dt_key(r.get("datetime") if "datetime" in work.columns else None),
                str(r.get("Count", "")),
            )
        )
    return ("ss", tuple(rows), ascending)


def lifer_lines_fragment_key(
    *,
    location_id: Any,
    show_subspecies_lifers: bool,
    tax_loc_key: str,
    effective_use_full: bool,
    lite_map_popups: bool,
    entries: list[dict],
) -> tuple[Any, ...]:
    """Key for :func:`~explorer.core.map_overlay_lifer_popups.format_lifer_popup_lines` output."""
    sig = tuple(
        sorted(
            (
                str(e.get("scientific_name") or ""),
                str(e.get("common_name") or ""),
                bool(e.get("is_base_lifer")),
                bool(e.get("is_taxon_lifer")),
            )
            for e in entries
        )
    )
    return (
        "lf",
        str(location_id),
        bool(show_subspecies_lifers),
        (tax_loc_key or "").strip(),
        bool(effective_use_full),
        bool(lite_map_popups),
        sig,
    )


def get_or_set_popup_fragment(
    cache: MutableMapping[tuple[Any, ...], str],
    key: tuple[Any, ...],
    factory: Callable[[], str],
) -> str:
    if key in cache:
        return cache[key]
    html = factory()
    cache[key] = html
    return html
