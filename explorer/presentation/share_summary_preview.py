"""
HTML layout prototypes for social-media-style birding summaries (#157).

Standalone design utility — not wired into the main explorer app yet.
"""

from __future__ import annotations

import contextvars
import contextlib
import html as html_module
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Literal

from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
    compute_share_summary_stats,
    period_for_custom,
    period_for_lifetime,
    period_for_month,
    period_for_week_containing,
    period_for_year,
)

from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT,
    SHARE_SUMMARY_COLOR_SCHEMES,
    SHARE_SUMMARY_COUNTRY_HERO_DEFAULT_STATS,
    SHARE_SUMMARY_COUNTRY_LIFETIME_HERO_DEFAULT_STATS,
    SHARE_SUMMARY_COUNTRY_LIFETIME_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_HERO_DEFAULT_STATS,
    SHARE_SUMMARY_LIFETIME_HERO_DEFAULT_STATS,
    SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_STORY_MAX_STATS,
    SHARE_SUMMARY_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
)

LayoutId = Literal["hero", "tiles", "minimal", "spotlight"]
FormatId = Literal["square", "portrait_post", "story"]

_color_scheme_index: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "share_summary_color_scheme_index",
    default=None,
)


def _active_color_scheme_index() -> int:
    override = _color_scheme_index.get()
    if override is not None:
        return override
    return SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT


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


def _colour(key: str) -> str:
    schemes = SHARE_SUMMARY_COLOR_SCHEMES
    idx = _active_color_scheme_index()
    scheme = schemes[idx] if 0 <= idx < len(schemes) else schemes[0]
    return scheme[key]


_FORMAT_PX: dict[FormatId, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait_post": (1080, 1350),
    "story": (1080, 1920),
}

FORMAT_LABELS: dict[FormatId, str] = {
    "square": "Square post (1080×1080)",
    "portrait_post": "Portrait post (1080×1350)",
    "story": "Story (1080×1920)",
}

# Taxonomy reference labels (eBird/Clements denominators — not user checklist counts).
LABEL_SPECIES_IN_TAXONOMY = "Species in eBird taxonomy"
LABEL_FAMILIES_IN_TAXONOMY = "Families in eBird taxonomy"
LABEL_OBSERVED_SPECIES_PCT = "Observed species (%)"


def _geo_scope_is_world(geo_scope: ShareSummaryGeoScope | None) -> bool:
    return geo_scope is None or geo_scope.is_world

@dataclass(frozen=True)
class _StatSpec:
    """One headline stat: which :class:`ShareSummaryStats` field, its card label, and formatting.

    ``decimals`` 0 → integer with thousands separators; 1 → one decimal place (and a ``—``
    placeholder when the value is zero). ``hide_if_zero`` drops the stat entirely at zero.
    """

    attr: str
    label: str
    decimals: int = 0
    hide_if_zero: bool = False


# Ordered headline stats. This order is the fallback priority used by ``card_stat_pairs`` and the
# single source of truth for stat labels (the Available statistics expander reorders separately).
_STAT_SPECS: tuple[_StatSpec, ...] = (
    _StatSpec("species", "Total species"),
    _StatSpec("lifers", "Lifers"),
    _StatSpec("checklists", "Total checklists"),
    _StatSpec("completed_checklists", "Completed checklists"),
    _StatSpec("locations", "Unique locations"),
    _StatSpec("families", "Bird families"),
    _StatSpec("individuals", "Total individuals"),
    _StatSpec("days_with_checklist", "Birding days"),
    _StatSpec("countries", "Countries"),
    _StatSpec("longest_streak", "Longest streak (days)"),
    _StatSpec("birding_hours", "Birding hours", decimals=1),
    _StatSpec("distance_km", "Total distance (km)", decimals=1),
    _StatSpec("shared_checklists", "Shared checklists", hide_if_zero=True),
    _StatSpec("days_birding_with_others", "Days birding with others", hide_if_zero=True),
)

