"""Tests for explorer CSV path resolution (Streamlit-aligned)."""

from __future__ import annotations

import os
import pytest


def test_build_explorer_candidate_dirs_config_then_cwd(tmp_path):
    from personal_ebird_explorer.explorer_paths import build_explorer_candidate_dirs

    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    cwd_dir = tmp_path / "cwd_here"
    cwd_dir.mkdir()

    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(cwd_dir))
    assert folders == [os.path.normpath(str(cwd_dir))]
    assert sources == ["cwd"]


def test_resolve_ebird_data_file_finds_in_cwd_when_no_config(tmp_path):
    from personal_ebird_explorer.explorer_paths import (
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    cwd_dir = tmp_path / "run_from_here"
    cwd_dir.mkdir()
    csv_path = cwd_dir / "MyEBirdData.csv"
    csv_path.write_text("Date,Time\n", encoding="utf-8")

    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(cwd_dir))
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(path) == os.path.normpath(str(csv_path))
    assert src == "cwd"


def test_resolve_prefers_config_secret_over_cwd(tmp_path):
    from personal_ebird_explorer.explorer_paths import (
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    config = repo / "config"
    config.mkdir(parents=True)
    data_secret = tmp_path / "secret_data"
    data_secret.mkdir()
    cwd_dir = tmp_path / "cwd_here"
    cwd_dir.mkdir()
    (data_secret / "MyEBirdData.csv").write_text("Date,Time\n", encoding="utf-8")
    (cwd_dir / "MyEBirdData.csv").write_text("wrong\n", encoding="utf-8")

    (config / "config_secret.yaml").write_text(
        f"data_folder: {data_secret.as_posix()}\n",
        encoding="utf-8",
    )

    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(cwd_dir))
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(folder) == os.path.normpath(str(data_secret))
    assert src == "config_secret"


def test_resolve_raises_file_not_found():
    from personal_ebird_explorer.explorer_paths import resolve_ebird_data_file

    with pytest.raises(FileNotFoundError) as exc:
        resolve_ebird_data_file("nope.csv", ["/nonexistent"], ["x"])
    assert "nope.csv" in str(exc.value)


def test_settings_yaml_path_for_source(tmp_path):
    from personal_ebird_explorer.explorer_paths import settings_yaml_path_for_source

    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)

    p1 = settings_yaml_path_for_source(str(repo), "config_secret")
    p2 = settings_yaml_path_for_source(str(repo), "config")
    p3 = settings_yaml_path_for_source(str(repo), "cwd")

    assert p1 and p1.endswith("config/config_secret.yaml")
    assert p2 and p2.endswith("config/config.yaml")
    assert p3 is None


def test_config_yaml_wins_over_cwd_when_both_have_csv(tmp_path):
    from personal_ebird_explorer.explorer_paths import (
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    config = repo / "config"
    config.mkdir(parents=True)
    data_from_config = tmp_path / "from_config"
    data_from_config.mkdir()
    cwd_dir = tmp_path / "cwd_here"
    cwd_dir.mkdir()
    (data_from_config / "MyEBirdData.csv").write_text("Date,Time\n", encoding="utf-8")
    (cwd_dir / "MyEBirdData.csv").write_text("wrong\n", encoding="utf-8")

    (config / "config.yaml").write_text(
        f"data_folder: {data_from_config.as_posix()}\n",
        encoding="utf-8",
    )

    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(cwd_dir))
    assert sources == ["config", "cwd"]
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(folder) == os.path.normpath(str(data_from_config))
    assert src == "config"
