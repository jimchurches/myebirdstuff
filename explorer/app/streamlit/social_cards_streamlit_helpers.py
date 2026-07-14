"""Pure helpers for Social Cards Streamlit UI (no widget calls)."""

from __future__ import annotations

from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_defaults import share_summary_color_scheme_fingerprint
from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact
from explorer.presentation.share_summary_circles_preview import (
    TILES_CIRCLE_CLUSTER_DEFAULT,
    tiles_circle_cluster_max,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
    layout_card_stat_max,
    layout_grid_stat_default_count,
    layout_grid_stat_min,
)


def card_stat_data_scope(
    *,
    data_source: str,
    period_kind: PeriodKind,
    period_label: str,
    geo_scope: ShareSummaryGeoScope | None = None,
    fmt: FormatId = "square",
    tiles_presentation: TilesPresentationId = "grid",
) -> str:
    """Session scope token — when this changes, card-stat picks re-initialize."""
    geo_token = (geo_scope or ShareSummaryGeoScope()).scope_token()
    return f"{data_source}|{period_kind}|{period_label}|{geo_token}|{fmt}|{tiles_presentation}"


def card_stat_data_scope_from_session_export(
    *,
    period_kind: PeriodKind,
    period_label: str,
    geo_scope: ShareSummaryGeoScope | None = None,
    fmt: FormatId = "square",
    tiles_presentation: TilesPresentationId = "grid",
) -> str:
    """Main-app wrapper — session export is the data source."""
    return card_stat_data_scope(
        data_source="export",
        period_kind=period_kind,
        period_label=period_label,
        geo_scope=geo_scope,
        fmt=fmt,
        tiles_presentation=tiles_presentation,
    )


def card_stat_data_scope_from_design_source(
    *,
    use_sample: bool,
    period_kind: PeriodKind,
    period_label: str,
    upload_name: str | None,
    geo_scope: ShareSummaryGeoScope | None = None,
    fmt: FormatId = "square",
    tiles_presentation: TilesPresentationId = "grid",
) -> str:
    """Design-studio wrapper — maps sample/CSV toggle to a data-source token."""
    source = "sample" if use_sample else (upload_name or "csv")
    return card_stat_data_scope(
        data_source=source,
        period_kind=period_kind,
        period_label=period_label,
        geo_scope=geo_scope,
        fmt=fmt,
        tiles_presentation=tiles_presentation,
    )


def period_has_checklist_data(stats: ShareSummaryStats) -> bool:
    """Return whether the selected period has checklists in the loaded export."""
    return stats.checklists is not None and stats.checklists > 0


def tiles_circle_cluster_picker(
    layout: LayoutId, tiles_presentation: TilesPresentationId
) -> bool:
    """Return whether the tiles layout uses circle-cluster presentation."""
    return layout == "tiles" and tiles_presentation == "circles"


def card_stat_min_slots(
    layout: LayoutId,
    fmt: FormatId,
    *,
    tiles_presentation: TilesPresentationId = "grid",
) -> int:
    """Return minimum stat slots for the layout and format."""
    if layout == "tiles" and not tiles_circle_cluster_picker(
        layout, tiles_presentation
    ):
        return layout_grid_stat_min(fmt)
    return 1


def default_card_stat_slot_count(
    *,
    circle_cluster: bool,
    defaults: list[str],
    max_slots: int,
    layout: LayoutId,
    fmt: FormatId,
    tiles_presentation: TilesPresentationId = "grid",
) -> int:
    """Return initial stat-row count for a freshly scoped card."""
    if circle_cluster:
        return min(max_slots, TILES_CIRCLE_CLUSTER_DEFAULT)
    if layout == "tiles" and tiles_presentation == "grid":
        target = layout_grid_stat_default_count(fmt)
        return min(max_slots, max(layout_grid_stat_min(fmt), target))
    return min(max_slots, max(1, len(defaults) if defaults else 1))


def card_stat_max_slots(
    layout: LayoutId,
    fmt: FormatId,
    *,
    tiles_presentation: TilesPresentationId = "grid",
    status_metrics: list[tuple[str, str]] | None = None,
    available_stat_count: int | None = None,
) -> int:
    """Return maximum stat slots for the layout, format, and available metrics."""
    if tiles_circle_cluster_picker(layout, tiles_presentation):
        return tiles_circle_cluster_max(fmt)
    count = available_stat_count
    if count is None and status_metrics is not None:
        count = len(status_metrics)
    return layout_card_stat_max(layout, fmt, available_stat_count=count)


