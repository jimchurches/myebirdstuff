"""Offline tests for the standalone GPS checklist-name resolver."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "scripts"))

import eBirdChecklistNameFromGPS as mod  # noqa: E402

_FIXTURE = _REPO / "tests/fixtures/gps_checklistName_testing.json"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-35.327454,148.860410", (-35.327454, 148.860410, 6, 6)),
        ("Place ( -35.5, 149.1250 )", (-35.5, 149.125, 1, 4)),
        ("149.1250 -35.5", (-35.5, 149.125, 1, 4)),
    ],
)
def test_parse_coords_accepts_supported_formats(
    text: str, expected: tuple[float, float, int, int]
) -> None:
    assert mod.parse_coords_from_text(text) == expected


@pytest.mark.parametrize("text", ["", "latitude only: -35.2", "91, 181"])
def test_parse_coords_rejects_missing_or_out_of_range_values(text: str) -> None:
    with pytest.raises(ValueError):
        mod.parse_coords_from_text(text)


def test_fetch_geocode_sends_coordinates_and_rejects_api_failure(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    get = Mock(return_value=response)
    monkeypatch.setattr(mod.requests, "get", get)

    with pytest.raises(RuntimeError, match="Geocode failed: ZERO_RESULTS"):
        mod.fetch_geocode(-35.1, 149.2, "secret")

    get.assert_called_once_with(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"latlng": "-35.1,149.2", "key": "secret"},
    )


def test_embedded_geocode_cases_resolve_to_expected_names() -> None:
    cases = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    checked = 0

    for case in cases:
        if not case.get("expected") or not case.get("geocode_json"):
            continue
        actual = mod.resolve_location_from_data(
            case["geocode_json"], float(case["lat"]), float(case["lng"])
        )
        assert actual.casefold() == case["expected"].strip().casefold(), case.get(
            "name"
        )
        checked += 1

    assert cases, "GPS fixture must contain offline cases"
    assert checked == len(cases), "every GPS fixture case must be complete and asserted"


def test_format_location_string_limits_precision_and_trims_zeroes() -> None:
    assert (
        mod.format_location_string("Canberra", -35.5000004, 149.125, 1, 3)
        == "Canberra ( -35.5, 149.125 )"
    )
