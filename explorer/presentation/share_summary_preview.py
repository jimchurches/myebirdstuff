"""
HTML layout prototypes for social-media-style birding summaries (#157).

Standalone design utility — not wired into the main explorer app yet.
"""

from __future__ import annotations

import html as html_module
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Literal

from explorer.core.checklist_stats_compute import ChecklistStatsPayload
from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryStats,
    compute_share_summary_stats,
    period_for_custom,
    period_for_iso_week,
    period_for_month,
    period_for_week_containing,
    period_for_year,
)

from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT,
    SHARE_SUMMARY_COLOR_SCHEMES,
    SHARE_SUMMARY_HERO_DEFAULT_STATS,
    SHARE_SUMMARY_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_SPOTLIGHT_STAT_DEFAULT,
)

LayoutId = Literal["hero", "tiles", "minimal", "spotlight"]
FormatId = Literal["square", "portrait_post", "story"]
SpotlightStatId = Literal["species", "lifers", "checklists", "locations"]


def _colour(key: str) -> str:
    schemes = SHARE_SUMMARY_COLOR_SCHEMES
    idx = SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT
    scheme = schemes[idx] if 0 <= idx < len(schemes) else schemes[0]
    return scheme[key]


_FORMAT_PX: dict[FormatId, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait_post": (1080, 1350),
    "story": (1080, 1920),
}

_FORMAT_LABELS: dict[FormatId, str] = {
    "square": "Square post (1080×1080)",
    "portrait_post": "Portrait post (1080×1350)",
    "story": "Story (1080×1920)",
}

_STAT_LABELS: dict[str, str] = {
    "species": "Total species",
    "families": "Total bird families",
    "individuals": "Total individuals",
    "checklists": "Total checklists",
    "locations": "Unique locations",
    "lifers": "Lifers",
    "birding_hours": "Total birding hours",
    "days_with_checklist": "Birding days",
    "longest_streak": "Longest streak",
    "countries": "Countries",
}

_SPOTLIGHT_TITLES: dict[SpotlightStatId, str] = {
    "lifers": "Lifers",
    "checklists": "Checklists",
    "locations": "Locations visited",
}


def spotlight_species_label(period_kind: PeriodKind) -> str:
    """Spotlight label for species count — matches selected period."""
    if period_kind == "year":
        return "Year birds"
    if period_kind == "month":
        return "Month birds"
    if period_kind == "week":
        return "Week birds"
    return "Species"


def spotlight_stat_label(stat: SpotlightStatId, period_kind: PeriodKind) -> str:
    """Human label for a spotlight stat (sidebar + card)."""
    if stat == "species":
        return spotlight_species_label(period_kind)
    return _SPOTLIGHT_TITLES[stat]

_YEARLY_ICON_RE = re.compile(
    r'\s*<span class="stats-info-icon">.*?</span>',
    flags=re.DOTALL,
)

_LOGO_PATH = Path(__file__).resolve().parents[2] / "docs" / "explorer" / "assets" / "personal-ebird-explorer-logo.svg"


@lru_cache(maxsize=1)
def _logo_svg_inline(*, height_px: int = 56, accent: bool = True) -> str:
    """Small inline logo for card headers/footers."""
    if not _LOGO_PATH.is_file():
        return ""
    raw = _LOGO_PATH.read_text(encoding="utf-8")
    fill = _colour("accent") if accent else _colour("muted")
    raw = raw.replace('fill="#000000"', f'fill="{fill}"')
    return (
        f'<img src="data:image/svg+xml;base64,{_svg_to_data_uri(raw)}" '
        f'alt="" style="height:{height_px}px;width:auto;display:block;margin:0 auto;" />'
    )


