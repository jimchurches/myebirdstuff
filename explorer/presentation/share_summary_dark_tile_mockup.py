"""
Dark theme Statistics Grid tile contrast mockups (#308).

Design-studio only — compare lifted graphite tile palettes against the current
dark scheme before updating :data:`SHARE_SUMMARY_COLOR_SCHEMES`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_defaults import SHARE_SUMMARY_COLOR_SCHEMES
from explorer.presentation.share_summary_preview import (
    FormatId,
    TilesPresentationId,
    render_share_summary_preview_html,
    share_summary_scheme_override,
)

DarkTileVariantId = Literal[
    "current",
    "lift_subtle_a",
    "lift_subtle_b",
    "lift_medium",
    "lift_clear",
    "lift_strong",
    "graphite_cool",
    "graphite_warm",
    "solid_lift",
    "border_emphasis",
    "card_deep",
    "gradient_flip",
    "max_nudge",
]

_SCHEME_KEYS = ("bg", "bg_alt", "text", "muted", "border", "accent")
_TILE_KEYS = ("tile_bg", "tile_bg_alt", "tile_border")

_DARK_BASE = SHARE_SUMMARY_COLOR_SCHEMES[1]


@dataclass(frozen=True)
class _DarkTileVariant:
    label: str
    description: str
    overrides: dict[str, str]


def _scheme_for_variant(overrides: dict[str, str]) -> dict[str, str]:
    return {**_DARK_BASE, **overrides}


DARK_TILE_VARIANT_SPECS: dict[DarkTileVariantId, _DarkTileVariant] = {
    "current": _DarkTileVariant(
        "1 · Current dark (baseline)",
        "Production dark theme — tiles use card bg / bg_alt gradient today.",
        {},
    ),
    "lift_subtle_a": _DarkTileVariant(
        "2 · Subtle lift A",
        "Smallest tile lift — graphite tiles just above the card surface.",
        {"tile_bg_alt": "#1a2420", "tile_bg": "#1e2a24"},
    ),
    "lift_subtle_b": _DarkTileVariant(
        "3 · Subtle lift B",
        "Slightly cooler graphite lift than A.",
        {"tile_bg_alt": "#192522", "tile_bg": "#1d2b26"},
    ),
    "lift_medium": _DarkTileVariant(
        "4 · Medium lift",
        "Clear but restrained separation from the card background.",
        {"tile_bg_alt": "#1e2a24", "tile_bg": "#243229"},
    ),
    "lift_clear": _DarkTileVariant(
        "5 · Clear lift",
        "Noticeable tile panels without breaking the forest palette.",
        {"tile_bg_alt": "#212e28", "tile_bg": "#28362f"},
    ),
    "lift_strong": _DarkTileVariant(
        "6 · Strong lift",
        "Boldest tile lift in the set — still graphite green, not grey.",
        {"tile_bg_alt": "#25332c", "tile_bg": "#2d3d35"},
    ),
    "graphite_cool": _DarkTileVariant(
        "7 · Cool graphite",
        "Medium lift with a touch more blue in the tile graphite.",
        {"tile_bg_alt": "#1b2728", "tile_bg": "#21302f"},
    ),
    "graphite_warm": _DarkTileVariant(
        "8 · Warm graphite",
        "Medium lift with a slightly warmer olive graphite.",
        {"tile_bg_alt": "#222a22", "tile_bg": "#293328"},
    ),
    "solid_lift": _DarkTileVariant(
        "9 · Solid lift",
        "Flat tile fill (no gradient) at medium lift.",
        {"tile_bg_alt": "#212e28", "tile_bg": "#212e28"},
    ),
    "border_emphasis": _DarkTileVariant(
        "10 · Border emphasis",
        "Subtle lift plus a brighter tile border for edge definition.",
        {
            "tile_bg_alt": "#1e2a24",
            "tile_bg": "#243229",
            "tile_border": "#32483c",
        },
    ),
    "card_deep": _DarkTileVariant(
        "11 · Deeper card",
        "Card sinks slightly; tiles at medium lift for extra contrast.",
        {
            "bg": "#0a0e0c",
            "tile_bg_alt": "#1e2a24",
            "tile_bg": "#243229",
        },
    ),
    "gradient_flip": _DarkTileVariant(
        "12 · Gradient flip",
        "Lifted tiles with gradient reversed (lighter toward bottom-right).",
        {"tile_bg_alt": "#243229", "tile_bg": "#1e2a24"},
    ),
    "max_nudge": _DarkTileVariant(
        "13 · Max nudge",
        "Upper bound of a small nudge — between medium and strong lift.",
        {"tile_bg_alt": "#1f2c26", "tile_bg": "#26352e"},
    ),
}

DARK_TILE_VARIANT_IDS: tuple[DarkTileVariantId, ...] = tuple(DARK_TILE_VARIANT_SPECS.keys())
DARK_TILE_VARIANT_LABELS: dict[DarkTileVariantId, str] = {
    key: spec.label for key, spec in DARK_TILE_VARIANT_SPECS.items()
}
# Working pick for enlarged preview until production dark theme is updated (#308).
DARK_TILE_MOCKUP_DEFAULT_VARIANT: DarkTileVariantId = "lift_strong"


def dark_tile_variant_scheme(variant: DarkTileVariantId) -> dict[str, str]:
    """Full palette dict for one mockup variant (dark base + overrides)."""
    return _scheme_for_variant(DARK_TILE_VARIANT_SPECS[variant].overrides)


def _resolved_hex(scheme: dict[str, str], key: str, fallback_key: str) -> str:
    return scheme.get(key, scheme[fallback_key])


def _scheme_reference_html(scheme: dict[str, str]) -> str:
    """Compact swatch row for the mockup card chrome."""
    rows: list[str] = []
    for key in _SCHEME_KEYS:
        hex_val = scheme[key]
        rows.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;margin:0 14px 6px 0;">'
            f'<span style="width:14px;height:14px;border-radius:3px;background:{hex_val};'
            f'border:1px solid rgba(255,255,255,0.12);"></span>'
            f'<span style="font-size:11px;font-family:ui-monospace,monospace;color:#9ca3af;">'
            f'{key} {hex_val}</span></span>'
        )
    tile_bg = _resolved_hex(scheme, "tile_bg", "bg")
    tile_bg_alt = _resolved_hex(scheme, "tile_bg_alt", "bg_alt")
    tile_border = _resolved_hex(scheme, "tile_border", "border")
    for label, hex_val in (
        ("tile_bg", tile_bg),
        ("tile_bg_alt", tile_bg_alt),
        ("tile_border", tile_border),
    ):
        suffix = "" if label in scheme else " (inherits)"
        rows.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;margin:0 14px 6px 0;">'
            f'<span style="width:14px;height:14px;border-radius:3px;background:{hex_val};'
            f'border:1px solid rgba(255,255,255,0.12);"></span>'
            f'<span style="font-size:11px;font-family:ui-monospace,monospace;color:#9ca3af;">'
            f'{label} {hex_val}{suffix}</span></span>'
        )
    return (
        '<div style="margin:0 0 10px;padding:10px 12px;border-radius:8px;'
        'background:#111827;border:1px solid #374151;line-height:1.5;">'
        f'{"".join(rows)}</div>'
    )


def render_dark_tile_mockup_scheme_reference_html(variant: DarkTileVariantId) -> str:
    """Scheme swatches for one mockup variant (shared above paired previews)."""
    return _scheme_reference_html(dark_tile_variant_scheme(variant))


def render_dark_tile_mockup_preview_html(
    stats: ShareSummaryStats,
    *,
    variant: DarkTileVariantId = "current",
    fmt: FormatId = "square",
    scale: float = 0.32,
    tiles_presentation: TilesPresentationId = "grid",
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
    show_scheme_reference: bool = True,
) -> str:
    """Scaled Statistics Grid or circle-cluster preview; optional scheme swatches."""
    scheme = dark_tile_variant_scheme(variant)
    with share_summary_scheme_override(scheme):
        card_html = render_share_summary_preview_html(
            stats,
            layout="tiles",
            fmt=fmt,
            tiles_presentation=tiles_presentation,
            scale=scale,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            color_scheme_index=1,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
    ref = _scheme_reference_html(scheme) if show_scheme_reference else ""
    return f"{ref}{card_html}"


__all__ = [
    "DARK_TILE_MOCKUP_DEFAULT_VARIANT",
    "DARK_TILE_VARIANT_IDS",
    "DARK_TILE_VARIANT_LABELS",
    "DARK_TILE_VARIANT_SPECS",
    "DarkTileVariantId",
    "dark_tile_variant_scheme",
    "render_dark_tile_mockup_preview_html",
    "render_dark_tile_mockup_scheme_reference_html",
]
