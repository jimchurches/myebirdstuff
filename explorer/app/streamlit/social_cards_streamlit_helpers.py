"""Pure helpers for Social Cards Streamlit UI (no widget calls)."""

from __future__ import annotations

from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.presentation.share_summary_circles_preview import (
    TILES_CIRCLE_CLUSTER_DEFAULT,
    tiles_circle_cluster_max,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
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
    """False when the selected period has no checklists in the loaded export."""
    return stats.checklists is not None and stats.checklists > 0


def tiles_circle_cluster_picker(
    layout: LayoutId, tiles_presentation: TilesPresentationId
) -> bool:
    """True when the tiles layout uses circle-cluster presentation."""
    return layout == "tiles" and tiles_presentation == "circles"


def card_stat_min_slots(
    layout: LayoutId,
    fmt: FormatId,
    *,
    tiles_presentation: TilesPresentationId = "grid",
) -> int:
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


def card_can_accept_stat(
    layout: LayoutId,
    fmt: FormatId,
    picks: list[str],
    slot_count: int,
    *,
    tiles_presentation: TilesPresentationId = "grid",
    status_metrics: list[tuple[str, str]] | None = None,
) -> bool:
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
