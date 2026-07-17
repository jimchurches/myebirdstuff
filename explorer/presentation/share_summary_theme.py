"""
Colour schemes, format IDs, and shared HTML helpers for share-summary cards.
"""

from __future__ import annotations

import contextlib
import contextvars
import html as html_module
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT,
    SHARE_SUMMARY_COLOR_SCHEMES,
)

TilesPresentationId = Literal["grid", "circles"]
SpotlightPresentationId = Literal["classic", "circle"]
LayoutId = Literal["tiles", "minimal", "spotlight", "insight"]


FormatId = Literal["square", "portrait_post", "story"]

_color_scheme_index: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "share_summary_color_scheme_index",
    default=None,
)
_custom_color_scheme: contextvars.ContextVar[dict[str, str] | None] = (
    contextvars.ContextVar(
        "share_summary_custom_color_scheme",
        default=None,
    )
)


def _active_color_scheme_index() -> int:
    override = _color_scheme_index.get()
    if override is not None:
        return override
    return SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT


def _active_color_scheme() -> dict[str, str]:
    custom = _custom_color_scheme.get()
    if custom is not None:
        return custom
    schemes = SHARE_SUMMARY_COLOR_SCHEMES
    idx = _active_color_scheme_index()
    return schemes[idx] if 0 <= idx < len(schemes) else schemes[0]


@contextlib.contextmanager
def _color_scheme_context(index: int | None):
    token = None
    if index is not None:
        token = _color_scheme_index.set(index)
    try:
        yield
    finally:
        if token is not None:
            _color_scheme_index.reset(token)


@contextlib.contextmanager
def share_summary_scheme_override(scheme: dict[str, str]):
    """Temporarily replace the active palette (e.g. theme trials in tests)."""
    token = _custom_color_scheme.set(scheme)
    try:
        yield
    finally:
        _custom_color_scheme.reset(token)


def _colour(key: str) -> str:
    return _active_color_scheme()[key]


def _colour_or(key: str, fallback_key: str) -> str:
    scheme = _active_color_scheme()
    return scheme.get(key, scheme[fallback_key])


_FORMAT_PX: dict[FormatId, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait_post": (1080, 1350),
    "story": (1080, 1920),
}

FORMAT_PIXELS: dict[FormatId, tuple[int, int]] = _FORMAT_PX

FORMAT_LABELS: dict[FormatId, str] = {
    "square": "Square post (1080×1080)",
    "portrait_post": "Portrait post (1080×1350)",
    "story": "Story (1080×1920)",
}

# Taxonomy reference labels (eBird/Clements denominators — not user checklist counts).
LABEL_SPECIES_IN_TAXONOMY = "Species in eBird taxonomy"
LABEL_FAMILIES_IN_TAXONOMY = "Families in eBird taxonomy"
LABEL_OBSERVED_SPECIES_PCT = "Observed species (%)"



def _esc(text: Any) -> str:
    return html_module.escape(str(text), quote=False)


_LOGO_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "explorer"
    / "assets"
    / "personal-ebird-explorer-logo.svg"
)


@lru_cache(maxsize=16)
def _logo_svg_inline(*, height_px: int = 56, fill: str) -> str:
    """Small inline logo for card headers/footers."""
    if not _LOGO_PATH.is_file():
        return ""
    raw = _LOGO_PATH.read_text(encoding="utf-8")
    raw = raw.replace('fill="#000000"', f'fill="{fill}"')
    return (
        f'<img src="data:image/svg+xml;base64,{_svg_to_data_uri(raw)}" '
        f'alt="" style="height:{height_px}px;width:auto;display:block;margin:0 auto;" />'
    )


def _svg_to_data_uri(svg: str) -> str:
    import base64

    return base64.b64encode(svg.encode("utf-8")).decode("ascii")



