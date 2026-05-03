"""Tests for Go to GPS coordinate parsing (refs #199)."""

from __future__ import annotations

import pytest

from explorer.app.streamlit.app_go_to_gps_ui import (
    format_coord_for_display,
    parse_lat_lon_pair,
    parse_single_coord,
)


def test_parse_google_style_pair_from_issue_comment() -> None:
    raw = "-35.268965820020014, 149.08053613146686"
    pair = parse_lat_lon_pair(raw)
    assert pair is not None
    la, lo = pair
    assert la == pytest.approx(-35.268965820020014)
    assert lo == pytest.approx(149.08053613146686)


def test_parse_lat_lon_pair_rejects_invalid_ranges() -> None:
    assert parse_lat_lon_pair("91, 0") is None
    assert parse_lat_lon_pair("0, 181") is None


def test_parse_lat_lon_pair_requires_comma() -> None:
    assert parse_lat_lon_pair("-35.27 149.08") is None


def test_parse_single_coord_strips_commas() -> None:
    assert parse_single_coord("-35.26897") == pytest.approx(-35.26897)
    assert parse_single_coord("149.08054,") == pytest.approx(149.08054)


def test_format_coord_trims_trailing_zeros() -> None:
    assert format_coord_for_display(-35.5) == "-35.5"
    assert "0000000000" not in format_coord_for_display(-35.26896582)

