"""Ensure :mod:`explorer.app.streamlit.defaults` stays aligned with persisted settings."""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")


def test_persisted_defaults_match_streamlit_settings_model():
    from explorer.core.settings_schema_defaults import (
        SETTINGS_SCHEMA_VERSION,
        build_persisted_settings_defaults_dict,
    )
    from explorer.core.settings_config import StreamlitSettingsConfig, defaults_dict

    raw = build_persisted_settings_defaults_dict()
    cfg = StreamlitSettingsConfig.model_validate(raw)
    assert cfg.version == SETTINGS_SCHEMA_VERSION

    assert defaults_dict() == cfg.model_dump()
    assert StreamlitSettingsConfig().model_dump() == cfg.model_dump()


def test_lifer_location_cluster_tunables_match_all_locations_v1() -> None:
    """Lifer map has separate constants; v1 values match All locations."""
    from explorer.app.streamlit.defaults import (
        MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
        MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
        MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
        MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
        MAP_LIFER_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
        MAP_LIFER_LOCATION_CLUSTER_MAX_RADIUS_PX,
        MAP_LIFER_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
        MAP_LIFER_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    )

    assert MAP_LIFER_LOCATION_CLUSTER_MAX_RADIUS_PX == MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX
    assert MAP_LIFER_LOCATION_CLUSTER_DISABLE_AT_ZOOM == 7
    assert MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM == 9
    assert (
        MAP_LIFER_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM
        == MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM
    )
    assert (
        MAP_LIFER_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
        == MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
    )
