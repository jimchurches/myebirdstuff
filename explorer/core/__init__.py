"""Compatibility façade for the ``explorer.core`` *package* (the ``explorer/core/`` directory).

This file is **not** “core domain logic only.” It exports two different layers:

**1. Domain / data (eager imports)** — Submodules alongside this file: loading and
cleaning data, stats, working sets, taxonomy, species logic, checklist payloads, etc.
Examples: ``load_dataset``, ``compute_rankings``, :class:`WorkingSet`.

**2. Presentation (re-exported)** — HTML builders, rankings tables, map helpers, and
maintenance formatters from :mod:`explorer.presentation`, plus several map-related
names loaded lazily from :mod:`explorer.presentation.map_renderer` and
:mod:`explorer.core.map_controller` (see ``_LAZY_IMPORTS``). Examples:
``rankings_table``, ``create_map``, ``format_checklist_stats_bundle``.

**Why both appear here** — Older scripts and notebooks used ``from explorer.core import …``
for a single import surface. That convenience blurs layering for newcomers.

**What to do in new code**

- Import **domain** from the specific submodule, e.g.
  ``from explorer.core.stats import compute_rankings``,
  ``from explorer.core.map_prep import prepare_all_locations_map_context``,
  ``from explorer.core.family_map_compute import build_family_location_pins``.
- Import **HTML / Folium / table rendering** from :mod:`explorer.presentation` (or
  ``explorer.presentation.<module>``) explicitly.
- Treat this module as a **backward-compatible barrel**, not the definition of
  “what core means.”

Optional heavy stacks (Whoosh, Folium) load only when lazy names are accessed.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# IDE / static-analysis friendliness:
# ``explorer.core`` exposes some symbols lazily via ``__getattr__``. At runtime this keeps optional
# stacks (Folium, Whoosh) from being imported unless needed, but some editors cannot “jump to
# definition” for lazy names. The TYPE_CHECKING block below makes those names visible to type
# checkers and many IDEs without changing runtime imports.
if TYPE_CHECKING:  # pragma: no cover
    from explorer.core.map_controller import MapOverlayResult, build_species_overlay_map
    from explorer.core.species_search import whoosh_common_name_suggestions
    from explorer.presentation.checklist_stats_display import (
        format_checklist_stats_bundle,
        format_rankings_tab_html,
    )
    from explorer.presentation.map_renderer import (
        build_all_species_banner_html,
        build_legend_html,
        build_location_popup_html,
        build_species_banner_html,
        build_visit_info_html,
        classify_locations,
        create_map,
        format_sighting_row,
        format_visit_time,
        pin_legend_item,
        popup_scroll_script,
        resolve_lifer_last_seen,
    )

from explorer.core.constants import (
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from explorer.core.data_loader import load_dataset, add_datetime_column
from explorer.core.path_resolution import find_data_file
from explorer.core.species_logic import (
    base_species_name,
    is_countable,
    filter_species,
    countable_species_vectorized,
    base_species_for_lifer,
)
from explorer.core.stats import (
    safe_count,
    longest_streak,
    compute_rankings,
    yearly_summary_stats,
    get_sex_notation_by_year,
)
from explorer.core.duplicate_checks import get_map_maintenance_data
from explorer.core.ui_state import ExplorerState
from explorer.core.region_display import country_for_display, state_for_display
from explorer.presentation.rankings_display import (
    rankings_scroll_wrapper,
    rankings_table,
    rankings_table_location_5col,
    rankings_table_with_rank,
    rankings_visited_table,
    rankings_seen_once_table,
)
from explorer.core.taxonomy import (
    load_taxonomy,
    get_species_url,
    get_species_lifelist_url,
    get_species_and_lifelist_urls,
)
from explorer.core.working_set import WorkingSet, rebuild_working_set_from_date_filter
from explorer.core.lifer_last_seen_prep import (
    LiferLastSeenPrep,
    aggregate_lifer_sites,
    prepare_lifer_last_seen,
)
from explorer.core.checklist_stats_compute import (
    ChecklistStatsPayload,
    compute_checklist_stats_payload,
    protocol_display_name,
)
from explorer.presentation.maintenance_display import (
    EBIRD_LOCATION_EDIT_BASE,
    format_map_maintenance_html,
    format_sex_notation_maintenance_html,
    format_incomplete_checklists_maintenance_html,
)

# Whoosh / Folium are heavy optional stacks for search + map UIs. Lazy-load so
# lightweight imports do not require whoosh or folium installed.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "whoosh_common_name_suggestions": (
        "explorer.core.species_search",
        "whoosh_common_name_suggestions",
    ),
    "MapOverlayResult": ("explorer.core.map_controller", "MapOverlayResult"),
    "build_species_overlay_map": (
        "explorer.core.map_controller",
        "build_species_overlay_map",
    ),
    "create_map": ("explorer.presentation.map_renderer", "create_map"),
    "format_visit_time": ("explorer.presentation.map_renderer", "format_visit_time"),
    "format_sighting_row": ("explorer.presentation.map_renderer", "format_sighting_row"),
    "popup_scroll_script": ("explorer.presentation.map_renderer", "popup_scroll_script"),
    "pin_legend_item": ("explorer.presentation.map_renderer", "pin_legend_item"),
    "build_all_species_banner_html": (
        "explorer.presentation.map_renderer",
        "build_all_species_banner_html",
    ),
    "build_species_banner_html": ("explorer.presentation.map_renderer", "build_species_banner_html"),
    "build_legend_html": ("explorer.presentation.map_renderer", "build_legend_html"),
    "build_visit_info_html": ("explorer.presentation.map_renderer", "build_visit_info_html"),
    "build_location_popup_html": ("explorer.presentation.map_renderer", "build_location_popup_html"),
    "resolve_lifer_last_seen": ("explorer.presentation.map_renderer", "resolve_lifer_last_seen"),
    "classify_locations": ("explorer.presentation.map_renderer", "classify_locations"),
    "format_checklist_stats_bundle": (
        "explorer.presentation.checklist_stats_display",
        "format_checklist_stats_bundle",
    ),
    "format_rankings_tab_html": (
        "explorer.presentation.checklist_stats_display",
        "format_rankings_tab_html",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        mod_path, attr = _LAZY_IMPORTS[name]
        return getattr(importlib.import_module(mod_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)


__all__ = [
    "load_taxonomy",
    "get_species_url",
    "get_species_lifelist_url",
    "get_species_and_lifelist_urls",
    "load_dataset",
    "add_datetime_column",
    "find_data_file",
    "base_species_name",
    "is_countable",
    "filter_species",
    "countable_species_vectorized",
    "base_species_for_lifer",
    "safe_count",
    "longest_streak",
    "compute_rankings",
    "yearly_summary_stats",
    "get_sex_notation_by_year",
    "get_map_maintenance_data",
    "ExplorerState",
    "MapOverlayResult",
    "build_species_overlay_map",
    "create_map",
    "format_visit_time",
    "format_sighting_row",
    "popup_scroll_script",
    "pin_legend_item",
    "build_all_species_banner_html",
    "build_species_banner_html",
    "build_legend_html",
    "build_visit_info_html",
    "build_location_popup_html",
    "resolve_lifer_last_seen",
    "classify_locations",
    "country_for_display",
    "state_for_display",
    "rankings_scroll_wrapper",
    "rankings_table",
    "rankings_table_location_5col",
    "rankings_table_with_rank",
    "rankings_visited_table",
    "rankings_seen_once_table",
    "WorkingSet",
    "rebuild_working_set_from_date_filter",
    "LiferLastSeenPrep",
    "aggregate_lifer_sites",
    "prepare_lifer_last_seen",
    "ChecklistStatsPayload",
    "compute_checklist_stats_payload",
    "protocol_display_name",
    "COUNTRY_TAB_SORT_ALPHABETICAL",
    "COUNTRY_TAB_SORT_LIFERS_WORLD",
    "COUNTRY_TAB_SORT_TOTAL_SPECIES",
    "format_checklist_stats_bundle",
    "format_rankings_tab_html",
    "EBIRD_LOCATION_EDIT_BASE",
    "format_map_maintenance_html",
    "format_sex_notation_maintenance_html",
    "format_incomplete_checklists_maintenance_html",
    "whoosh_common_name_suggestions",
]
