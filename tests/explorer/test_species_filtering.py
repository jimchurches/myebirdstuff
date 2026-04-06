"""Tests for species filtering logic (explorer.core.species_logic.filter_species)."""

import pandas as pd

from explorer.core.species_logic import filter_species


def test_filter_species_prefix_and_subspecies_but_not_species_level_slash():
    df = pd.DataFrame(
        {
            "Scientific Name": [
                "Anas gracilis",
                "Anas gracilis rogersi",
                "Anas gracilis/castanea",  # species-level slash
            ],
            "Common Name": [
                "Grey Teal",
                "Grey Teal (rogersi)",
                "Grey Teal / Chestnut Teal",
            ],
        }
    )

    out = filter_species(df, "anas gracilis")

    # Should include species + subspecies, but not the species-level slash row
    assert len(out) == 2
    assert set(out["Scientific Name"]) == {"Anas gracilis", "Anas gracilis rogersi"}


def test_filter_species_exact_slash_when_requested():
    df = pd.DataFrame(
        {
            "Scientific Name": ["Anas gracilis/castanea", "Anas gracilis"],
            "Common Name": ["Grey Teal / Chestnut Teal", "Grey Teal"],
        }
    )

    out = filter_species(df, "anas gracilis/castanea")

    assert len(out) == 1
    assert out.iloc[0]["Scientific Name"] == "Anas gracilis/castanea"


def test_filter_species_no_matches_returns_empty():
    df = pd.DataFrame(
        {
            "Scientific Name": ["Anas gracilis", "Anas castanea"],
            "Common Name": ["Grey Teal", "Chestnut Teal"],
        }
    )

    out = filter_species(df, "anas platyrhynchos")  # species not present

    assert out.empty


def test_filter_species_handles_missing_scientific_name():
    df = pd.DataFrame(
        {
            "Scientific Name": ["Anas gracilis", None],
            "Common Name": ["Grey Teal", "Unknown duck"],
        }
    )

    out = filter_species(df, "anas gracilis")

    # Only the non-null match should be returned
    assert len(out) == 1
    assert out.iloc[0]["Scientific Name"] == "Anas gracilis"


def test_filter_species_case_insensitive():
    df = pd.DataFrame(
        {
            "Scientific Name": ["Anas Gracilis", "anas gracilis"],
            "Common Name": ["Grey Teal", "Grey Teal"],
        }
    )

    out = filter_species(df, "Anas Gracilis")

    assert len(out) == 2
