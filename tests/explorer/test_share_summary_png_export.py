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
    shutdown_shared_chromium,
)
from explorer.presentation.share_summary_preview import sample_share_summary_stats


@pytest.fixture(autouse=True)
def _reset_warm_chromium():
    """Avoid leaking warm browsers across unit tests."""
    yield
    shutdown_shared_chromium()


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
    finally:
        shutdown_shared_chromium()


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

        def close(self):
            calls["page_closed"] = True

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
    assert calls["page_closed"] is True
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
    playwright_exits = {"n": 0}

    class _Browser:
        def close(self):
            pass

        def is_connected(self):
            return True

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
            playwright_exits["n"] += 1
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
    # Warm reuse keeps Playwright open until explicit shutdown (#344).
    assert playwright_exits["n"] == 0
    shutdown_shared_chromium()
    assert playwright_exits["n"] == 1


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


def test_warm_chromium_reused_across_exports(monkeypatch):
    """Second export reuses the same browser instance (#344)."""
    starts = {"n": 0}
    pages_opened = {"n": 0}
    pages_closed = {"n": 0}

    class _Page:
        def set_content(self, html, *, wait_until):
            del html, wait_until

        def screenshot(self, **kwargs):
            del kwargs
            return b"png"

        def close(self):
            pages_closed["n"] += 1

    class _Browser:
        def new_page(self, **kwargs):
            del kwargs
            pages_opened["n"] += 1
            return _Page()

        def is_connected(self):
            return True

        def close(self):
            pass

    class _Playwright:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @property
        def chromium(self):
            return self

        def launch(self):
            starts["n"] += 1
            return _Browser()

    fake_sync_api = types.SimpleNamespace(sync_playwright=lambda: _Playwright())
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

    stats = sample_share_summary_stats(period_label="2025", period_kind="year")
    assert share_summary_to_png_bytes(stats, layout="tiles", fmt="square") == b"png"
    assert share_summary_to_png_bytes(stats, layout="minimal", fmt="square") == b"png"

    assert starts["n"] == 1
    assert pages_opened["n"] == 2
    assert pages_closed["n"] == 2


def test_shutdown_shared_chromium_closes_warm_browser(monkeypatch):
    closed = {"browser": 0, "playwright": 0}

    class _Browser:
        def is_connected(self):
            return True

        def close(self):
            closed["browser"] += 1

    class _Playwright:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            closed["playwright"] += 1
            return False

        @property
        def chromium(self):
            return self

        def launch(self):
            return _Browser()

    fake_sync_api = types.SimpleNamespace(sync_playwright=lambda: _Playwright())
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

    with share_summary_png_export._launch_chromium() as browser:
        assert browser.is_connected()
    shutdown_shared_chromium()
    assert closed == {"browser": 1, "playwright": 1}

    # A later export can start a fresh warm session.
    with share_summary_png_export._launch_chromium() as browser_again:
        assert browser_again.is_connected()


def test_warm_chromium_restarts_when_disconnected(monkeypatch):
    launches = {"n": 0}
    browsers: list[object] = []

    class _Browser:
        def __init__(self):
            self._connected = True
            browsers.append(self)

        def is_connected(self):
            return self._connected

        def close(self):
            self._connected = False

    class _Playwright:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @property
        def chromium(self):
            return self

        def launch(self):
            launches["n"] += 1
            return _Browser()

    fake_sync_api = types.SimpleNamespace(sync_playwright=lambda: _Playwright())
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

    with share_summary_png_export._launch_chromium() as first:
        assert first is browsers[0]
    browsers[0]._connected = False  # type: ignore[attr-defined]
    with share_summary_png_export._launch_chromium() as second:
        assert second is browsers[1]
        assert second is not first
    assert launches["n"] == 2


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
