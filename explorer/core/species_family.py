"""eBird taxonomy → species-group (family) mapping for stats and Rankings.

Fetches the same eBird taxonomy CSV and species-group JSON as the **Families** tab
(:func:`~explorer.app.streamlit.bird_families_streamlit_html.build_group_coverage_tables`).
Core code uses :func:`build_base_species_to_family_map` with ``functools.lru_cache``;
Streamlit layers may add separate ``@st.cache_data`` around the loaders.

Network loads are shared via :func:`~explorer.core.taxonomy_bundle.load_taxonomy_bundle`.
"""

from __future__ import annotations

import functools
from typing import Any

import pandas as pd

from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.taxonomy_bundle import load_taxonomy_bundle, taxonomy_locale_key


def load_taxonomy_species_rows(locale: str) -> pd.DataFrame:
    """Load eBird taxonomy rows (species only) with taxon order and base species key."""
    return load_taxonomy_bundle(taxonomy_locale_key(locale)).species_rows


def load_taxonomy_groups(locale: str) -> list[dict[str, Any]]:
    """Load eBird species-group (family) ranges for taxon order."""
    return list(load_taxonomy_bundle(taxonomy_locale_key(locale)).groups)


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
    loc = taxonomy_locale_key(locale) or TAXONOMY_LOCALE_DEFAULT
    try:
        return dict(_base_species_family_items_cached(loc))
    except Exception:
        return {}
