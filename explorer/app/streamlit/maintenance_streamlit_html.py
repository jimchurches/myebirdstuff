"""
**Maintenance** tab (Streamlit): top-level ``st.tabs`` + ``st.expander`` + HTML tables.

Reuses builders from ``explorer.presentation.maintenance_display`` (refs #69, #79).
Uses the same scoped CSS as Checklist Statistics / Country (``CHECKLIST_STATS_*`` + ``.streamlit-checklist-html-ab``).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from explorer.presentation.maintenance_display import (
    incomplete_checklists_intro_html,
    incomplete_checklists_year_table_html,
    iter_incomplete_checklists_years_desc,
    iter_sex_notation_years_desc,
    map_maintenance_table_sections_html,
    sex_notation_intro_html,
    sex_notation_year_table_html,
)
from explorer.app.streamlit.app_caches import cached_species_url_fn
from explorer.app.streamlit.app_constants import (
    DEFAULT_TAXONOMY_LOCALE,
    MAINTENANCE_TAB_SYNC_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
)
from explorer.app.streamlit.streamlit_theme import inject_streamlit_checklist_css

# Same wrapper class as Checklist Statistics + Country HTML tabs (typography, tables, links).
_WRAPPER_OPEN = '<div class="streamlit-checklist-html-ab">'
_WRAPPER_CLOSE = "</div>"


def _md(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def sync_maintenance_tab_session_inputs(
    loc_df: pd.DataFrame,
    *,
    close_location_meters: int,
    incomplete_by_year: Dict[Any, List[Tuple[Any, ...]]],
    sex_notation_by_year: Dict[Any, List[Tuple[Any, ...]]],
) -> None:
    """Store maintenance inputs for :func:`run_maintenance_streamlit_tab_fragment` (full script runs)."""
    st.session_state[MAINTENANCE_TAB_SYNC_KEY] = {
        "loc_df": loc_df,
        "close_location_meters": close_location_meters,
        "incomplete_by_year": incomplete_by_year,
        "sex_notation_by_year": sex_notation_by_year,
    }


@st.fragment
def run_maintenance_streamlit_tab_fragment() -> None:
    """Maintenance tab; expander interactions avoid full-app reruns where possible."""
    data = st.session_state.get(MAINTENANCE_TAB_SYNC_KEY)
    if not data:
        return
    tax = (st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY) or "").strip() or DEFAULT_TAXONOMY_LOCALE
    species_url_fn = cached_species_url_fn(tax)
    render_maintenance_streamlit_tab(
        data["loc_df"],
        close_location_meters=int(data["close_location_meters"]),
        incomplete_by_year=data["incomplete_by_year"],
        sex_notation_by_year=data["sex_notation_by_year"],
        species_url_fn=species_url_fn,
    )


def render_maintenance_streamlit_tab(
    loc_df: pd.DataFrame,
    *,
    close_location_meters: int,
    incomplete_by_year: Dict[Any, List[Tuple[Any, ...]]],
    sex_notation_by_year: Dict[Any, List[Tuple[Any, ...]]],
    species_url_fn: Callable[[str], Optional[str]],
) -> None:
    """Three category tabs; expanders collapsed by default; HTML tables only (refs #79)."""
    inject_streamlit_checklist_css()

    tab_sex, tab_inc, tab_loc = st.tabs(
        [
            "Sex notation in checklist comments",
            "Incomplete checklists (Traveling or Stationary)",
            "Location Maintenance",
        ]
    )

    with tab_sex:
        _md(_WRAPPER_OPEN + sex_notation_intro_html() + _WRAPPER_CLOSE)
        if not sex_notation_by_year:
            _md(
                _WRAPPER_OPEN
                + '<p class="maint-html-caption">No shorthand sex or age notation detected in checklist comments.</p>'
                + _WRAPPER_CLOSE
            )
        else:
            for y, items in iter_sex_notation_years_desc(sex_notation_by_year):
                with st.expander(str(y), expanded=False):
                    table = sex_notation_year_table_html(
                        y, items, species_url_fn=species_url_fn
                    )
                    _md(_WRAPPER_OPEN + table + _WRAPPER_CLOSE)

    with tab_inc:
        _md(_WRAPPER_OPEN + incomplete_checklists_intro_html() + _WRAPPER_CLOSE)
        if not incomplete_by_year:
            _md(
                _WRAPPER_OPEN
                + '<p class="maint-html-caption">No incomplete travelling or stationary checklists found.</p>'
                + _WRAPPER_CLOSE
            )
        else:
            for y, items in iter_incomplete_checklists_years_desc(incomplete_by_year):
                with st.expander(str(y), expanded=False):
                    table = incomplete_checklists_year_table_html(y, items)
                    _md(_WRAPPER_OPEN + table + _WRAPPER_CLOSE)

    with tab_loc:
        intro, exact_body, close_body = map_maintenance_table_sections_html(
            loc_df, close_location_meters
        )
        _md(_WRAPPER_OPEN + intro + _WRAPPER_CLOSE)
        with st.expander("Exact duplicates", expanded=False):
            _md(_WRAPPER_OPEN + exact_body + _WRAPPER_CLOSE)
        with st.expander("Close locations", expanded=False):
            _md(_WRAPPER_OPEN + close_body + _WRAPPER_CLOSE)
