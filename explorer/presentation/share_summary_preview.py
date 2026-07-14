"""
HTML layout prototypes for social-media-style birding summaries (#157).

Shared by the Social Cards tab, design playground, and PNG export.

Implementation is split across:

- ``share_summary_theme`` — formats, colour schemes, escaping
- ``share_summary_metrics`` — stat labels, metrics, samples
- ``share_summary_layouts`` — card HTML + preview/export renderers

This module re-exports the public API (and private helpers used by sibling
preview modules) so existing imports keep working.
"""

from __future__ import annotations

from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryStats,
    compute_share_summary_stats,
    period_for_custom,
    period_for_lifetime,
    period_for_month,
    period_for_week_containing,
    period_for_year,
)
from explorer.presentation.share_summary_layouts import (
    render_share_summary_export_html,
    render_share_summary_preview_html,
    resolve_insight_fact,
)
from explorer.presentation.share_summary_metrics import (
    card_stat_pairs,
    default_card_stat_labels,
    layout_card_stat_max,
    layout_card_stat_storage_max,
    layout_grid_slot_limits_caption,
    layout_grid_stat_default_count,
    layout_grid_stat_max,
    layout_grid_stat_min,
    resolve_spotlight_label,
    sample_share_summary_stats,
    spotlight_pair_for_label,
    spotlight_stat_display_label,
    stat_card_display_label,
    stat_pairs,
    summary_status_metrics,
)
from explorer.presentation.share_summary_theme import (
    FORMAT_LABELS,
    FORMAT_PIXELS,
    LABEL_FAMILIES_IN_TAXONOMY,
    LABEL_OBSERVED_SPECIES_PCT,
    LABEL_SPECIES_IN_TAXONOMY,
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
    share_summary_scheme_override,
)

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
    "spotlight_stat_display_label",
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
    "FORMAT_PIXELS",
    "LABEL_FAMILIES_IN_TAXONOMY",
    "LABEL_OBSERVED_SPECIES_PCT",
    "LABEL_SPECIES_IN_TAXONOMY",
]
