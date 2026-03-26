"""Tests for personal_ebird_explorer.lifer_last_seen_prep (refs #68)."""

import pandas as pd

from personal_ebird_explorer.lifer_last_seen_prep import aggregate_lifer_sites, prepare_lifer_last_seen
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


def test_aggregate_lifer_sites_two_locations():
    prep = prepare_lifer_last_seen(_tiny_df(), base_species_fn=base_species_for_lifer)
    by_loc, n = aggregate_lifer_sites(
        prep.lifer_lookup_df,
        prep.true_lifer_locations,
        prep.true_lifer_locations_taxon,
    )
    assert n == 2
    assert set(by_loc.keys()) == {"A", "C"}
    assert len(by_loc["A"]) == 1
    assert len(by_loc["C"]) == 1


def test_prepare_lifer_last_seen_invariants_first_last_consistent():
    """Prepared lifer/last-seen location IDs must match min/max datetime per base/taxon."""
    prep = prepare_lifer_last_seen(_tiny_df(), base_species_fn=base_species_for_lifer)

    # Base species invariants.
    for base, lifer_lid in prep.true_lifer_locations.items():
        subset = prep.lifer_lookup_df[prep.lifer_lookup_df["_base"] == base].sort_values("datetime")
        assert not subset.empty
        assert subset.iloc[0]["Location ID"] == lifer_lid
        assert subset.iloc[-1]["Location ID"] == prep.true_last_seen_locations[base]

    # Taxon (scientific name) invariants.
    for taxon, lifer_lid in prep.true_lifer_locations_taxon.items():
        subset = prep.lifer_lookup_df[prep.lifer_lookup_df["_taxon"] == taxon].sort_values("datetime")
        assert not subset.empty
        assert subset.iloc[0]["Location ID"] == lifer_lid
        assert subset.iloc[-1]["Location ID"] == prep.true_last_seen_locations_taxon[taxon]


def test_aggregate_lifer_sites_invariants_dedupes_and_count_matches():
    """aggregate_lifer_sites must dedupe scientific names per location and report correct totals."""
    prep = prepare_lifer_last_seen(_tiny_df(), base_species_fn=base_species_for_lifer)
    by_loc, n_distinct = aggregate_lifer_sites(
        prep.lifer_lookup_df,
        prep.true_lifer_locations,
        prep.true_lifer_locations_taxon,
    )

    global_sci: set[str] = set()
    for _lid, entries in by_loc.items():
        sci_names = [e["scientific_name"] for e in entries]
        assert len(sci_names) == len(set(sci_names))  # no duplicates per location
        global_sci.update(sci_names)

    assert n_distinct == len(global_sci)
