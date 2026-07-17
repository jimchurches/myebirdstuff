"""
HTML card layouts and preview/export entry points for share-summary cards.
"""

from __future__ import annotations

from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_INSIGHT_FACT_DEFAULT,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    share_summary_card_subtitle,
    share_summary_period_subtitle,
)
from explorer.core.share_summary_insight_facts import (
    InsightFactId,
    ShareSummaryInsightFact,
    format_insight_fact_metric,
    format_insight_peak_tie_note,
    insight_fact_by_id,
)
from explorer.presentation.share_summary_metrics import (
    _metrics_lookup,
    card_stat_pairs,
    layout_card_stat_max,
    resolve_spotlight_label,
    spotlight_pair_for_label,
)
from explorer.presentation.share_summary_rich_fact_layout import (
    rich_fact_layout_spec,
    rich_fact_line_style_css,
)
from explorer.presentation.share_summary_theme import (
    _FORMAT_PX,
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
    _color_scheme_context,
    _colour,
    _colour_or,
    _esc,
    _logo_svg_inline,
)

# Grid tile typography — belongs with layout rendering
_GRID_TILE_VALUE_PX = "52px"
_GRID_TILE_LABEL_PX = "20px"
_GRID_TILE_CELL_PAD = "32px 20px"
_GRID_TILE_GAP = "20px"


def _is_tall(fmt: FormatId, width: int, height: int) -> bool:
    return height > width


def _footer_pad(
    fmt: FormatId,
    width: int,
    height: int,
) -> int:
    """Reserve space above the absolute footer (logo + label ≈ 120px)."""
    del width, height
    if fmt == "story":
        return 140
    if fmt == "portrait_post":
        return 128
    return 120


def _card_shell(
    *,
    width: int,
    height: int,
    inner_html: str,
    scale: float = 0.38,
) -> str:
    """Fixed-size card scaled down for in-browser preview."""
    display_w = int(width * scale)
    display_h = int(height * scale)
    return f"""
<div class="pebird-share-preview-wrap" style="
  width:{display_w}px;height:{display_h}px;overflow:hidden;margin:0 auto 16px;
  border:1px solid {_colour("border")};border-radius:8px;background:{_colour("bg_alt")};
  box-shadow:0 1px 3px rgba(0,0,0,0.08);">
  <div style="
    width:{width}px;height:{height}px;overflow:hidden;
    transform:scale({scale});transform-origin:top left;
    font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
    background:{_colour("bg")};color:{_colour("text")};box-sizing:border-box;">
    {inner_html}
  </div>
</div>"""


def _subtitle_for_period(stats: ShareSummaryStats) -> str:
    if stats.trip_title:
        return stats.trip_title
    return share_summary_period_subtitle(stats.period_kind)


def _headline_for_period(stats: ShareSummaryStats) -> str:
    return stats.period_label


def _header_block(stats: ShareSummaryStats, *, subtitle: str | None = None) -> str:
    sub = subtitle if subtitle is not None else _subtitle_for_period(stats)
    headline = _headline_for_period(stats)
    title_size = (
        "96px" if len(headline) <= 5 else ("64px" if len(headline) > 28 else "72px")
    )
    sub_style = (
        f"margin:0 0 8px;font-size:28px;letter-spacing:0.08em;text-transform:uppercase;"
        f"color:{_colour('accent')};font-weight:600;"
    )
    return f"""
<div style="padding:48px 56px 24px;text-align:center;">
  <div style="{sub_style}">{_esc(sub)}</div>
  <h1 style="margin:0;font-size:{title_size};font-weight:700;line-height:1.08;">{_esc(headline)}</h1>
</div>"""


def _footer_block(*, scope_label: str | None = None) -> str:
    """Card footer chrome. ``<div>`` copy (not ``<p>``) so Streamlit preview keeps muted colour."""
    footer_muted = _colour("muted")
    logo = _logo_svg_inline(height_px=46, fill=footer_muted)
    logo_row = f'<div style="margin:4px 0;line-height:0;">{logo}</div>' if logo else ""
    scope_row = ""
    if scope_label:
        scope_row = (
            f'<div style="margin:0 0 7px;font-size:36px;font-weight:600;line-height:1.05;'
            f'letter-spacing:0.04em;">{_esc(scope_label)}</div>'
        )
    return f"""
<div style="position:absolute;left:0;right:0;bottom:0;padding:22px 56px 26px;text-align:center;
  color:{footer_muted};border-top:1px solid {_colour("border")};background:{_colour("bg_alt")};">
  {scope_row}
  {logo_row}
  <div style="margin:5px 0 0;font-size:18px;">Personal eBird Explorer</div>
</div>"""


