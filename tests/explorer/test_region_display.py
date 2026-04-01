"""Tests for explorer.core.region_display (country/state name display, refs #43)."""

import pandas as pd
import pytest

from explorer.core.region_display import country_for_display, state_for_display


def test_country_for_display_empty_and_none():
    """Empty, None, NaN return empty string."""
    assert country_for_display(None) == ""
    assert country_for_display("") == ""
    assert country_for_display("   ") == ""
    assert country_for_display(pd.NA) == ""
    assert country_for_display(float("nan")) == ""


def test_state_for_display_empty_state():
    """Empty/None/NaN state returns empty string regardless of country."""
    assert state_for_display("AU", None) == ""
    assert state_for_display("AU", "") == ""
    assert state_for_display("AU", "   ") == ""
    assert state_for_display("AU", float("nan")) == ""


def test_country_for_display_known_code():
    """Known ISO code returns country name (requires pycountry)."""
    pytest.importorskip("pycountry")
    assert country_for_display("AU") == "Australia"
    assert country_for_display("au") == "Australia"
    assert country_for_display("IN") == "India"


def test_country_for_display_unknown_code():
    """Unknown code returns code as-is."""
    pytest.importorskip("pycountry")
    assert country_for_display("XX") == "XX"
    assert country_for_display("ZZ") == "ZZ"


def test_state_for_display_known_code():
    """Known subdivision returns name (requires pycountry)."""
    pytest.importorskip("pycountry")
    assert state_for_display("AU", "NSW") == "New South Wales"
    assert state_for_display("AU", "WA") == "Western Australia"
    assert state_for_display("IN", "GA") == "Goa"


def test_state_for_display_unknown_code():
    """Unknown subdivision returns state code as-is."""
    pytest.importorskip("pycountry")
    assert state_for_display("AU", "X9") == "X9"
    assert state_for_display("XX", "YY") == "YY"


def test_state_for_display_no_country_returns_state_code():
    """Missing country returns state code (no lookup)."""
    pytest.importorskip("pycountry")
    assert state_for_display("", "NSW") == "NSW"
    assert state_for_display(None, "NSW") == "NSW"
