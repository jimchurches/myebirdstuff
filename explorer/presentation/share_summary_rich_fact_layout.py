"""
Typography and vertical placement for Interesting Insights cards (#285).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FormatId = Literal["square", "portrait_post", "story"]

ColorRole = Literal["text", "muted", "accent"]


@dataclass(frozen=True)
class RichFactLineStyle:
    """One line in the rich-fact content block (label, primary, metric, or tie note)."""

    font_size_px: int
    font_weight: int
    color_role: ColorRole
    line_height: float = 1.1
    margin_top_px: int = 0
    margin_bottom_px: int = 0


@dataclass(frozen=True)
class RichFactLayoutSpec:
    """Rich-fact body typography and block offset for one export format."""

    label: RichFactLineStyle
    primary: RichFactLineStyle
    metric: RichFactLineStyle
    note: RichFactLineStyle
    block_offset_y_px: int = 0
    max_width_px: int = 920
    tile_frame: bool = True


def _shared_rich_fact_line_styles() -> tuple[
    RichFactLineStyle, RichFactLineStyle, RichFactLineStyle, RichFactLineStyle
]:
    """Shared Interesting Insights line typography (label, primary, metric, note)."""
    return (
        RichFactLineStyle(
            font_size_px=52,
            font_weight=500,
            color_role="muted",
            line_height=1.25,
            margin_bottom_px=48,
        ),
        RichFactLineStyle(
            font_size_px=60,
            font_weight=700,
            color_role="text",
            line_height=1.08,
        ),
        RichFactLineStyle(
            font_size_px=46,
            font_weight=700,
            color_role="text",
            line_height=1.1,
            margin_top_px=48,
        ),
        # Peak-tie soft note (#334) — smaller muted line under the metric.
        RichFactLineStyle(
            font_size_px=32,
            font_weight=500,
            color_role="muted",
            line_height=1.25,
            margin_top_px=28,
        ),
    )


def _story_spec() -> RichFactLayoutSpec:
    label, primary, metric, note = _shared_rich_fact_line_styles()
    return RichFactLayoutSpec(
        label=label,
        primary=primary,
        metric=metric,
        note=note,
        block_offset_y_px=-220,
    )


def _portrait_spec() -> RichFactLayoutSpec:
    label, primary, metric, note = _shared_rich_fact_line_styles()
    return RichFactLayoutSpec(
        label=label,
        primary=primary,
        metric=metric,
        note=note,
        block_offset_y_px=-160,
    )


def _square_spec() -> RichFactLayoutSpec:
    label, primary, metric, note = _shared_rich_fact_line_styles()
    return RichFactLayoutSpec(
        label=label,
        primary=primary,
        metric=metric,
        note=note,
        block_offset_y_px=-110,
    )


RICH_FACT_LAYOUT_SPECS: dict[FormatId, RichFactLayoutSpec] = {
    "story": _story_spec(),
    "portrait_post": _portrait_spec(),
    "square": _square_spec(),
}


def rich_fact_layout_spec(fmt: FormatId) -> RichFactLayoutSpec:
    """Layout spec for Interesting Insights cards at export size."""
    return RICH_FACT_LAYOUT_SPECS.get(fmt, RICH_FACT_LAYOUT_SPECS["story"])


def rich_fact_line_style_css(
    style: RichFactLineStyle,
    *,
    colour: str,
) -> str:
    """Inline CSS for one rich-fact line."""
    parts = [
        f"font-size:{style.font_size_px}px",
        f"font-weight:{style.font_weight}",
        f"line-height:{style.line_height}",
        f"color:{colour}",
    ]
    if style.margin_top_px:
        parts.append(f"margin-top:{style.margin_top_px}px")
    if style.margin_bottom_px:
        parts.append(f"margin-bottom:{style.margin_bottom_px}px")
    return ";".join(parts)
