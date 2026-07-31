"""
Stat labels, metrics, and sample payloads for share-summary cards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
    geo_region_lifer_stat_label,
)
from explorer.core.share_summary_defaults import (
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
    SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS,
    SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS,
    SHARE_SUMMARY_MINIMAL_STORY_MAX_STATS,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    SHARE_SUMMARY_SPOTLIGHT_SPECIES_LABEL_BY_PERIOD,
    SHARE_SUMMARY_TILES_DEFAULT_STATS,
)
from explorer.presentation.share_summary_theme import (
    LABEL_FAMILIES_IN_TAXONOMY,
    LABEL_OBSERVED_SPECIES_PCT,
    LABEL_SPECIES_IN_TAXONOMY,
    FormatId,
    LayoutId,
)


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
    # Observers > 1 in the CSV — not eBird's "shared with another account" glyph.
    _StatSpec("shared_checklists", "Checklists with others", hide_if_zero=True),
    _StatSpec(
        "days_birding_with_others", "Days birding with others", hide_if_zero=True
    ),
)

_CARD_LABEL_BY_PICKER: dict[str, str] = {
    spec.label: spec.card_label for spec in _STAT_SPECS if spec.card_label is not None
}


def stat_card_display_label(picker_label: str) -> str:
    """Short tile label for cards; picker keys and defaults keep ``picker_label``."""
    return _CARD_LABEL_BY_PICKER.get(picker_label, picker_label)


def spotlight_stat_display_label(picker_label: str, *, period_kind: PeriodKind) -> str:
    """Spotlight card title — period-aware species wording; tiles keep ``stat_card_display_label``."""
    if picker_label == "Total species":
        return SHARE_SUMMARY_SPOTLIGHT_SPECIES_LABEL_BY_PERIOD.get(
            period_kind, stat_card_display_label(picker_label)
        )
    return stat_card_display_label(picker_label)


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
    title = spotlight_stat_display_label(cleaned, period_kind=stats.period_kind)
    return title, lookup[cleaned]


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
    "Checklists with others",
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
            lookup[geo_region_lifer_stat_label(geo_scope)] = (
                f"{int(stats.region_lifers):,}"
            )
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
        available_stat_count=len(available_list)
        if layout == "minimal" and fmt == "story"
        else None,
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
        completed_checklists=int(d["completed_checklists"])
        if "completed_checklists" in d
        else None,
        incidental_checklists=int(d["incidental_checklists"])
        if "incidental_checklists" in d
        else None,
        locations=int(d["locations"]),
        families=int(d["families"]),
        individuals=int(d["individuals"]),
        days_with_checklist=int(d["days_with_checklist"]),
        birding_hours=float(d["birding_hours"]),
        distance_km=float(d["distance_km"]) if "distance_km" in d else None,
        longest_streak=int(d["longest_streak"]) if "longest_streak" in d else None,
        countries=int(d["countries"]) if "countries" in d else None,
        shared_checklists=int(d["shared_checklists"])
        if "shared_checklists" in d
        else None,
        days_birding_with_others=int(d["days_birding_with_others"])
        if "days_birding_with_others" in d
        else None,
    )



