"""Tests for species normalisation (personal_ebird_explorer.species_logic)."""

import pandas as pd

from personal_ebird_explorer.species_logic import (
    countable_species_vectorized,
    base_species_for_lifer,
    _base_species_for_count,
)


# --- countable_species_vectorized ---

def test_countable_species_vectorized_filters_spuh_hybrid_domestic_and_slash():
    df = pd.DataFrame(
        {
            "Scientific Name": [
                "Anas gracilis",              # countable species
                "Anas gracilis rogersi",      # subspecies, should roll to base
                "Anas sp.",                   # spuh
                "Anas castanea x Anas gracilis",  # hybrid
                "Anas castanea/Anas gracilis",    # species-level slash
                "Corvus domesticus",          # domestic by name
            ],
            "Common Name": [
                "Grey Teal",
                "Grey Teal (rogersi)",
                "Duck sp.",
                "Hybrid duck",
                "Duck slash",
                "Domestic Duck",
            ],
        }
    )

    base = countable_species_vectorized(df)

    # First two rows are kept and share the same base (genus + species)
    assert base.iloc[0] == "anas gracilis"
    assert base.iloc[1] == "anas gracilis"

    # Spuh, hybrid, slash, and domestic all excluded (NaN in result)
    assert pd.isna(base.iloc[2])
    assert pd.isna(base.iloc[3])
    assert pd.isna(base.iloc[4])
    assert pd.isna(base.iloc[5])


def test_countable_species_vectorized_empty_dataframe():
    df = pd.DataFrame({"Scientific Name": [], "Common Name": []})
    base = countable_species_vectorized(df)
    assert base.empty


def test_countable_species_vectorized_single_word_scientific_name():
    df = pd.DataFrame(
        {"Scientific Name": ["Anas"], "Common Name": ["Something"]}
    )
    base = countable_species_vectorized(df)
    assert pd.isna(base.iloc[0])


def test_countable_species_vectorized_domestic_type_in_parentheses():
    df = pd.DataFrame(
        {
            "Scientific Name": ["Columba livia"],
            "Common Name": ["Rock Pigeon (Domestic type)"],
        }
    )
    base = countable_species_vectorized(df)
    assert pd.isna(base.iloc[0])


def test_countable_species_vectorized_hybrid_in_common_name():
    df = pd.DataFrame(
        {
            "Scientific Name": ["Anas gracilis castanea"],
            "Common Name": ["Some duck (hybrid)"],
        }
    )
    base = countable_species_vectorized(df)
    assert pd.isna(base.iloc[0])


# --- base_species_for_lifer ---

def test_base_species_for_lifer_normal():
    assert base_species_for_lifer("Anas gracilis") == "anas gracilis"


def test_base_species_for_lifer_subspecies():
    assert base_species_for_lifer("Anas gracilis rogersi") == "anas gracilis"


def test_base_species_for_lifer_none():
    assert base_species_for_lifer(None) is None


def test_base_species_for_lifer_empty_string():
    assert base_species_for_lifer("") is None


def test_base_species_for_lifer_whitespace_only():
    assert base_species_for_lifer("   ") is None


def test_base_species_for_lifer_single_word():
    assert base_species_for_lifer("Anas") is None


def test_base_species_for_lifer_nan():
    import math
    assert base_species_for_lifer(float("nan")) is None


def test_base_species_for_lifer_does_not_filter_spuh():
    """Unlike countable species, base_species_for_lifer extracts from spuhs without filtering."""
    assert base_species_for_lifer("Anas sp.") == "anas sp."


def test_base_species_for_lifer_does_not_filter_hybrid():
    """Extracts base from hybrid name (first two words) without filtering."""
    assert base_species_for_lifer("Anas castanea x Anas gracilis") == "anas castanea"


# --- _base_species_for_count ---

def test_base_species_for_count_normal():
    row = {"Scientific Name": "Anas gracilis", "Common Name": "Grey Teal"}
    assert _base_species_for_count(row) == "anas gracilis"


def test_base_species_for_count_excludes_spuh():
    row = {"Scientific Name": "Anas sp.", "Common Name": "Duck sp."}
    assert _base_species_for_count(row) is None


def test_base_species_for_count_excludes_hybrid():
    row = {"Scientific Name": "Anas castanea x Anas gracilis", "Common Name": "Hybrid"}
    assert _base_species_for_count(row) is None


def test_base_species_for_count_excludes_domestic():
    row = {"Scientific Name": "Columba livia", "Common Name": "Domestic Pigeon"}
    assert _base_species_for_count(row) is None


def test_base_species_for_count_excludes_slash():
    row = {"Scientific Name": "Anas gracilis/castanea", "Common Name": "Teal slash"}
    assert _base_species_for_count(row) is None


def test_base_species_for_count_empty_scientific_name():
    row = {"Scientific Name": "", "Common Name": "Unknown"}
    assert _base_species_for_count(row) is None


def test_base_species_for_count_none_scientific_name():
    row = {"Scientific Name": None, "Common Name": "Unknown"}
    assert _base_species_for_count(row) is None