def _svg_to_data_uri(svg: str) -> str:
    import base64

    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def stat_pairs(stats: ShareSummaryStats) -> list[tuple[str, str]]:
    """Ordered (label, display value) pairs for layouts; skips missing stats."""
    raw: list[tuple[str, int | float | None, str]] = [
        ("species", stats.species, "species"),
        ("lifers", stats.lifers, "lifers"),
        ("checklists", stats.checklists, "checklists"),
        ("locations", stats.locations, "locations"),
        ("families", stats.families, "families"),
        ("individuals", stats.individuals, "individuals"),
        ("days_with_checklist", stats.days_with_checklist, "birding_days"),
        ("countries", stats.countries, "countries"),
        ("longest_streak", stats.longest_streak, "streak"),
        ("birding_hours", stats.birding_hours, "hours"),
    ]
    out: list[tuple[str, str]] = []
    for key, val, fmt in raw:
        if val is None:
            continue
        if fmt == "hours":
            display = f"{val:,.1f}" if val else "—"
            label = "Birding hours"
        elif fmt == "birding_days":
            display = f"{int(val):,}"
            label = "Birding days"
        elif fmt == "countries":
            display = f"{int(val):,}"
            label = "Countries"
        elif fmt == "streak":
            display = f"{int(val):,}"
            label = "Longest streak (days)"
        else:
            display = f"{int(val):,}"
            label = _STAT_LABELS.get(key, key.replace("_", " ").title())
        out.append((label, display))
    return out


def summary_status_metrics(
    stats: ShareSummaryStats,
    *,
    world_bird_coverage_pct: float | None = None,
) -> list[tuple[str, str]]:
    """Metrics row above card previews (period stats + optional global coverage).

    World bird coverage is **not** included on card tiles — status row only until layout TBD.
    """
    pairs = list(stat_pairs(stats))
    if world_bird_coverage_pct is not None:
        pairs.append(("World bird coverage", f"{world_bird_coverage_pct:.1f}%"))
    return pairs


def card_stat_pairs(
    stats: ShareSummaryStats,
    *,
    max_count: int,
    layout: LayoutId | None = None,
) -> list[tuple[str, str]]:
    """Stats for share cards — layout defaults first, then any remaining computed stats."""
    all_p = stat_pairs(stats)
    lookup = {label: value for label, value in all_p}

    if layout == "hero":
        preferred = SHARE_SUMMARY_HERO_DEFAULT_STATS
    elif layout in ("tiles", "minimal"):
        preferred = SHARE_SUMMARY_TILES_DEFAULT_STATS
    elif max_count <= 4:
        preferred = SHARE_SUMMARY_HERO_DEFAULT_STATS
    else:
        preferred = SHARE_SUMMARY_TILES_DEFAULT_STATS

    labels: list[str] = []
    for lab in preferred:
        if lab in lookup and lab not in labels:
            labels.append(lab)
    for lab, _ in all_p:
        if lab not in labels:
            labels.append(lab)

    return [(lab, lookup[lab]) for lab in labels[:max_count]]


def spotlight_value(stats: ShareSummaryStats, stat: SpotlightStatId) -> tuple[str, str] | None:
    """Return (title, display value) for single-stat spotlight cards."""
    values: dict[SpotlightStatId, int | None] = {
        "species": stats.species,
        "lifers": stats.lifers,
        "checklists": stats.checklists,
        "locations": stats.locations,
    }
    val = values[stat]
    if val is None:
        return None
    title = spotlight_stat_label(stat, stats.period_kind)
    return title, f"{int(val):,}"


def _strip_yearly_label(label: str) -> str:
    return _YEARLY_ICON_RE.sub("", label or "").strip()


