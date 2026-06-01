"""Tests for shared eBird taxonomy bundle (single fetch per locale)."""

import csv
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from explorer.core import species_family, taxonomy
from explorer.core.taxonomy_bundle import clear_taxonomy_bundle_cache, load_taxonomy_bundle


def _make_csv(rows, fieldnames=("common_name", "species_code", "category", "scientific_name", "taxon_order")):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def _mock_urlopen_responses(csv_bodies: list[str], groups_body: str = "[]"):
    """Build urlopen side_effect: taxonomy CSV URL(s) then species-group JSON."""
    ctxs: list[MagicMock] = []
    for body in csv_bodies:
        r = MagicMock()
        r.read.return_value = body.encode("utf-8")
        c = MagicMock()
        c.__enter__ = MagicMock(return_value=r)
        c.__exit__ = MagicMock(return_value=False)
        ctxs.append(c)
    gr = MagicMock()
    gr.read.return_value = groups_body.encode("utf-8")
    gc = MagicMock()
    gc.__enter__ = MagicMock(return_value=gr)
    gc.__exit__ = MagicMock(return_value=False)
    ctxs.append(gc)
    return ctxs


@pytest.fixture(autouse=True)
def _clear_bundle_cache():
    yield
    taxonomy._common_to_code = None
    clear_taxonomy_bundle_cache()


def test_load_taxonomy_bundle_fetches_csv_and_groups_once_per_locale():
    csv_data = _make_csv(
        [
            {
                "common_name": "Grey Teal",
                "species_code": "grtea",
                "category": "species",
                "scientific_name": "Anas gracilis",
                "taxon_order": "100",
            }
        ]
    )
    ctxs = _mock_urlopen_responses([csv_data, csv_data])
    with patch("explorer.core.taxonomy_bundle.urlopen", side_effect=ctxs) as m_urlopen:
        b1 = load_taxonomy_bundle("en_AU")
        b2 = load_taxonomy_bundle("en_AU")
    assert m_urlopen.call_count == 3
    assert b1 is b2
    assert len(b1.species_rows) == 1
    assert b1.common_to_code["Grey Teal"] == "grtea"


def test_species_family_and_load_taxonomy_share_one_csv_fetch():
    csv_data = _make_csv(
        [
            {
                "common_name": "Grey Teal",
                "species_code": "grtea",
                "category": "species",
                "scientific_name": "Anas gracilis",
                "taxon_order": "100",
            }
        ]
    )
    ctxs = _mock_urlopen_responses([csv_data, csv_data])
    with patch("explorer.core.taxonomy_bundle.urlopen", side_effect=ctxs) as m_urlopen:
        assert taxonomy.load_taxonomy(locale="en_AU") is True
        rows = species_family.load_taxonomy_species_rows("en_AU")
    assert m_urlopen.call_count == 3
    assert len(rows) == 1
    assert taxonomy.get_species_url("Grey Teal") == "https://ebird.org/species/grtea"


def test_en_au_merges_us_csv_without_extra_species_row_fetch():
    au_csv = _make_csv(
        [
            {
                "common_name": "Grey Ternlet",
                "species_code": "grynod1",
                "category": "species",
                "scientific_name": "Procelerna cerulea",
                "taxon_order": "200",
            }
        ]
    )
    us_csv = _make_csv(
        [
            {
                "common_name": "Gray Noddy",
                "species_code": "grynod1",
                "category": "species",
                "scientific_name": "Procelerna cerulea",
                "taxon_order": "200",
            }
        ]
    )
    ctxs = _mock_urlopen_responses([au_csv, us_csv])
    with patch("explorer.core.taxonomy_bundle.urlopen", side_effect=ctxs) as m_urlopen:
        bundle = load_taxonomy_bundle("en_AU")
    assert m_urlopen.call_count == 3
    assert bundle.common_to_code["Gray Noddy"] == "grynod1"
    assert bundle.common_to_code["Grey Ternlet"] == "grynod1"


def test_parse_taxonomy_csv_retains_extinct_fields():
    csv_data = _make_csv(
        [
            {
                "common_name": "Living Bird",
                "species_code": "livbrd",
                "category": "species",
                "scientific_name": "Aves vivus",
                "taxon_order": "100",
                "extinct": "0",
                "extinct_year": "",
            },
            {
                "common_name": "Extinct Bird",
                "species_code": "extbrd",
                "category": "species",
                "scientific_name": "Aves extinctus",
                "taxon_order": "101",
                "extinct": "1",
                "extinct_year": "1900",
            },
        ],
        fieldnames=(
            "common_name",
            "species_code",
            "category",
            "scientific_name",
            "taxon_order",
            "extinct",
            "extinct_year",
        ),
    )
    ctxs = _mock_urlopen_responses([csv_data])
    with patch("explorer.core.taxonomy_bundle.urlopen", side_effect=ctxs):
        bundle = load_taxonomy_bundle("en_US")
    rows = bundle.species_rows.sort_values("taxon_order").reset_index(drop=True)
    assert list(rows["is_extinct"]) == [False, True]
    assert rows.loc[1, "extinct_year"] == "1900"


def test_taxonomy_row_is_extinct_from_year_when_flag_unset():
    from explorer.core.taxonomy_bundle import _taxonomy_row_is_extinct

    assert _taxonomy_row_is_extinct("0", "1900") is True
    assert _taxonomy_row_is_extinct("", "1938") is True
    assert _taxonomy_row_is_extinct("0", "") is False
    assert _taxonomy_row_is_extinct("1", "") is True


def test_parse_taxonomy_csv_marks_extinct_from_extinct_year_only():
    csv_data = _make_csv(
        [
            {
                "common_name": "Year Only Extinct",
                "species_code": "yrext",
                "category": "species",
                "scientific_name": "Aves antiquus",
                "taxon_order": "102",
                "extinct": "0",
                "extinct_year": "1938",
            },
        ],
        fieldnames=(
            "common_name",
            "species_code",
            "category",
            "scientific_name",
            "taxon_order",
            "extinct",
            "extinct_year",
        ),
    )
    ctxs = _mock_urlopen_responses([csv_data])
    with patch("explorer.core.taxonomy_bundle.urlopen", side_effect=ctxs):
        bundle = load_taxonomy_bundle("en_US")
    assert bool(bundle.species_rows.iloc[0]["is_extinct"]) is True
