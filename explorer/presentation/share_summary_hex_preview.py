"""
Hexagonal statistics-grid experiments for share summary cards (#157).

Prototype-only — compares uniform-size honeycomb layouts using the same
color schemes as :mod:`explorer.presentation.share_summary_preview`.
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
    favourite_birds_for_card,
    _favourite_birds_block,
)

HexVariantId = Literal[
    "clip_flat_classic",
    "clip_flat_compact",
    "clip_flat_shadow",
    "clip_pointy",
    "svg_flat",
    "clip_flat_gradient",
    "tessellate_flat",
    "tessellate_flat_shadow",
    "tessellate_pointy",
    "blob_ring",
    "blob_spiral",
    "blob_cluster",
]

HexLayoutMode = Literal["overlap_rows", "organic_blob"]
OrganicMode = Literal["grow_tip", "grow_east", "grow_west", "grow_north", "hand_windy_a", "hand_windy_b"]


@dataclass(frozen=True)
class _HexVariantSpec:
    label: str
    layout: HexLayoutMode
    clip: Literal["flat", "pointy"]
    shadow: bool = False
    compact: bool = False
    strong_gradient: bool = False
    use_svg: bool = False
    organic: OrganicMode | None = None


HEX_VARIANT_SPECS: dict[HexVariantId, _HexVariantSpec] = {
    "clip_flat_classic": _HexVariantSpec(
        "Legacy — overlapping rows (dashboard-style, not target)",
        "overlap_rows",
        "flat",
    ),
    "clip_flat_compact": _HexVariantSpec(
        "Legacy — compact overlapping rows",
        "overlap_rows",
        "flat",
        compact=True,
    ),
    "clip_flat_shadow": _HexVariantSpec(
        "Legacy — overlapping rows with shadow",
        "overlap_rows",
        "flat",
        shadow=True,
    ),
    "clip_pointy": _HexVariantSpec(
        "Legacy — pointy overlapping rows",
        "overlap_rows",
        "pointy",
    ),
    "svg_flat": _HexVariantSpec(
        "Legacy — SVG overlapping rows",
        "overlap_rows",
        "flat",
        use_svg=True,
    ),
    "clip_flat_gradient": _HexVariantSpec(
        "Legacy — overlapping rows, strong gradient",
        "overlap_rows",
        "flat",
        strong_gradient=True,
    ),
    "tessellate_flat": _HexVariantSpec(
        "Organic hive — jagged tip growth, edge-to-edge",
        "organic_blob",
        "flat",
        organic="grow_tip",
    ),
    "tessellate_flat_shadow": _HexVariantSpec(
        "Organic hive — jagged growth with soft shadow",
        "organic_blob",
        "flat",
        shadow=True,
        organic="grow_tip",
    ),
    "tessellate_pointy": _HexVariantSpec(
        "Organic hive — pointy hex, jagged growth",
        "organic_blob",
        "pointy",
        organic="grow_tip",
    ),
    "blob_ring": _HexVariantSpec(
        "Organic hive — hand-tuned windy cluster A",
        "organic_blob",
        "flat",
        organic="hand_windy_a",
    ),
    "blob_spiral": _HexVariantSpec(
        "Organic hive — grow eastward (asymmetric drift)",
        "organic_blob",
        "flat",
        organic="grow_east",
    ),
    "blob_cluster": _HexVariantSpec(
        "Organic hive — hand-tuned windy cluster B",
        "organic_blob",
        "flat",
        organic="hand_windy_b",
    ),
}

HEX_VARIANT_LABELS: dict[HexVariantId, str] = {
    key: spec.label for key, spec in HEX_VARIANT_SPECS.items()
}
HEX_VARIANT_IDS: tuple[HexVariantId, ...] = tuple(HEX_VARIANT_SPECS.keys())

_CLIP_FLAT = "polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)"
_CLIP_POINTY = "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)"

_AXIAL_NEIGHBORS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (0, -1),
    (1, -1),
)

# Hand-tuned irregular blobs (connected, jagged edges, not row-balanced).
_ORGANIC_HAND_WINDY_A: dict[int, tuple[tuple[int, int], ...]] = {
    4: ((0, -1), (0, 0), (1, 0), (0, 1)),
    5: ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)),
    6: ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1), (1, 1)),
    7: ((0, -2), (0, -1), (-1, 0), (0, 0), (1, 0), (0, 1), (1, 1)),
    8: ((0, -2), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1)),
    9: ((0, -2), (-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (0, 1), (1, 1)),
    10: (
        (0, -2),
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (0, 0),
        (1, 0),
        (2, 0),
        (0, 1),
        (1, 1),
    ),
}

_ORGANIC_HAND_WINDY_B: dict[int, tuple[tuple[int, int], ...]] = {
    4: ((1, -1), (0, 0), (1, 0), (0, 1)),
    5: ((1, -1), (-1, 0), (0, 0), (1, 0), (2, 0)),
    6: ((1, -1), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1)),
    7: ((0, -2), (0, -1), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1)),
    8: ((0, -2), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (2, 0), (1, 1)),
    9: ((0, -2), (1, -1), (-1, -1), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1), (2, 1)),
    10: (
        (0, -2),
        (0, -1),
        (1, -1),
        (-1, 0),
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 0),
        (0, 1),
        (1, 1),
    ),
}


def _hex_rows_for_count(count: int) -> list[int]:
    """Row lengths for legacy overlapping-row layouts."""
    if count <= 0:
        return []
    if count <= 2:
        return [count]
    if count <= 4:
        return [2, count - 2]
    if count <= 6:
        return [3, count - 3]
    if count <= 8:
        return [4, count - 4]
    if count <= 10:
        return [4, 3, count - 7]
    return [4, 4, count - 8]


def _hex_size(*, compact: bool, pointy: bool) -> tuple[int, int]:
    hex_w = 236 if compact else 252
    if pointy:
        hex_h = int(hex_w * 1.1547005)
    else:
        hex_h = int(hex_w * 0.8660254)
    return hex_w, hex_h


def _axial_to_pixel(
    q: int,
    r: int,
    *,
    hex_w: int,
    pointy: bool,
) -> tuple[float, float]:
    """Axial (q, r) to pixel centre — edge-to-edge tessellation spacing."""
    if pointy:
        size = hex_w / math.sqrt(3)
        x = size * (1.5 * q)
        y = size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
    else:
        size = hex_w / 2
        x = size * math.sqrt(3) * (q + r / 2)
        y = size * 1.5 * r
    return x, y


def _organic_grow(
    count: int,
    *,
    mode: OrganicMode,
) -> list[tuple[int, int]]:
    """Grow a connected cluster from one seed; prefer jagged tips over filling holes."""
    if count <= 0:
        return []
    placed: set[tuple[int, int]] = {(0, 0)}
    order = [(0, 0)]
    while len(order) < count:
        frontier: dict[tuple[int, int], int] = {}
        for q, r in placed:
            for dq, dr in _AXIAL_NEIGHBORS:
                cell = (q + dq, r + dr)
                if cell in placed:
                    continue
                neigh = sum(
                    1
                    for dq2, dr2 in _AXIAL_NEIGHBORS
                    if (cell[0] + dq2, cell[1] + dr2) in placed
                )
                frontier[cell] = neigh
        if not frontier:
            break

        def rank(cell: tuple[int, int]) -> tuple[int, float, int, int]:
            q, r = cell
            neigh = frontier[cell]
            # Extend tips (1 neighbour) before shoulders (2) before interior fills (3+).
            tip_rank = 0 if neigh == 1 else (1 if neigh == 2 else 2)
            drift = 0.0
            if mode == "grow_east":
                drift = -float(q)
            elif mode == "grow_west":
                drift = float(q)
            elif mode == "grow_north":
                drift = float(r)
            elif mode == "grow_tip":
                drift = -float(abs(q) + abs(r) + abs(q + r))
            # Light asymmetry so ties break irregularly (not mirrored).
            wobble = (q * 3 + r * 5) % 7
            return (tip_rank, drift, wobble, abs(q) + abs(r))

        pick = min(frontier.keys(), key=rank)
        placed.add(pick)
        order.append(pick)
    return order


def _organic_coords(count: int, mode: OrganicMode) -> list[tuple[int, int]]:
    if mode == "hand_windy_a":
        preset = _ORGANIC_HAND_WINDY_A.get(count)
        if preset is not None:
            return list(preset)
        return _organic_grow(count, mode="grow_tip")
    if mode == "hand_windy_b":
        preset = _ORGANIC_HAND_WINDY_B.get(count)
        if preset is not None:
            return list(preset)
        return _organic_grow(count, mode="grow_east")
    return _organic_grow(count, mode=mode)


def _organic_positions(
    count: int,
    *,
    mode: OrganicMode,
    hex_w: int,
    pointy: bool,
) -> list[tuple[float, float]]:
    coords = _organic_coords(count, mode)
    raw = [_axial_to_pixel(q, r, hex_w=hex_w, pointy=pointy) for q, r in coords]
    cx = sum(x for x, _ in raw) / len(raw)
    cy = sum(y for _, y in raw) / len(raw)
    return [(x - cx, y - cy) for x, y in raw]


def _hex_face_style(*, spec: _HexVariantSpec) -> str:
    if spec.strong_gradient:
        bg = (
            f"linear-gradient(160deg,{_colour('bg_alt')} 0%,{_colour('bg')} 55%,"
            f"{_colour('bg_alt')} 100%)"
        )
        border = f"2px solid {_colour('border')}"
    else:
        bg = f"linear-gradient(145deg,{_colour('bg_alt')},{_colour('bg')})"
        border = f"1px solid {_colour('border')}"
    shadow = "filter:drop-shadow(0 6px 10px rgba(0,0,0,0.14));" if spec.shadow else ""
    clip = _CLIP_POINTY if spec.clip == "pointy" else _CLIP_FLAT
    return (
        f"width:100%;height:100%;display:flex;flex-direction:column;"
        f"align-items:center;justify-content:center;text-align:center;"
        f"background:{bg};border:{border};clip-path:{clip};{shadow}"
    )


def _hex_cell_clip(
    label: str,
    value: str,
    *,
    spec: _HexVariantSpec,
    hex_w: int,
    hex_h: int,
    value_px: str,
    label_px: str,
) -> str:
    face = _hex_face_style(spec=spec)
    pad = "18px 22px" if spec.compact else "22px 26px"
    return f"""