def _is_empty_period(stats: ShareSummaryStats) -> bool:
    """True when stats were computed for a period with zero checklists."""
    return stats.checklists is not None and stats.checklists == 0


def _layout_empty_period(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    scope_label: str | None = None,
) -> str:
    """Dedicated no-data card when the period has zero checklists."""
    pad_bottom = _footer_pad(fmt, width, height)
    message_size = "40px" if _is_tall(fmt, width, height) else "36px"
    hint_size = "28px" if _is_tall(fmt, width, height) else "24px"
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  {_header_block(stats)}
  <div style="position:absolute;left:0;right:0;top:0;bottom:{pad_bottom}px;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:64px 56px 32px;text-align:center;box-sizing:border-box;">
    <div style="font-size:{message_size};font-weight:700;line-height:1.2;color:{_colour("text")};">
      No checklists in this period</div>
    <div style="margin-top:20px;font-size:{hint_size};color:{_colour("muted")};font-weight:500;max-width:80%;">
      Try a different date range in the sidebar.</div>
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _resolve_card_stat_pairs(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId,
    fmt: FormatId | None = None,
    card_stat_labels: tuple[str, ...] = (),
    max_count: int | None = None,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> list[tuple[str, str]]:
    lookup = _metrics_lookup(stats, all_time=all_time, geo_scope=geo_scope)
    available_count = len(lookup) if layout == "minimal" and fmt == "story" else None
    resolved_max = (
        max_count
        if max_count is not None
        else layout_card_stat_max(layout, fmt, available_stat_count=available_count)
    )
    if card_stat_labels:
        return card_stat_pairs(
            stats,
            max_count=resolved_max,
            selected_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
        )
    return card_stat_pairs(
        stats,
        max_count=resolved_max,
        layout=layout,
        all_time=all_time,
        geo_scope=geo_scope,
    )


def _layout_subtitle(stats: ShareSummaryStats, layout: LayoutId) -> str | None:
    """Layout-specific green subtitle; trip title wins on custom ranges."""
    return share_summary_card_subtitle(
        layout=layout,
        period_kind=stats.period_kind,
        trip_title=stats.trip_title,
    )


def _layout_tiles(
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
    pairs = _resolve_card_stat_pairs(
        stats,
        layout="tiles",
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    value_px, label_px, cell_pad, grid_gap = (
        _GRID_TILE_VALUE_PX,
        _GRID_TILE_LABEL_PX,
        _GRID_TILE_CELL_PAD,
        _GRID_TILE_GAP,
    )
    cells = []
    tile_bg_alt = _colour_or("tile_bg_alt", "bg_alt")
    tile_bg = _colour_or("tile_bg", "bg")
    tile_border = _colour_or("tile_border", "border")
    for label, value in pairs:
        cells.append(f"""
<div style="padding:{cell_pad};border-radius:12px;
  background:linear-gradient(145deg,{tile_bg_alt},{tile_bg});
  border:1px solid {tile_border};text-align:center;">
  <div style="font-size:{value_px};font-weight:700;">{_esc(value)}</div>
  <div style="margin-top:8px;font-size:{label_px};color:{_colour("muted")};">{_esc(label)}</div>
</div>""")
    cells_html = "".join(cells)
    grid_html = (
        f'<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));'
        f'gap:{grid_gap};">{cells_html}</div>'
    )
    pad_bottom = _footer_pad(fmt, width, height)
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "tiles"))}
  <div style="padding:8px 48px {pad_bottom}px;">
    {grid_html}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _layout_minimal(
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
    pairs = _resolve_card_stat_pairs(
        stats,
        layout="minimal",
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    if fmt == "story" and len(pairs) > 10:
        label_px, value_px, row_pad = "22px", "32px", "10px"
    elif fmt == "story" and len(pairs) > 6:
        label_px, value_px, row_pad = "24px", "38px", "12px"
    elif fmt == "square":
        # Tighter rows so six stats clear the enlarged footer scope label on 1080×1080.
        label_px, value_px, row_pad = "28px", "40px", "17px"
    else:
        label_px, value_px, row_pad = "28px", "44px", "20px"
    rows = []
    for label, value in pairs:
        rows.append(f"""
<div style="display:flex;justify-content:space-between;align-items:baseline;
  padding:{row_pad} 0;border-bottom:1px solid {_colour("border")};">
  <span style="font-size:{label_px};color:{_colour("muted")};">{_esc(label)}</span>
  <span style="font-size:{value_px};font-weight:700;">{_esc(value)}</span>
</div>""")
    pad_bottom = _footer_pad(fmt, width, height)
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "minimal"))}
  <div style="padding:24px 72px {pad_bottom}px;">
    {"".join(rows)}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _layout_spotlight_header_html(stats: ShareSummaryStats) -> str:
    """Shared period / trip header for classic Spotlight layout."""
    if stats.trip_title:
        return f"""
<p style="margin:0 0 8px;font-size:28px;letter-spacing:0.06em;text-transform:uppercase;
  color:{_colour("accent")};font-weight:600;">{_esc(stats.trip_title)}</p>
<p style="margin:0 0 28px;font-size:36px;font-weight:700;line-height:1.1;color:{_colour("text")};">
  {_esc(stats.period_label)}</p>"""
    subtitle = _layout_subtitle(stats, "spotlight")
    if subtitle:
        return f"""
<p style="margin:0 0 8px;font-size:28px;letter-spacing:0.08em;text-transform:uppercase;
  color:{_colour("accent")};font-weight:600;">{_esc(subtitle)}</p>
<p style="margin:0 0 32px;font-size:36px;font-weight:700;line-height:1.1;color:{_colour("text")};">
  {_esc(stats.period_label)}</p>"""
    return f"""
<p style="margin:0 0 32px;font-size:36px;letter-spacing:0.04em;color:{_colour("accent")};font-weight:600;">
  {_esc(stats.period_label)}</p>"""