def resolve_spotlight_label(spotlight_label: str | None) -> str:
    """Normalize the chosen spotlight label, falling back to the default."""
    cleaned = (spotlight_label or "").strip()
    return cleaned or SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT


def spotlight_pair_for_label(
    stats: ShareSummaryStats,
    label: str,
    *,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> tuple[str, str] | None:
    """Return (title, display value) for one Available statistics label."""
    lookup = _metrics_lookup(stats, all_time=all_time, geo_scope=geo_scope)
    cleaned = (label or "").strip()
    if not cleaned or cleaned not in lookup:
        return None
    return cleaned, lookup[cleaned]

_LOGO_PATH = Path(__file__).resolve().parents[2] / "docs" / "explorer" / "assets" / "personal-ebird-explorer-logo.svg"


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


def stat_pairs(
    stats: ShareSummaryStats,
    *,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> list[tuple[str, str]]:
    """Ordered (label, display value) pairs for layouts; skips missing stats."""
    out: list[tuple[str, str]] = []
    for spec in _STAT_SPECS:
        if spec.attr == "countries" and not _geo_scope_is_world(geo_scope):
            continue
        val = getattr(stats, spec.attr)
        if val is None:
            continue
        if spec.hide_if_zero and val == 0:
            continue
        if spec.decimals:
            display = f"{val:,.{spec.decimals}f}" if val else "—"
        else:
            display = f"{int(val):,}"
        out.append((spec.label, display))
    return out


_SUMMARY_STATUS_ORDER: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Total checklists",
    "Completed checklists",
    "Shared checklists",
    "Unique locations",
    "Countries",
    "Birding hours",
    "Total distance (km)",
    "Birding days",
    "Days birding with others",
    "Longest streak (days)",
    "Total individuals",
    "Bird families",
    LABEL_OBSERVED_SPECIES_PCT,
    LABEL_SPECIES_IN_TAXONOMY,
    LABEL_FAMILIES_IN_TAXONOMY,
)


def _period_species_coverage_pct(
    stats: ShareSummaryStats,
    all_time: ShareSummaryAllTimeStats | None,
) -> float | None:
    """Period species count as a share of living eBird/Clements taxonomy species."""
    if stats.species is None or all_time is None or not all_time.total_species_taxa:
        return None
    return stats.species / all_time.total_species_taxa * 100.0


def _metrics_lookup(
    stats: ShareSummaryStats,
    *,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> dict[str, str]:
    """Label → display value for period stats and optional taxonomy reference rows."""
    lookup: dict[str, str] = dict(stat_pairs(stats, geo_scope=geo_scope))
    if not _geo_scope_is_world(geo_scope) or all_time is None:
        return lookup
    if all_time.total_species_taxa is not None:
        lookup[LABEL_SPECIES_IN_TAXONOMY] = f"{all_time.total_species_taxa:,}"
    if all_time.total_families_taxa is not None:
        lookup[LABEL_FAMILIES_IN_TAXONOMY] = f"{all_time.total_families_taxa:,}"
    pct = _period_species_coverage_pct(stats, all_time)
    if pct is not None:
        lookup[LABEL_OBSERVED_SPECIES_PCT] = f"{pct:.1f}%"
    return lookup


def summary_status_metrics(
    stats: ShareSummaryStats,
    *,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> list[tuple[str, str]]:
    """Metrics row above card previews (period stats + optional taxonomy reference)."""
    lookup = _metrics_lookup(stats, all_time=all_time, geo_scope=geo_scope)

    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label in _SUMMARY_STATUS_ORDER:
        if label in lookup:
            ordered.append((label, lookup[label]))
            seen.add(label)
    for label, value in lookup.items():
        if label not in seen:
            ordered.append((label, value))
    return ordered


def layout_card_stat_max(layout: LayoutId | None, fmt: FormatId | None = None) -> int:
    """Maximum stat slots on grid/list layouts (spotlight uses a separate control)."""
    if layout == "hero":
        return 4
    if layout == "tiles":
        if fmt == "story":
            return SHARE_SUMMARY_STORY_MAX_STATS
        return 6
    if layout == "minimal":
        if fmt == "story":
            return SHARE_SUMMARY_STORY_MAX_STATS
        return 6
    return 6


def layout_card_stat_storage_max(layout: LayoutId | None) -> int:
    """Session storage cap — story layouts retain extra picks when switching aspect ratio."""
    if layout in ("minimal", "tiles"):
        return SHARE_SUMMARY_STORY_MAX_STATS
    return layout_card_stat_max(layout)


def _preferred_default_stats(
    layout: LayoutId,
    period_kind: PeriodKind,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> tuple[str, ...]:
    """Default stat label order for *layout*, *period_kind*, and geographic scope."""
    geo_constrained = geo_scope is not None and not geo_scope.is_world
    if period_kind == "lifetime":
        if layout == "hero":
            return (
                SHARE_SUMMARY_COUNTRY_LIFETIME_HERO_DEFAULT_STATS
                if geo_constrained
                else SHARE_SUMMARY_LIFETIME_HERO_DEFAULT_STATS
            )
        return (
            SHARE_SUMMARY_COUNTRY_LIFETIME_TILES_DEFAULT_STATS
            if geo_constrained
            else SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS
        )
    if layout == "hero":
        return (
            SHARE_SUMMARY_COUNTRY_HERO_DEFAULT_STATS
            if geo_constrained
            else SHARE_SUMMARY_HERO_DEFAULT_STATS
        )
    return (
        SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS
        if geo_constrained
        else SHARE_SUMMARY_TILES_DEFAULT_STATS
    )


def default_card_stat_labels(
    layout: LayoutId,
    available_metrics: Iterable[tuple[str, str]],
    *,
    period_kind: PeriodKind = "year",
    geo_scope: ShareSummaryGeoScope | None = None,
) -> tuple[str, ...]:
    """Layout default stat labels filtered to *available_metrics*."""
    available = {label for label, _ in available_metrics}
    preferred = _preferred_default_stats(layout, period_kind, geo_scope=geo_scope)
    max_count = layout_card_stat_max(layout)
    return tuple(lab for lab in preferred if lab in available)[:max_count]


def card_stat_pairs(
    stats: ShareSummaryStats,
    *,
    max_count: int,
    layout: LayoutId | None = None,
    selected_labels: tuple[str, ...] | None = None,
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> list[tuple[str, str]]:
    """Stats for share cards — user picks, layout defaults, or remaining computed stats."""
    lookup = _metrics_lookup(stats, all_time=all_time, geo_scope=geo_scope)

    if selected_labels is not None:
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for lab in selected_labels:
            if lab in lookup and lab not in seen:
                out.append((lab, lookup[lab]))
                seen.add(lab)
            if len(out) >= max_count:
                break
        return out

    all_p = stat_pairs(stats, geo_scope=geo_scope)
    period_kind = stats.period_kind

    if layout == "hero":
        preferred = _preferred_default_stats("hero", period_kind, geo_scope=geo_scope)
    elif layout in ("tiles", "minimal"):
        preferred = _preferred_default_stats("tiles", period_kind, geo_scope=geo_scope)
    elif max_count <= 4:
        preferred = _preferred_default_stats("hero", period_kind, geo_scope=geo_scope)
    else:
        preferred = _preferred_default_stats("tiles", period_kind, geo_scope=geo_scope)

    labels: list[str] = []
    for lab in preferred:
        if lab in lookup and lab not in labels:
            labels.append(lab)
    for lab, _ in all_p:
        if lab not in labels:
            labels.append(lab)

    return [(lab, lookup[lab]) for lab in labels[:max_count]]


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
            "completed_checklists": 172,
            "locations": 42,
            "families": 89,
            "individuals": 12_450,
            "days_with_checklist": 98,
            "birding_hours": 214.5,
            "distance_km": 1_842.5,
            "longest_streak": 14,
            "countries": 5,
        },
        "week": {
            "species": 34,
            "lifers": 2,
            "checklists": 6,
            "completed_checklists": 5,
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
            "completed_checklists": 20,
            "locations": 11,
            "families": 45,
            "individuals": 1_840,
            "days_with_checklist": 14,
            "birding_hours": 38.5,
            "longest_streak": 5,
            "countries": 3,
            "shared_checklists": 4,
            "days_birding_with_others": 3,
        },
        "custom": {
            "species": 56,
            "lifers": 3,
            "checklists": 8,
            "completed_checklists": 7,
            "locations": 6,
            "families": 32,
            "individuals": 680,
            "days_with_checklist": 7,
            "birding_hours": 18.0,
            "countries": 2,
        },
        "lifetime": {
            "species": 847,
            "checklists": 1_240,
            "completed_checklists": 1_104,
            "locations": 186,
            "families": 248,
            "individuals": 98_400,
            "days_with_checklist": 412,
            "birding_hours": 892.0,
            "distance_km": 28_450.0,
            "longest_streak": 21,
            "countries": 12,
            "shared_checklists": 86,
            "days_birding_with_others": 54,
        },
    }
    d = demo.get(period_kind, demo["year"])
    return ShareSummaryStats(
        period_label=period_label,
        period_kind=period_kind,
        trip_title=trip_title,
        species=int(d["species"]),
        lifers=int(d["lifers"]) if "lifers" in d else None,
        checklists=int(d["checklists"]),
        completed_checklists=int(d["completed_checklists"]) if "completed_checklists" in d else None,
        locations=int(d["locations"]),
        families=int(d["families"]),
        individuals=int(d["individuals"]),
        days_with_checklist=int(d["days_with_checklist"]),
        birding_hours=float(d["birding_hours"]),
        distance_km=float(d["distance_km"]) if "distance_km" in d else None,
        longest_streak=int(d["longest_streak"]) if "longest_streak" in d else None,
        countries=int(d["countries"]) if "countries" in d else None,
        shared_checklists=int(d["shared_checklists"]) if "shared_checklists" in d else None,
        days_birding_with_others=int(d["days_birding_with_others"]) if "days_birding_with_others" in d else None,
    )


def _esc(text: Any) -> str:
    return html_module.escape(str(text), quote=False)


def _is_tall(fmt: FormatId, width: int, height: int) -> bool:
    return height > width


def _footer_pad(
    fmt: FormatId,
    width: int,
    height: int,
    *,
    favourite_bird_count: int = 0,
) -> int:
    """Reserve space above the absolute footer (logo + label ≈ 120px)."""
    del width, height
    if fmt == "story":
        pad = 140
    elif fmt == "portrait_post":
        pad = 128
    else:
        pad = 120
    if favourite_bird_count:
        pad += 4 * favourite_bird_count
    return pad


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
    if stats.period_kind == "lifetime":
        return "My eBird data"
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


def _footer_block(*, scope_label: str | None = None) -> str:
    logo = _logo_svg_inline(height_px=40, fill=_colour("muted"))
    logo_row = logo if logo else ""
    scope_row = ""
    if scope_label:
        scope_row = (
            f'<p style="margin:0 0 12px;font-size:18px;color:{_colour("muted")};'
            f'letter-spacing:0.04em;">{_esc(scope_label)}</p>'
        )
    return f"""
<div style="position:absolute;left:0;right:0;bottom:0;padding:24px 56px 28px;text-align:center;
  border-top:1px solid {_colour("border")};background:{_colour("bg_alt")};">
  {scope_row}
  {logo_row}
  <p style="margin:8px 0 0;font-size:20px;color:{_colour("muted")};">Personal eBird Explorer</p>
</div>"""


def _favourite_birds_block(names: tuple[str, ...] | list[str], *, name_size_px: int = 36) -> str:
    """Full-width list block under the stat grid (hero / tiles)."""
    cleaned = [n.strip() for n in names if (n or "").strip()]
    if not cleaned:
        return ""
    n = len(cleaned)
    item_rows = []
    for i, name in enumerate(cleaned):
        top = "0" if i == 0 else "8px"
        item_rows.append(
            f'<div style="margin-top:{top};font-size:{name_size_px}px;font-weight:600;line-height:1.22;">'
            f"{_esc(name)}</div>"
        )
    heading = "Favourite bird" if n == 1 else "Favourite birds"
    return f"""
<div style="flex:0 0 auto;width:100%;padding:28px 32px;border-radius:16px;
  border:1px solid {_colour("border")};background:{_colour("bg_alt")};">
  <div style="margin-bottom:12px;font-size:22px;color:{_colour("muted")};
    letter-spacing:0.06em;text-transform:uppercase;font-weight:600;">{_esc(heading)}</div>
  <div>{"".join(item_rows)}</div>
</div>"""


def _resolve_card_stat_pairs(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId,
    fmt: FormatId | None = None,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> list[tuple[str, str]]:
    max_count = layout_card_stat_max(layout, fmt)
    if card_stat_labels:
        return card_stat_pairs(
            stats,
            max_count=max_count,
            selected_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
        )
    return card_stat_pairs(
        stats,
        max_count=max_count,
        layout=layout,
        all_time=all_time,
        geo_scope=geo_scope,
    )


def _layout_hero(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
    favourite_birds: tuple[str, ...] = (),
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    pairs = _resolve_card_stat_pairs(
        stats,
        layout="hero",
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        geo_scope=geo_scope,
    )
    cells = []
    for label, value in pairs:
        cells.append(f"""
<div style="flex:1;min-width:40%;padding:28px 24px;border:1px solid {_colour("border")};
  border-radius:16px;background:{_colour("bg_alt")};text-align:center;">
  <div style="font-size:64px;font-weight:700;line-height:1.1;">{_esc(value)}</div>
  <div style="margin-top:12px;font-size:24px;color:{_colour("muted")};">{_esc(label)}</div>
</div>""")
    favourite_block = _favourite_birds_block(favourite_birds, name_size_px=36)
    pad_bottom = _footer_pad(fmt, width, height, favourite_bird_count=len(favourite_birds))
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats)}
  <div style="display:flex;flex-wrap:wrap;gap:24px;padding:16px 56px {pad_bottom}px;
    justify-content:center;align-content:flex-start;">
    {''.join(cells)}
    {favourite_block}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def favourite_birds_for_card(
    layout: LayoutId,
    fmt: FormatId,
    favourite_birds: tuple[str, ...],
) -> tuple[str, ...]:
    """Favourite birds render on hero and on stat tiles except square aspect ratio."""
    if layout == "hero":
        return favourite_birds
    if layout == "tiles" and fmt != "square":
        return favourite_birds
    return ()


def _layout_subtitle(stats: ShareSummaryStats, layout_default: str) -> str | None:
    """Layout-specific green subtitle; trip title wins on custom ranges."""
    if stats.trip_title:
        return None
    return layout_default


def _layout_tiles(
    stats: ShareSummaryStats,
    width: int,
    height: int,
    fmt: FormatId,
    *,
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
    if fmt == "story" and len(pairs) > 6:
        value_px, label_px, cell_pad, grid_gap = "40px", "18px", "20px 12px", "12px"
    else:
        value_px, label_px, cell_pad, grid_gap = "52px", "20px", "32px 20px", "20px"
    cells = []
    for label, value in pairs:
        cells.append(f"""
<div style="padding:{cell_pad};border-radius:12px;
  background:linear-gradient(145deg,{_colour("bg_alt")},{_colour("bg")});
  border:1px solid {_colour("border")};text-align:center;">
  <div style="font-size:{value_px};font-weight:700;">{_esc(value)}</div>
  <div style="margin-top:8px;font-size:{label_px};color:{_colour("muted")};">{_esc(label)}</div>
</div>""")
    birds = favourite_birds_for_card("tiles", fmt, favourite_birds)
    favourite_block = _favourite_birds_block(birds, name_size_px=32)
    pad_bottom = _footer_pad(fmt, width, height, favourite_bird_count=len(birds))
    return f"""
<div style="position:relative;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "My birding stats"))}
  <div style="padding:8px 48px {pad_bottom}px;">
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:{grid_gap};">
      {''.join(cells)}
    </div>
    {favourite_block}
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
    if fmt == "story" and len(pairs) > 6:
        label_px, value_px, row_pad = "24px", "38px", "12px"
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
  {_header_block(stats, subtitle=_layout_subtitle(stats, "Summary"))}
  <div style="padding:24px 72px {pad_bottom}px;">
    {''.join(rows)}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


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
  {_footer_block(scope_label=scope_label)}
</div>"""


_LAYOUT_BUILDERS = {
    "hero": _layout_hero,
    "tiles": _layout_tiles,
    "minimal": _layout_minimal,
}


def _card_inner_html(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId,
    fmt: FormatId,
    spotlight_label: str | None = None,
    favourite_birds: tuple[str, ...] = (),
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> tuple[str, int, int]:
    """Return (inner HTML, width, height) at export pixel dimensions."""
    width, height = _FORMAT_PX[fmt]
    if layout == "spotlight":
        label = resolve_spotlight_label(spotlight_label)
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
    elif layout in ("hero", "tiles"):
        builder = _LAYOUT_BUILDERS[layout]
        inner = builder(
            stats,
            width,
            height,
            fmt,
            favourite_birds=favourite_birds,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
    else:
        builder = _LAYOUT_BUILDERS.get(layout, _layout_hero)
        inner = builder(
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
    layout: LayoutId = "hero",
    fmt: FormatId = "square",
    spotlight_label: str | None = None,
    favourite_birds: tuple[str, ...] = (),
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
            spotlight_label=spotlight_label,
            favourite_birds=favourite_birds,
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
  background:{_colour('bg')};color:{_colour('text')};">
  {inner}
</div>
</body>
</html>"""


def render_share_summary_preview_html(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId = "hero",
    fmt: FormatId = "square",
    scale: float = 0.38,
    spotlight_label: str | None = None,
    favourite_birds: tuple[str, ...] = (),
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    geo_scope: ShareSummaryGeoScope | None = None,
    scope_label: str | None = None,
) -> str:
    """Return scaled HTML preview for one layout + aspect ratio."""
    with _color_scheme_context(color_scheme_index):
        birds = favourite_birds_for_card(layout, fmt, favourite_birds)
        labels = card_stat_labels if layout in ("hero", "tiles", "minimal") else ()
        inner, width, height = _card_inner_html(
            stats,
            layout=layout,
            fmt=fmt,
            spotlight_label=spotlight_label,
            favourite_birds=birds,
            card_stat_labels=labels,
            all_time=all_time,
            geo_scope=geo_scope,
            scope_label=scope_label,
        )
        return _card_shell(width=width, height=height, inner_html=inner, scale=scale)


# Re-export period helpers for the design app.
__all__ = [
    "FormatId",
    "LayoutId",
    "ShareSummaryAllTimeStats",
    "ShareSummaryStats",
    "compute_share_summary_stats",
    "period_for_custom",
    "period_for_lifetime",
    "period_for_week_containing",
    "period_for_month",
    "period_for_year",
    "render_share_summary_export_html",
    "render_share_summary_preview_html",
    "sample_share_summary_stats",
    "spotlight_pair_for_label",
    "resolve_spotlight_label",
    "stat_pairs",
    "summary_status_metrics",
    "layout_card_stat_max",
    "layout_card_stat_storage_max",
    "favourite_birds_for_card",
    "default_card_stat_labels",
    "card_stat_pairs",
    "FORMAT_LABELS",
]
