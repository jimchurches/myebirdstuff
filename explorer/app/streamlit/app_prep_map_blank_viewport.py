"""Blank-map default viewport recipe for Species / Family awaiting-selection (R13)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from explorer.app.streamlit.app_constants import (
    STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
    STREAMLIT_BLANK_MAP_DEFAULT_VIEWPORT_RECIPE_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
)
from explorer.app.streamlit.defaults import (
    MAP_ALL_LOCATIONS_CENTRE_OF_GRAVITY_ZOOM,
    MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM,
    MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX,
    MAP_ALL_LOCATIONS_FOCUSED_MIN_OBSERVATIONS_PER_COUNTRY,
    MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_HIGH,
    MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_LOW,
    MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM,
    MAP_SPECIES_DEFAULT_CENTER_LAT,
    MAP_SPECIES_DEFAULT_CENTER_LON,
    MAP_SPECIES_DEFAULT_ZOOM,
)
from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FOCUS_ALL,
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    coordinate_pairs_focused_viewport,
    coordinate_pairs_for_viewport,
    location_id_to_country_map,
    mean_center_from_pairs,
    observation_row_counts_by_country_key,
)


def seed_blank_map_default_viewport_recipe(
    ctx: dict[str, Any],
    *,
    map_view_mode: str,
) -> dict[str, Any]:
    """Persist and return the session blank-map viewport recipe used when Species/Family have no pins."""
    _seed_recipe = {
        "mode": "center_zoom",
        "center": [float(MAP_SPECIES_DEFAULT_CENTER_LAT), float(MAP_SPECIES_DEFAULT_CENTER_LON)],
        "zoom": int(MAP_SPECIES_DEFAULT_ZOOM),
    }
    _cached_recipe = st.session_state.get(STREAMLIT_BLANK_MAP_DEFAULT_VIEWPORT_RECIPE_KEY)
    blank_viewport_recipe = _cached_recipe if isinstance(_cached_recipe, dict) else _seed_recipe

    _date_filter_on = bool(st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False))
    if map_view_mode == "all" and not _date_filter_on:
        _scope = str(
            st.session_state.get(
                STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
                ALL_LOCATIONS_SCOPE_FOCUSED,
            )
            or ALL_LOCATIONS_SCOPE_FOCUSED
        ).strip()
        _allowed_scopes = {
            ALL_LOCATIONS_FRAMING_FIT_ALL,
            ALL_LOCATIONS_SCOPE_FOCUSED,
            ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
        }
        if _scope in _allowed_scopes:
            _loc_c = location_id_to_country_map(ctx["df"])
            _pairs: list[list[float]] = []
            if _scope == ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY:
                _pairs = coordinate_pairs_for_viewport(
                    ctx["effective_location_data"],
                    location_id_to_country=_loc_c,
                    focus_country=ALL_LOCATIONS_FOCUS_ALL,
                )
                _mc = mean_center_from_pairs(_pairs)
                if _mc is not None:
                    blank_viewport_recipe = {
                        "mode": "center_zoom",
                        "center": [float(_mc[0]), float(_mc[1])],
                        "zoom": int(MAP_ALL_LOCATIONS_CENTRE_OF_GRAVITY_ZOOM),
                    }
            elif _scope == ALL_LOCATIONS_SCOPE_FOCUSED:
                _min_c = int(MAP_ALL_LOCATIONS_FOCUSED_MIN_OBSERVATIONS_PER_COUNTRY)
                _obs_by_c = observation_row_counts_by_country_key(ctx["df"]) if _min_c > 0 else {}
                _pairs = coordinate_pairs_focused_viewport(
                    ctx["effective_location_data"],
                    location_id_to_country=_loc_c,
                    observation_counts_by_country=_obs_by_c,
                    quantile_low=MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_LOW,
                    quantile_high=MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_HIGH,
                    min_observations_full_country=_min_c,
                )
            else:
                _pairs = coordinate_pairs_for_viewport(
                    ctx["effective_location_data"],
                    location_id_to_country=_loc_c,
                    focus_country=ALL_LOCATIONS_FOCUS_ALL,
                )
            if _scope != ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY and _pairs:
                blank_viewport_recipe = {
                    "mode": "fit_bounds",
                    "pairs": [[float(p[0]), float(p[1])] for p in _pairs],
                    "padding_px": int(MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX),
                    "max_zoom": int(MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM),
                    "single_point_zoom": int(MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM),
                }
            st.session_state[STREAMLIT_BLANK_MAP_DEFAULT_VIEWPORT_RECIPE_KEY] = blank_viewport_recipe

    return blank_viewport_recipe
