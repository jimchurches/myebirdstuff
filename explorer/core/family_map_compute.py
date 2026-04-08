"""Pure aggregation for the taxonomy-family map: how rich each checklist location is for a chosen family.

This module stays UI-free so the same numbers feed Folium and tests. Density uses **distinct base
species** per location (subspecies roll up to base). Popup lines use **distinct common names** as
recorded (subspecies can appear as separate lines). Highlight targets a **base species**; any
subspecies row counts as a match.

Callers supply :func:`~explorer.core.species_family.build_base_species_to_family_map` and taxonomy
tables built the same way as Rankings **Families** (``group_name`` per species row).
"""

from __future__ import annotations

import html as html_module
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from explorer.core.species_logic import countable_species_vectorized

UNMAPPED_FAMILY_LABEL = "Unmapped"

# Legend bands: 1 | 2–3 | 4–5 | 6+ distinct base species in the family at the location.
DENSITY_BAND_LABELS: tuple[str, ...] = ("1", "2–3", "4–5", "6+")


def family_density_band_index(distinct_base_species_count: int) -> int:
    """Map a richness count to a band index in ``0 .. len(DENSITY_BAND_LABELS)-1``."""
    n = int(distinct_base_species_count)
    if n <= 0:
        return 0
    if n == 1:
        return 0
    if n <= 3:
        return 1
    if n <= 5:
        return 2
    return 3


def family_density_band_label(distinct_base_species_count: int) -> str:
    """Human-readable band label for legend rows (matches :data:`DENSITY_BAND_LABELS`)."""
    idx = family_density_band_index(distinct_base_species_count)
    return DENSITY_BAND_LABELS[idx]


@dataclass(frozen=True)
class FamilyMapBannerMetrics:
    """Summary stats for the family-map banner: taxonomy size, species you recorded, and location count."""

    family_name: str
    total_species_taxonomy: int
    species_recorded_user: int
    locations_with_records: int


@dataclass(frozen=True)
class FamilyLocationPin:
    """One location row for family composition map rendering."""

    location_id: str
    location_name: str
    latitude: float
    longitude: float
    distinct_base_species_count: int
    density_band_index: int
    common_name_lines: tuple[str, ...]
    highlight_match: bool


def prepare_family_map_work_frame(
    df: pd.DataFrame,
    base_to_family: dict[str, str],
) -> pd.DataFrame:
    """Attach ``_base`` and ``_family``; keep only countable rows with a mapped family.

    *base_to_family* is typically from :func:`~explorer.core.species_family.build_base_species_to_family_map`.
    Rows with missing family or :data:`UNMAPPED_FAMILY_LABEL` are dropped (family map is taxonomy-backed).
    """
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    work["_base"] = countable_species_vectorized(work)
    work = work[work["_base"].notna()].copy()
    work["_base"] = work["_base"].astype(str).str.strip()
    fam_series = work["_base"].map(lambda b: base_to_family.get(b))
    work["_family"] = fam_series
    work = work[work["_family"].notna()].copy()
    work = work[work["_family"].astype(str).str.strip() != UNMAPPED_FAMILY_LABEL].copy()
    return work


def families_recorded_alphabetically(work: pd.DataFrame) -> tuple[str, ...]:
    """Distinct family names in *work*, sorted A→Z for the sidebar dropdown."""
    if work.empty or "_family" not in work.columns:
        return ()
    s = work["_family"].dropna().astype(str).str.strip()
    s = s[s != ""]
    return tuple(sorted(s.unique(), key=str.casefold))


def filter_work_to_family(work: pd.DataFrame, family_name: str) -> pd.DataFrame:
    """Rows for a single family (caller ensures *family_name* is non-empty)."""
    if work.empty:
        return work
    fn = str(family_name).strip()
    return work[work["_family"].astype(str).str.strip() == fn].copy()


def taxonomy_species_count_for_family(taxonomy_merged: pd.DataFrame, family_name: str) -> int:
    """Count distinct ``base_species`` in *taxonomy_merged* for ``group_name == family_name``.

    *taxonomy_merged* matches the Rankings Families merge: at least ``base_species`` and ``group_name``.
    """
    if taxonomy_merged.empty or not family_name:
        return 0
    fn = str(family_name).strip()
    sub = taxonomy_merged[taxonomy_merged["group_name"].astype(str).str.strip() == fn]
    if sub.empty or "base_species" not in sub.columns:
        return 0
    return int(sub["base_species"].nunique())


def compute_family_map_banner_metrics(
    work: pd.DataFrame,
    family_name: str,
    taxonomy_merged: pd.DataFrame,
) -> FamilyMapBannerMetrics | None:
    """Banner metrics; returns ``None`` if *family_name* is empty or there is no user data for the family."""
    fn = (family_name or "").strip()
    if not fn:
        return None
    wf = filter_work_to_family(work, fn)
    if wf.empty:
        return None
    total_tax = taxonomy_species_count_for_family(taxonomy_merged, fn)
    user_species = int(wf["_base"].nunique())
    locs = int(wf["Location ID"].nunique())
    return FamilyMapBannerMetrics(
        family_name=fn,
        total_species_taxonomy=total_tax,
        species_recorded_user=user_species,
        locations_with_records=locs,
    )


