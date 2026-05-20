"""Tests for lifer / last-seen date-filter helpers."""

import pandas as pd

from explorer.core.lifer_last_seen_prep import (
    observation_date_within_filter,
    prepare_lifer_last_seen,
    subset_lifer_lookup_for_species,
)
from explorer.core.species_logic import base_species_for_lifer


def test_observation_date_within_filter_inclusive_bounds():
    assert observation_date_within_filter(
        pd.Timestamp("2021-06-15"),
        filter_start_date="2021-01-01",
        filter_end_date="2021-12-31",
    )
    assert not observation_date_within_filter(
        pd.Timestamp("2020-12-31"),
        filter_start_date="2021-01-01",
        filter_end_date="2021-12-31",
    )


def test_subset_lifer_lookup_for_species_uses_taxon_for_subspecies():
    df = pd.DataFrame(
        {
            "Submission ID": ["S1", "S2"],
            "Date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-01")],
            "datetime": [
                pd.Timestamp("2024-01-01 08:00"),
                pd.Timestamp("2024-06-01 08:00"),
            ],
            "Location ID": ["L1", "L2"],
            "Scientific Name": ["Anas gracilis rogersi", "Anas gracilis rogersi"],
            "Common Name": ["Grey Teal", "Grey Teal"],
        }
    )
    prep = prepare_lifer_last_seen(df, base_species_fn=base_species_for_lifer)
    subset = subset_lifer_lookup_for_species(
        prep.lifer_lookup_df,
        "Anas gracilis rogersi",
        base_species_for_lifer,
    )
    assert len(subset) == 2
    assert subset.iloc[0]["Location ID"] == "L1"
