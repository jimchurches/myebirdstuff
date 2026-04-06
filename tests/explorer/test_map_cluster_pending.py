"""Settings → Apply map settings: deferred cluster key applied before sidebar (refs #98)."""

from __future__ import annotations

from explorer.app.streamlit.app_constants import (
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
)
from explorer.app.streamlit.app_settings_state import apply_pending_map_cluster_toggle


def test_apply_pending_map_cluster_true_sets_live_and_clears_pending():
    ss: dict = {STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY: True}
    apply_pending_map_cluster_toggle(ss)
    assert STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY not in ss
    assert ss[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY] is True


def test_apply_pending_map_cluster_false_sets_live_false():
    ss: dict = {STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY: False}
    apply_pending_map_cluster_toggle(ss)
    assert STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY not in ss
    assert ss[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY] is False


def test_apply_pending_map_cluster_missing_pending_leaves_live_unchanged():
    ss: dict = {STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY: True}
    apply_pending_map_cluster_toggle(ss)
    assert STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY not in ss
    assert ss[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY] is True


def test_apply_pending_map_cluster_missing_pending_and_live_does_not_add_live():
    ss: dict = {}
    apply_pending_map_cluster_toggle(ss)
    assert STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY not in ss
