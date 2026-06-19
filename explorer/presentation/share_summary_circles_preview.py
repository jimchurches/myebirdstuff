"""
Circular statistics-grid experiments for share summary cards (#157).

Prototype-only — radial circle clusters on the card canvas (Statistics Grid stats).
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
from explorer.presentation.share_summary_preview import (
    FormatId,
    _FORMAT_PX,
    _card_shell,
    _colour,
    _color_scheme_context,
    _esc,
    _footer_block,
    _footer_pad,
    _header_block,
    _layout_subtitle,
    _resolve_card_stat_pairs,
)

CircleVariantId = Literal[
    "cluster_soft",
    "cluster_tight",
    "cluster_stagger_a",
    "cluster_stagger_b",
    "cluster_wide",
    "cluster_compact",
]

CIRCLE_LAYOUT_MAX_STATS = 9
CIRCLE_LAYOUT_MIN_STATS = 6
TILES_CIRCLE_CLUSTER_MIN = 6
TILES_CIRCLE_CLUSTER_MAX = 7
TILES_CIRCLE_CLUSTER_VARIANT: CircleVariantId = "cluster_wide"
_SHADOW_PAD_PX = 12


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
}

CIRCLE_VARIANT_LABELS: dict[CircleVariantId, str] = {
    key: spec.label for key, spec in CIRCLE_VARIANT_SPECS.items()
}
CIRCLE_VARIANT_IDS: tuple[CircleVariantId, ...] = tuple(CIRCLE_VARIANT_SPECS.keys())


_CIRCLE_CLUSTER_UP_BIAS = 0.07  # shift cluster up as fraction of canvas height


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
    if count <= 7:
        d_max = (avail - ring_step * gap_px) / (ring_step + 0.5)
    else:
        d_max = (avail - 2 * ring_step * gap_px) / (2 * ring_step + 0.5)
    width_cap = int(canvas_w * 0.20) if count > 6 else int(canvas_w * 0.23)
    return max(96, min(int(d_max), width_cap, 210))


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

    spec = CIRCLE_VARIANT_SPECS[variant]
    for try_d in range(diameter, 95, -4):
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
    bg = f"linear-gradient(145deg,{_colour('bg_alt')},{_colour('bg')})"
    border = f"2px solid {_colour('border')}"
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


def _centres_in_grid_reading_order(
    centres: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Top-to-bottom, left-to-right — matches Statistics Grid tile order."""
    return [
        centres[i]
        for i, _ in sorted(
            enumerate(centres),
            key=lambda item: (round(item[1][1], 1), round(item[1][0], 1)),
        )
    ]


def _circles_canvas_html(
    pairs: list[tuple[str, str]],
    *,
    variant: CircleVariantId,
    period_label: str,
    canvas_w: int,
    canvas_h: int,
) -> str:
    count = len(pairs)
    spec = CIRCLE_VARIANT_SPECS[variant]
    diameter = _circle_diameter(
        count,
        canvas_w,
        canvas_h,
        gap_px=spec.gap_px,
        ring_step=spec.ring_step,
    )
    centres, diameter = place_circle_centers(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
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
    """Statistics Grid stats in a wide radial circle cluster (production style)."""
    pairs = _resolve_card_stat_pairs(
        stats,
        layout="tiles",
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        max_count=TILES_CIRCLE_CLUSTER_MAX,
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
        variant=TILES_CIRCLE_CLUSTER_VARIANT,
        period_label=stats.period_label,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )}
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
    "CIRCLE_LAYOUT_MAX_STATS",
    "CIRCLE_LAYOUT_MIN_STATS",
    "TILES_CIRCLE_CLUSTER_MAX",
    "TILES_CIRCLE_CLUSTER_MIN",
    "TILES_CIRCLE_CLUSTER_VARIANT",
    "CIRCLE_VARIANT_IDS",
    "CIRCLE_VARIANT_LABELS",
    "CircleVariantId",
    "circles_layout_non_overlapping",
    "circles_within_canvas",
    "layout_tiles_circle_cluster",
    "place_circle_centers",
    "render_circles_preview_html",
]
