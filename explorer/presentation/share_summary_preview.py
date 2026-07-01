"""
HTML layout prototypes for social-media-style birding summaries (#157).

Standalone design utility — not wired into the main explorer app yet.
"""

from __future__ import annotations

import contextlib
import contextvars
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
    geo_region_lifer_stat_label,
    period_for_custom,
    period_for_lifetime,
    period_for_month,
    period_for_week_containing,
    period_for_year,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT,
    SHARE_SUMMARY_COLOR_SCHEMES,
    SHARE_SUMMARY_COUNTRY_FOUR_STAT_DEFAULT_STATS,
    SHARE_SUMMARY_COUNTRY_LIFETIME_FOUR_STAT_DEFAULT_STATS,
    SHARE_SUMMARY_COUNTRY_LIFETIME_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS,
    SHARE_SUMMARY_GRID_MIN_STATS,
    SHARE_SUMMARY_GRID_PORTRAIT_DEFAULT_SLOT_COUNT,
    SHARE_SUMMARY_GRID_PORTRAIT_MAX_STATS,
    SHARE_SUMMARY_GRID_SQUARE_DEFAULT_SLOT_COUNT,
    SHARE_SUMMARY_GRID_SQUARE_MAX_STATS,
    SHARE_SUMMARY_GRID_STORY_DEFAULT_SLOT_COUNT,
    SHARE_SUMMARY_GRID_STORY_MAX_STATS,
    SHARE_SUMMARY_INSIGHT_FACT_DEFAULT,
    SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS,
    SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_MINIMAL_STORY_MAX_STATS,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    SHARE_SUMMARY_TILES_DEFAULT_STATS,
    share_summary_card_subtitle,
    share_summary_period_subtitle,
)
from explorer.core.share_summary_insight_facts import (
    InsightFactId,
    ShareSummaryInsightFact,
    format_insight_fact_metric,
    insight_fact_by_id,
)
from explorer.presentation.share_summary_rich_fact_layout import (
    rich_fact_layout_spec,
    rich_fact_line_style_css,
)

TilesPresentationId = Literal["grid", "circles"]
SpotlightPresentationId = Literal["classic", "circle"]
LayoutId = Literal["tiles", "minimal", "spotlight", "insight"]

# Statistics Grid rectangular tiles — uniform across square, portrait, and story.
# At max grid counts (square 6, portrait 8, story 14) this fits 1080×1080 / ×1350 / ×1920;
# very long stat labels may wrap and add row height on story at high tile counts.
_GRID_TILE_VALUE_PX = "52px"
_GRID_TILE_LABEL_PX = "20px"
_GRID_TILE_CELL_PAD = "32px 20px"
_GRID_TILE_GAP = "20px"

FormatId = Literal["square", "portrait_post", "story"]

_color_scheme_index: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "share_summary_color_scheme_index",
    default=None,
)
_custom_color_scheme: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "share_summary_custom_color_scheme",
    default=None,
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


def _geo_scope_is_world(geo_scope: ShareSummaryGeoScope | None) -> bool:
    return geo_scope is None or geo_scope.is_world

@dataclass(frozen=True)
class _StatSpec:
    """One headline stat: which :class:`ShareSummaryStats` field, its card label, and formatting.

    ``label`` is the picker / session key (Available statistics, defaults, reorder).
    ``card_label`` overrides the short tile heading on rendered cards when set.

    ``decimals`` 0 → integer with thousands separators; 1 → one decimal place (and a ``—``
    placeholder when the value is zero). ``hide_if_zero`` drops the stat entirely at zero.
    """

    attr: str
    label: str
    decimals: int = 0
    hide_if_zero: bool = False
    card_label: str | None = None