<div style="width:{hex_w}px;height:{hex_h}px;flex:0 0 auto;">
  <div style="{face}padding:{pad};box-sizing:border-box;">
    <div style="font-size:{value_px};font-weight:700;line-height:1.05;">{_esc(value)}</div>
    <div style="margin-top:8px;font-size:{label_px};color:{_colour('muted')};line-height:1.15;">
      {_esc(label)}</div>
  </div>
</div>"""


def _hex_cell_svg(
    label: str,
    value: str,
    *,
    spec: _HexVariantSpec,
    hex_w: int,
    hex_h: int,
    value_px: str,
    label_px: str,
    uid: str,
) -> str:
    del spec
    bg_alt = _colour("bg_alt")
    bg = _colour("bg")
    border = _colour("border")
    text = _colour("text")
    muted = _colour("muted")
    points = (
        f"{hex_w * 0.25},1 {hex_w * 0.75},1 {hex_w - 1},{hex_h * 0.5} "
        f"{hex_w * 0.75},{hex_h - 1} {hex_w * 0.25},{hex_h - 1} 1,{hex_h * 0.5}"
    )
    return f"""
<div style="width:{hex_w}px;height:{hex_h}px;flex:0 0 auto;">
  <svg width="{hex_w}" height="{hex_h}" viewBox="0 0 {hex_w} {hex_h}" role="img" aria-hidden="true">
    <defs>
      <linearGradient id="hexFill{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="{bg_alt}" />
        <stop offset="100%" stop-color="{bg}" />
      </linearGradient>
    </defs>
    <polygon points="{points}" fill="url(#hexFill{uid})" stroke="{border}" stroke-width="1.5" />
    <text x="50%" y="44%" text-anchor="middle" fill="{text}"
      font-family="system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"
      font-size="{value_px}" font-weight="700">{_esc(value)}</text>
    <text x="50%" y="62%" text-anchor="middle" fill="{muted}"
      font-family="system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"
      font-size="{label_px}">{_esc(label)}</text>
  </svg>
