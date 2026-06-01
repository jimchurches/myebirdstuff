"""Tests for explorer.core.species_link_urls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from explorer.core.species_link_urls import species_banner_url


def test_species_banner_url_empty_base_returns_none():
    assert (
        species_banner_url(
            base_species="",
            taxonomy_locale="en_AU",
            display_name="Test Bird",
            species_url_fn=lambda _: "https://ebird.org/species/x",
        )
        is None
    )


@patch("explorer.core.species_link_urls.load_taxonomy_bundle")
def test_species_banner_url_resolves_via_taxonomy_base_to_code(mock_load: MagicMock):
    mock_load.return_value = MagicMock(
        species_rows=pd.DataFrame(
            {
                "base_species": ["sturnus vulgaris"],
                "species_code": ["eursta"],
                "common_name": ["European Starling"],
            }
        )
    )
    url = species_banner_url(
        base_species="sturnus vulgaris",
        taxonomy_locale="en_US",
        display_name="Common Starling",
        species_url_fn=lambda _: None,
    )
    assert url == "https://ebird.org/species/eursta"
    mock_load.assert_called_once_with("en_US")


@patch("explorer.core.species_link_urls.load_taxonomy_bundle")
def test_species_banner_url_falls_back_to_common_name_fn(mock_load: MagicMock):
    mock_load.return_value = MagicMock(
        species_rows=pd.DataFrame(
            {
                "base_species": ["other sp"],
                "species_code": [""],
                "common_name": ["Other"],
            }
        )
    )
    url = species_banner_url(
        base_species="unknownus species",
        taxonomy_locale="en_AU",
        display_name="Mystery Bird",
        species_url_fn=lambda n: "https://ebird.org/species/fallback"
        if n == "Mystery Bird"
        else None,
    )
    assert url == "https://ebird.org/species/fallback"
