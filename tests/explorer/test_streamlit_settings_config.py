"""Tests for Streamlit settings model and persistence helpers."""

from __future__ import annotations

import yaml
import pytest

pytest.importorskip("pydantic")


def test_load_yaml_settings_defaults_when_missing(tmp_path):
    from explorer.core.settings_config import load_yaml_settings

    cfg, warn = load_yaml_settings(str(tmp_path / "missing.yaml"))
    assert warn is None
    assert cfg["version"] == 1
    assert cfg["tables_lists"]["rankings_top_n"] == 200
    assert cfg["tables_lists"]["high_count_sort"] == "total_count"
    assert cfg["tables_lists"]["high_count_tie_break"] == "last"


def test_load_yaml_settings_rejects_invalid_type(tmp_path):
    from explorer.core.settings_config import load_yaml_settings

    p = tmp_path / "bad.yaml"
    p.write_text("tables_lists:\n  rankings_top_n: nope\n", encoding="utf-8")
    cfg, warn = load_yaml_settings(str(p))
    assert warn is not None
    assert cfg["tables_lists"]["rankings_top_n"] == 200


def test_write_sparse_preserves_unknown_keys(tmp_path):
    from explorer.core.settings_config import write_sparse_yaml_settings

    p = tmp_path / "config_secret.streamlit.yaml"
    p.write_text("custom:\n  keep: true\n", encoding="utf-8")
    current = {
        "version": 1,
        "map_display": {
            "popup_sort_order": "descending",
            "popup_scroll_hint": "shading",
            "mark_lifer": True,
            "mark_last_seen": True,
            "basemap": "default",
            "map_height_px": 720,
            "cluster_all_locations": True,
            "map_marker_colour_scheme": 2,
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
    assert raw["map_display"]["map_marker_colour_scheme"] == 2
    assert "tables_lists" not in raw  # defaults omitted


def test_config_path_yaml_roundtrip(tmp_path):
    from explorer.core.settings_config import (
        load_settings_from_config_path,
        write_sparse_settings_to_config_path,
    )

    p = tmp_path / "config_secret.yaml"
    p.write_text(
        "google_api_key: abc123\n"
        "data_folder: /tmp/ebird\n"
        "deploy_destination: /tmp/deploy.py\n",
        encoding="utf-8",
    )
    current = {
        "version": 1,
        "map_display": {
            "popup_sort_order": "descending",
            "popup_scroll_hint": "shading",
            "mark_lifer": True,
            "mark_last_seen": True,
            "basemap": "default",
            "map_height_px": 720,
            "cluster_all_locations": True,
            "map_marker_colour_scheme": 2,
        },
        "tables_lists": {"rankings_top_n": 200, "rankings_visible_rows": 16},
        "yearly_summary": {"recent_column_count": 10},
        "country": {"sort": "alphabetical"},
        "maintenance": {"close_location_meters": 10},
        "taxonomy": {"locale": "en_AU"},
    }
    ok, err = write_sparse_settings_to_config_path(str(p), current)
    assert ok and err is None
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert raw["google_api_key"] == "abc123"
    assert raw["data_folder"] == "/tmp/ebird"
    assert raw["deploy_destination"] == "/tmp/deploy.py"
    assert "explorer_settings" in raw

    cfg, warn = load_settings_from_config_path(str(p))
    assert warn is None
    assert cfg["map_display"]["popup_sort_order"] == "descending"
    assert cfg["map_display"]["map_marker_colour_scheme"] == 2


def test_settings_data_path_html_includes_config_path_when_given():
    from explorer.app.streamlit.app_settings_state import settings_data_path_html

    html_out = settings_data_path_html(
        data_basename="MyEBirdData.csv",
        data_abs_path="/data/MyEBirdData.csv",
        source_label="config_secret",
        repo_root="/repo",
        config_yaml_abs_path="/repo/config/config_secret.yaml",
    )
    assert "Configuration file path:" in html_out
    assert "/repo/config/config_secret.yaml" in html_out


def test_settings_data_path_html_omits_config_path_when_not_passed():
    from explorer.app.streamlit.app_settings_state import settings_data_path_html

    html_out = settings_data_path_html(
        data_basename="MyEBirdData.csv",
        data_abs_path="/data/MyEBirdData.csv",
        source_label="cwd",
        repo_root="/repo",
    )
    assert "Configuration file path:" not in html_out

