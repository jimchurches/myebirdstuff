"""
Circular Statistics Tiles layouts for share summary cards (#157).

Hand-tuned circle layouts live in ``CIRCLE_CARD_TEMPLATES``; the renderer is shared.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_defaults import SHARE_SUMMARY_STORY_MAX_STATS
from explorer.presentation.share_summary_preview import (
    _FORMAT_PX,
    FormatId,
    _card_shell,
    _color_scheme_context,
    _colour,
    _colour_or,
    _esc,
    _footer_block,
    _footer_pad,
    _header_block,
    _layout_subtitle,
    _resolve_card_stat_pairs,
    spotlight_pair_for_label,
)

CircleVariantId = Literal[
    "cluster_soft",
    "cluster_tight",
    "cluster_stagger_a",
    "cluster_stagger_b",
    "cluster_wide",
    "cluster_compact",
    "tiles_cluster",
]

CIRCLE_LAYOUT_MAX_STATS = 9
CIRCLE_LAYOUT_MIN_STATS = 6
TILES_CIRCLE_CLUSTER_MIN = 6
TILES_CIRCLE_CLUSTER_DEFAULT = 6
# Circle-cluster caps — separate from Statistics Grid (see layout_grid_stat_* in preview).
TILES_CIRCLE_CLUSTER_SQUARE_MAX = 6
TILES_CIRCLE_CLUSTER_PORTRAIT_MAX = 8
TILES_CIRCLE_CLUSTER_MAX = TILES_CIRCLE_CLUSTER_PORTRAIT_MAX
TILES_CIRCLE_CLUSTER_STORY_MAX = SHARE_SUMMARY_STORY_MAX_STATS
TILES_CIRCLE_CLUSTER_VARIANT: CircleVariantId = "tiles_cluster"
CLUSTER_DIAMETER_SEARCH_START = 320
TILES_CIRCLE_DIAMETER_SEARCH_START = CLUSTER_DIAMETER_SEARCH_START
_SHADOW_PAD_PX = 12

CircleCardBoundsId = Literal["cluster", "story"]
TilesCircleCardType = Literal["tiles"]


@dataclass(frozen=True)
class CircleCardCountSpec:
    """Normalised positions and optional fixed diameter for one circle count."""

    positions: tuple[tuple[float, float], ...]
    diameter: int | None = None


@dataclass(frozen=True)
class CircleCardTemplate:
    """Hand-tuned circle layout for one card type and export format."""

    card_type: TilesCircleCardType
    fmt: FormatId
    bounds: CircleCardBoundsId
    counts: dict[int, CircleCardCountSpec]


@dataclass(frozen=True)
class _CircleVariantSpec:
    label: str
    gap_px: int
    ring1_angle_offset_rad: float
    ring_step: float = 1.0
    ring2_angle_offset_rad: float | None = None
    shadow: bool = True


CIRCLE_VARIANT_SPECS: dict[CircleVariantId, _CircleVariantSpec] = {
    "cluster_soft": _CircleVariantSpec(
        "Soft cluster — gentle ring spacing with shadow",
        gap_px=18,
        ring1_angle_offset_rad=math.pi / 9,
        shadow=True,
    ),
    "cluster_tight": _CircleVariantSpec(
        "Tight cluster — closer rings, no shadow",
        gap_px=8,
        ring1_angle_offset_rad=math.pi / 12,
        ring_step=1.0,
        shadow=False,
    ),
    "cluster_stagger_a": _CircleVariantSpec(
        "Staggered cluster A — offset first ring with shadow",
        gap_px=14,
        ring1_angle_offset_rad=math.pi / 6,
        ring2_angle_offset_rad=math.pi / 4,
        shadow=True,
    ),
    "cluster_stagger_b": _CircleVariantSpec(
        "Staggered cluster B — wider ring offset with shadow",
        gap_px=14,
        ring1_angle_offset_rad=math.pi / 4,
        ring2_angle_offset_rad=math.pi / 3,
        shadow=True,
    ),
    "cluster_wide": _CircleVariantSpec(
        "Wide cluster — roomier rings with shadow",
        gap_px=18,
        ring1_angle_offset_rad=math.pi / 10,
        ring_step=1.06,
        shadow=True,
    ),
    "cluster_compact": _CircleVariantSpec(
        "Compact cluster — dense rings, no shadow",
        gap_px=10,
        ring1_angle_offset_rad=math.pi / 7,
        ring_step=1.0,
        shadow=False,
    ),
    "tiles_cluster": _CircleVariantSpec(
        "Statistics Tiles cluster — count-aware sizing with moderate ring gap",
        gap_px=11,
        ring1_angle_offset_rad=math.pi / 10,
        ring_step=1.04,
        shadow=True,
    ),
}

CIRCLE_VARIANT_LABELS: dict[CircleVariantId, str] = {
    key: spec.label for key, spec in CIRCLE_VARIANT_SPECS.items()
}
CIRCLE_VARIANT_IDS: tuple[CircleVariantId, ...] = tuple(CIRCLE_VARIANT_SPECS.keys())


_CIRCLE_CLUSTER_UP_BIAS = 0.07  # shift cluster up as fraction of canvas height


def _tiles_circle_layout_reserves(
    fmt: FormatId,
    *,
    scope_label: str | None,
) -> tuple[int, int, int]:
    """Header/footer chrome matching ``_header_block`` / ``_footer_block`` in production cards."""
    if fmt == "story":
        return (
            200,
            210 if scope_label else 172,
            20,
        )
    return (
        192,
        178 if scope_label else 132,
        12,
    )


def _tiles_circle_body_insets(
    fmt: FormatId,
    *,
    scope_label: str | None,
) -> tuple[int, int, int, int]:
    """Absolute top/bottom/left/right insets for the Statistics Tiles circle body."""
    header_reserve, footer_reserve, vertical_pad = _tiles_circle_layout_reserves(
        fmt,
        scope_label=scope_label,
    )
    top = header_reserve + vertical_pad // 2
    bottom = footer_reserve + vertical_pad - vertical_pad // 2
    return top, bottom, 48, 48


def _cluster_body_canvas_size(
    width: int,
    height: int,
    *,
    header_reserve: int,
    footer_reserve: int,
    vertical_pad: int = 12,
) -> tuple[int, int]:
    canvas_w = width - 96
    canvas_h = height - header_reserve - footer_reserve - vertical_pad
    return canvas_w, max(340, canvas_h)


def _circle_canvas_size(
    width: int,
    height: int,
    fmt: FormatId,
    *,
    scope_label: str | None,
) -> tuple[int, int]:
    """Usable circle area between header and absolute footer (incl. scope line)."""
    del fmt
    header_reserve = 192
    footer_reserve = 178 if scope_label else 132
    vertical_pad = 20
    canvas_w = width - 96
    canvas_h = height - header_reserve - footer_reserve - vertical_pad
    return canvas_w, max(340, canvas_h)


def _tiles_circle_canvas_size(
    width: int,
    height: int,
    fmt: FormatId,
    *,
    scope_label: str | None,
) -> tuple[int, int]:
    """Statistics Tiles circle body — room for layout subtitle above the period headline."""
    header_reserve, footer_reserve, vertical_pad = _tiles_circle_layout_reserves(
        fmt,
        scope_label=scope_label,
    )
    return _cluster_body_canvas_size(
        width,
        height,
        header_reserve=header_reserve,
        footer_reserve=footer_reserve,
        vertical_pad=vertical_pad,
    )


def _max_single_cluster_diameter(canvas_w: int, canvas_h: int) -> int:
    """Upper bound for a lone circle in a cluster layout."""
    pad = _SHADOW_PAD_PX + 8
    return max(96, min(canvas_w, canvas_h) - 2 * pad)


def _circle_diameter(
    count: int,
    canvas_w: int,
    canvas_h: int,
    *,
    gap_px: int = 18,
    ring_step: float = 1.06,
) -> int:
    """Uniform circle size — fits radial rings inside the canvas safe area."""
    pad = _SHADOW_PAD_PX + 8
    avail = min(canvas_w / 2, canvas_h / 2) - pad - 4
    if count <= 1:
        return _max_single_cluster_diameter(canvas_w, canvas_h)
    if count <= 7:
        ring_count = count - 1
        # Single-ring clusters: tighter rings (few outer circles) can use larger tiles.
        ring_factor = 0.42 + 0.08 * min(ring_count, 6)
        d_max = (avail - ring_step * gap_px) / (ring_step + ring_factor)
    else:
        d_max = (avail - 2 * ring_step * gap_px) / (2 * ring_step + 0.5)
    if count <= 4:
        width_cap = int(canvas_w * 0.30)
        max_diameter = 260
    elif count > 6:
        width_cap = int(canvas_w * 0.20)
        max_diameter = 210
    else:
        width_cap = int(canvas_w * 0.23)
        max_diameter = 210
    return max(96, min(int(d_max), width_cap, max_diameter))


def _cluster_fit_scale(
    centres_rel: list[tuple[float, float]],
    *,
    radius: float,
    canvas_w: float,
    canvas_h: float,
) -> float:
    if not centres_rel:
        return 1.0
    pad = radius + _SHADOW_PAD_PX + 8
    min_x = min(x for x, _ in centres_rel) - radius
    max_x = max(x for x, _ in centres_rel) + radius
    min_y = min(y for _, y in centres_rel) - radius
    max_y = max(y for _, y in centres_rel) + radius
    width = max_x - min_x
    height = max_y - min_y
    avail_w = canvas_w - 2 * pad
    avail_h = canvas_h - 2 * pad
    if width <= 0 or height <= 0:
        return 1.0
    return min(1.0, avail_w / width, avail_h / height)


def _fit_cluster_to_canvas(
    centres_rel: list[tuple[float, float]],
    *,
    radius: float,
    canvas_w: float,
    canvas_h: float,
) -> list[tuple[float, float]]:
    if not centres_rel:
        return []
    pad = radius + _SHADOW_PAD_PX + 8
    min_x = min(x for x, _ in centres_rel) - radius
    max_x = max(x for x, _ in centres_rel) + radius
    min_y = min(y for _, y in centres_rel) - radius
    max_y = max(y for _, y in centres_rel) + radius
    width = max_x - min_x
    height = max_y - min_y
    avail_w = canvas_w - 2 * pad
    avail_h = canvas_h - 2 * pad
    scale = min(1.0, avail_w / width, avail_h / height)
    cx = canvas_w / 2
    cy = canvas_h / 2 - canvas_h * _CIRCLE_CLUSTER_UP_BIAS
    return [(cx + x * scale, cy + y * scale) for x, y in centres_rel]


def _circles_overlap(
    x: float,
    y: float,
    r: float,
    others: list[tuple[float, float]],
    *,
    gap: float,
) -> bool:
    min_dist = 2 * r + gap
    min_dist_sq = min_dist * min_dist
    epsilon = 1e-6
    for ox, oy in others:
        dx = x - ox
        dy = y - oy
        if dx * dx + dy * dy + epsilon < min_dist_sq:
            return True
    return False


def _radial_ring_centre(
    cx: float,
    cy: float,
    radius: float,
    angle: float,
) -> tuple[float, float]:
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def _radial_centres_relative(
    count: int,
    *,
    diameter: int,
    spec: _CircleVariantSpec,
) -> list[tuple[float, float]]:
    gap = float(spec.gap_px)
    step = (diameter + gap) * spec.ring_step
    centres_rel: list[tuple[float, float]] = [(0.0, 0.0)]
    if count == 1:
        return centres_rel

    if count <= 7:
        ring_count = count - 1
        for i in range(ring_count):
            angle = spec.ring1_angle_offset_rad + i * (2 * math.pi / ring_count)
            centres_rel.append(_radial_ring_centre(0.0, 0.0, step, angle))
        return centres_rel

    ring1_count = 6
    for i in range(ring1_count):
        angle = spec.ring1_angle_offset_rad + i * (2 * math.pi / ring1_count)
        centres_rel.append(_radial_ring_centre(0.0, 0.0, step, angle))

    ring2_count = count - 7
    ring2_step = 2 * step
    ring2_offset = (
        spec.ring2_angle_offset_rad
        if spec.ring2_angle_offset_rad is not None
        else spec.ring1_angle_offset_rad + math.pi / ring2_count
    )
    for i in range(ring2_count):
        angle = ring2_offset + i * (2 * math.pi / ring2_count)
        centres_rel.append(_radial_ring_centre(0.0, 0.0, ring2_step, angle))
    return centres_rel


def largest_cluster_diameter(
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    variant: CircleVariantId,
    search_start: int = CLUSTER_DIAMETER_SEARCH_START,
) -> int:
    """Largest uniform circle diameter that fits *count* stats without overlap."""
    start = search_start
    if count <= 1:
        start = min(start, _max_single_cluster_diameter(canvas_w, canvas_h))
    _, diameter = place_circle_centers(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=start,
        variant=variant,
    )
    return diameter


def place_circle_centers(
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
    variant: CircleVariantId,
    period_label: str = "",
) -> tuple[list[tuple[float, float]], int]:
    """Deterministic radial cluster: centre circle + one or two concentric rings."""
    del period_label
    if count <= 0:
        return [], diameter
    if count == 1:
        diameter = min(diameter, _max_single_cluster_diameter(canvas_w, canvas_h))

    spec = CIRCLE_VARIANT_SPECS[variant]
    for try_d in range(diameter, 95, -1):
        centres_rel = _radial_centres_relative(count, diameter=try_d, spec=spec)
        radius = try_d / 2
        if _cluster_fit_scale(
            centres_rel,
            radius=radius,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        ) < 0.999:
            continue
        centres = _fit_cluster_to_canvas(
            centres_rel,
            radius=radius,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        )
        gap = float(spec.gap_px)
        if not any(
            _circles_overlap(
                x,
                y,
                radius,
                [c for j, c in enumerate(centres) if j != i],
                gap=gap,
            )
            for i, (x, y) in enumerate(centres)
        ):
            return centres, try_d

    centres_rel = _radial_centres_relative(count, diameter=96, spec=spec)
    return (
        _fit_cluster_to_canvas(
            centres_rel,
            radius=48.0,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        ),
        96,
    )


def _circle_value_font_px(value: str, base_px: int, *, diameter: int) -> int:
    """Single-line stat figure sized to fit inside the circle width."""
    inner_w = max(68, diameter - 44)
    n = len(value)
    px = base_px
    if n > 4:
        px = min(base_px, int(base_px * 4.5 / n))
    while n * px * 0.58 > inner_w and px > 24:
        px -= 1
    return px


def _circle_tile_html(
    label: str,
    value: str,
    *,
    diameter: int,
    value_px: str,
    label_px: str,
    shadow: bool = False,
) -> str:
    tile_bg_alt = _colour_or("tile_bg_alt", "bg_alt")
    tile_bg = _colour_or("tile_bg", "bg")
    tile_border = _colour_or("tile_border", "border")
    bg = f"linear-gradient(145deg,{tile_bg_alt},{tile_bg})"
    border = f"2px solid {tile_border}"
    base_value_px = int(value_px.replace("px", ""))
    fitted_value_px = _circle_value_font_px(value, base_value_px, diameter=diameter)
    shadow_css = "box-shadow:0 8px 18px rgba(0,0,0,0.12);" if shadow else ""
    return f"""
