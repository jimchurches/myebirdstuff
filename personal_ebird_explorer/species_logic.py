"""
Species-related pure logic for Personal eBird Explorer.

Functions for species filtering, countable-species normalisation, and
base-species extraction. All functions are pure (explicit inputs/outputs,
no widget or notebook state dependencies).
"""

import pandas as pd


def _base_species_for_count(row):
    """Normalize a single row to its countable base species (genus + species, lowercased).

    Returns None for non-countable entries: spuhs, hybrids, domestic types,
    species-level slashes, or rows missing a two-part scientific name.
    """
    sci = (row.get("Scientific Name") or "").strip()
    common = (row.get("Common Name") or "").strip()
    if not sci:
        return None
    if " sp." in sci or sci.lower().endswith(" sp"):
        return None  # spuh
    if " x " in sci or "(hybrid)" in common.lower():
        return None  # hybrid
    if "Domestic" in common or "(Domestic type)" in common:
        return None
    parts = sci.split()
    if len(parts) < 2:
        return None
    if "/" in parts[1]:
        return None  # species-level slash (not countable)
    return f"{parts[0]} {parts[1]}".lower()


def countable_species_vectorized(df):
    """Vectorized species count: exclude spuhs, slashes, hybrids, domestic; roll up subspecies.

    Returns a Series of base species names (genus + species, lowercased) with NaN
    for non-countable rows.
    """
    sci = df["Scientific Name"].fillna("").astype(str).str.strip()
    common = df["Common Name"].fillna("").astype(str).str.strip()
    if sci.empty:
        return pd.Series(dtype="object")
    spuh = sci.str.contains(r" sp\.", case=False, na=False) | sci.str.lower().str.endswith(" sp")
    hybrid = sci.str.contains(" x ", na=False) | common.str.lower().str.contains(r"\(hybrid\)", na=False)
    domestic = common.str.contains("Domestic", na=False) | common.str.contains(r"\(Domestic type\)", na=False)
    parts = sci.str.split(expand=True)
    has_two_parts = 1 in parts.columns
    slash = parts[1].str.contains("/", na=False) if has_two_parts else pd.Series(False, index=df.index)
    too_short = (parts[0].isna() | parts[1].isna()) if has_two_parts else pd.Series(True, index=df.index)
    exclude = spuh | hybrid | domestic | slash | too_short
    if has_two_parts:
        base = parts[0].str.lower() + " " + parts[1].str.lower()
    else:
        base = pd.Series(pd.NA, index=df.index)
    return base.where(~exclude)


def filter_species(df, base_species):
    """Filter a DataFrame to rows matching a base species (including subspecies).

    - If base_species contains a slash, matches exactly (species-level slash selection).
    - Otherwise, matches rows whose Scientific Name starts with base_species,
      excluding species-level slash groups (e.g. Anas gracilis/castanea) but
      including subspecies with slash in later parts.
    """
    base_species = base_species.lower().strip()
    if "/" in base_species:
        return df[df["Scientific Name"].str.lower() == base_species]
    filtered_df = df[df["Scientific Name"].fillna("").str.lower().str.startswith(base_species)]

    def is_species_level_slash(sci_name):
        sn = (sci_name or "").lower()
        if "/" not in sn:
            return False
        rest = sn[len(base_species):].lstrip()
        return rest.startswith("/")

    mask = filtered_df["Scientific Name"].fillna("").apply(
        lambda s: not is_species_level_slash(s)
    )
    return filtered_df[mask]


def base_species_for_lifer(sci_name):
    """Extract base species (genus + species, lowercased) from a scientific name.

    Returns None for missing/empty names or names with fewer than two parts.
    Does not filter non-countable entries (spuhs, hybrids, etc.) — use
    countable_species_vectorized for that.
    """
    if pd.isna(sci_name) or not str(sci_name).strip():
        return None
    parts = str(sci_name).strip().split()
    if len(parts) < 2:
        return None
    return f"{parts[0]} {parts[1]}".lower()
