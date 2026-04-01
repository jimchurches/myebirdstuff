"""
Species-related pure logic for Personal eBird Explorer.

Functions for species filtering, countable-species normalisation, and
base-species extraction. All functions are pure (explicit inputs/outputs,
no widget or UI state dependencies).
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def base_species_name(sci_name):
    """Extract base species (genus + species, lowercased) from a scientific name.

    Returns None for missing/empty names or names with fewer than two parts.
    Does not apply any countability filter — use ``is_countable`` for that.
    """
    if pd.isna(sci_name) or not str(sci_name).strip():
        return None
    parts = str(sci_name).strip().split()
    if len(parts) < 2:
        return None
    return f"{parts[0]} {parts[1]}".lower()


def is_countable(sci_name, common_name):
    """Return True if a species entry is countable (not a spuh, hybrid, domestic, or slash).

    Mirrors the exclusion rules used by ``countable_species_vectorized``:
    - spuh: scientific name contains " sp." or ends with " sp"
    - hybrid: scientific name contains " x " or common name contains "(hybrid)"
    - domestic: common name contains "Domestic" or "(Domestic type)"
    - species-level slash: second word of scientific name contains "/"
    - too short: scientific name has fewer than two words

    Args:
        sci_name: Scientific name string (may be None/NaN/empty).
        common_name: Common name string (may be None/NaN/empty).

    Returns:
        True if the entry should be counted as a species, False otherwise.
    """
    sci = (str(sci_name) if not pd.isna(sci_name) else "").strip()
    common = (str(common_name) if not pd.isna(common_name) else "").strip()
    if not sci:
        return False
    if " sp." in sci or sci.lower().endswith(" sp"):
        return False
    if " x " in sci or "(hybrid)" in common.lower():
        return False
    if "Domestic" in common or "(Domestic type)" in common:
        return False
    parts = sci.split()
    if len(parts) < 2:
        return False
    if "/" in parts[1]:
        return False
    return True


# ---------------------------------------------------------------------------
# Higher-level functions
# ---------------------------------------------------------------------------

def base_species_for_lifer(sci_name):
    """Extract base species (genus + species, lowercased) from a scientific name.

    Convenience wrapper around ``base_species_name`` — identical behaviour.
    Kept for API stability; callers may use either name.
    """
    return base_species_name(sci_name)


def countable_species_vectorized(df):
    """Vectorized species count: exclude spuhs, slashes, hybrids, domestic; roll up subspecies.

    Returns a Series of base species names (genus + species, lowercased) with NaN
    for non-countable rows.  Exclusion rules match ``is_countable``.
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
