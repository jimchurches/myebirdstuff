"""HTML fragments for lifer-location map popups (checklist links, first-record dates)."""

from __future__ import annotations

import html as html_module
from typing import Hashable, List

import pandas as pd

from explorer.core.map_overlay_types import BaseSpeciesFn


def format_lifer_popup_lines(
    *,
    entries: list[dict],
    lifer_lookup_df: pd.DataFrame,
    location_id: Hashable,
    base_species_fn: BaseSpeciesFn,
) -> str:
    """Build lifer popup list lines with first-record date and checklist links.

    Each *entry* is a dict produced by
    :func:`~explorer.core.lifer_last_seen_prep.aggregate_lifer_sites`, with:

    - scientific_name / common_name
    - is_base_lifer / is_taxon_lifer
    """

    def _pick_first_row_for_entry(entry: dict) -> pd.Series | None:
        candidates: list[pd.Series] = []
        if entry.get("is_base_lifer"):
            base = base_species_fn(entry.get("scientific_name") or "")
            if base:
                sub = lifer_lookup_df[
                    (lifer_lookup_df.get("_base") == base)
                    & (lifer_lookup_df.get("Location ID") == location_id)
                ]
                if not sub.empty:
                    candidates.append(sub.iloc[0])
        if entry.get("is_taxon_lifer"):
            sci = str(entry.get("scientific_name") or "").strip()
            taxon = sci.lower() if sci else ""
            if taxon:
                sub = lifer_lookup_df[
                    (lifer_lookup_df.get("_taxon") == taxon)
                    & (lifer_lookup_df.get("Location ID") == location_id)
                ]
                if not sub.empty:
                    candidates.append(sub.iloc[0])
        if not candidates:
            return None

        def _dt_key(r: pd.Series):
            dt = r.get("datetime")
            if pd.notna(dt):
                return pd.Timestamp(dt)
            d = r.get("Date")
            if pd.notna(d):
                return pd.to_datetime(d, errors="coerce")
            return pd.Timestamp.max

        return min(candidates, key=_dt_key)

    parts: List[str] = []
    for i, e in enumerate(entries):
        label = e.get("common_name") or e.get("scientific_name") or ""
        esc_label = html_module.escape(str(label), quote=False)

        row = _pick_first_row_for_entry(e)
        if row is None:
            date_str = "?"
            checklist_url = "#"
        else:
            d = row.get("Date")
            if pd.notna(d):
                date_str = pd.to_datetime(d, errors="coerce").strftime("%Y-%m-%d")
            else:
                date_str = "?"
            cid = row.get("Submission ID", "")
            checklist_url = (
                f"https://ebird.org/checklist/{cid}"
                if pd.notna(cid) and str(cid).strip()
                else "#"
            )

        prefix = "<br>" if i > 0 else ""
        parts.append(
            f'{prefix}<a href="{html_module.escape(checklist_url, quote=True)}" '
            f'target="_blank" rel="noopener">{esc_label} : {html_module.escape(date_str)}</a>'
        )
    return "".join(parts)
