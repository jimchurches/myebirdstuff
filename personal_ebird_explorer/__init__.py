# Personal eBird Explorer — dataset loading and utilities

from personal_ebird_explorer.data_loader import load_dataset, add_datetime_column
from personal_ebird_explorer.path_resolution import find_data_file
from personal_ebird_explorer.species_logic import (
    base_species_name,
    is_countable,
    filter_species,
    countable_species_vectorized,
    base_species_for_lifer,
)
from personal_ebird_explorer.stats import (
    safe_count,
    longest_streak,
    compute_rankings,
    yearly_summary_stats,
    get_sex_notation_by_year,
)
from personal_ebird_explorer.duplicate_checks import get_map_maintenance_data
from personal_ebird_explorer.ui_state import ExplorerState
from personal_ebird_explorer.region_display import country_for_display, state_for_display
from personal_ebird_explorer.rankings_display import (
    rankings_scroll_wrapper,
    rankings_table,
    rankings_table_location_5col,
    rankings_table_with_rank,
    rankings_visited_table,
    rankings_seen_once_table,
)
from personal_ebird_explorer.taxonomy import (
    load_taxonomy,
    get_species_url,
    get_species_lifelist_url,
)
from personal_ebird_explorer.map_renderer import (
    create_map,
    format_visit_time,
    format_sighting_row,
    popup_scroll_script,
    pin_legend_item,
    build_all_species_banner_html,
    build_species_banner_html,
    build_legend_html,
    build_visit_info_html,
    build_location_popup_html,
    resolve_lifer_last_seen,
    classify_locations,
)

__all__ = [
    "load_taxonomy",
    "get_species_url",
    "get_species_lifelist_url",
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
]
