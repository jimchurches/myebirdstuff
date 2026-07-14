"""Tests for :mod:`explorer.presentation.share_summary_png_export`."""

import sys
import types
from contextlib import contextmanager

import pytest

from explorer.core.share_summary_compute import ShareSummaryStats
from explorer.presentation import share_summary_png_export
from explorer.presentation.share_summary_png_export import (
    png_dimensions,
    share_summary_png_filename,
    share_summary_to_png_bytes,
)
from explorer.presentation.share_summary_preview import sample_share_summary_stats


@pytest.fixture(scope="module")
def chromium_available():
    try:
        share_summary_to_png_bytes(
            sample_share_summary_stats(),
            layout="tiles",
            fmt="square",
        )
    except RuntimeError as exc:
        msg = str(exc)
        if (
            "Chromium is not installed" in msg
            or "Chromium is not available" in msg
            or "Playwright is not installed" in msg
            or "Failed to install Playwright Chromium" in msg
            or "packages.txt" in msg
        ):
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


def test_share_summary_png_filename_empty_label_falls_back():
    # _slugify("") -> "birding-summary", then filename adds "-birding-summary.png"
    stats = ShareSummaryStats(period_label="", period_kind="custom")
    assert share_summary_png_filename(stats) == "birding-summary-birding-summary.png"
    stats_whitespace = ShareSummaryStats(period_label="   ", period_kind="custom")
    assert share_summary_png_filename(stats_whitespace) == "birding-summary-birding-summary.png"


def test_png_dimensions_rejects_invalid_bytes():
    with pytest.raises(ValueError, match="Not a valid PNG image"):
        png_dimensions(b"")
    with pytest.raises(ValueError, match="Not a valid PNG image"):
        png_dimensions(b"not a png")


def test_share_summary_to_png_bytes_builds_full_size_screenshot(monkeypatch):
    calls: dict[str, object] = {}

    class _Page:
        def set_content(self, html, *, wait_until):
            calls["html"] = html
            calls["wait_until"] = wait_until

        def screenshot(self, **kwargs):
            calls["screenshot"] = kwargs
            return b"rendered-png"

    class _Browser:
        def new_page(self, **kwargs):
            calls["new_page"] = kwargs
            return _Page()

    @contextmanager
    def _fake_launch_chromium():
        yield _Browser()

    monkeypatch.setattr(
        share_summary_png_export,
        "_launch_chromium",
        _fake_launch_chromium,
    )
    stats = sample_share_summary_stats(period_label="2025", period_kind="year")

    png = share_summary_to_png_bytes(
        stats,
        layout="tiles",
        fmt="portrait_post",
        card_stat_labels=("Species", "Checklists"),
    )

    assert png == b"rendered-png"
    assert calls["new_page"] == {
        "viewport": {"width": 1080, "height": 1350},
        "device_scale_factor": 1,
    }
    assert calls["wait_until"] == "load"
    assert "<!DOCTYPE html>" in str(calls["html"])
    assert "2025" in str(calls["html"])
    assert calls["screenshot"] == {
        "type": "png",
        "clip": {"x": 0, "y": 0, "width": 1080, "height": 1350},
    }


def test_install_chromium_runs_playwright_module(monkeypatch):
    calls: list[tuple[list[str], dict[str, object]]] = []

    def _fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(share_summary_png_export.subprocess, "run", _fake_run)

    share_summary_png_export._install_chromium()

    assert calls == [
        (
            [
                sys.executable,
                "-m",
                "playwright",
                "install",
                "chromium",
            ],
            {
                "capture_output": True,
                "text": True,
                "check": False,
            },
        )
    ]


def test_launch_chromium_installs_when_executable_missing(monkeypatch):
    """Cloud pip-only deploys need a one-shot ``playwright install chromium`` (#345)."""
    launches = {"n": 0}
    installs = {"n": 0}

    class _Browser:
        def close(self):
            pass

    class _Chromium:
        def launch(self):
            launches["n"] += 1
            if launches["n"] == 1:
                raise RuntimeError(
                    "Executable doesn't exist at /tmp/ms-playwright/chromium/chrome"
                )
            return _Browser()

    class _Playwright:
        chromium = _Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        share_summary_png_export,
        "_chromium_install_attempted",
        False,
    )
    monkeypatch.setattr(
        share_summary_png_export,
        "_install_chromium",
        lambda: installs.__setitem__("n", installs["n"] + 1),
    )

    fake_sync_api = types.SimpleNamespace(sync_playwright=lambda: _Playwright())
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

    with share_summary_png_export._launch_chromium() as browser:
        assert isinstance(browser, _Browser)

    assert installs["n"] == 1
    assert launches["n"] == 2


def test_launch_chromium_maps_missing_system_deps(monkeypatch):
    class _Chromium:
        def launch(self):
            raise RuntimeError("Host system is missing dependencies to run browsers.")

    class _Playwright:
        chromium = _Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    fake_sync_api = types.SimpleNamespace(sync_playwright=lambda: _Playwright())
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

    with pytest.raises(RuntimeError, match="packages.txt"):
        with share_summary_png_export._launch_chromium():
            pass


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