def _layout_insight(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    insight_fact: ShareSummaryInsightFact,
    scope_label: str | None = None,
) -> str:
    """Interesting Insights — label, hero text, optional metric, and peak-tie note."""
    pad_bottom = _footer_pad(fmt, width, height)
    spec = rich_fact_layout_spec(fmt)
    metric = format_insight_fact_metric(insight_fact)
    tie_note = format_insight_peak_tie_note(insight_fact)
    label_css = rich_fact_line_style_css(
        spec.label,
        colour=_colour(spec.label.color_role),
    )
    primary_css = rich_fact_line_style_css(
        spec.primary,
        colour=_colour(spec.primary.color_role),
    )
    metric_line = ""
    if metric:
        metric_css = rich_fact_line_style_css(
            spec.metric,
            colour=_colour(spec.metric.color_role),
        )
        metric_line = (
            f'<div class="rich-metric" style="{metric_css}">{_esc(metric)}</div>'
        )
    note_line = ""
    if tie_note:
        note_css = rich_fact_line_style_css(
            spec.note,
            colour=_colour(spec.note.color_role),
        )
        note_line = f'<div class="rich-note" style="{note_css}">{_esc(tie_note)}</div>'
    offset = spec.block_offset_y_px
    transform = f"transform:translateY({offset}px);" if offset else ""
    tile_css = ""
    if spec.tile_frame:
        tile_bg_alt = _colour_or("tile_bg_alt", "bg_alt")
        tile_bg = _colour_or("tile_bg", "bg")
        tile_border = _colour_or("tile_border", "border")
        tile_css = (
            f"padding:{_GRID_TILE_CELL_PAD};border-radius:12px;box-sizing:border-box;"
            f"background:linear-gradient(145deg,{tile_bg_alt},{tile_bg});"
            f"border:1px solid {tile_border};text-align:center;"
        )
    inner_block = (
        f'<div class="rich-label" style="{label_css}">{_esc(insight_fact.label)}</div>'
        f'<div class="rich-primary" style="{primary_css};word-wrap:break-word;">'
        f"{_esc(insight_fact.primary_text)}</div>{metric_line}{note_line}"
    )
    if tile_css:
        inner_block = f'<div style="{tile_css}">{inner_block}</div>'
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;display:flex;flex-direction:column;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "insight"))}
  <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:8px 48px {pad_bottom}px;text-align:center;box-sizing:border-box;min-height:0;">
    <div style="max-width:{spec.max_width_px}px;width:100%;{transform}">{inner_block}</div>
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def resolve_insight_fact(
    facts: list[ShareSummaryInsightFact],
    fact_id: InsightFactId | str | None,
) -> ShareSummaryInsightFact | None:
    """Pick an insight fact by id, falling back to the default or first available."""
    if not facts:
        return None
    cleaned = (fact_id or "").strip()
    if cleaned:
        found = insight_fact_by_id(facts, cleaned)  # type: ignore[arg-type]
        if found is not None:
            return found
    default = insight_fact_by_id(facts, SHARE_SUMMARY_INSIGHT_FACT_DEFAULT)
    return default or facts[0]


