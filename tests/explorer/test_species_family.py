"""Focused tests for explorer.core.species_family."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from explorer.core import species_family
from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT


@pytest.fixture(autouse=True)
def _clear_species_family_cache():
    """Clear memoized family map cache between tests."""
    species_family._base_species_family_items_cached.cache_clear()
    yield
    species_family._base_species_family_items_cached.cache_clear()


def _mock_urlopen_payload(payload: str) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = payload.encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_load_taxonomy_species_rows_filters_and_parses_species_rows():
    csv_data = """CATEGORY,SCIENTIFIC_NAME,COMMON_NAME,SPECIES_CODE,TAXON_ORDER
species,Corvus corax,Common Raven,comrav,100.5
species,Anas gracilis,Grey Teal,grtea,200
spuh,Corvus sp.,Crow sp.,corsp,300
species,Missing Order Bird,No Order,misord,
species,No Common, ,nocomm,400
"""
    with patch(
        "explorer.core.species_family.urlopen",
        return_value=_mock_urlopen_payload(csv_data),
    ) as m_urlopen:
        out = species_family.load_taxonomy_species_rows("en_AU")

    req = m_urlopen.call_args[0][0]
    assert "locale=en_AU" in req.full_url
    assert list(out["common_name"]) == ["Common Raven", "Grey Teal"]
    assert list(out["base_species"]) == ["corvus corax", "anas gracilis"]
    assert list(out["taxon_order"]) == [100.5, 200.0]


def test_load_taxonomy_groups_parses_bounds_and_skips_invalid_entries():
    payload = json.dumps(
        [
            {
                "groupName": "Ducks",
                "groupOrder": 2,
                "taxonOrderBounds": [[10, 20], ["x", 30], [31], [40, 50]],
            },
            {"groupName": "Ravens", "groupOrder": 3, "taxonOrderBounds": []},
        ]
    )
    with patch(
        "explorer.core.species_family.urlopen",
        return_value=_mock_urlopen_payload(payload),
    ) as m_urlopen:
        out = species_family.load_taxonomy_groups("en_AU")

    req = m_urlopen.call_args[0][0]
    assert "locale=en_AU" in req.full_url
    assert out[0]["group_name"] == "Ducks"
    assert out[0]["bounds"] == [(10.0, 20.0), (40.0, 50.0)]
    assert out[1]["bounds"] == []


@pytest.mark.parametrize(
    ("taxon_order", "expected"),
    [
        (10.0, ("Ducks", 5)),
        (20.0, ("Ducks", 5)),
        (50.5, ("Raptors", 7)),
        (9.9, ("Unmapped", 999999)),
    ],
)
def test_assign_group_for_taxon_order_boundaries_and_unmapped(taxon_order, expected):
    groups = [
        {"group_name": "Ducks", "group_order": 5, "bounds": [(10.0, 20.0)]},
        {"group_name": "Raptors", "group_order": 7, "bounds": [(50.0, 60.0)]},
    ]
    assert species_family.assign_group_for_taxon_order(taxon_order, groups) == expected


def test_build_base_species_to_family_map_uses_default_locale_and_returns_mapping():
    tax = pd.DataFrame(
        [
            {"base_species": "corvus corax", "taxon_order": 11.0},
            {"base_species": "anas gracilis", "taxon_order": 51.0},
        ]
    )
    groups = [
        {"group_name": "Corvids", "group_order": 1, "bounds": [(10.0, 20.0)]},
        {"group_name": "Ducks", "group_order": 2, "bounds": [(50.0, 60.0)]},
    ]
    with patch(
        "explorer.core.species_family.load_taxonomy_species_rows",
        return_value=tax,
    ) as m_tax, patch(
        "explorer.core.species_family.load_taxonomy_groups",
        return_value=groups,
    ) as m_groups:
        out = species_family.build_base_species_to_family_map("")

    m_tax.assert_called_once_with(TAXONOMY_LOCALE_DEFAULT)
    m_groups.assert_called_once_with(TAXONOMY_LOCALE_DEFAULT)
    assert out == {"anas gracilis": "Ducks", "corvus corax": "Corvids"}


def test_build_base_species_to_family_map_returns_empty_on_loader_error():
    with patch(
        "explorer.core.species_family.load_taxonomy_species_rows",
        side_effect=RuntimeError("offline"),
    ):
        assert species_family.build_base_species_to_family_map("en_AU") == {}
