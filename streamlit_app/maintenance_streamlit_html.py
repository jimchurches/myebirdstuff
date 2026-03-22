"""
**Maintenance** tab (Streamlit): top-level ``st.tabs`` + ``st.expander`` + HTML tables.

Reuses builders from ``personal_ebird_explorer.maintenance_display`` (refs #69, #79).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from personal_ebird_explorer.maintenance_display import (
    MAINTENANCE_STREAMLIT_COMBINED_CSS,
    incomplete_checklists_intro_html,
    incomplete_checklists_year_table_html,
    iter_incomplete_checklists_years_desc,
    iter_sex_notation_years_desc,
    map_maintenance_table_sections_html,
    sex_notation_intro_html,
    sex_notation_year_table_html,
)

_MAINT_WRAPPER_OPEN = (
    '<div class="streamlit-maint-html-ab" '
    'style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">'
)
_MAINT_WRAPPER_CLOSE = "</div>"


def _md(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def render_maintenance_streamlit_tab(
    loc_df: pd.DataFrame,
    *,
    close_location_meters: int,
    incomplete_by_year: Dict[Any, List[Tuple[Any, ...]]],
    sex_notation_by_year: Dict[Any, List[Tuple[Any, ...]]],
    species_url_fn: Callable[[str], Optional[str]],
) -> None:
    """Three category tabs; expanders collapsed by default; HTML tables only (refs #79)."""
    _md("<style>" + MAINTENANCE_STREAMLIT_COMBINED_CSS + "</style>")

    tab_loc, tab_inc, tab_sex = st.tabs(
        [
            "Location Maintenance",
            "Incomplete checklists (Traveling or Stationary)",
            "Sex notation in checklist comments",
        ]
    )

    with tab_loc:
        intro, exact_body, close_body = map_maintenance_table_sections_html(
            loc_df, close_location_meters
        )
        _md(_MAINT_WRAPPER_OPEN + intro + _MAINT_WRAPPER_CLOSE)
        with st.expander("Exact duplicates", expanded=False):
            _md(_MAINT_WRAPPER_OPEN + exact_body + _MAINT_WRAPPER_CLOSE)
        with st.expander("Close locations", expanded=False):
            _md(_MAINT_WRAPPER_OPEN + close_body + _MAINT_WRAPPER_CLOSE)

    with tab_inc:
        _md(_MAINT_WRAPPER_OPEN + incomplete_checklists_intro_html() + _MAINT_WRAPPER_CLOSE)
        if not incomplete_by_year:
            _md(
                _MAINT_WRAPPER_OPEN
                + '<p style="margin:8px 0;color:#6b7280;">No incomplete travelling or stationary checklists found.</p>'
                + _MAINT_WRAPPER_CLOSE
            )
        else:
            for y, items in iter_incomplete_checklists_years_desc(incomplete_by_year):
                with st.expander(str(y), expanded=False):
                    table = incomplete_checklists_year_table_html(y, items)
                    _md(_MAINT_WRAPPER_OPEN + table + _MAINT_WRAPPER_CLOSE)

    with tab_sex:
        _md(_MAINT_WRAPPER_OPEN + sex_notation_intro_html() + _MAINT_WRAPPER_CLOSE)
        if not sex_notation_by_year:
            _md(
                _MAINT_WRAPPER_OPEN
                + '<p style="margin:8px 0;color:#6b7280;">No shorthand sex or age notation detected in checklist comments.</p>'
                + _MAINT_WRAPPER_CLOSE
            )
        else:
            for y, items in iter_sex_notation_years_desc(sex_notation_by_year):
                with st.expander(str(y), expanded=False):
                    table = sex_notation_year_table_html(
                        y, items, species_url_fn=species_url_fn
                    )
                    _md(_MAINT_WRAPPER_OPEN + table + _MAINT_WRAPPER_CLOSE)
