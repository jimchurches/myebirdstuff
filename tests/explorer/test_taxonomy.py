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
    """When a non-en_US locale is passed, we fetch that locale and en_US, then merge."""
    csv_data = _make_csv([{"common_name": "Grey Teal", "species_code": "grtea", "category": "species"}])
    resp = MagicMock()
    resp.read.return_value = csv_data.encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("explorer.core.taxonomy.urlopen", return_value=cm) as m_urlopen:
        taxonomy.load_taxonomy(locale="en_AU")
    assert m_urlopen.call_count == 2
    urls = [c[0][0].full_url for c in m_urlopen.call_args_list]
    assert any("locale=en_AU" in u for u in urls)
    assert any("locale=en_US" in u for u in urls)
    assert taxonomy.get_species_url("Grey Teal") == "https://ebird.org/species/grtea"


def test_load_taxonomy_en_us_fetches_once():
    """en_US is the merge source; loading it directly only needs one request."""
    csv_data = _make_csv([{"common_name": "Gray Teal", "species_code": "gretea1", "category": "species"}])
    resp = MagicMock()
    resp.read.return_value = csv_data.encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("explorer.core.taxonomy.urlopen", return_value=cm) as m_urlopen:
        taxonomy.load_taxonomy(locale="en_US")
    assert m_urlopen.call_count == 1
    assert "locale=en_US" in m_urlopen.call_args[0][0].full_url


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


def test_merged_lookup_includes_en_us_alternate_spellings():
    """After en_AU + en_US merge, both regional labels for the same code resolve (e.g. Gray vs Grey Teal)."""
    taxonomy._common_to_code = {
        "Grey Teal": "gretea1",
        "Gray Teal": "gretea1",
        "Willie Wagtail": "wilwag1",
        "Common Starling": "eursta",
    }
    try:
        assert taxonomy.get_species_url("Grey Teal") == "https://ebird.org/species/gretea1"
        assert taxonomy.get_species_url("Gray Teal") == "https://ebird.org/species/gretea1"
        assert taxonomy.get_species_url("Willie Wagtail") == "https://ebird.org/species/wilwag1"
        assert taxonomy.get_species_url("Common Starling") == "https://ebird.org/species/eursta"
    finally:
        taxonomy._common_to_code = None


def test_load_taxonomy_en_au_merges_en_us_alternate_names():
    """regional + US names for the same species code both link (refs #201, e.g. Gray Noddy / Grey Ternlet)."""
    au_csv = _make_csv(
        [{"common_name": "Grey Ternlet", "species_code": "grynod1", "category": "species"}]
    )
    us_csv = _make_csv(
        [{"common_name": "Gray Noddy", "species_code": "grynod1", "category": "species"}]
    )
    ctxs = []
    for body in (au_csv, us_csv):
        r = MagicMock()
        r.read.return_value = body.encode("utf-8")
        c = MagicMock()
        c.__enter__ = MagicMock(return_value=r)
        c.__exit__ = MagicMock(return_value=False)
        ctxs.append(c)
    with patch("explorer.core.taxonomy.urlopen", side_effect=ctxs) as m_urlopen:
        ok = taxonomy.load_taxonomy(locale="en_AU")
    assert ok is True
    assert m_urlopen.call_count == 2
    assert taxonomy.get_species_url("Gray Noddy") == "https://ebird.org/species/grynod1"
    assert taxonomy.get_species_url("Grey Ternlet") == "https://ebird.org/species/grynod1"


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
    """Spaced name from UI/export resolves when the loaded taxonomy only has a hyphenated key.

    Mirrors locale skew: export wording can differ from the common-name column in the CSV
    loaded for URLs (hyphen vs space, and letter case after hyphens).
    """
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