def _parse_display_int(cell: str) -> int | None:
    s = (cell or "").strip().replace(",", "")
    if not s or s == "—":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_display_float(cell: str) -> float | None:
    s = (cell or "").strip().replace(",", "")
    if not s or s == "—":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _yearly_row_lookup(
    yearly_rows: Iterable[tuple[str, list[str]]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for label, vals in yearly_rows:
        out[_strip_yearly_label(label)] = list(vals)
    return out


def _countries_in_year_from_payload(payload: ChecklistStatsPayload, year: int) -> int | None:
    """Count countries with checklists in *year* (from Country tab payload blocks)."""
    sections = payload.country_sections or []
    if not sections:
        return None
    count = 0
    for country_key, years, _rows in sections:
        if not country_key or country_key == "_UNKNOWN" or not years:
            continue
        if year in years:
            count += 1
    return count if count > 0 else None


def share_summary_stats_for_year(
    payload: ChecklistStatsPayload,
    year: int,
) -> ShareSummaryStats | None:
    """Extract summary stats for one calendar year from a checklist stats payload.

    Reads the Yearly Summary table rows in *payload* plus country blocks for
    **Countries**. ``longest_streak`` is left ``None`` here — yearly rows do not
    include per-year streak; use :func:`compute_share_summary_stats` with
    :func:`period_for_year` when a full year card is needed from raw CSV data.
    """
    years = list(payload.years_list or [])
    if year not in years:
        return None
    idx = years.index(year)
    rows = _yearly_row_lookup(payload.yearly_rows or [])

    def _int(label: str) -> int | None:
        vals = rows.get(label)
        if not vals or idx >= len(vals):
            return None
        return _parse_display_int(vals[idx])

    def _float(label: str) -> float | None:
        vals = rows.get(label)
        if not vals or idx >= len(vals):
            return None
        return _parse_display_float(vals[idx])

    return ShareSummaryStats(
        period_label=str(year),
        period_kind="year",
        species=_int("Total species"),
        lifers=_int("Lifers"),
        checklists=_int("Total checklists"),
        locations=_int("Unique locations"),
        families=_int("Total bird families"),
        individuals=_int("Total individuals"),
        days_with_checklist=_int("Days with checklist"),
        birding_hours=_float("Total birding hours"),
        countries=_countries_in_year_from_payload(payload, year),
    )


def sample_share_summary_stats(
    *,
    period_label: str = "2025",
    period_kind: PeriodKind = "year",
    trip_title: str | None = None,
) -> ShareSummaryStats:
    """Dummy stats for layout tuning without eBird data."""
    # Illustrative counts per period so previews change when toggling range in sample mode.
    demo: dict[PeriodKind, dict[str, int | float]] = {
        "year": {
            "species": 312,
            "lifers": 47,
            "checklists": 186,
            "locations": 42,
            "families": 89,
            "individuals": 12_450,
            "days_with_checklist": 98,
            "birding_hours": 214.5,
            "longest_streak": 14,
            "countries": 5,
        },
        "week": {
            "species": 34,
            "lifers": 2,
            "checklists": 6,
            "locations": 4,
            "families": 28,
            "individuals": 420,
            "days_with_checklist": 5,
            "birding_hours": 12.0,
            "countries": 2,
        },
        "month": {
            "species": 89,
            "lifers": 8,
            "checklists": 22,
            "locations": 11,
            "families": 45,
            "individuals": 1_840,
            "days_with_checklist": 14,
            "birding_hours": 38.5,
            "longest_streak": 5,
            "countries": 3,
        },
        "custom": {
            "species": 56,
            "lifers": 3,
            "checklists": 8,
            "locations": 6,
            "families": 32,
            "individuals": 680,
            "days_with_checklist": 7,
            "birding_hours": 18.0,
            "countries": 2,
        },
    }
    d = demo.get(period_kind, demo["year"])
    return ShareSummaryStats(
        period_label=period_label,
        period_kind=period_kind,
        trip_title=trip_title,
        species=int(d["species"]),
        lifers=int(d["lifers"]),
        checklists=int(d["checklists"]),
        locations=int(d["locations"]),
        families=int(d["families"]),
        individuals=int(d["individuals"]),
        days_with_checklist=int(d["days_with_checklist"]),
        birding_hours=float(d["birding_hours"]),
        longest_streak=int(d["longest_streak"]) if "longest_streak" in d else None,
        countries=int(d["countries"]) if "countries" in d else None,
    )


def _esc(text: Any) -> str:
    return html_module.escape(str(text), quote=False)


def _is_tall(fmt: FormatId, width: int, height: int) -> bool:
    return height > width


def _footer_pad(fmt: FormatId, width: int, height: int) -> int:
    if fmt == "story":
        return 140
    if fmt == "portrait_post":
        return 120
    return 80


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
    if stats.period_kind == "year":
        return "Birding year in review"
    if stats.period_kind == "month":
        return "Monthly birding summary"
    if stats.period_kind == "week":
        return "Weekly birding summary"
    return "Birding summary"


def _headline_for_period(stats: ShareSummaryStats) -> str:
    return stats.period_label


def _header_block(stats: ShareSummaryStats, *, subtitle: str | None = None) -> str:
    sub = subtitle if subtitle is not None else _subtitle_for_period(stats)
    headline = _headline_for_period(stats)
    title_size = "96px" if len(headline) <= 5 else ("64px" if len(headline) > 28 else "72px")
    sub_style = (
        f"margin:0 0 8px;font-size:28px;letter-spacing:0.08em;text-transform:uppercase;"
        f"color:{_colour('accent')};font-weight:600;"
    )
    return f"""
<div style="padding:48px 56px 24px;text-align:center;">
  <p style="{sub_style}">{_esc(sub)}</p>
  <h1 style="margin:0;font-size:{title_size};font-weight:700;line-height:1.08;">{_esc(headline)}</h1>
</div>"""


def _footer_block() -> str:
    logo = _logo_svg_inline(height_px=40, accent=False)
    logo_row = logo if logo else ""
    return f"""
<div style="position:absolute;left:0;right:0;bottom:0;padding:24px 56px 28px;text-align:center;
  border-top:1px solid {_colour("border")};background:{_colour("bg_alt")};">
  {logo_row}
  <p style="margin:8px 0 0;font-size:20px;color:{_colour("muted")};">Personal eBird Explorer</p>
</div>"""


def _layout_hero(stats: ShareSummaryStats, width: int, height: int, fmt: FormatId) -> str:
    pairs = card_stat_pairs(stats, max_count=4, layout="hero")
    cells = []
    for label, value in pairs:
        cells.append(f"""
<div style="flex:1;min-width:40%;padding:28px 24px;border:1px solid {_colour("border")};
  border-radius:16px;background:{_colour("bg_alt")};text-align:center;">
  <div style="font-size:64px;font-weight:700;line-height:1.1;">{_esc(value)}</div>
  <div style="margin-top:12px;font-size:24px;color:{_colour("muted")};">{_esc(label)}</div>
</div>""")
    pad_bottom = _footer_pad(fmt, width, height)
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats)}
  <div style="display:flex;flex-wrap:wrap;gap:24px;padding:16px 56px {pad_bottom}px;justify-content:center;">
    {''.join(cells)}
  </div>
  {_footer_block()}
