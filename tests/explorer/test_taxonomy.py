"""Unit tests for explorer.core.taxonomy (eBird species links, refs #56)."""

import csv
import io
from unittest.mock import patch, MagicMock

import pytest

from explorer.core import taxonomy


def _make_csv(rows, fieldnames=("common_name", "species_code", "category")):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _reset_taxonomy_after_each():
    """Reset taxonomy module state after each test so tests don't affect each other."""
    yield
    taxonomy._common_to_code = None


def test_load_taxonomy_success_builds_lookup():
    """When API returns valid CSV with species rows, get_species_url and get_species_lifelist_url return URLs."""
    csv_data = _make_csv([
        {"common_name": "Sulphur-crested Cockatoo", "species_code": "succoc", "category": "species"},
        {"common_name": "Grey Teal", "species_code": "grtea", "category": "species"},
        {"common_name": "Some spuh", "species_code": "spuh1", "category": "spuh"},
    ])
    resp = MagicMock()
    resp.read.return_value = csv_data.encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("explorer.core.taxonomy.urlopen", return_value=cm) as m_urlopen:
        ok = taxonomy.load_taxonomy()
    assert ok is True
    m_urlopen.assert_called_once()
    call_args = m_urlopen.call_args[0][0]
    assert call_args.full_url == "https://api.ebird.org/v2/ref/taxonomy/ebird"
    assert taxonomy.get_species_url("Sulphur-crested Cockatoo") == "https://ebird.org/species/succoc"
    assert taxonomy.get_species_url("Grey Teal") == "https://ebird.org/species/grtea"
    assert taxonomy.get_species_lifelist_url("Grey Teal") == "https://ebird.org/lifelist?spp=grtea"
    assert taxonomy.get_species_url("Some spuh") is None


def test_load_taxonomy_with_locale_requests_url_with_param():
    """When locale is passed, the request URL includes locale query parameter."""
    csv_data = _make_csv([{"common_name": "Grey Teal", "species_code": "grtea", "category": "species"}])
    resp = MagicMock()
    resp.read.return_value = csv_data.encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("explorer.core.taxonomy.urlopen", return_value=cm) as m_urlopen:
        taxonomy.load_taxonomy(locale="en_AU")
    call_args = m_urlopen.call_args[0][0]
    assert "locale=en_AU" in call_args.full_url
    assert taxonomy.get_species_url("Grey Teal") == "https://ebird.org/species/grtea"


def test_load_taxonomy_network_failure_returns_false():
    """When the API is unavailable, load_taxonomy returns False and lookups return None."""
    from urllib.error import URLError
    with patch("explorer.core.taxonomy.urlopen", side_effect=URLError("offline")):
        ok = taxonomy.load_taxonomy()
    assert ok is False
    assert taxonomy.get_species_url("Grey Teal") is None
    assert taxonomy.get_species_lifelist_url("Grey Teal") is None


def test_get_species_url_none_before_load():
    """Before any load, get_species_url returns None."""
    taxonomy._common_to_code = None
    assert taxonomy.get_species_url("Grey Teal") is None


def test_get_species_url_empty_name_returns_none():
    """Empty or blank common name returns None."""
    taxonomy._common_to_code = {"Grey Teal": "grtea"}
    try:
        assert taxonomy.get_species_url("") is None
        assert taxonomy.get_species_lifelist_url("  ") is None
    finally:
        taxonomy._common_to_code = None


def test_exact_match_required_after_locale_load():
    """With locale set, API returns names that match export; exact match is sufficient."""
    # Simulate API returning en_AU names (Grey Teal, Willie Wagtail, Common Starling)
    taxonomy._common_to_code = {
        "Grey Teal": "grtea",
        "Willie Wagtail": "wilwag",
        "Common Starling": "eursta",
    }
    try:
        assert taxonomy.get_species_url("Grey Teal") == "https://ebird.org/species/grtea"
        assert taxonomy.get_species_url("Willie Wagtail") == "https://ebird.org/species/wilwag"
        assert taxonomy.get_species_url("Common Starling") == "https://ebird.org/species/eursta"
        assert taxonomy.get_species_url("Gray Teal") is None  # US spelling not in en_AU lookup
    finally:
        taxonomy._common_to_code = None


def test_get_species_and_lifelist_urls_single_lookup():
    """get_species_and_lifelist_urls returns both URLs from one lookup."""
    taxonomy._common_to_code = {"Grey Teal": "grtea"}
    try:
        species_url, lifelist_url = taxonomy.get_species_and_lifelist_urls("Grey Teal")
        assert species_url == "https://ebird.org/species/grtea"
        assert lifelist_url == "https://ebird.org/lifelist?spp=grtea"
        assert taxonomy.get_species_and_lifelist_urls("Unknown") == (None, None)
    finally:
        taxonomy._common_to_code = None


def test_subspecies_links_to_main_species():
    """Subspecies common name (trailing ' (X)') falls back to main species for URL."""
    taxonomy._common_to_code = {"Eastern Barn Owl": "easbar1"}
    try:
        assert taxonomy.get_species_url("Eastern Barn Owl (Eastern)") == "https://ebird.org/species/easbar1"
        assert taxonomy.get_species_lifelist_url("Eastern Barn Owl (Eastern)") == "https://ebird.org/lifelist?spp=easbar1"
        assert taxonomy.get_species_url("Eastern Barn Owl") == "https://ebird.org/species/easbar1"
    finally:
        taxonomy._common_to_code = None


def test_hyphen_vs_space_locale_mismatch_jacky_winter():
    """Spaced export name matches hyphenated taxonomy row (e.g. en_US vs en_AU) (#156)."""
    taxonomy._common_to_code = {"Jacky-winter": "jacwin1"}
    try:
        assert taxonomy.get_species_url("Jacky Winter") == "https://ebird.org/species/jacwin1"
        assert taxonomy.get_species_lifelist_url("Jacky Winter") == "https://ebird.org/lifelist?spp=jacwin1"
    finally:
        taxonomy._common_to_code = None


def test_hyphen_vs_space_reverse_lookup():
    """Hyphenated query matches spaced taxonomy row."""
    taxonomy._common_to_code = {"Jacky Winter": "jacwin1"}
    try:
        assert taxonomy.get_species_url("Jacky-winter") == "https://ebird.org/species/jacwin1"
    finally:
        taxonomy._common_to_code = None
