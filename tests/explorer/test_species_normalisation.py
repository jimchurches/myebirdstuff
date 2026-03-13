import pandas as pd
import pytest

try:
    from notebooks.personal_ebird_explorer import _countable_species_vectorized
except (FileNotFoundError, ImportError):
    _countable_species_vectorized = None

pytestmark = pytest.mark.skipif(
    _countable_species_vectorized is None,
    reason="Notebook import requires local eBird data file",
)


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

    base = _countable_species_vectorized(df)

    # First two rows are kept and share the same base (genus + species)
    assert base.iloc[0] == "anas gracilis"
    assert base.iloc[1] == "anas gracilis"

    # Spuh, hybrid, slash, and domestic all excluded (NaN in result)
    assert base.iloc[2] is pd.NA or pd.isna(base.iloc[2])
    assert base.iloc[3] is pd.NA or pd.isna(base.iloc[3])
    assert base.iloc[4] is pd.NA or pd.isna(base.iloc[4])
    assert base.iloc[5] is pd.NA or pd.isna(base.iloc[5])