<div style="width:{diameter}px;height:{diameter}px;border-radius:50%;
  background:{bg};border:{border};{shadow_css}
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:16px;box-sizing:border-box;">
  <div style="font-size:{fitted_value_px}px;font-weight:700;line-height:1;
    white-space:nowrap;letter-spacing:-0.02em;">{_esc(value)}</div>
  <div style="margin-top:6px;font-size:{label_px};color:{_colour('muted')};line-height:1.12;">
    {_esc(label)}</div>
</div>"""


def _empty_circle_tile_html(
    *,
    diameter: int,
    shadow: bool = False,
) -> str:
    shadow_css = "box-shadow:0 8px 18px rgba(0,0,0,0.08);" if shadow else ""
    return f"""
<div style="width:{diameter}px;height:{diameter}px;border-radius:50%;
  background:{_colour('bg')};border:2px dashed {_colour('border')};{shadow_css}
  box-sizing:border-box;"></div>"""


def tiles_circle_cluster_max(fmt: FormatId) -> int:
    """Maximum Statistics Tiles circle slots for *fmt*."""
    if fmt == "story":
        return TILES_CIRCLE_CLUSTER_STORY_MAX
    if fmt == "portrait_post":
        return TILES_CIRCLE_CLUSTER_PORTRAIT_MAX
    if fmt == "square":
        return TILES_CIRCLE_CLUSTER_SQUARE_MAX
    return TILES_CIRCLE_CLUSTER_MAX


