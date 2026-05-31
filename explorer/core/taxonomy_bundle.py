"""Shared eBird taxonomy load: one CSV fetch/parse per locale for tables and species links.

``load_taxonomy_bundle`` is the single entry point used by :mod:`explorer.core.species_family`
(species rows + species groups) and :mod:`explorer.core.taxonomy` (common name → species code).
Non-``en_US`` locales still merge **en_US** common names into the lookup dict (same rules as
:func:`~explorer.core.taxonomy.load_taxonomy`).
"""

from __future__ import annotations

import csv
import functools
import io
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

_TAXONOMY_EBIRD_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird"
_GROUPS_EBIRD_URL = "https://api.ebird.org/v2/ref/sppgroup/ebird"


def taxonomy_locale_key(locale: str | None) -> str:
    """Normalized locale string for bundle cache keys (empty = API default / en_US)."""
    return (locale or "").strip()


def _taxonomy_csv_url(locale_key: str) -> str:
    if locale_key:
        return f"{_TAXONOMY_EBIRD_URL}?{urlencode({'locale': locale_key})}"
    return _TAXONOMY_EBIRD_URL


def _groups_json_url(locale_key: str) -> str:
    if locale_key:
        return f"{_GROUPS_EBIRD_URL}?{urlencode({'locale': locale_key})}"
    return _GROUPS_EBIRD_URL


def _fetch_taxonomy_csv(url: str) -> str | None:
    try:
        req = Request(url, headers={"Accept": "text/csv"})
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, TimeoutError):
        return None


def _parse_taxonomy_csv(raw: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Parse one taxonomy CSV into species rows and common_name → species_code (species category only)."""
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return pd.DataFrame(), {}
    field_lower = {f.strip().lower(): f for f in reader.fieldnames}
    common_key = field_lower.get("common_name") or field_lower.get("common name")
    code_key = field_lower.get("species_code") or field_lower.get("species code")
    category_key = field_lower.get("category")
    sci_keys = (
        field_lower.get("scientific_name"),
        field_lower.get("sci_name"),
        field_lower.get("scientific name"),
    )
    tax_order_key = field_lower.get("taxon_order") or field_lower.get("taxon order")
    extinct_key = field_lower.get("extinct")
    extinct_year_key = field_lower.get("extinct_year") or field_lower.get("extinct year")

    rows: list[dict[str, Any]] = []
    lookup: dict[str, str] = {}
    for row in reader:
        cat = ""
        if category_key:
            cat = str(row.get(category_key) or "").strip().lower()
        if cat != "species":
            continue
        sci = ""
        for sk in sci_keys:
            if sk:
                sci = str(row.get(sk) or "").strip()
                if sci:
                    break
        common = ""
        if common_key:
            common = str(row.get(common_key) or "").strip()
        if not common and field_lower.get("primary_com_name"):
            common = str(row.get(field_lower["primary_com_name"]) or "").strip()
        code = ""
        if code_key:
            code = str(row.get(code_key) or "").strip()
        if common and code:
            lookup[common] = code
        if not sci or not common:
            continue
        tax_raw = row.get(tax_order_key) if tax_order_key else ""
        try:
            taxon_order = float(str(tax_raw).strip())
        except Exception:
            continue
        extinct_raw = str(row.get(extinct_key) or "").strip() if extinct_key else ""
        extinct_year_raw = str(row.get(extinct_year_key) or "").strip() if extinct_year_key else ""
        is_extinct = extinct_raw in {"1", "true", "True", "yes", "Yes"}
        rows.append(
            {
                "scientific_name": sci,
                "common_name": common,
                "species_code": code,
                "taxon_order": taxon_order,
                "base_species": " ".join(sci.lower().split()[:2]).strip(),
                "extinct": extinct_raw,
                "extinct_year": extinct_year_raw,
                "is_extinct": is_extinct,
            }
        )
    return pd.DataFrame(rows), lookup


def _fetch_taxonomy_groups(locale_key: str) -> list[dict[str, Any]]:
    url = _groups_json_url(locale_key)
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


@dataclass(frozen=True)
class TaxonomyBundle:
    """One locale's taxonomy CSV (species rows), species groups, and link lookup dict."""

    species_rows: pd.DataFrame
    groups: tuple[dict[str, Any], ...]
    common_to_code: dict[str, str]


@functools.lru_cache(maxsize=16)
def load_taxonomy_bundle(locale: str | None = None) -> TaxonomyBundle:
    """Fetch and parse eBird taxonomy once per locale (cached in-process).

    *locale* — same semantics as :func:`~explorer.core.taxonomy.load_taxonomy` (``None``/``""``
    for API default). Uses :data:`~explorer.core.settings_schema_defaults.TAXONOMY_LOCALE_DEFAULT`
    only when callers pass that explicitly via :mod:`species_family`.
    """
    loc = taxonomy_locale_key(locale)
    raw_primary = _fetch_taxonomy_csv(_taxonomy_csv_url(loc))
    if raw_primary is None:
        return TaxonomyBundle(pd.DataFrame(), (), {})

    species_rows, common = _parse_taxonomy_csv(raw_primary)
    if loc and loc.lower() != "en_us":
        raw_us = _fetch_taxonomy_csv(_taxonomy_csv_url("en_US"))
        if raw_us:
            _, us_lookup = _parse_taxonomy_csv(raw_us)
            if us_lookup:
                common = {**us_lookup, **common}

    groups = tuple(_fetch_taxonomy_groups(loc))
    return TaxonomyBundle(species_rows, groups, common)


def clear_taxonomy_bundle_cache() -> None:
    """Clear the in-process bundle cache (tests)."""
    load_taxonomy_bundle.cache_clear()
