"""
PNG export for share-summary cards (#275) — HTML layouts → Playwright screenshot.

Requires the ``playwright`` package and Chromium binaries
(``python -m playwright install chromium``).

On Streamlit Community Cloud, ``pip install`` alone does not download browsers.
This module installs Chromium into the user cache on first use when the
executable is missing (#345). System libraries still need ``packages.txt``.
"""

from __future__ import annotations

import contextlib
import logging
import re
import struct
import subprocess
import sys
import threading
from typing import TYPE_CHECKING

from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact
from explorer.presentation.share_summary_layouts import render_share_summary_export_html
from explorer.presentation.share_summary_theme import (
    _FORMAT_PX,
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
)

if TYPE_CHECKING:
    from explorer.core.share_summary_compute import (
        ShareSummaryAllTimeStats,
        ShareSummaryGeoScope,
        ShareSummaryStats,
    )

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_logger = logging.getLogger(__name__)

# One install attempt per process — avoids install loops if download fails.
_chromium_install_lock = threading.Lock()
_chromium_install_attempted = False


def png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    """Read width and height from PNG bytes (IHDR chunk)."""
    if len(png_bytes) < 24 or png_bytes[:8] != _PNG_SIGNATURE:
        raise ValueError("Not a valid PNG image")
    width, height = struct.unpack(">II", png_bytes[16:24])
    return width, height


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    if not slug:
        return "birding-summary"
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug


def share_summary_png_filename(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId | None = None,
    fmt: FormatId | None = None,
) -> str:
    """Suggested download filename, e.g. ``2025-birding-summary.png``."""
    del layout, fmt  # reserved for future disambiguation in filename
    base = _slugify(stats.trip_title or stats.period_label)
    return f"{base}-birding-summary.png"


def _chromium_executable_missing(exc: BaseException) -> bool:
    """True when Playwright reports browsers were never installed."""
    return "Executable doesn't exist" in str(exc)


def _install_chromium() -> None:
    """Download Playwright Chromium into the user cache (no apt / no sudo)."""
    _logger.info("Installing Playwright Chromium for share-summary PNG export")
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        # Prefer the last Error: line from Playwright's downloader over full logs.
        for line in reversed(detail.splitlines()):
            stripped = line.strip()
            if stripped.startswith("Error:"):
                detail = stripped
                break
        else:
            if len(detail) > 280:
                detail = detail[-280:]
        raise RuntimeError(
            "Failed to install Playwright Chromium for PNG export. "
            f"{detail or 'Unknown error.'}"
        )


def _ensure_chromium_installed() -> None:
    """Install Chromium once per process if launch reported it missing."""
    global _chromium_install_attempted
    with _chromium_install_lock:
        if _chromium_install_attempted:
            return
        _chromium_install_attempted = True
        _install_chromium()


def _chromium_missing_message() -> str:
    return (
        "Playwright Chromium is not available for PNG export. "
        "Locally run: python -m playwright install chromium. "
        "On Streamlit Cloud, confirm packages.txt system libraries are "
        "installed and redeploy after merging Cloud PNG support (#345)."
    )


def _system_deps_missing(exc: BaseException) -> bool:
    """True when Chromium cannot start due to missing OS libraries."""
    return "Host system is missing dependencies" in str(exc)


def _raise_launch_failure(exc: BaseException) -> None:
    """Translate Playwright launch failures into user-facing RuntimeError."""
    if _system_deps_missing(exc):
        raise RuntimeError(
            "PNG export needs system libraries for Chromium. "
            "On Streamlit Cloud, ensure packages.txt is present at the "
            "repo root and redeploy (#345)."
        ) from exc
    if _chromium_executable_missing(exc):
        raise RuntimeError(_chromium_missing_message()) from exc
    raise exc


@contextlib.contextmanager
def _launch_chromium():
    """Launch a short-lived Chromium for one PNG export.

    A fresh browser per export keeps shutdown simple and avoids leaked
    headless processes across Streamlit reruns. Warm reuse across exports
    can land later if batch or rapid-fire export becomes common (#344).

    When binaries are missing (typical after Cloud ``pip install`` only),
    download Chromium once into the user cache, then retry launch.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && "
            "python -m playwright install chromium"
        ) from exc
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as exc:
            if not _chromium_executable_missing(exc):
                _raise_launch_failure(exc)
            try:
                _ensure_chromium_installed()
                browser = playwright.chromium.launch()
            except RuntimeError:
                raise
            except Exception as retry_exc:
                _raise_launch_failure(retry_exc)
        try:
            yield browser
        finally:
            browser.close()


def share_summary_to_png_bytes(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId = "tiles",
    fmt: FormatId = "square",
    spotlight_label: str | None = None,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    scope_label: str | None = None,
    geo_scope: "ShareSummaryGeoScope | None" = None,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    insight_fact: ShareSummaryInsightFact | None = None,
) -> bytes:
    """Render a share card to PNG bytes at the layout's target pixel size."""
    width, height = _FORMAT_PX[fmt]
    labels = card_stat_labels if layout in ("tiles", "minimal") else ()
    html = render_share_summary_export_html(
        stats,
        layout=layout,
        fmt=fmt,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
        spotlight_label=spotlight_label,
        insight_fact=insight_fact,
        card_stat_labels=labels,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        geo_scope=geo_scope,
        scope_label=scope_label,
    )
    with _launch_chromium() as browser:
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        page.set_content(html, wait_until="load")
        return page.screenshot(
            type="png",
            clip={"x": 0, "y": 0, "width": width, "height": height},
        )


__all__ = [
    "png_dimensions",
    "share_summary_png_filename",
    "share_summary_to_png_bytes",
]