def _metrics_lookup_for_story_slots(
    stats: ShareSummaryStats,
    *,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> dict[str, str]:
    from explorer.presentation.share_summary_preview import _metrics_lookup

    return _metrics_lookup(stats, all_time=all_time, geo_scope=geo_scope)


def _resolve_story_circle_slot_pairs(
    stats: ShareSummaryStats,
    slot_labels: tuple[str, ...],
    *,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> list[tuple[str, str]]:
    """Story circle slots preserve empty picks as blank tiles on the card."""
    lookup = _metrics_lookup_for_story_slots(
        stats,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for lab in slot_labels[:TILES_CIRCLE_CLUSTER_STORY_MAX]:
        cleaned = lab.strip() if lab else ""
        if cleaned and cleaned in lookup and cleaned not in seen:
            pairs.append((cleaned, lookup[cleaned]))
            seen.add(cleaned)
        else:
            pairs.append(("", ""))
    return pairs


def _centres_in_grid_reading_order(
    centres: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Top-to-bottom, left-to-right — matches Statistics Tiles tile order."""
    return [
        centres[i]
        for i, _ in sorted(
            enumerate(centres),
            key=lambda item: (round(item[1][1], 1), round(item[1][0], 1)),
        )
    ]


# Hand-tuned template tuning constants (shared by story and cluster bounds).
_HAND_TUNED_CIRCLE_TOP_CLEARANCE = 20
_HAND_TUNED_CIRCLE_BOTTOM_CLEARANCE = 52
_STORY_CIRCLE_TOP_CLEARANCE = _HAND_TUNED_CIRCLE_TOP_CLEARANCE
_STORY_CIRCLE_BOTTOM_CLEARANCE = _HAND_TUNED_CIRCLE_BOTTOM_CLEARANCE
_HAND_TUNED_CIRCLE_MIN_EDGE_GAP_PX = 20
_STORY_CIRCLE_MIN_EDGE_GAP_PX = _HAND_TUNED_CIRCLE_MIN_EDGE_GAP_PX
_HAND_TUNED_CIRCLE_MAX_DIAMETER_PX = 560
_STORY_CIRCLE_MAX_DIAMETER_PX = _HAND_TUNED_CIRCLE_MAX_DIAMETER_PX
_SINGLE_CIRCLE_LAYOUT: tuple[tuple[float, float], ...] = ((0.50, 0.50),)
_SINGLE_CIRCLE_DIAMETER_BY_FORMAT: dict[FormatId, int] = {
    "square": 560,
    "portrait_post": 560,
    "story": 560,
}
_SINGLE_CIRCLE_DIAMETER_PX = _SINGLE_CIRCLE_DIAMETER_BY_FORMAT["square"]
_HAND_TUNED_CIRCLE_TYPOGRAPHY: dict[tuple[FormatId, int], tuple[int, int]] = {
    ("square", 1): (110, 30),
    ("square", 2): (75, 22),
    ("portrait_post", 1): (110, 30),
    ("portrait_post", 2): (80, 24),
    ("story", 1): (110, 30),
    ("story", 2): (90, 26),
}
_SINGLE_CIRCLE_TYPOGRAPHY_BY_FORMAT: dict[FormatId, tuple[int, int]] = {
    fmt: typography
    for (fmt, count), typography in _HAND_TUNED_CIRCLE_TYPOGRAPHY.items()
    if count == 1
}
_SPOTLIGHT_CIRCLE_EDGE_PAD_PX = _SHADOW_PAD_PX + 12
_SPOTLIGHT_CIRCLE_MIN_DIAMETER_PX = 240
_HAND_TUNED_CIRCLE_WIDTH_FRACTION = 0.62
_STORY_CIRCLE_WIDTH_FRACTION = _HAND_TUNED_CIRCLE_WIDTH_FRACTION


def single_circle_diameter_px(fmt: FormatId) -> int:
    """Hand-tuned count-1 circle diameter for Statistics Tiles."""
    return _SINGLE_CIRCLE_DIAMETER_BY_FORMAT.get(fmt, _SINGLE_CIRCLE_DIAMETER_PX)


def single_circle_typography_px(fmt: FormatId) -> tuple[int, int] | None:
    """Hand-tuned count-1 value/label font sizes when set for *fmt*."""
    return hand_tuned_circle_typography_px(fmt, 1)


def hand_tuned_circle_typography_px(
    fmt: FormatId,
    count: int,
) -> tuple[int, int] | None:
    """Hand-tuned value/label font sizes for one format and circle count."""
    return _HAND_TUNED_CIRCLE_TYPOGRAPHY.get((fmt, count))


def _hand_tuned_circle_typography(
    template: CircleCardTemplate,
    count: int,
    diameter: int,
) -> tuple[str, str]:
    """Value and label font sizes for one hand-tuned circle cluster."""
    tuned = hand_tuned_circle_typography_px(template.fmt, count)
    if tuned is not None:
        value_px, label_px = tuned
        return f"{value_px}px", f"{label_px}px"
    if count >= _hand_tuned_compact_type_threshold(template):
        return "40px", "16px"
    if diameter >= 260:
        return "52px", "19px"
    if diameter >= 240:
        return "46px", "17px"
    return "48px", "18px"


def _build_circle_card_template(
    fmt: FormatId,
    *,
    bounds: CircleCardBoundsId,
    layouts: dict[int, tuple[tuple[float, float], ...]],
    diameters: dict[int, int],
) -> CircleCardTemplate:
    return CircleCardTemplate(
        card_type="tiles",
        fmt=fmt,
        bounds=bounds,
        counts={
            count: CircleCardCountSpec(
                positions=positions,
                diameter=diameters.get(count),
            )
            for count, positions in layouts.items()
        },
    )


CIRCLE_CARD_TEMPLATES: dict[tuple[TilesCircleCardType, FormatId], CircleCardTemplate] = {
    ("tiles", "story"): _build_circle_card_template(
        "story",
        bounds="story",
        layouts={
            1: _SINGLE_CIRCLE_LAYOUT,
            2: (
                (0.21, 0.21),
                (0.77, 0.77),
            ),
            3: (
                (0.82, 0.50),
                (0.42, 0.97),
                (0.13, 0.11),
            ),
            4: (
                (0.18, 0.32),
                (0.81, 0.67),
                (0.11, 0.92),
                (0.79, 0.07),
            ),
            5: (
                (0.50, 0.42),
                (0.80, 0.82),
                (0.07, 1.00),
                (0.07, 0.12),
                (0.82, 0.05),
            ),
            6: (
                (0.10, 0.02),
                (0.87, 0.18),
                (0.17, 0.40),
                (0.66, 0.62),
                (0.12, 0.91),
                (0.86, 0.98),
            ),
            7: (
                (0.18, 0.08),
                (0.78, 0.15),
                (0.07, 0.39),
                (0.89, 0.49),
                (0.38, 0.66),
                (0.80, 0.93),
                (0.11, 0.96),
            ),
            8: (
                (0.08, 0.08),
                (0.78, 0.12),
                (0.40, 0.33),
                (0.90, 0.44),
                (0.06, 0.58),
                (0.58, 0.70),
                (0.18, 0.91),
                (0.84, 0.99),
            ),
            9: (
                (0.01, 0.09),
                (0.76, 0.05),
                (0.92, 0.34),
                (0.37, 0.26),
                (0.55, 0.57),
                (0.05, 0.58),
                (0.94, 0.78),
                (0.10, 0.93),
                (0.62, 1.00),
            ),
            10: (
                (0.09, 0.14),
                (0.54, 0.06),
                (0.92, 0.21),
                (0.41, 0.37),
                (0.85, 0.49),
                (0.04, 0.54),
                (0.94, 0.76),
                (0.42, 0.70),
                (0.13, 0.94),
                (0.74, 1.00),
            ),
        },
        diameters={
            1: single_circle_diameter_px("story"),
            2: 465,
            3: 380,
            4: 340,
            5: 340,
            6: 340,
            7: 295,
            8: 265,
            9: 255,
            10: 255,
        },
    ),
    ("tiles", "portrait_post"): _build_circle_card_template(
        "portrait_post",
        bounds="cluster",
        layouts={
            1: _SINGLE_CIRCLE_LAYOUT,
            2: (
                (0.15, 0.19),
                (0.86, 0.79),
            ),
            3: (
                (0.73, 0.24),
                (0.80, 0.87),
                (0.10, 0.16),
            ),
            4: (
                (0.82, 0.28),
                (0.77, 0.94),
                (0.02, 0.68),
                (0.20, 0.13),
            ),
            5: (
                (0.58, 0.54),
                (0.96, 0.83),
                (0.19, 0.86),
                (0.08, 0.19),
                (0.78, 0.04),
            ),
            6: (
                (0.46, 0.47),
                (0.90, 0.51),
                (0.65, 0.91),
                (0.08, 0.79),
                (0.15, 0.16),
                (0.77, 0.06),
            ),
            7: (
                (0.35, 0.58),
                (0.93, 0.51),
                (0.76, 0.94),
                (0.06, 0.93),
                (0.04, 0.09),
                (0.47, 0.16),
                (0.89, 0.07),
            ),
            8: (
                (0.50, 0.70),
                (0.91, 0.53),
                (0.83, 0.99),
                (0.06, 0.92),
                (0.17, 0.44),
                (0.47, 0.15),
                (0.87, 0.03),
                (0.00, 0.03),
            ),
        },
        diameters={
            1: single_circle_diameter_px("portrait_post"),
            2: 400,
            3: 310,
            4: 285,
            5: 268,
            6: 255,
            7: 255,
            8: 245,
        },
    ),
    ("tiles", "square"): _build_circle_card_template(
        "square",
        bounds="cluster",
        layouts={
            1: _SINGLE_CIRCLE_LAYOUT,
            2: (
                (0.12, 0.22),
                (0.89, 0.75),
            ),
            3: (
                (0.59, 0.28),
                (0.96, 0.95),
                (0.06, 0.08),
            ),
            4: (
                (0.80, 0.93),
                (0.76, 0.06),
                (0.07, 0.91),
                (0.25, 0.18),
            ),
            5: (
                (0.51, 0.28),
                (0.93, 0.91),
                (0.22, 0.93),
                (0.03, 0.10),
                (0.96, 0.10),
            ),
            6: (
                (0.47, 0.17),
                (0.53, 0.92),
                (0.96, 0.94),
                (0.05, 0.89),
                (0.04, 0.06),
                (0.91, 0.07),
            ),
        },
        diameters={
            1: single_circle_diameter_px("square"),
            2: 365,
            3: 285,
            4: 275,
            5: 265,
            6: 250,
        },
    ),
}


def circle_card_template(
    card_type: TilesCircleCardType,
    fmt: FormatId,
) -> CircleCardTemplate | None:
    """Return a hand-tuned circle template, if one exists for this card and format."""
    return CIRCLE_CARD_TEMPLATES.get((card_type, fmt))


def circle_card_template_positions(
    template: CircleCardTemplate,
) -> dict[int, tuple[tuple[float, float], ...]]:
    return {count: spec.positions for count, spec in template.counts.items()}


def circle_card_template_diameters(template: CircleCardTemplate) -> dict[int, int]:
    return {
        count: spec.diameter
        for count, spec in template.counts.items()
        if spec.diameter is not None
    }


_STORY_TEMPLATE = CIRCLE_CARD_TEMPLATES[("tiles", "story")]
_PORTRAIT_TEMPLATE = CIRCLE_CARD_TEMPLATES[("tiles", "portrait_post")]
STORY_CIRCLE_LAYOUTS = circle_card_template_positions(_STORY_TEMPLATE)
STORY_CIRCLE_LAYOUT_DIAMETERS = circle_card_template_diameters(_STORY_TEMPLATE)
PORTRAIT_TILES_CIRCLE_LAYOUTS = circle_card_template_positions(_PORTRAIT_TEMPLATE)
PORTRAIT_TILES_CIRCLE_LAYOUT_DIAMETERS = circle_card_template_diameters(_PORTRAIT_TEMPLATE)
FORMAT_TILES_CIRCLE_LAYOUTS: dict[str, dict[int, tuple[tuple[float, float], ...]]] = {
    fmt: circle_card_template_positions(template)
    for (card_type, fmt), template in CIRCLE_CARD_TEMPLATES.items()
    if card_type == "tiles" and template.bounds == "cluster"
}
FORMAT_TILES_CIRCLE_LAYOUT_DIAMETERS: dict[str, dict[int, int]] = {
    fmt: circle_card_template_diameters(template)
    for (card_type, fmt), template in CIRCLE_CARD_TEMPLATES.items()
    if card_type == "tiles" and template.bounds == "cluster"
}


def _hand_tuned_body_bounds(
    bounds: CircleCardBoundsId,
    canvas_w: int,
    canvas_h: int,
    *,
    diameter: int,
) -> tuple[float, float, float, float]:
    """Pixel bounds for mapping normalised hand-tuned centre positions."""
    pad = diameter / 2 + _SHADOW_PAD_PX
    x_min, x_max = pad, canvas_w - pad
    if bounds == "story":
        y_min = _HAND_TUNED_CIRCLE_TOP_CLEARANCE / 2 + pad
        y_max = canvas_h - _HAND_TUNED_CIRCLE_BOTTOM_CLEARANCE - _SHADOW_PAD_PX - pad
    else:
        y_min, y_max = pad, canvas_h - pad
    return x_min, x_max, y_min, y_max


def _hand_tuned_edge_limits(
    bounds: CircleCardBoundsId,
    canvas_w: int,
    canvas_h: int,
) -> tuple[float, float, float, float]:
    """Allowed circle centre limits including radius and shadow (x_min, x_max, y_min, y_max)."""
    if bounds == "story":
        return (
            0.0,
            float(canvas_w),
            _HAND_TUNED_CIRCLE_TOP_CLEARANCE / 2,
            canvas_h - _HAND_TUNED_CIRCLE_BOTTOM_CLEARANCE - _SHADOW_PAD_PX,
        )
    return 0.0, float(canvas_w), 0.0, float(canvas_h)


def _hand_tuned_min_centre_distance(diameter: int, gap_px: int) -> float:
    min_edge_gap = max(float(gap_px), float(_HAND_TUNED_CIRCLE_MIN_EDGE_GAP_PX))
    return diameter + min_edge_gap + 2 * _SHADOW_PAD_PX


def _hand_tuned_template_centres(
    template: CircleCardTemplate,
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
) -> list[tuple[float, float]]:
    spec = template.counts.get(count)
    if spec is None:
        return []
    x_min, x_max, y_min, y_max = _hand_tuned_body_bounds(
        template.bounds,
        canvas_w,
        canvas_h,
        diameter=diameter,
    )
    x_span = max(0.0, x_max - x_min)
    y_span = max(0.0, y_max - y_min)
    return [
        (x_min + x_norm * x_span, y_min + y_norm * y_span)
        for x_norm, y_norm in spec.positions
    ]


def _hand_tuned_template_fits(
    template: CircleCardTemplate,
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
    gap_px: int,
) -> bool:
    centres = _hand_tuned_template_centres(
        template,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
    )
    if len(centres) != count:
        return False
    min_dist = _hand_tuned_min_centre_distance(diameter, gap_px)
    min_dist_sq = min_dist * min_dist
    pad = diameter / 2 + _SHADOW_PAD_PX
    x_lo, x_hi, y_lo, y_hi = _hand_tuned_edge_limits(
        template.bounds,
        canvas_w,
        canvas_h,
    )
    for i, (x1, y1) in enumerate(centres):
        for x2, y2 in centres[i + 1 :]:
            dx = x1 - x2
            dy = y1 - y2
            if dx * dx + dy * dy + 1e-6 < min_dist_sq:
                return False
        if (
            x1 - pad < x_lo
            or x1 + pad > x_hi
            or y1 - pad < y_lo
            or y1 + pad > y_hi
        ):
            return False
    return True


def _hand_tuned_template_within_canvas(
    template: CircleCardTemplate,
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
) -> bool:
    """True when every circle stays inside the canvas (playground hand-tune tolerance)."""
    centres = _hand_tuned_template_centres(
        template,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
    )
    if len(centres) != count:
        return False
    pad = diameter / 2 + _SHADOW_PAD_PX
    x_lo, x_hi, y_lo, y_hi = _hand_tuned_edge_limits(
        template.bounds,
        canvas_w,
        canvas_h,
    )
    return all(
        x_lo <= x - pad and x + pad <= x_hi and y_lo <= y - pad and y + pad <= y_hi
        for x, y in centres
    )


def _hand_tuned_template_diameter(
    template: CircleCardTemplate,
    count: int,
    canvas_w: int,
    canvas_h: int,
    *,
    gap_px: int,
) -> int:
    """Largest or fixed circle size that fits a hand-tuned template."""
    if count <= 0 or count not in template.counts:
        return 96
    fixed = template.counts[count].diameter
    if fixed is not None and (
        _hand_tuned_template_fits(
            template,
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=fixed,
            gap_px=gap_px,
        )
        or _hand_tuned_template_within_canvas(
            template,
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=fixed,
        )
    ):
        return fixed
    by_width = int(canvas_w * _HAND_TUNED_CIRCLE_WIDTH_FRACTION)
    for try_d in range(min(by_width, _HAND_TUNED_CIRCLE_MAX_DIAMETER_PX), 95, -1):
        if _hand_tuned_template_fits(
            template,
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=try_d,
            gap_px=gap_px,
        ):
            return try_d
    return 96


def _hand_tuned_compact_type_threshold(template: CircleCardTemplate) -> int:
    return 10 if template.bounds == "story" else 7


def _hand_tuned_template_canvas_html(
    pairs: list[tuple[str, str]],
    *,
    template: CircleCardTemplate,
    variant: CircleVariantId,
    canvas_w: int,
    canvas_h: int,
) -> str:
    count = len(pairs)
    spec = CIRCLE_VARIANT_SPECS[variant]
    gap_px = spec.gap_px
    diameter = _hand_tuned_template_diameter(
        template,
        count,
        canvas_w,
        canvas_h,
        gap_px=gap_px,
    )
    centres = _hand_tuned_template_centres(
        template,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
    )
    centres = _centres_in_grid_reading_order(centres)
    value_px, label_px = _hand_tuned_circle_typography(template, count, diameter)
    shadow = spec.shadow
    tiles = []
    for (label, value), (x, y) in zip(pairs, centres, strict=False):
        if label or value:
            tile = _circle_tile_html(
                label,
                value,
                diameter=diameter,
                value_px=value_px,
                label_px=label_px,
                shadow=shadow,
            )
        else:
            tile = _empty_circle_tile_html(diameter=diameter, shadow=shadow)
        tiles.append(
            f"""
<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;
  transform:translate(-50%,-50%);">
  {tile}
</div>"""
        )
    return f"""
<div style="position:relative;width:{canvas_w}px;height:{canvas_h}px;margin:0 auto;overflow:hidden;">
  {''.join(tiles)}
</div>"""


def _story_circle_body_bounds(
    canvas_w: int,
    canvas_h: int,
    *,
    diameter: int,
) -> tuple[float, float, float, float]:
    """Pixel bounds for circle centres inside the story card body."""
    return _hand_tuned_body_bounds(
        "story",
        canvas_w,
        canvas_h,
        diameter=diameter,
    )


def _story_circle_min_centre_distance(diameter: int, gap_px: int) -> float:
    return _hand_tuned_min_centre_distance(diameter, gap_px)


def _story_circle_template_centres(
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
) -> list[tuple[float, float]]:
    return _hand_tuned_template_centres(
        _STORY_TEMPLATE,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
    )


def _story_circle_fits(
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
    gap_px: int,
) -> bool:
    return _hand_tuned_template_fits(
        _STORY_TEMPLATE,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        gap_px=gap_px,
    )


def _story_circle_diameter(
    count: int,
    canvas_w: int,
    canvas_h: int,
    *,
    gap_px: int,
) -> int:
    return _hand_tuned_template_diameter(
        _STORY_TEMPLATE,
        count,
        canvas_w,
        canvas_h,
        gap_px=gap_px,
    )


def _story_template_canvas_html(
    pairs: list[tuple[str, str]],
    *,
    variant: CircleVariantId,
    canvas_w: int,
    canvas_h: int,
) -> str:
    return _hand_tuned_template_canvas_html(
        pairs,
        template=_STORY_TEMPLATE,
        variant=variant,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )


def _cluster_template_centres(
    layouts: dict[int, tuple[tuple[float, float], ...]],
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
) -> list[tuple[float, float]]:
    """Map normalised cluster templates to pixel centres (legacy helper)."""
    template = _build_circle_card_template(
        "portrait_post",
        bounds="cluster",
        layouts=layouts,
        diameters={},
    )
    return _hand_tuned_template_centres(
        template,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
    )


def _cluster_body_bounds(
    canvas_w: int,
    canvas_h: int,
    *,
    diameter: int,
) -> tuple[float, float, float, float]:
    return _hand_tuned_body_bounds("cluster", canvas_w, canvas_h, diameter=diameter)


def _cluster_template_fits(
    layouts: dict[int, tuple[tuple[float, float], ...]],
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
    gap_px: int,
) -> bool:
    template = _build_circle_card_template(
        "portrait_post",
        bounds="cluster",
        layouts=layouts,
        diameters={},
    )
    return _hand_tuned_template_fits(
        template,
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        gap_px=gap_px,
    )


def _cluster_template_diameter(
    layouts: dict[int, tuple[tuple[float, float], ...]],
    diameters: dict[int, int],
    count: int,
    canvas_w: int,
    canvas_h: int,
    *,
    gap_px: int,
) -> int:
    template = _build_circle_card_template(
        "portrait_post",
        bounds="cluster",
        layouts=layouts,
        diameters=diameters,
    )
    return _hand_tuned_template_diameter(
        template,
        count,
        canvas_w,
        canvas_h,
        gap_px=gap_px,
    )


def _cluster_template_canvas_html(
    pairs: list[tuple[str, str]],
    *,
    layouts: dict[int, tuple[tuple[float, float], ...]],
    diameters: dict[int, int],
    variant: CircleVariantId,
    canvas_w: int,
    canvas_h: int,
) -> str:
    template = _build_circle_card_template(
        "portrait_post",
        bounds="cluster",
        layouts=layouts,
        diameters=diameters,
    )
    return _hand_tuned_template_canvas_html(
        pairs,
        template=template,
        variant=variant,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )


def _circles_canvas_html(
    pairs: list[tuple[str, str]],
    *,
    variant: CircleVariantId,
    period_label: str,
    canvas_w: int,
    canvas_h: int,
    diameter_start: int | None = None,
) -> str:
    count = len(pairs)
    spec = CIRCLE_VARIANT_SPECS[variant]
    estimate = _circle_diameter(
        count,
        canvas_w,
        canvas_h,
        gap_px=spec.gap_px,
        ring_step=spec.ring_step,
    )
    search_from = (
        max(estimate, diameter_start) if diameter_start is not None else estimate
    )
    centres, diameter = place_circle_centers(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=search_from,
        variant=variant,
        period_label=period_label,
    )
    centres = _centres_in_grid_reading_order(centres)
    if count > 6:
        value_px, label_px = "40px", "16px"
    else:
        value_px, label_px = "48px", "18px"
    shadow = CIRCLE_VARIANT_SPECS[variant].shadow
    tiles = []
    for (label, value), (x, y) in zip(pairs, centres, strict=False):
        tile = _circle_tile_html(
            label,
            value,
            diameter=diameter,
            value_px=value_px,
            label_px=label_px,
            shadow=shadow,
        )
        tiles.append(
            f"""
<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;
  transform:translate(-50%,-50%);">
  {tile}
</div>"""
        )
    return f"""
<div style="position:relative;width:{canvas_w}px;height:{canvas_h}px;margin:0 auto;overflow:hidden;">
  {''.join(tiles)}
</div>"""


def layout_tiles_circle_cluster(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """Statistics Tiles stats in a wide radial circle cluster (production style)."""
    fmt_max = tiles_circle_cluster_max(fmt)
    if fmt == "story" and card_stat_labels:
        pairs = _resolve_story_circle_slot_pairs(
            stats,
            card_stat_labels[:fmt_max],
            all_time=all_time,
            geo_scope=geo_scope,
        )
    else:
        filled_labels = tuple(label for label in card_stat_labels if label)
        if filled_labels:
            pair_max = min(len(filled_labels), fmt_max)
        else:
            pair_max = TILES_CIRCLE_CLUSTER_MIN
        pairs = _resolve_card_stat_pairs(
            stats,
            layout="tiles",
            fmt=fmt,
            card_stat_labels=filled_labels,
            max_count=pair_max,
            all_time=all_time,
            geo_scope=geo_scope,
        )
    subtitle = _layout_subtitle(stats, "tiles")
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        width,
        height,
        fmt,
        scope_label=scope_label,
    )
    body_top, body_bottom, body_left, body_right = _tiles_circle_body_insets(
        fmt,
        scope_label=scope_label,
    )
    template = circle_card_template("tiles", fmt)
    if template is not None and len(pairs) in template.counts:
        circles_html = _hand_tuned_template_canvas_html(
            pairs,
            template=template,
            variant=TILES_CIRCLE_CLUSTER_VARIANT,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        )
    else:
        circles_html = _circles_canvas_html(
            pairs,
            variant=TILES_CIRCLE_CLUSTER_VARIANT,
            period_label=stats.period_label,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter_start=TILES_CIRCLE_DIAMETER_SEARCH_START,
        )
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  {_header_block(stats, subtitle=subtitle)}
  <div style="position:absolute;left:{body_left}px;right:{body_right}px;top:{body_top}px;
    bottom:{body_bottom}px;display:flex;justify-content:center;align-items:flex-start;overflow:hidden;">
    {circles_html}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _spotlight_circle_max_fit_diameter(canvas_w: int, canvas_h: int) -> int:
    """Largest circle diameter that fits the spotlight body canvas."""
    pad = _SPOTLIGHT_CIRCLE_EDGE_PAD_PX
    return min(canvas_w - 2 * pad, canvas_h - 2 * pad)


def _spotlight_circle_diameter(
    canvas_w: int,
    canvas_h: int,
    *,
    fmt: FormatId,
) -> int:
    """Single spotlight circle — same diameter as Statistics Tiles count-1 preset."""
    max_fit = _spotlight_circle_max_fit_diameter(canvas_w, canvas_h)
    target = single_circle_diameter_px(fmt)
    return max(
        _SPOTLIGHT_CIRCLE_MIN_DIAMETER_PX,
        min(target, max_fit),
    )


def _spotlight_circle_value_base_px(
    diameter: int,
    *,
    width: int,
    height: int,
) -> int:
    """Match classic spotlight num size (160/200px), capped to the circle width."""
    classic = 200 if height > width else 160
    inner_w = max(68, diameter - 44)
    max_by_width = int(inner_w / 0.58)
    return min(classic, max_by_width)


def layout_spotlight_circle(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """Spotlight stat in one large circle below the card header."""
    pair = spotlight_pair_for_label(
        stats,
        spotlight_label,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    if pair is None:
        title, value = spotlight_label, "—"
    else:
        title, value = pair
    pad_bottom = _footer_pad(fmt, width, height)
    subtitle = _layout_subtitle(stats, "spotlight")
    canvas_w, canvas_h = _circle_canvas_size(
        width,
        height,
        fmt,
        scope_label=scope_label,
    )
    diameter = _spotlight_circle_diameter(canvas_w, canvas_h, fmt=fmt)
    value_base = _spotlight_circle_value_base_px(
        diameter,
        width=width,
        height=height,
    )
    cx = canvas_w / 2
    cy = canvas_h / 2 - canvas_h * _CIRCLE_CLUSTER_UP_BIAS
    circle = _circle_tile_html(
        title,
        value,
        diameter=diameter,
        value_px=f"{value_base}px",
        label_px="24px",
        shadow=True,
    )
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  {_header_block(stats, subtitle=subtitle)}
  <div style="padding:0 48px {pad_bottom}px;display:flex;justify-content:center;">
    <div style="position:relative;width:{canvas_w}px;height:{canvas_h}px;margin:0 auto;overflow:hidden;">
      <div style="position:absolute;left:{cx:.1f}px;top:{cy:.1f}px;
        transform:translate(-50%,-50%);">
        {circle}
      </div>
    </div>
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _layout_tiles_circles(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    variant: CircleVariantId,
    card_stat_labels: tuple[str, ...] = (),
    stat_count: int | None = None,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    if stat_count is None:
        max_count = CIRCLE_LAYOUT_MAX_STATS if fmt == "story" else min(6, CIRCLE_LAYOUT_MAX_STATS)
    else:
        max_count = max(
            CIRCLE_LAYOUT_MIN_STATS,
            min(stat_count, CIRCLE_LAYOUT_MAX_STATS),
        )
    pairs = _resolve_card_stat_pairs(
        stats,
        layout="tiles",
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        max_count=max_count,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    pad_bottom = _footer_pad(fmt, width, height)
    subtitle = _layout_subtitle(stats, "tiles")
    canvas_w, canvas_h = _circle_canvas_size(
        width,
        height,
        fmt,
        scope_label=scope_label,
    )
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  {_header_block(stats, subtitle=subtitle)}
  <div style="padding:0 48px {pad_bottom}px;display:flex;justify-content:center;">
    {_circles_canvas_html(
        pairs,
        variant=variant,
        period_label=stats.period_label,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def render_circles_preview_html(
    stats: ShareSummaryStats,
    *,
    variant: CircleVariantId = "cluster_soft",
    fmt: FormatId = "square",
    scale: float = 1.0,
    card_stat_labels: tuple[str, ...] = (),
    stat_count: int | None = None,
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """HTML preview for one radial circle-cluster variant (default scale = export size)."""
    with _color_scheme_context(color_scheme_index):
        width, height = _FORMAT_PX[fmt]
        inner = _layout_tiles_circles(
            stats,
            width,
            height,
            fmt,
            variant=variant,
            card_stat_labels=card_stat_labels,
            stat_count=stat_count,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
        return _card_shell(width=width, height=height, inner_html=inner, scale=scale)


def circles_layout_non_overlapping(
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
    variant: CircleVariantId,
    period_label: str,
) -> bool:
    """True when placed circles do not overlap (for tests)."""
    centres, used_diameter = place_circle_centers(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        variant=variant,
        period_label=period_label,
    )
    if len(centres) != count:
        return False
    r = used_diameter / 2
    gap = float(CIRCLE_VARIANT_SPECS[variant].gap_px)
    for i, (x, y) in enumerate(centres):
        others = [c for j, c in enumerate(centres) if j != i]
        if _circles_overlap(x, y, r, others, gap=gap):
            return False
    return True


def circles_within_canvas(
    count: int,
    *,
    canvas_w: int,
    canvas_h: int,
    diameter: int,
    variant: CircleVariantId,
    period_label: str,
) -> bool:
    """True when every circle fits inside the canvas including shadow pad."""
    centres, used_diameter = place_circle_centers(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        variant=variant,
        period_label=period_label,
    )
    r = used_diameter / 2
    pad = r + _SHADOW_PAD_PX
    for x, y in centres:
        if x - pad < 0 or x + pad > canvas_w or y - pad < 0 or y + pad > canvas_h:
            return False
    return True


__all__ = [
    "CIRCLE_CARD_TEMPLATES",
    "CIRCLE_LAYOUT_MAX_STATS",
    "CIRCLE_LAYOUT_MIN_STATS",
    "CircleCardCountSpec",
    "CircleCardTemplate",
    "STORY_CIRCLE_LAYOUTS",
    "STORY_CIRCLE_LAYOUT_DIAMETERS",
    "PORTRAIT_TILES_CIRCLE_LAYOUTS",
    "PORTRAIT_TILES_CIRCLE_LAYOUT_DIAMETERS",
    "FORMAT_TILES_CIRCLE_LAYOUTS",
    "FORMAT_TILES_CIRCLE_LAYOUT_DIAMETERS",
    "circle_card_template",
    "circle_card_template_diameters",
    "circle_card_template_positions",
    "TILES_CIRCLE_CLUSTER_DEFAULT",
    "TILES_CIRCLE_CLUSTER_MAX",
    "TILES_CIRCLE_CLUSTER_PORTRAIT_MAX",
    "TILES_CIRCLE_CLUSTER_SQUARE_MAX",
    "TILES_CIRCLE_CLUSTER_STORY_MAX",
    "TILES_CIRCLE_CLUSTER_MIN",
    "TILES_CIRCLE_CLUSTER_VARIANT",
    "tiles_circle_cluster_max",
    "TILES_CIRCLE_DIAMETER_SEARCH_START",
    "CLUSTER_DIAMETER_SEARCH_START",
    "CIRCLE_VARIANT_IDS",
    "CIRCLE_VARIANT_LABELS",
    "CircleVariantId",
    "circles_layout_non_overlapping",
    "circles_within_canvas",
    "largest_cluster_diameter",
    "layout_tiles_circle_cluster",
    "place_circle_centers",
    "render_circles_preview_html",
]