def highlight_species_choices_alphabetical(
    work_family: pd.DataFrame,
    base_to_common: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    """(display label, base species key) for the highlight dropdown, A→Z by display label.

    *base_to_common* maps lowercased base scientific key → preferred common name (e.g. from taxonomy).
    Multiple bases fall back to the base string itself. Only **base species** are listed so the
    dropdown stays one row per species (subspecies are covered via the parent base).
    """
    if work_family.empty or "_base" not in work_family.columns:
        return ()
    bases = sorted(work_family["_base"].dropna().astype(str).str.strip().unique(), key=str.casefold)

    def label_for(b: str) -> str:
        return (base_to_common.get(b) or b).strip() or b

    pairs = [(label_for(b), b) for b in bases]
    pairs.sort(key=lambda p: (p[0].casefold(), p[1].casefold()))
    return tuple(pairs)


def _location_coords_and_name(grp: pd.DataFrame) -> tuple[float, float, str]:
    lat = grp["Latitude"].iloc[0]
    lon = grp["Longitude"].iloc[0]
    if hasattr(lat, "item"):
        lat = float(lat.item())
    else:
        lat = float(lat)
    if hasattr(lon, "item"):
        lon = float(lon.item())
    else:
        lon = float(lon)
    loc_col = "Location" if "Location" in grp.columns else None
    name = ""
    if loc_col:
        name = str(grp[loc_col].iloc[0] if len(grp) else "").strip()
    return lat, lon, name


def build_family_location_pins(
    work_family: pd.DataFrame,
    *,
    highlight_base_species: str | None = None,
) -> tuple[FamilyLocationPin, ...]:
    """One pin per location with richness, popup lines, and optional highlight match."""
    if work_family.empty:
        return ()
    required = {"Location ID", "Latitude", "Longitude", "_base", "Common Name"}
    missing = required - set(work_family.columns)
    if missing:
        raise ValueError(f"work_family missing columns: {sorted(missing)}")

    hb = (highlight_base_species or "").strip().lower() or None

    rows: list[FamilyLocationPin] = []
    for lid, grp in work_family.groupby("Location ID", sort=False):
        grp = grp.dropna(subset=["Latitude", "Longitude"])
        if grp.empty:
            continue
        n_base = int(grp["_base"].nunique())
        band_idx = family_density_band_index(n_base)
        commons = grp["Common Name"].fillna("").astype(str).str.strip()
        lines = tuple(sorted(c for c in commons.unique() if c))
        lat, lon, loc_name = _location_coords_and_name(grp)
        bases_lower = {str(b).strip().lower() for b in grp["_base"].dropna().astype(str)}
        hl = bool(hb and hb in bases_lower)
        rows.append(
            FamilyLocationPin(
                location_id=str(lid),
                location_name=loc_name,
                latitude=lat,
                longitude=lon,
                distinct_base_species_count=n_base,
                density_band_index=band_idx,
                common_name_lines=lines,
                highlight_match=hl,
            )
        )
    # Stable order: alphabetical by location name, then id
    rows.sort(key=lambda p: (p.location_name.casefold(), p.location_id.casefold()))
    return tuple(rows)


def merge_taxonomy_detail_for_family_map(
    taxonomy_species_rows: pd.DataFrame,
    groups: Iterable[dict],
) -> pd.DataFrame:
    """Same merge as Rankings Families: species rows + ``group_name`` / ``group_order``.

    *taxonomy_species_rows* is from :func:`~explorer.core.species_family.load_taxonomy_species_rows`.
    *groups* is from :func:`~explorer.core.species_family.load_taxonomy_groups`.
    """
    from explorer.core.species_family import assign_group_for_taxon_order

    tax = taxonomy_species_rows.copy()
    if tax.empty:
        return pd.DataFrame()
    glist = list(groups)
    if not glist:
        return pd.DataFrame()

    tax[["group_name", "group_order"]] = tax["taxon_order"].apply(
        lambda x: pd.Series(assign_group_for_taxon_order(float(x), glist))
    )
    return tax


def base_species_to_common_from_taxonomy(taxonomy_merged: pd.DataFrame) -> dict[str, str]:
    """Map lowercased ``base_species`` → ``common_name`` (first occurrence wins)."""
    if taxonomy_merged.empty:
        return {}
    need = {"base_species", "common_name"}
    if not need.issubset(taxonomy_merged.columns):
        return {}
    out: dict[str, str] = {}
    for _, row in taxonomy_merged.iterrows():
        b = str(row["base_species"]).strip().lower()
        c = str(row.get("common_name", "")).strip()
        if b and b not in out and c:
            out[b] = c
    return out


def format_family_location_popup_html(
    pin: FamilyLocationPin,
    *,
    location_page_url: str | None = None,
    species_url_by_common: dict[str, str] | None = None,
) -> str:
    """HTML for a map pin body: location heading (optional hotspot link) and species lines (optional links).

    *species_url_by_common* maps exact common-name strings (as in *pin.common_name_lines*) to
    eBird species URLs; missing keys render as plain text.
    """
    title = pin.location_name or pin.location_id
    esc_title = html_module.escape(title)
    if location_page_url and str(location_page_url).strip():
        esc_href = html_module.escape(str(location_page_url).strip(), quote=True)
        head = f'<div style="font-weight:600;margin-bottom:0.35em;"><a href="{esc_href}" target="_blank" rel="noopener noreferrer">{esc_title}</a></div>'
    else:
        head = f'<div style="font-weight:600;margin-bottom:0.35em;">{esc_title}</div>'
    lines: list[str] = []
    url_map = species_url_by_common or {}
    for name in pin.common_name_lines:
        esc_n = html_module.escape(name)
        u = url_map.get(name) or url_map.get(name.strip())
        if u and str(u).strip():
            esc_u = html_module.escape(str(u).strip(), quote=True)
            lines.append(f'<div style="font-size:0.92em;"><a href="{esc_u}" target="_blank" rel="noopener noreferrer">{esc_n}</a></div>')
        else:
            lines.append(f'<div style="font-size:0.92em;">{esc_n}</div>')
    body = "".join(lines) if lines else '<div style="opacity:0.7;font-size:0.85em;">No species lines</div>'
    return f'<div style="min-width:12rem;max-width:22rem;">{head}{body}</div>'
