import pandas as pd

from notebooks.personal_ebird_explorer import filter_species


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