def card_stat_ui_row_count(
    layout: LayoutId,
    fmt: FormatId,
    *,
    slot_count: int,
    tiles_presentation: TilesPresentationId = "grid",
    status_metrics: list[tuple[str, str]] | None = None,
    available_stat_count: int | None = None,
) -> int:
    """Clamp slot count to the layout min/max and return UI row count."""
    max_slots = card_stat_max_slots(
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
        available_stat_count=available_stat_count,
    )
    min_slots = card_stat_min_slots(layout, fmt, tiles_presentation=tiles_presentation)
    return min(max(min_slots, slot_count), max_slots)


def effective_card_stat_labels(
    picks: list[str],
    layout: LayoutId,
    fmt: FormatId,
    *,
    tiles_presentation: TilesPresentationId = "grid",
    status_metrics: list[tuple[str, str]] | None = None,
) -> tuple[str, ...]:
    """Return non-empty picks trimmed to the layout's max slot count."""
    max_slots = card_stat_max_slots(
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    return tuple(label for label in picks if label)[:max_slots]


def sanitize_card_stat_picks(
    picks: list[str],
    *,
    available: frozenset[str],
    max_slots: int,
) -> list[str]:
    """Filter picks to available labels, dedupe, and cap at max_slots."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in picks:
        label = raw.strip() if isinstance(raw, str) else str(raw).strip()
        if label and label in available and label not in seen:
            seen.add(label)
            out.append(label)
        if len(out) >= max_slots:
            break
    return out


def resolve_card_stat_selectbox_value(
    *,
    session_value: object,
    desired: str,
    options: list[str],
) -> str:
    """Pick a valid selectbox value, preferring the widget over stale session picks."""
    if session_value is not None:
        value = (
            session_value.strip()
            if isinstance(session_value, str)
            else str(session_value).strip()
        )
        if value in options:
            return value
    fallback = desired.strip() if isinstance(desired, str) else str(desired).strip()
    return fallback if fallback in options else ""


def status_metrics_lookup(status_metrics: list[tuple[str, str]]) -> dict[str, str]:
    """Map stat label to display value from status_metrics rows."""
    return dict(status_metrics)


def stats_on_card(picks: list[str]) -> set[str]:
    """Non-empty stat labels currently assigned to card slots."""
    return {label for label in picks if label}


def png_export_fingerprint(
    *,
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    spotlight_presentation: SpotlightPresentationId,
    insight_fact: ShareSummaryInsightFact | None,
) -> tuple[object, ...]:
    """Stable cache key for lazy PNG export — invalidates when card inputs change."""
    stats_token = (
        stats.period_kind,
        stats.period_label,
        stats.trip_title,
        stats.species,
        stats.families,
        stats.individuals,
        stats.checklists,
        stats.completed_checklists,
        stats.incidental_checklists,
        stats.locations,
        stats.lifers,
        stats.region_lifers,
        stats.birding_hours,
        stats.distance_km,
        stats.days_with_checklist,
        stats.longest_streak,
        stats.countries,
        stats.shared_checklists,
        stats.days_birding_with_others,
    )
    all_time_token: tuple[object, ...] = ()
    if all_time is not None:
        all_time_token = (
            all_time.observed_species_taxa,
            all_time.total_species_taxa,
            all_time.world_bird_coverage_pct,
            all_time.observed_families,
            all_time.total_families_taxa,
        )
    insight_token: tuple[object, ...] = ()
    if insight_fact is not None:
        insight_token = (
            insight_fact.fact_id,
            insight_fact.label,
            insight_fact.primary_text,
            insight_fact.metric_value,
            insight_fact.metric_unit,
        )
    return (
        stats_token,
        layout,
        fmt,
        card_stat_labels,
        spotlight_label,
        all_time_token,
        color_scheme_index,
        share_summary_color_scheme_fingerprint(color_scheme_index),
        scope_label,
        geo_scope.scope_token(),
        tiles_presentation,
        spotlight_presentation,
        insight_token,
    )


def card_can_accept_stat(
    layout: LayoutId,
    fmt: FormatId,
    picks: list[str],
    slot_count: int,
    *,
    tiles_presentation: TilesPresentationId = "grid",
    status_metrics: list[tuple[str, str]] | None = None,
) -> bool:
    """Return whether another stat can be added to the card."""
    max_slots = card_stat_max_slots(
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    ui_rows = card_stat_ui_row_count(
        layout,
        fmt,
        slot_count=slot_count,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    active = (picks + [""] * ui_rows)[:ui_rows]
    if any(not label for label in active):
        return True
    return ui_rows < max_slots
