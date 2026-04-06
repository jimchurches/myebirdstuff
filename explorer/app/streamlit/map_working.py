"""
Working DataFrame + date filter for the Streamlit map (refs #70).

Wraps :func:`explorer.core.working_set.rebuild_working_set_from_date_filter`
with Streamlit-friendly semantics: *All locations* vs *Lifer locations*, optional **Date filter** (range) vs all-time.
"""

from __future__ import annotations

from datetime import date
from typing import Any, MutableMapping, Optional, Set, Tuple

import pandas as pd

from explorer.core.working_set import WorkingSet, rebuild_working_set_from_date_filter

MapCaches = Tuple[dict, MutableMapping[Any, Any]]


def location_ids_with_checklists(df: pd.DataFrame) -> Set[Any]:
    """Location IDs that have at least one checklist row."""
    if df.empty or "Submission ID" not in df.columns:
        return set()
    return set(df.dropna(subset=["Submission ID"])["Location ID"].unique())


def date_bounds_from_df(df: pd.DataFrame) -> Tuple[date, date]:
    """Min/max calendar dates from ``Date`` column; fallback to today if empty."""
    if df.empty or "Date" not in df.columns:
        today = date.today()
        return today, today
    s = pd.to_datetime(df["Date"], errors="coerce").dropna()
    if s.empty:
        today = date.today()
        return today, today
    return s.min().date(), s.max().date()


def date_inception_to_today_default(df: pd.DataFrame) -> Tuple[date, date]:
    """Default range for the date picker: earliest observation → **today** (not last row in export)."""
    d_lo, _ = date_bounds_from_df(df)
    today = date.today()
    if d_lo > today:
        return today, today
    return d_lo, today


def streamlit_working_set_and_status(
    df_full: pd.DataFrame,
    *,
    map_view_mode: str,
    date_filter_on: bool,
    date_range: Optional[Tuple[date, date]],
    map_caches: Optional[MapCaches],
) -> Tuple[Optional[WorkingSet], str]:
    """
    Return ``(working_set, date_filter_status)`` for map banners.

    *map_view_mode* — ``\"all\"`` | ``\"species\"`` | ``\"lifers\"``.
    ``\"species\"`` uses the same date filter as ``\"all\"`` (refs #70).
    Lifer mode forces all-time data and returns status ``\"Lifer view uses all-time data\"``.

    *date_filter_on* — when ``True`` (and *map_view_mode* is ``all``), apply *date_range*; when ``False``, no filter.
    """
    lids = location_ids_with_checklists(df_full)
    mode = (map_view_mode or "all").strip().lower()

    if mode == "lifers":
        ws = rebuild_working_set_from_date_filter(
            df_full,
            lids,
            filter_by_date=False,
            filter_start_date="",
            filter_end_date="",
            map_caches=map_caches,
        )
        return ws, "Lifer view uses all-time data"

    # "all" and "species" share the same date-filter semantics.
    filter_by_date = bool(date_filter_on)
    if not filter_by_date:
        ws = rebuild_working_set_from_date_filter(
            df_full,
            lids,
            filter_by_date=False,
            filter_start_date="",
            filter_end_date="",
            map_caches=map_caches,
        )
        return ws, "Date filter: Off"

    if date_range is None or len(date_range) != 2:
        ws = rebuild_working_set_from_date_filter(
            df_full,
            lids,
            filter_by_date=False,
            filter_start_date="",
            filter_end_date="",
            map_caches=map_caches,
        )
        return ws, "Date filter: Off"

    start_d, end_d = date_range[0], date_range[1]
    if start_d > end_d:
        return None, "Date filter: invalid range"

    start_s = start_d.isoformat()
    end_s = end_d.isoformat()
    ws = rebuild_working_set_from_date_filter(
        df_full,
        lids,
        filter_by_date=True,
        filter_start_date=start_s,
        filter_end_date=end_s,
        map_caches=map_caches,
    )
    if ws is None:
        return None, "Date filter: invalid range"
    return ws, f"Date filter: {start_s} to {end_s}"


def folium_map_to_html_bytes(m: Any) -> bytes:
    """Serialize a Folium map to UTF-8 HTML bytes for ``st.download_button``."""
    root = m.get_root()
    html = root.render()
    if isinstance(html, bytes):
        return html
    return str(html).encode("utf-8")
