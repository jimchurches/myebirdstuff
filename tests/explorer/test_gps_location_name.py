"""Tests for Maintenance GPS → locality naming (shared with GPS script)."""

from __future__ import annotations

from pathlib import Path

import pytest

from explorer.core import gps_location_name as subject
from explorer.presentation.maintenance_display import gps_name_from_coords_intro_html


@pytest.fixture(autouse=True)
def _clear_gps_module_cache() -> None:
    subject._gps_script_module.cache_clear()
    yield
    subject._gps_script_module.cache_clear()


def test_google_geocode_api_key_from_yaml_none_when_missing(tmp_path: Path) -> None:
    assert subject.google_geocode_api_key_from_yaml(str(tmp_path)) is None


def test_google_geocode_api_key_from_yaml_prefers_config_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config_secret.yaml").write_text(
        'google_api_key: "yaml-secret-key"\n', encoding="utf-8"
    )
    (config_dir / "config.yaml").write_text(
        'google_api_key: "yaml-fallback-key"\n', encoding="utf-8"
    )
    monkeypatch.setenv("EXPLORER_CONFIG_DIR", str(config_dir))

    assert subject.google_geocode_api_key_from_yaml(str(tmp_path)) == "yaml-secret-key"


def test_load_google_geocode_api_key_prefers_session_override(tmp_path: Path) -> None:
    assert (
        subject.load_google_geocode_api_key(str(tmp_path), override=" session-paste ")
        == "session-paste"
    )


def test_load_google_geocode_api_key_reads_config_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config_secret.yaml").write_text(
        'google_api_key: "yaml-secret-key"\n', encoding="utf-8"
    )
    monkeypatch.setenv("EXPLORER_CONFIG_DIR", str(config_dir))

    assert subject.load_google_geocode_api_key(str(tmp_path)) == "yaml-secret-key"


def test_load_google_geocode_api_key_rejects_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Google API key not configured"):
        subject.load_google_geocode_api_key(str(tmp_path), override="")


def test_resolve_formatted_location_name_matches_script_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gps = subject._gps_script_module()
    monkeypatch.setattr(
        gps,
        "parse_coords_from_text",
        lambda text: (-35.339578, 148.923133, 6, 6),
    )
    monkeypatch.setattr(
        gps,
        "resolve_location",
        lambda lat, lng, api_key, debug=False, include_json=False: "Paddy's River",
    )

    assert (
        subject.resolve_formatted_location_name("-35.339578, 148.923133", "k")
        == "Paddy's River ( -35.339578, 148.923133 )"
    )


def test_resolve_formatted_location_name_propagates_parse_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gps = subject._gps_script_module()
    monkeypatch.setattr(
        gps,
        "parse_coords_from_text",
        lambda text: (_ for _ in ()).throw(ValueError("No coordinates provided.")),
    )

    with pytest.raises(ValueError, match="No coordinates provided"):
        subject.resolve_formatted_location_name("", "k")


def test_resolve_formatted_location_name_uses_real_parse_and_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse + format run for real; only the live geocode call is stubbed."""
    gps = subject._gps_script_module()
    monkeypatch.setattr(
        gps,
        "resolve_location",
        lambda lat, lng, api_key, debug=False, include_json=False: "Paddy's River",
    )
    assert (
        subject.resolve_formatted_location_name("-35.339578, 148.923133", "k")
        == "Paddy's River ( -35.339578, 148.923133 )"
    )


def test_gps_name_intro_html_uses_maintenance_blurb_style() -> None:
    html = gps_name_from_coords_intro_html()
    assert 'class="maint-html-blurb"' in html
    assert "Sutton ( -35.172194, 149.224916 )" in html
    assert "Google Maps API key" in html
    assert "Select and copy the resolved result into eBird manually." in html
