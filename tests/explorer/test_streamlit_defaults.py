"""Ensure :mod:`streamlit_app.defaults` stays aligned with persisted settings (refs #70)."""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")


def test_persisted_defaults_match_streamlit_settings_model():
    from streamlit_app.defaults import SETTINGS_SCHEMA_VERSION, build_persisted_settings_defaults_dict
    from personal_ebird_explorer.streamlit_settings_config import StreamlitSettingsConfig, defaults_dict

    raw = build_persisted_settings_defaults_dict()
    cfg = StreamlitSettingsConfig.model_validate(raw)
    assert cfg.version == SETTINGS_SCHEMA_VERSION

    assert defaults_dict() == cfg.model_dump()
    assert StreamlitSettingsConfig().model_dump() == cfg.model_dump()