</div>"""


def _hex_cell_html(
    label: str,
    value: str,
    *,
    spec: _HexVariantSpec,
    hex_w: int,
    hex_h: int,
    value_px: str,
    label_px: str,
    uid: str = "",
) -> str:
    if spec.use_svg:
        return _hex_cell_svg(
            label,
            value,
            spec=spec,
            hex_w=hex_w,
            hex_h=hex_h,
            value_px=value_px,
            label_px=label_px,
            uid=uid,
        )
    return _hex_cell_clip(
        label,
        value,
        spec=spec,
        hex_w=hex_w,
        hex_h=hex_h,
        value_px=value_px,
        label_px=label_px,
    )


def _overlap_rows_html(
    pairs: list[tuple[str, str]],
    *,
    spec: _HexVariantSpec,
    fmt: FormatId,
) -> str:
    if fmt == "story" and len(pairs) > 6:
        value_px, label_px = "40px", "18px"
    else:
        value_px, label_px = "52px", "20px"
    hex_w, hex_h = _hex_size(compact=spec.compact, pointy=spec.clip == "pointy")
    row_overlap = int(hex_h * (0.30 if spec.compact else 0.26))
    row_gap = 4 if spec.compact else 12
    rows = _hex_rows_for_count(len(pairs))
    offset = int(hex_w * 0.5) + (row_gap // 2)
    row_blocks: list[str] = []
    idx = 0
    for row_i, row_len in enumerate(rows):
        cells = []
        for cell_i in range(row_len):
            if idx >= len(pairs):
                break
            label, value = pairs[idx]
            cells.append(
                _hex_cell_html(
                    label,
                    value,
                    spec=spec,
                    hex_w=hex_w,
                    hex_h=hex_h,
                    value_px=value_px,
                    label_px=label_px,
                    uid=f"r{row_i}c{cell_i}",
                )
            )
            idx += 1
        margin_top = f"-{row_overlap}px" if row_i else "0"
        margin_left = f"{offset}px" if row_i % 2 else "0"
        row_blocks.append(
            f"""
