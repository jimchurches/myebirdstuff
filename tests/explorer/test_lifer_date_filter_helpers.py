"""Tests for lifer / last-seen date-filter helpers."""

import pandas as pd
import pytest

from explorer.core.lifer_last_seen_prep import (
    observation_date_within_filter,
    prepare_lifer_last_seen,
    subset_lifer_lookup_for_species,
)
from explorer.core.species_logic import base_species_for_lifer


@pytest.mark.parametrize(
    ("observation_date", "expected"),
    [
        (pd.Timestamp("2021-01-01"), True),
        (pd.Timestamp("2021-12-31"), True),
        (pd.Timestamp("2020-12-31"), False),
        (pd.Timestamp("2022-01-01"), False),
        (pd.NaT, False),
        ("not-a-date", False),
    ],
)
def test_observation_date_within_filter_inclusive_bounds(
    observation_date,
    expected,
):
    assert observation_date_within_filter(
        observation_date,
        filter_start_date="2021-01-01",
        filter_end_date="2021-12-31",
    ) is expected


def test_subset_lifer_lookup_for_species_uses_taxon_for_subspecies():
    df = pd.DataFrame(
        {
            "Submission ID": ["S0", "S1", "S2"],
            "Date": [
                pd.Timestamp("2023-01-01"),
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-06-01"),
            ],
            "datetime": [
                pd.Timestamp("2023-01-01 08:00"),
                pd.Timestamp("2024-01-01 08:00"),
                pd.Timestamp("2024-06-01 08:00"),
            ],
            "Location ID": ["L0", "L1", "L2"],
            "Scientific Name": [
                "Anas gracilis",
                "Anas gracilis rogersi",
                "Anas gracilis rogersi",
            ],
            "Common Name": ["Grey Teal", "Grey Teal (rogersi)", "Grey Teal (rogersi)"],
        }
    )
    prep = prepare_lifer_last_seen(df, base_species_fn=base_species_for_lifer)
    subset = subset_lifer_lookup_for_species(
        prep.lifer_lookup_df,
        "Anas gracilis rogersi",
        base_species_for_lifer,
    )
    assert len(subset) == 2
    assert subset["Location ID"].tolist() == ["L1", "L2"]
    assert subset["Scientific Name"].unique().tolist() == ["Anas gracilis rogersi"]
