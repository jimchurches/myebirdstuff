"""eBird taxonomy → species-group (family) mapping for stats and Rankings.

Fetches the same eBird taxonomy CSV and species-group JSON as the **Families** tab
(:func:`~explorer.app.streamlit.rankings_streamlit_html._build_group_coverage_tables`).
Core code uses :func:`build_base_species_to_family_map` with ``functools.lru_cache``;
Streamlit layers may add separate ``@st.cache_data`` around the loaders.
"""

from __future__ import annotations

import csv
import functools
import io
import json
from typing import Any

from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT

_TAXONOMY_EBIRD_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird"
_GROUPS_EBIRD_URL = "https://api.ebird.org/v2/ref/sppgroup/ebird"


def load_taxonomy_species_rows(locale: str) -> pd.DataFrame:
    """Load eBird taxonomy rows (species only) with taxon order and base species key."""
    loc = (locale or "").strip()
    url = _TAXONOMY_EBIRD_URL
    if loc:
        url = f"{url}?{urlencode({'locale': loc})}"
    req = Request(url, headers={"Accept": "text/csv"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    rows: list[dict[str, Any]] = []
    for row in reader:
        cat = str(row.get("CATEGORY", row.get("category", ""))).strip().lower()
        if cat != "species":
            continue
        sci = str(
            row.get("SCIENTIFIC_NAME")
            or row.get("SCI_NAME")
            or row.get("scientific_name")
            or row.get("sci_name")
            or ""
        ).strip()
        common = str(
            row.get("COMMON_NAME")
            or row.get("PRIMARY_COM_NAME")
            or row.get("common_name")
            or ""
        ).strip()
        code = str(row.get("SPECIES_CODE") or row.get("species_code") or "").strip()
        tax_raw = row.get("TAXON_ORDER") or row.get("taxon_order") or ""
        try:
            taxon_order = float(str(tax_raw).strip())
        except Exception:
            continue
        if not sci or not common:
            continue
        rows.append(
            {
                "scientific_name": sci,
                "common_name": common,
                "species_code": code,
                "taxon_order": taxon_order,
                "base_species": " ".join(sci.lower().split()[:2]).strip(),
            }
        )
    return pd.DataFrame(rows)


def load_taxonomy_groups(locale: str) -> list[dict[str, Any]]:
    """Load eBird species-group (family) ranges for taxon order."""
    loc = (locale or "").strip()
    url = _GROUPS_EBIRD_URL
    if loc:
        url = f"{url}?{urlencode({'locale': loc})}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    out: list[dict[str, Any]] = []
    for item in data:
        bounds_in = item.get("taxonOrderBounds", []) or []
        bounds: list[tuple[float, float]] = []
        for pair in bounds_in:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            try:
                lo = float(pair[0])
                hi = float(pair[1])
            except Exception:
                continue
            bounds.append((lo, hi))
        out.append(
            {
                "group_name": str(item.get("groupName", "")).strip(),
                "group_order": int(item.get("groupOrder", 0) or 0),
                "bounds": bounds,
            }
        )
    return out


def assign_group_for_taxon_order(taxon_order: float, groups: list[dict[str, Any]]) -> tuple[str, int]:
    """Map one taxon order to (group_name, group_order) by bounds."""
    for g in groups:
        for lo, hi in g["bounds"]:
            if lo <= taxon_order <= hi:
                return g["group_name"], g["group_order"]
    return "Unmapped", 999999


@functools.lru_cache(maxsize=16)
def _base_species_family_items_cached(locale: str) -> tuple[tuple[str, str], ...]:
    tax = load_taxonomy_species_rows(locale)
    groups = load_taxonomy_groups(locale)
    if tax.empty or not groups:
        return ()
    out: dict[str, str] = {}
    for _, row in tax.iterrows():
        base = str(row["base_species"]).strip()
        to = float(row["taxon_order"])
        gn, _ = assign_group_for_taxon_order(to, groups)
        out[base] = gn
    return tuple(sorted(out.items()))


def build_base_species_to_family_map(locale: str) -> dict[str, str]:
    """Map countable base species key → eBird species-group (family) name.

    Uses the same assignment as Rankings **Families**. Returns ``{}`` if taxonomy
    cannot be loaded (network error, empty response).
    """
    loc = (locale or "").strip() or TAXONOMY_LOCALE_DEFAULT
    try:
        return dict(_base_species_family_items_cached(loc))
    except Exception:
        return {}
