"""Regression: E2E helpers must not read or write repo ``config/config_secret.yaml``."""

from __future__ import annotations

import os
from pathlib import Path

from tests.explorer.e2e_support import INTEGRATION_FIXTURE_CSV, temporary_ebird_csv_config


def test_temporary_ebird_csv_config_leaves_repo_config_untouched(tmp_path):
    """Repo ``config/`` files stay byte-identical; no ``.e2e-bak`` sidecar."""
    repo = tmp_path / "repo"
    config_dir = repo / "config"
    config_dir.mkdir(parents=True)
    secret = config_dir / "config_secret.yaml"
    secret.write_text(
        "data_folder: /home/me/ebird\n"
        "google_api_key: test-key-should-survive\n"
        "explorer_settings:\n  map_height_px: 640\n",
        encoding="utf-8",
    )
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text("data_folder: /home/me/ebird\n", encoding="utf-8")
    secret_before = secret.read_bytes()
    config_before = config_yaml.read_bytes()

    pytest_tmp = tmp_path / "pytest_tmp"
    pytest_tmp.mkdir()
    with temporary_ebird_csv_config(pytest_tmp, INTEGRATION_FIXTURE_CSV) as env:
        assert "EXPLORER_CONFIG_DIR" in env
        isolated = Path(env["EXPLORER_CONFIG_DIR"])
        assert isolated.is_dir()
        assert (isolated / "config.yaml").is_file()
        assert not (isolated / "config_secret.yaml").exists()

    assert secret.read_bytes() == secret_before
    assert config_yaml.read_bytes() == config_before
    assert not (config_dir / "config_secret.yaml.e2e-bak").exists()


def test_build_explorer_candidate_dirs_honours_explorer_config_dir(tmp_path, monkeypatch):
    """``EXPLORER_CONFIG_DIR`` redirects YAML lookup away from ``repo/config``."""
    from explorer.core.explorer_paths import (
        EXPLORER_CONFIG_DIR_ENV,
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    isolated_config = tmp_path / "isolated_config"
    isolated_config.mkdir()
    data_dir = tmp_path / "isolated_data"
    data_dir.mkdir()
    (data_dir / "MyEBirdData.csv").write_text("Date,Time\n", encoding="utf-8")

    (isolated_config / "config.yaml").write_text(
        f"data_folder: {data_dir.as_posix()}\n",
        encoding="utf-8",
    )
    # Repo config would point elsewhere if accidentally read.
    (repo / "config" / "config.yaml").write_text(
        "data_folder: /wrong/path\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(EXPLORER_CONFIG_DIR_ENV, str(isolated_config))
    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(tmp_path / "cwd"))
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(folder) == os.path.normpath(str(data_dir))
    assert src == "config"
