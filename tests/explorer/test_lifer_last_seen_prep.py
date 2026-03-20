"""Tests for personal_ebird_explorer.lifer_last_seen_prep (refs #68)."""

import pandas as pd

from personal_ebird_explorer.lifer_last_seen_prep import prepare_lifer_last_seen
from personal_ebird_explorer.species_logic import base_species_for_lifer


def _tiny_df():
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2020-01-01", "2020-06-01", "2021-01-01"], utc=False
            ),
            "Date": pd.to_datetime(["2020-01-01", "2020-06-01", "2021-01-01"], utc=False),
            "Scientific Name": ["Turdus migratorius", "Turdus migratorius", "Anas superciliosa"],
            "Location ID": ["A", "B", "C"],
        }
    )


def test_prepare_lifer_last_seen_first_last_by_base():
    prep = prepare_lifer_last_seen(_tiny_df(), base_species_fn=base_species_for_lifer)
    base = base_species_for_lifer("Turdus migratorius")
    assert prep.true_lifer_locations[base] == "A"
    assert prep.true_last_seen_locations[base] == "B"
    assert prep.true_lifer_locations_taxon["turdus migratorius"] == "A"
    assert prep.true_last_seen_locations_taxon["turdus migratorius"] == "B"
    assert len(prep.lifer_lookup_df) == 3
