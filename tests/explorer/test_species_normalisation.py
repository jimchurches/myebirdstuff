"""Tests for species normalisation (explorer.core.species_logic)."""

import pandas as pd

from explorer.core.species_logic import (
    base_species_name,
    is_countable,
    countable_species_vectorized,
    base_species_for_lifer,
)


# ---------------------------------------------------------------------------
# base_species_name
# ---------------------------------------------------------------------------

def test_base_species_name_normal():
    assert base_species_name("Anas gracilis") == "anas gracilis"


def test_base_species_name_subspecies():
    assert base_species_name("Anas gracilis rogersi") == "anas gracilis"


def test_base_species_name_none():
    assert base_species_name(None) is None


def test_base_species_name_empty_string():
    assert base_species_name("") is None


def test_base_species_name_whitespace_only():
    assert base_species_name("   ") is None


def test_base_species_name_single_word():
    assert base_species_name("Anas") is None


def test_base_species_name_nan():
    assert base_species_name(float("nan")) is None


def test_base_species_name_spuh_extracts_without_filtering():
    """base_species_name does not filter — it extracts from anything with 2+ words."""
    assert base_species_name("Anas sp.") == "anas sp."


def test_base_species_name_hybrid_extracts_first_two_words():
    assert base_species_name("Anas castanea x Anas gracilis") == "anas castanea"


# ---------------------------------------------------------------------------
# is_countable
# ---------------------------------------------------------------------------

def test_is_countable_normal_species():
    assert is_countable("Anas gracilis", "Grey Teal") is True


def test_is_countable_subspecies():
    assert is_countable("Anas gracilis rogersi", "Grey Teal (rogersi)") is True


def test_is_countable_excludes_spuh():
    assert is_countable("Anas sp.", "Duck sp.") is False


def test_is_countable_excludes_spuh_no_dot():
    assert is_countable("Anas sp", "Duck sp") is False


def test_is_countable_excludes_hybrid_scientific():
    assert is_countable("Anas castanea x Anas gracilis", "Hybrid duck") is False


def test_is_countable_excludes_hybrid_common():
    assert is_countable("Anas gracilis castanea", "Some duck (hybrid)") is False


def test_is_countable_excludes_domestic():
    assert is_countable("Columba livia", "Domestic Pigeon") is False


def test_is_countable_excludes_domestic_type():
    assert is_countable("Columba livia", "Rock Pigeon (Domestic type)") is False


def test_is_countable_excludes_slash():
    assert is_countable("Anas gracilis/castanea", "Teal slash") is False


def test_is_countable_excludes_single_word():
    assert is_countable("Anas", "Something") is False


def test_is_countable_excludes_empty():
    assert is_countable("", "Unknown") is False


def test_is_countable_excludes_none():
    assert is_countable(None, "Unknown") is False


def test_is_countable_excludes_nan():
    assert is_countable(float("nan"), "Unknown") is False


# ---------------------------------------------------------------------------
# is_countable agrees with countable_species_vectorized
# ---------------------------------------------------------------------------

def test_is_countable_agrees_with_vectorized():
    """Scalar is_countable must agree with vectorized for every test case."""
    rows = [
        ("Anas gracilis", "Grey Teal"),
        ("Anas gracilis rogersi", "Grey Teal (rogersi)"),
        ("Anas sp.", "Duck sp."),
        ("Anas castanea x Anas gracilis", "Hybrid duck"),
        ("Anas gracilis/castanea", "Teal slash"),
        ("Columba livia", "Domestic Pigeon"),
        ("Columba livia", "Rock Pigeon (Domestic type)"),
        ("Anas gracilis castanea", "Some duck (hybrid)"),
        ("Anas", "Something"),
    ]
    df = pd.DataFrame(rows, columns=["Scientific Name", "Common Name"])
    vec = countable_species_vectorized(df)
    for i, (sci, common) in enumerate(rows):
        scalar = is_countable(sci, common)
        vectorized_countable = pd.notna(vec.iloc[i])
        assert scalar == vectorized_countable, (
            f"Row {i} ({sci!r}, {common!r}): is_countable={scalar}, "
            f"vectorized={'countable' if vectorized_countable else 'excluded'}"
        )


# ---------------------------------------------------------------------------
# base_species_for_lifer (delegates to base_species_name)
# ---------------------------------------------------------------------------

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
    assert base_species_for_lifer(float("nan")) is None


def test_base_species_for_lifer_does_not_filter_spuh():
    """Unlike countable species, base_species_for_lifer extracts from spuhs without filtering."""
    assert base_species_for_lifer("Anas sp.") == "anas sp."


def test_base_species_for_lifer_does_not_filter_hybrid():
    """Extracts base from hybrid name (first two words) without filtering."""
    assert base_species_for_lifer("Anas castanea x Anas gracilis") == "anas castanea"


def test_base_species_for_lifer_matches_base_species_name():
    """base_species_for_lifer is now a wrapper — should match exactly."""
    cases = ["Anas gracilis", "Anas sp.", None, "", "Anas", float("nan")]
    for case in cases:
        assert base_species_for_lifer(case) == base_species_name(case), f"Mismatch for {case!r}"


# ---------------------------------------------------------------------------
# countable_species_vectorized
# ---------------------------------------------------------------------------

def test_countable_species_vectorized_filters_spuh_hybrid_domestic_and_slash():
    df = pd.DataFrame(
        {
            "Scientific Name": [
                "Anas gracilis",
                "Anas gracilis rogersi",
                "Anas sp.",
                "Anas castanea x Anas gracilis",
                "Anas castanea/Anas gracilis",
                "Corvus domesticus",
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

    assert base.iloc[0] == "anas gracilis"
    assert base.iloc[1] == "anas gracilis"
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
