"""Tests for ``explorer.app.streamlit.app_map_working_ui`` orchestration (#362)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

pytest.importorskip(
    "streamlit", reason="explorer.app.streamlit.app_map_working_ui is for Streamlit UI"
)

import streamlit as st  # noqa: E402

from explorer.app.streamlit import app_map_working_ui as mwu  # noqa: E402
from explorer.app.streamlit.app_constants import (  # noqa: E402
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_WS_KEY,
    STREAMLIT_MAP_VIEW_LABEL_KEY,
)


def test_species_search_index_built_before_sidebar_renders(monkeypatch):
    """Regression for #362: the species searchbox fragment renders nothing when
    ``SESSION_SPECIES_IX_KEY`` is absent, so species session prep must complete
    before ``render_map_sidebar`` runs.
    """
    state: dict = {STREAMLIT_MAP_VIEW_LABEL_KEY: "Species locations"}
    monkeypatch.setattr(st, "session_state", state)

    monkeypatch.setattr(mwu, "ensure_streamlit_map_basemap_height_keys", lambda: None)
    monkeypatch.setattr(mwu, "ensure_streamlit_map_marker_colour_scheme_keys", lambda: None)
    monkeypatch.setattr(mwu, "apply_pending_map_cluster_toggle", lambda _s: None)
    monkeypatch.setattr(mwu, "apply_pending_map_basemap_override", lambda _s: None)
    monkeypatch.setattr(mwu, "apply_pending_map_height_override", lambda _s: None)
    monkeypatch.setattr(mwu, "apply_pending_map_marker_colour_scheme", lambda _s: None)
    monkeypatch.setattr(mwu, "inject_spinner_theme_css", lambda: None)
    monkeypatch.setattr(mwu, "is_social_cards_main_tab", lambda: False)
    monkeypatch.setattr(mwu, "invalidate_map_embed_cache", lambda: None)
    monkeypatch.setattr(mwu, "_all_locations_leaflet_embed_active", lambda _s: True)

    df = pd.DataFrame({"Submission ID": ["s1"], "Date": ["2025-06-01"]})
    ws = SimpleNamespace(
        df=df,
        species_list=["Grey Teal"],
        name_map={"Grey Teal": "Anas gracilis"},
    )
    monkeypatch.setattr(
        mwu,
        "streamlit_working_set_and_status",
        lambda *_a, **_k: (ws, None),
    )
    monkeypatch.setattr(
        mwu, "build_ram_species_whoosh_index", lambda *_a, **_k: "SENTINEL_INDEX"
    )

    seen_at_sidebar_render: dict = {}

    def _fake_render_map_sidebar(_df_full, *, work_df):
        seen_at_sidebar_render["index"] = state.get(SESSION_SPECIES_IX_KEY)
        seen_at_sidebar_render["ws"] = state.get(SESSION_SPECIES_WS_KEY)

    monkeypatch.setattr(mwu, "render_map_sidebar", _fake_render_map_sidebar)

    ctx = mwu.render_map_sidebar_and_working_set(df)

    assert seen_at_sidebar_render["index"] == "SENTINEL_INDEX"
    assert seen_at_sidebar_render["ws"] is ws
    assert ctx.map_view_mode == "species"
