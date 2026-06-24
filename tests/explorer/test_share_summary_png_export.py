"""Tests for :mod:`explorer.presentation.share_summary_png_export`."""

import pytest

from explorer.presentation.share_summary_png_export import (
    png_dimensions,
    share_summary_png_filename,
    share_summary_to_png_bytes,
)
from explorer.presentation.share_summary_preview import sample_share_summary_stats

pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def chromium_available():
    try:
        share_summary_to_png_bytes(
            sample_share_summary_stats(),
            layout="tiles",
            fmt="square",
        )
    except RuntimeError as exc:
        if "Chromium is not installed" in str(exc) or "Playwright is not installed" in str(exc):
            pytest.skip(str(exc))
        raise


def test_share_summary_png_filename_year():
    stats = sample_share_summary_stats(period_label="2025", period_kind="year")
    assert share_summary_png_filename(stats) == "2025-birding-summary.png"


def test_share_summary_png_filename_trip_title():
    stats = sample_share_summary_stats(
        period_label="1 – 7 June 2025",
        period_kind="custom",
        trip_title="North Coast NSW Exploration",
    )
    assert share_summary_png_filename(stats) == "north-coast-nsw-exploration-birding-summary.png"


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        ("square", (1080, 1080)),
        ("portrait_post", (1080, 1350)),
        ("story", (1080, 1920)),
    ],
)
def test_share_summary_to_png_bytes_dimensions(fmt, expected, chromium_available):
    del chromium_available
    stats = sample_share_summary_stats()
    png = share_summary_to_png_bytes(stats, layout="tiles", fmt=fmt)
    assert png_dimensions(png) == expected


def test_share_summary_to_png_bytes_spotlight(chromium_available):
    del chromium_available
    stats = sample_share_summary_stats(period_kind="year")
    png = share_summary_to_png_bytes(stats, layout="spotlight", fmt="square", spotlight_label="Lifers")
    assert png_dimensions(png) == (1080, 1080)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
