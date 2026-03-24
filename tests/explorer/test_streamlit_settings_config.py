"""Tests for Streamlit settings model and persistence helpers."""

from __future__ import annotations

import yaml
import pytest

pytest.importorskip("pydantic")


def test_load_yaml_settings_defaults_when_missing(tmp_path):
    from personal_ebird_explorer.streamlit_settings_config import load_yaml_settings

    cfg, warn = load_yaml_settings(str(tmp_path / "missing.yaml"))
    assert warn is None
    assert cfg["version"] == 1
    assert cfg["tables_lists"]["rankings_top_n"] == 200


def test_load_yaml_settings_rejects_invalid_type(tmp_path):
    from personal_ebird_explorer.streamlit_settings_config import load_yaml_settings

    p = tmp_path / "bad.yaml"
    p.write_text("tables_lists:\n  rankings_top_n: nope\n", encoding="utf-8")
    cfg, warn = load_yaml_settings(str(p))
    assert warn is not None
    assert cfg["tables_lists"]["rankings_top_n"] == 200


def test_write_sparse_preserves_unknown_keys(tmp_path):
    from personal_ebird_explorer.streamlit_settings_config import write_sparse_yaml_settings

    p = tmp_path / "config_secret.streamlit.yaml"
    p.write_text("custom:\n  keep: true\n", encoding="utf-8")
    current = {
        "version": 1,
        "map_display": {
            "popup_sort_order": "descending",
            "popup_scroll_hint": "shading",
            "mark_lifer": True,
            "mark_last_seen": True,
            "default_color": "green",
            "default_fill": "lightgreen",
            "species_color": "purple",
            "species_fill": "red",
            "lifer_color": "purple",
            "lifer_fill": "yellow",
            "last_seen_color": "purple",
            "last_seen_fill": "lightgreen",
        },
        "tables_lists": {"rankings_top_n": 200, "rankings_visible_rows": 16},
        "yearly_summary": {"recent_column_count": 10},
        "country": {"sort": "alphabetical"},
        "maintenance": {"close_location_meters": 10},
        "taxonomy": {"locale": "en_AU"},
    }
    ok, err = write_sparse_yaml_settings(str(p), current)
    assert ok and err is None
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert raw["custom"]["keep"] is True
    assert raw["map_display"]["popup_sort_order"] == "descending"
    assert "tables_lists" not in raw  # defaults omitted


def test_write_settings_embedded_in_python_config(tmp_path):
    from personal_ebird_explorer.streamlit_settings_config import (
        load_settings_from_python_config,
        write_sparse_settings_to_python_config,
    )

    p = tmp_path / "config_secret.py"
    p.write_text('DATA_FOLDER = "/tmp/data"\n', encoding="utf-8")
    current = {
        "version": 1,
        "map_display": {
            "popup_sort_order": "descending",
            "popup_scroll_hint": "shading",
            "mark_lifer": True,
            "mark_last_seen": True,
            "default_color": "green",
            "default_fill": "lightgreen",
            "species_color": "purple",
            "species_fill": "red",
            "lifer_color": "purple",
            "lifer_fill": "yellow",
            "last_seen_color": "purple",
            "last_seen_fill": "lightgreen",
        },
        "tables_lists": {"rankings_top_n": 200, "rankings_visible_rows": 16},
        "yearly_summary": {"recent_column_count": 10},
        "country": {"sort": "alphabetical"},
        "maintenance": {"close_location_meters": 10},
        "taxonomy": {"locale": "en_AU"},
    }
    ok, err = write_sparse_settings_to_python_config(str(p), current)
    assert ok and err is None
    text = p.read_text(encoding="utf-8")
    assert "STREAMLIT_SETTINGS_YAML" in text

    cfg, warn = load_settings_from_python_config(str(p))
    assert warn is None
    assert cfg["map_display"]["popup_sort_order"] == "descending"