def _layout_spotlight(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    spotlight_label: str = SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
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
    num_size = "200px" if _is_tall(fmt, width, height) else "160px"
    label_size = "40px" if _is_tall(fmt, width, height) else "36px"
    header_html = _layout_spotlight_header_html(stats)
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  <div style="position:absolute;left:0;right:0;top:0;bottom:{pad_bottom}px;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:64px 56px 32px;text-align:center;box-sizing:border-box;">
    {header_html}
    <div style="font-size:{num_size};font-weight:800;line-height:1.05;color:{_colour("text")};">
      {_esc(value)}</div>
    <div style="margin-top:20px;font-size:{label_size};color:{_colour("muted")};font-weight:500;">
      {_esc(title)}</div>
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _card_inner_html(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId,
    fmt: FormatId,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    spotlight_label: str | None = None,
    insight_fact: ShareSummaryInsightFact | None = None,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> tuple[str, int, int]:
    """Return (inner HTML, width, height) at export pixel dimensions."""
    width, height = _FORMAT_PX[fmt]
    if _is_empty_period(stats):
        return (
            _layout_empty_period(stats, width, height, fmt, scope_label=scope_label),
            width,
            height,
        )
    if layout == "insight":
        if insight_fact is None:
            raise ValueError("insight_fact is required for layout='insight'")
        inner = _layout_insight(
            stats,
            width,
            height,
            fmt,
            insight_fact=insight_fact,
            scope_label=scope_label,
        )
    elif layout == "spotlight":
        label = resolve_spotlight_label(spotlight_label)
        if spotlight_presentation == "circle":
            from explorer.presentation.share_summary_circles_preview import (
                layout_spotlight_circle,
            )

            inner = layout_spotlight_circle(
                stats,
                width,
                height,
                fmt,
                spotlight_label=label,
                all_time=all_time,
                geo_scope=geo_scope,
                scope_label=scope_label,
            )
        else:
            inner = _layout_spotlight(
                stats,
                width,
                height,
                fmt,
                spotlight_label=label,
                all_time=all_time,
                geo_scope=geo_scope,
                scope_label=scope_label,
            )
    elif layout == "tiles" and tiles_presentation == "circles":
        from explorer.presentation.share_summary_circles_preview import (
            layout_tiles_circle_cluster,
        )

        inner = layout_tiles_circle_cluster(
            stats,
            width,
            height,
            fmt,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
    elif layout == "tiles":
        inner = _layout_tiles(
            stats,
            width,
            height,
            fmt,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
    else:
        inner = _layout_minimal(
            stats,
            width,
            height,
            fmt,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
    return inner, width, height


def render_share_summary_export_html(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId = "tiles",
    fmt: FormatId = "square",
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    spotlight_label: str | None = None,
    insight_fact: ShareSummaryInsightFact | None = None,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """Full-size HTML document for headless screenshot (Playwright PNG export)."""
    with _color_scheme_context(color_scheme_index):
        inner, width, height = _card_inner_html(
            stats,
            layout=layout,
            fmt=fmt,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
            spotlight_label=spotlight_label,
            insight_fact=insight_fact,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width={width}, height={height}" />
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    padding: 0;
    width: {width}px;
    height: {height}px;
    overflow: hidden;
  }}
</style>
</head>
<body>
<div style="
  width:{width}px;height:{height}px;overflow:hidden;
  font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  background:{_colour("bg")};color:{_colour("text")};">
  {inner}
</div>
</body>
</html>"""


def render_share_summary_preview_html(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId = "tiles",
    fmt: FormatId = "square",
    tiles_presentation: TilesPresentationId = "grid",
    scale: float = 0.38,
    spotlight_presentation: SpotlightPresentationId = "classic",
    spotlight_label: str | None = None,
    insight_fact: ShareSummaryInsightFact | None = None,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """Return scaled HTML preview for one layout + aspect ratio."""
    with _color_scheme_context(color_scheme_index):
        labels = card_stat_labels if layout in ("tiles", "minimal") else ()
        inner, width, height = _card_inner_html(
            stats,
            layout=layout,
            fmt=fmt,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
            spotlight_label=spotlight_label,
            insight_fact=insight_fact,
            card_stat_labels=labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
        return _card_shell(width=width, height=height, inner_html=inner, scale=scale)