# Ordered headline stats. This order is the fallback priority used by ``card_stat_pairs`` and the
# single source of truth for stat labels (the Available statistics expander reorders separately).
_STAT_SPECS: tuple[_StatSpec, ...] = (
    _StatSpec("species", "Total species", card_label="Species"),
    _StatSpec("lifers", "Lifers"),
    _StatSpec("checklists", "Total checklists"),
    _StatSpec("completed_checklists", "Completed checklists"),
    _StatSpec("incidental_checklists", "Incidental checklists"),
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

_CARD_LABEL_BY_PICKER: dict[str, str] = {
    spec.label: spec.card_label for spec in _STAT_SPECS if spec.card_label is not None
}


def stat_card_display_label(picker_label: str) -> str:
    """Short tile label for cards; picker keys and defaults keep ``picker_label``."""
    return _CARD_LABEL_BY_PICKER.get(picker_label, picker_label)


def _card_stat_pair(picker_label: str, value: str) -> tuple[str, str]:
    return stat_card_display_label(picker_label), value

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
    return _card_stat_pair(cleaned, lookup[cleaned])

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
    "Incidental checklists",
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
    if geo_scope is not None and not _geo_scope_is_world(geo_scope):
        if stats.region_lifers is not None:
            lookup[geo_region_lifer_stat_label(geo_scope)] = f"{int(stats.region_lifers):,}"
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
    region_label = (
        geo_region_lifer_stat_label(geo_scope)
        if geo_scope is not None and not _geo_scope_is_world(geo_scope)
        else ""
    )
    for label in _SUMMARY_STATUS_ORDER:
        if label in lookup:
            ordered.append((label, lookup[label]))
            seen.add(label)
            if label == "Lifers" and region_label and region_label in lookup:
                ordered.append((region_label, lookup[region_label]))
                seen.add(region_label)
    for label, value in lookup.items():
        if label not in seen:
            ordered.append((label, value))
    return ordered


def layout_grid_stat_min(fmt: FormatId | None = None) -> int:
    """Minimum stat slots on Statistics Grid (all formats)."""
    del fmt
    return SHARE_SUMMARY_GRID_MIN_STATS


def layout_grid_stat_max(fmt: FormatId | None = None) -> int:
    """Maximum stat slots on Statistics Grid — not circle-cluster caps."""
    if fmt == "story":
        return SHARE_SUMMARY_GRID_STORY_MAX_STATS
    if fmt == "portrait_post":
        return SHARE_SUMMARY_GRID_PORTRAIT_MAX_STATS
    return SHARE_SUMMARY_GRID_SQUARE_MAX_STATS


def layout_grid_stat_default_count(fmt: FormatId | None = None) -> int:
    """Default visible stat slots on Statistics Grid (non-circle)."""
    if fmt == "story":
        return SHARE_SUMMARY_GRID_STORY_DEFAULT_SLOT_COUNT
    if fmt == "portrait_post":
        return SHARE_SUMMARY_GRID_PORTRAIT_DEFAULT_SLOT_COUNT
    return SHARE_SUMMARY_GRID_SQUARE_DEFAULT_SLOT_COUNT


def layout_grid_slot_limits_caption() -> str:
    """Human-readable Statistics Grid min–max ranges for square, portrait, and story."""
    mn = SHARE_SUMMARY_GRID_MIN_STATS
    return (
        f"square {mn}–{SHARE_SUMMARY_GRID_SQUARE_MAX_STATS}, "
        f"portrait {mn}–{SHARE_SUMMARY_GRID_PORTRAIT_MAX_STATS}, "
        f"story {mn}–{SHARE_SUMMARY_GRID_STORY_MAX_STATS}"
    )


def layout_card_stat_max(
    layout: LayoutId | None,
    fmt: FormatId | None = None,
    *,
    available_stat_count: int | None = None,
) -> int:
    """Maximum stat slots on grid/list layouts (spotlight and insight use separate controls)."""
    if layout == "tiles":
        return layout_grid_stat_max(fmt)
    if layout == "minimal":
        if fmt == "story":
            cap = SHARE_SUMMARY_MINIMAL_STORY_MAX_STATS
            if available_stat_count is not None:
                return min(max(1, available_stat_count), cap)
            return cap
        return 6
    return 6


def layout_card_stat_storage_max(layout: LayoutId | None) -> int:
    """Session storage cap — story layouts retain extra picks when switching aspect ratio."""
    if layout == "minimal":
        return SHARE_SUMMARY_MINIMAL_STORY_MAX_STATS
    if layout == "tiles":
        return SHARE_SUMMARY_GRID_STORY_MAX_STATS
    return layout_card_stat_max(layout)


def _four_stat_default_labels(
    period_kind: PeriodKind,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> tuple[str, ...]:
    """Default four-stat label order when a card shows at most four metrics."""
    geo_constrained = geo_scope is not None and not geo_scope.is_world
    if period_kind == "lifetime":
        return (
            SHARE_SUMMARY_COUNTRY_LIFETIME_FOUR_STAT_DEFAULT_STATS
            if geo_constrained
            else SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS
        )
    return (
        SHARE_SUMMARY_COUNTRY_FOUR_STAT_DEFAULT_STATS
        if geo_constrained
        else SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS
    )


def _preferred_default_stats(
    layout: LayoutId,
    period_kind: PeriodKind,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> tuple[str, ...]:
    """Default stat label order for *layout*, *period_kind*, and geographic scope."""
    del layout
    geo_constrained = geo_scope is not None and not geo_scope.is_world
    if period_kind == "lifetime":
        return (
            SHARE_SUMMARY_COUNTRY_LIFETIME_TILES_DEFAULT_STATS
            if geo_constrained
            else SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS
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
    fmt: FormatId | None = None,
) -> tuple[str, ...]:
    """Layout default stat labels filtered to *available_metrics*."""
    available_list = list(available_metrics)
    available = {label for label, _ in available_list}
    preferred = _preferred_default_stats(layout, period_kind, geo_scope=geo_scope)
    max_count = layout_card_stat_max(
        layout,
        fmt,
        available_stat_count=len(available_list) if layout == "minimal" and fmt == "story" else None,
    )
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
                out.append(_card_stat_pair(lab, lookup[lab]))
                seen.add(lab)
            if len(out) >= max_count:
                break
        return out

    all_p = stat_pairs(stats, geo_scope=geo_scope)
    period_kind = stats.period_kind

    if layout in ("tiles", "minimal"):
        preferred = _preferred_default_stats(layout, period_kind, geo_scope=geo_scope)
    elif max_count <= 4:
        preferred = _four_stat_default_labels(period_kind, geo_scope=geo_scope)
    else:
        preferred = _preferred_default_stats("tiles", period_kind, geo_scope=geo_scope)

    labels: list[str] = []
    for lab in preferred:
        if lab in lookup and lab not in labels:
            labels.append(lab)
    for lab, _ in all_p:
        if lab not in labels:
            labels.append(lab)

    return [_card_stat_pair(lab, lookup[lab]) for lab in labels[:max_count]]


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
            "incidental_checklists": 14,
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
            "incidental_checklists": 2,
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
        incidental_checklists=int(d["incidental_checklists"]) if "incidental_checklists" in d else None,
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
) -> int:
    """Small gap between card body and footer (footer is in normal document flow)."""
    del fmt, width, height
    return 16


def _footer_scope_colour() -> str:
    """Geographic scope line in the card footer (e.g. World)."""
    return _colour("muted")


def _footer_brand_colour() -> str:
    """App name and logo in the card footer."""
    return _colour("muted")


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
    brand_colour = _footer_brand_colour()
    logo = _logo_svg_inline(height_px=46, fill=brand_colour)
    logo_row = (
        f'<div style="margin:4px 0;line-height:0;">{logo}</div>' if logo else ""
    )
    scope_row = ""
    if scope_label:
        scope_row = (
            f'<p style="margin:0 0 7px;font-size:36px;font-weight:600;line-height:1.05;'
            f'color:{_footer_scope_colour()};letter-spacing:0.04em;">{_esc(scope_label)}</p>'
        )
    return f"""
<div style="padding:22px 56px 26px;text-align:center;
  border-top:1px solid {_colour("border")};background:{_colour("bg_alt")};">
  {scope_row}
  {logo_row}
  <p style="margin:5px 0 0;font-size:18px;color:{brand_colour};">Personal eBird Explorer</p>
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
    available_count = (
        len(lookup) if layout == "minimal" and fmt == "story" else None
    )
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
    pad_bottom = _footer_pad(fmt, width, height)
    return f"""
<div style="display:flex;flex-direction:column;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "tiles"))}
  <div style="padding:8px 48px {pad_bottom}px;">
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:{grid_gap};">
      {''.join(cells)}
    </div>
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
<div style="display:flex;flex-direction:column;width:100%;height:100%;box-sizing:border-box;">
  {_header_block(stats, subtitle=_layout_subtitle(stats, "minimal"))}
  <div style="padding:24px 72px {pad_bottom}px;">
    {''.join(rows)}
  </div>
  {_footer_block(scope_label=scope_label)}
</div>"""


def _layout_spotlight_header_html(stats: ShareSummaryStats) -> str:
    """Shared period / trip header for classic Spotlight layout."""
    if stats.trip_title:
        return f"""
<p style="margin:0 0 8px;font-size:28px;letter-spacing:0.06em;text-transform:uppercase;
  color:{_colour('accent')};font-weight:600;">{_esc(stats.trip_title)}</p>
<p style="margin:0 0 28px;font-size:36px;font-weight:700;line-height:1.1;color:{_colour('text')};">
  {_esc(stats.period_label)}</p>"""
    subtitle = _layout_subtitle(stats, "spotlight")
    if subtitle:
        return f"""
<p style="margin:0 0 8px;font-size:28px;letter-spacing:0.08em;text-transform:uppercase;
  color:{_colour('accent')};font-weight:600;">{_esc(subtitle)}</p>
<p style="margin:0 0 32px;font-size:36px;font-weight:700;line-height:1.1;color:{_colour('text')};">
  {_esc(stats.period_label)}</p>"""
    return f"""
<p style="margin:0 0 32px;font-size:36px;letter-spacing:0.04em;color:{_colour('accent')};font-weight:600;">
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
    """Interesting Insights — label, species/text focus, optional metric."""
    pad_bottom = _footer_pad(fmt, width, height)
    spec = rich_fact_layout_spec(fmt)
    metric = format_insight_fact_metric(insight_fact)
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
        f"{_esc(insight_fact.primary_text)}</div>{metric_line}"
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
<div style="display:flex;flex-direction:column;width:100%;height:100%;box-sizing:border-box;overflow:hidden;">
  <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:64px 56px {pad_bottom}px;text-align:center;box-sizing:border-box;min-height:0;">
    {header_html}
    <div style="font-size:{num_size};font-weight:800;line-height:1.05;color:{_colour('text')};">
      {_esc(value)}</div>
    <div style="margin-top:20px;font-size:{label_size};color:{_colour('muted')};font-weight:500;">
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
  background:{_colour('bg')};color:{_colour('text')};">
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


# Re-export period helpers for the design app.
__all__ = [
    "FormatId",
    "TilesPresentationId",
    "SpotlightPresentationId",
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
    "share_summary_scheme_override",
    "spotlight_pair_for_label",
    "resolve_spotlight_label",
    "resolve_insight_fact",
    "stat_card_display_label",
    "stat_pairs",
    "summary_status_metrics",
    "layout_card_stat_max",
    "layout_card_stat_storage_max",
    "layout_grid_slot_limits_caption",
    "layout_grid_stat_default_count",
    "layout_grid_stat_max",
    "layout_grid_stat_min",
    "default_card_stat_labels",
    "card_stat_pairs",
    "FORMAT_LABELS",
]
