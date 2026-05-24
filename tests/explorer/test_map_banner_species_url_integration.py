"""Integration: map prep wires ``species_banner_url`` into banner HTML (#253)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pandas as pd
import pytest

from explorer.core.family_map_compute import (
    base_species_to_common_from_taxonomy,
    families_recorded_alphabetically,
    prepare_family_map_work_frame,
)
from explorer.core.map_prep import prepare_all_locations_map_context
from tests.explorer.test_family_map_compute import (
    _base_to_family_stub,
    _tiny_export_rows,
)
from tests.explorer.test_streamlit_map_prep import _tiny_df
from tests.explorer.test_streamlit_ui_helpers import _drop_submodule, _install_streamlit_stub


@pytest.fixture
def streamlit_stub(monkeypatch: pytest.MonkeyPatch):
    _install_streamlit_stub(monkeypatch)
    import streamlit as st

    st.session_state.clear()
    _drop_submodule("explorer.app.streamlit.app_prep_map_ui")
    _drop_submodule("explorer.app.streamlit.app_prep_map_leaflet_modes")
    return st


@pytest.fixture
def mock_species_banner_taxonomy(monkeypatch: pytest.MonkeyPatch):
    rows = pd.DataFrame(
        {
            "base_species": ["anas gracilis", "pachycephala rufiventris"],
            "species_code": ["grtea", "rufwhi1"],
            "common_name": ["Grey Teal", "Rufous Whistler"],
        }
    )
    bundle = MagicMock(species_rows=rows, groups=[])
    monkeypatch.setattr(
        "explorer.core.species_link_urls.load_taxonomy_bundle",
        lambda _locale: bundle,
    )
    return rows


@pytest.fixture
def noop_perf_span(monkeypatch: pytest.MonkeyPatch):
    import explorer.app.streamlit.app_prep_map_ui as app_prep_map_ui

    @contextmanager
    def _noop(*_a, **_k):
        yield

    monkeypatch.setattr(app_prep_map_ui, "perf_span", _noop)


def _mock_family_map_bundle(_df_full: pd.DataFrame, _taxonomy_locale: str) -> dict:
    df = _tiny_export_rows()
    work = prepare_family_map_work_frame(df, _base_to_family_stub())
    tax_merged = pd.DataFrame(
        {
            "base_species": [
                "pachycephala olivacea",
                "pachycephala pectoralis",
                "pachycephala rufiventris",
                "anas gracilis",
            ],
            "species_code": ["oliwhi1", "golwhi1", "rufwhi1", "grtea"],
            "common_name": [
                "Olive Whistler",
                "Golden Whistler",
                "Rufous Whistler",
                "Grey Teal",
            ],
            "group_name": [
                "Whistlers and Allies",
                "Whistlers and Allies",
                "Whistlers and Allies",
                "Ducks, Geese, and Swans",
            ],
        }
    )
    return {
        "work": work,
        "tax_merged": tax_merged,
        "base_to_common": base_species_to_common_from_taxonomy(tax_merged),
        "families": families_recorded_alphabetically(work),
    }


def test_species_map_prep_banner_includes_ebird_species_link(
    streamlit_stub,
    mock_species_banner_taxonomy,
    noop_perf_span,
) -> None:
    from explorer.app.streamlit.app_prep_map_leaflet_modes import (
        prep_standard_map_leaflet_modes,
    )

    df = _tiny_df()
    ctx = prepare_all_locations_map_context(df)
    bundle, hint = prep_standard_map_leaflet_modes(
        ctx=ctx,
        work_df=df,
        tax_locale_effective="en_AU",
        map_view_mode="species",
        date_filter_banner="",
        map_style="default",
        map_height=400,
        species_pick_common="Grey Teal",
        species_pick_sci="Anas gracilis",
        hide_non_matching_locations=False,
        popup_sort_order="date_desc",
        popup_scroll_hint="",
        mark_lifer=False,
        mark_last_seen=False,
        family_colour_scheme=0,
        blank_viewport_recipe={},
        species_url_fn=lambda _name: None,
    )

    assert hint is None
    assert bundle.use_species_leaflet is True
    assert 'href="https://ebird.org/species/grtea"' in (
        bundle.all_locations_leaflet_banner_html or ""
    )


def test_family_map_prep_highlight_banner_includes_ebird_species_link(
    streamlit_stub,
    mock_species_banner_taxonomy,
    noop_perf_span,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import explorer.app.streamlit.app_prep_map_leaflet_modes as leaflet_modes

    monkeypatch.setattr(
        leaflet_modes,
        "cached_family_map_bundle",
        _mock_family_map_bundle,
    )

    df = _tiny_export_rows()
    bundle, hint = leaflet_modes.prep_family_leaflet_mode(
        work_df=df,
        df_full=df,
        tax_locale_effective="en_AU",
        date_filter_banner="",
        map_style="default",
        map_height=400,
        map_view_mode="families",
        family_name="Whistlers and Allies",
        family_highlight_base="pachycephala rufiventris",
        family_colour_scheme=0,
        blank_viewport_recipe={},
        species_url_fn=lambda _name: None,
    )

    assert hint is None
    assert bundle.use_family_leaflet is True
    banner = bundle.all_locations_leaflet_banner_html or ""
    assert 'href="https://ebird.org/species/rufwhi1"' in banner