</div>"""


def _layout_subtitle(stats: ShareSummaryStats, layout_default: str) -> str | None:
    """Layout-specific green subtitle; trip title wins on custom ranges."""
    if stats.trip_title:
        return None
    return layout_default


def _layout_tiles(stats: ShareSummaryStats, width: int, height: int, fmt: FormatId) -> str:
    pairs = card_stat_pairs(stats, max_count=6, layout="tiles")
    cells = []
    for label, value in pairs:
        cells.append(f"""
<div style="flex:1 1 30%;min-width:28%;padding:32px 20px;border-radius:12px;
  background:linear-gradient(145deg,{_colour("bg_alt")},{_colour("bg")});
  border:1px solid {_colour("border")};text-align:center;">
  <div style="font-size:52px;font-weight:700;">{_esc(value)}</div>
  <div style="margin-top:8px;font-size:20px;color:{_colour("muted")};">{_esc(label)}</div>
</div>""")
    pad_bottom = _footer_pad(fmt, width, height)
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "My birding stats"))}
  <div style="display:flex;flex-wrap:wrap;gap:20px;padding:8px 48px {pad_bottom}px;">
    {''.join(cells)}
  </div>
  {_footer_block()}
</div>"""


def _layout_minimal(stats: ShareSummaryStats, width: int, height: int, fmt: FormatId) -> str:
    pairs = card_stat_pairs(stats, max_count=6, layout="minimal")
    rows = []
    for label, value in pairs:
        rows.append(f"""
<div style="display:flex;justify-content:space-between;align-items:baseline;
  padding:20px 0;border-bottom:1px solid {_colour("border")};">
  <span style="font-size:28px;color:{_colour("muted")};">{_esc(label)}</span>
  <span style="font-size:44px;font-weight:700;">{_esc(value)}</span>
</div>""")
    pad_bottom = _footer_pad(fmt, width, height)
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "Summary"))}
  <div style="padding:24px 72px {pad_bottom}px;">
    {''.join(rows)}
  </div>
  {_footer_block()}
