"""
PNG export for share-summary cards (#275) — HTML layouts → Playwright screenshot.

Requires the ``playwright`` package and Chromium binaries
(``python -m playwright install chromium``).
"""

from __future__ import annotations

import contextlib
import re
import struct
from typing import TYPE_CHECKING

from explorer.core.share_summary_spotlight_facts import ShareSummarySpotlightFact
from explorer.presentation.share_summary_preview import (
    _FORMAT_PX,
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
    render_share_summary_export_html,
)

if TYPE_CHECKING:
    from explorer.core.share_summary_compute import (
        ShareSummaryAllTimeStats,
        ShareSummaryGeoScope,
        ShareSummaryStats,
    )

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


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


@contextlib.contextmanager
def _launch_chromium():
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
            msg = str(exc)
            if "Executable doesn't exist" in msg:
                raise RuntimeError(
                    "Playwright Chromium is not installed. Run: "
                    "python -m playwright install chromium"
                ) from exc
            raise
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
    spotlight_fact: ShareSummarySpotlightFact | None = None,
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
        spotlight_fact=spotlight_fact,
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
