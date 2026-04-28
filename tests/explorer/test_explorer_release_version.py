"""Release id parsing / ordering for Explorer update notice (refs #189)."""

from __future__ import annotations

import pytest

from explorer.core.explorer_release_version import (
    explorer_build_version_is_valid_format,
    normalize_release_tag,
    parse_explorer_release_tuple,
    remote_release_is_newer_than_embedded,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-04-25", (2026, 4, 25, 0)),
        ("v2026-04-25", (2026, 4, 25, 0)),
        ("2026-04-24 Beta", (2026, 4, 24, 0)),
        ("2026-04-24  BETA ", (2026, 4, 24, 0)),
        ("2026-04-24-Beta", (2026, 4, 24, 0)),
        ("2026-04-25.2", (2026, 4, 25, 2)),
        ("2026-04-25.10", (2026, 4, 25, 10)),
        ("V2026-04-25.3", (2026, 4, 25, 3)),
    ],
)
def test_parse_explorer_release_tuple_ok(raw: str, expected: tuple[int, int, int, int]) -> None:
    assert parse_explorer_release_tuple(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "nope",
        "2026-13-01",
        "2026-04-25.0",
        "2026-04-25.1",
        "2026-4-25",
    ],
)
def test_parse_explorer_release_tuple_rejects(raw: str) -> None:
    assert parse_explorer_release_tuple(raw) is None


def test_explorer_build_version_is_valid_format() -> None:
    assert explorer_build_version_is_valid_format("2026-04-25") is True
    assert explorer_build_version_is_valid_format("2026-04-25.2") is True
    assert explorer_build_version_is_valid_format("2026-04-25.1") is False


def test_normalize_release_tag() -> None:
    assert normalize_release_tag("  v2026-04-25.2  ") == "2026-04-25.2"
    assert normalize_release_tag("2026-04-24 Beta") == "2026-04-24"
    assert normalize_release_tag("2026-04-24-Beta") == "2026-04-24"


def test_remote_release_is_newer_than_embedded() -> None:
    assert remote_release_is_newer_than_embedded("2026-04-24 Beta", "2026-04-22") is True
    assert remote_release_is_newer_than_embedded("2026-04-24-Beta", "2026-04-22") is True
    assert remote_release_is_newer_than_embedded("2026-04-26", "2026-04-25") is True
    assert remote_release_is_newer_than_embedded("2026-04-25.2", "2026-04-25") is True
    assert remote_release_is_newer_than_embedded("2026-04-25.3", "2026-04-25.2") is True
    assert remote_release_is_newer_than_embedded("2026-04-25", "2026-04-25") is False
    assert remote_release_is_newer_than_embedded("2026-04-25", "2026-04-25.2") is False
    assert remote_release_is_newer_than_embedded("2026-04-25.1", "2026-04-25") is False