</div>"""


def _layout_spotlight(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    spotlight_stat: SpotlightStatId = SHARE_SUMMARY_SPOTLIGHT_STAT_DEFAULT,
) -> str:
    pair = spotlight_value(stats, spotlight_stat)
    if pair is None:
        title, value = "Lifers", "—"
    else:
        title, value = pair
    pad_bottom = _footer_pad(fmt, width, height)
    num_size = "200px" if _is_tall(fmt, width, height) else "160px"
    label_size = "40px" if _is_tall(fmt, width, height) else "36px"
    if stats.trip_title:
        header_html = f"""
<p style="margin:0 0 8px;font-size:28px;letter-spacing:0.06em;text-transform:uppercase;
  color:{_colour('accent')};font-weight:600;">{_esc(stats.trip_title)}</p>
<p style="margin:0 0 28px;font-size:36px;font-weight:700;line-height:1.1;color:{_colour('text')};">
  {_esc(stats.period_label)}</p>"""
    else:
        header_html = f"""
<p style="margin:0 0 32px;font-size:36px;letter-spacing:0.04em;color:{_colour('accent')};font-weight:600;">
  {_esc(stats.period_label)}</p>"""
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  <div style="position:absolute;left:0;right:0;top:0;bottom:{pad_bottom}px;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:64px 56px 32px;text-align:center;box-sizing:border-box;">
    {header_html}
    <div style="font-size:{num_size};font-weight:800;line-height:1.05;color:{_colour('text')};">
      {_esc(value)}</div>
    <div style="margin-top:20px;font-size:{label_size};color:{_colour('muted')};font-weight:500;">
      {_esc(title)}</div>
  </div>
  {_footer_block()}
</div>"""


_LAYOUT_BUILDERS = {
    "hero": _layout_hero,
    "tiles": _layout_tiles,
    "minimal": _layout_minimal,
}


def render_share_summary_preview_html(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId = "hero",
    fmt: FormatId = "square",
    scale: float = 0.38,
    spotlight_stat: SpotlightStatId = "lifers",
) -> str:
    """Return scaled HTML preview for one layout + aspect ratio."""
    width, height = _FORMAT_PX[fmt]
    if layout == "spotlight":
        inner = _layout_spotlight(stats, width, height, fmt, spotlight_stat=spotlight_stat)
    else:
        builder = _LAYOUT_BUILDERS.get(layout, _layout_hero)
        inner = builder(stats, width, height, fmt)
    return _card_shell(width=width, height=height, inner_html=inner, scale=scale)


def all_layout_previews_html(
    stats: ShareSummaryStats,
    *,
    fmt: FormatId = "square",
    scale: float = 0.38,
    spotlight_stat: SpotlightStatId = "lifers",
) -> dict[str, str]:
    """All prototype layouts for side-by-side comparison."""
    layouts: list[LayoutId] = ["hero", "tiles", "minimal", "spotlight"]
    return {
        layout_id: render_share_summary_preview_html(
            stats,
            layout=layout_id,
            fmt=fmt,
            scale=scale,
            spotlight_stat=spotlight_stat,
        )
        for layout_id in layouts
    }


# Re-export period helpers for the design app.
__all__ = [
    "FormatId",
    "LayoutId",
    "SpotlightStatId",
    "ShareSummaryStats",
    "all_layout_previews_html",
    "compute_share_summary_stats",
    "period_for_custom",
    "period_for_iso_week",
    "period_for_week_containing",
    "period_for_month",
    "period_for_year",
    "render_share_summary_preview_html",
    "sample_share_summary_stats",
    "share_summary_stats_for_year",
    "spotlight_value",
    "spotlight_species_label",
    "spotlight_stat_label",
    "stat_pairs",
    "summary_status_metrics",
    "card_stat_pairs",
    "_FORMAT_LABELS",
]