<div style="display:flex;justify-content:center;gap:{row_gap}px;
  margin-top:{margin_top};margin-left:{margin_left};">
  {''.join(cells)}
</div>"""
        )
    return f"""
<div style="display:flex;flex-direction:column;align-items:center;">
  {''.join(row_blocks)}
</div>"""


def _organic_blob_html(
    pairs: list[tuple[str, str]],
    *,
    spec: _HexVariantSpec,
    fmt: FormatId,
) -> str:
    if fmt == "story" and len(pairs) > 6:
        value_px, label_px = "40px", "18px"
    else:
        value_px, label_px = "52px", "20px"
    pointy = spec.clip == "pointy"
    hex_w, hex_h = _hex_size(compact=False, pointy=pointy)
    mode = spec.organic or "grow_tip"
    positions = _organic_positions(len(pairs), mode=mode, hex_w=hex_w, pointy=pointy)
    tops = [y - hex_h / 2 for _, y in positions]
    min_top = min(tops) if tops else 0.0
    cells = []
    for i, ((label, value), (x, y)) in enumerate(zip(pairs, positions, strict=False)):
        cell = _hex_cell_html(
            label,
            value,
            spec=spec,
            hex_w=hex_w,
            hex_h=hex_h,
            value_px=value_px,
            label_px=label_px,
            uid=str(i),
        )
        top = y - hex_h / 2 - min_top
        cells.append(
            f"""
<div style="position:absolute;left:calc(50% + {x:.1f}px);top:{top:.1f}px;
  transform:translate(-50%,0);">
  {cell}
</div>"""
        )
    max_bottom = max(y + hex_h / 2 - min_top for _, y in positions) if positions else hex_h
    height = int(max_bottom + 8)
    return f"""
<div style="position:relative;width:100%;height:{height}px;margin:0 auto;">
  {''.join(cells)}
</div>"""


def _hex_grid_html(
    pairs: list[tuple[str, str]],
    *,
    variant: HexVariantId,
    fmt: FormatId,
) -> str:
    spec = HEX_VARIANT_SPECS[variant]
    if spec.layout == "overlap_rows":
        return _overlap_rows_html(pairs, spec=spec, fmt=fmt)
    return _organic_blob_html(pairs, spec=spec, fmt=fmt)


def _layout_tiles_hex(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    variant: HexVariantId,
    favourite_birds: tuple[str, ...] = (),
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    pairs = _resolve_card_stat_pairs(
        stats,
        layout="tiles",
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    birds = favourite_birds_for_card("tiles", fmt, favourite_birds)
    favourite_block = _favourite_birds_block(birds, name_size_px=32)
    pad_bottom = _footer_pad(fmt, width, height, favourite_bird_count=len(birds))
    subtitle = _layout_subtitle(stats, "tiles")
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=subtitle)}
  <div style="padding:8px 48px {pad_bottom}px;display:flex;flex-direction:column;align-items:center;">
    {_hex_grid_html(pairs, variant=variant, fmt=fmt)}
    {favourite_block}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def render_hex_grid_preview_html(
    stats: ShareSummaryStats,
    *,
    variant: HexVariantId = "clip_flat_classic",
    fmt: FormatId = "square",
    scale: float = 0.38,
    favourite_birds: tuple[str, ...] = (),
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """Scaled HTML preview for one hex-grid variant."""
    with _color_scheme_context(color_scheme_index):
        width, height = _FORMAT_PX[fmt]
        inner = _layout_tiles_hex(
            stats,
            width,
            height,
            fmt,
            variant=variant,
            favourite_birds=favourite_birds,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
        return _card_shell(width=width, height=height, inner_html=inner, scale=scale)


def organic_cluster_connected(coords: list[tuple[int, int]]) -> bool:
    """True when every hex in *coords* is connected (for tests)."""
    if not coords:
        return True
    start = coords[0]
    placed = {start}
    frontier = [start]
    target = set(coords)
    while frontier:
        q, r = frontier.pop()
        for dq, dr in _AXIAL_NEIGHBORS:
            cell = (q + dq, r + dr)
            if cell in target and cell not in placed:
                placed.add(cell)
                frontier.append(cell)
    return placed == target


__all__ = [
    "HEX_VARIANT_IDS",
    "HEX_VARIANT_LABELS",
    "HexVariantId",
    "organic_cluster_connected",
    "render_hex_grid_preview_html",
]
