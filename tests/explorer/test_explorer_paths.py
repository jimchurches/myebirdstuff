"""Tests for explorer CSV path resolution (Streamlit-aligned)."""

from __future__ import annotations

import os
import textwrap

import pytest


def test_build_explorer_candidate_dirs_config_then_cwd(tmp_path):
    from personal_ebird_explorer.explorer_paths import build_explorer_candidate_dirs

    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
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
    (repo / "scripts").mkdir(parents=True)
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
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    data_secret = tmp_path / "secret_data"
    data_secret.mkdir()
    cwd_dir = tmp_path / "cwd_here"
    cwd_dir.mkdir()
    (data_secret / "MyEBirdData.csv").write_text("Date,Time\n", encoding="utf-8")
    (cwd_dir / "MyEBirdData.csv").write_text("wrong\n", encoding="utf-8")

    (scripts / "config_secret.py").write_text(
        textwrap.dedent(
            f'''
            DATA_FOLDER = r"{data_secret}"
            '''
        ).strip(),
        encoding="utf-8",
    )

    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(cwd_dir))
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(folder) == os.path.normpath(str(data_secret))
    assert src == "config_secret"


def test_data_folder_from_config_file_reads_data_folder(tmp_path):
    from personal_ebird_explorer.explorer_paths import data_folder_from_config_file

    cfg = tmp_path / "config_secret.py"
    target = tmp_path / "ebird_data"
    target.mkdir()
    cfg.write_text(
        textwrap.dedent(
            f'''
            DATA_FOLDER = r"{target}"
            '''
        ).strip(),
        encoding="utf-8",
    )
    assert data_folder_from_config_file(str(cfg)) == os.path.normpath(str(target))


def test_resolve_raises_file_not_found():
    from personal_ebird_explorer.explorer_paths import resolve_ebird_data_file

    with pytest.raises(FileNotFoundError) as exc:
        resolve_ebird_data_file("nope.csv", ["/nonexistent"], ["x"])
    assert "nope.csv" in str(exc.value)


def test_settings_yaml_path_for_source(tmp_path):
    from personal_ebird_explorer.explorer_paths import settings_yaml_path_for_source

    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)

    p1 = settings_yaml_path_for_source(str(repo), "config_secret")
    p2 = settings_yaml_path_for_source(str(repo), "config")
    p3 = settings_yaml_path_for_source(str(repo), "cwd")

    assert p1 and p1.endswith("scripts/config_secret.py")
    assert p2 and p2.endswith("scripts/config.py")
    assert p3 is None


def test_config_py_wins_over_cwd_when_both_have_csv(tmp_path):
    from personal_ebird_explorer.explorer_paths import (
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    data_from_config = tmp_path / "from_config"
    data_from_config.mkdir()
    cwd_dir = tmp_path / "cwd_here"
    cwd_dir.mkdir()
    (data_from_config / "MyEBirdData.csv").write_text("Date,Time\n", encoding="utf-8")
    (cwd_dir / "MyEBirdData.csv").write_text("wrong\n", encoding="utf-8")

    (scripts / "config.py").write_text(
        textwrap.dedent(
            f'''
            DATA_FOLDER = r"{data_from_config}"
            '''
        ).strip(),
        encoding="utf-8",
    )

    folders, sources = build_explorer_candidate_dirs(repo_root=str(repo), cwd=str(cwd_dir))
    assert sources == ["config", "cwd"]
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(folder) == os.path.normpath(str(data_from_config))
    assert src == "config"
