"""Tests for shared notebook/Streamlit path resolution."""

from __future__ import annotations

import os
import textwrap

import pytest


def test_build_explorer_candidate_dirs_order_and_anchor_label(tmp_path):
    from personal_ebird_explorer.explorer_paths import build_explorer_candidate_dirs

    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    anchor = repo / "notebooks"
    anchor.mkdir()

    folders, sources = build_explorer_candidate_dirs(
        repo_root=str(repo),
        anchor_dir=str(anchor),
        data_folder_hardcoded=str(tmp_path / "hard"),
        anchor_label="notebook folder",
    )
    assert folders[0] == os.path.normpath(str(tmp_path / "hard"))
    assert sources[0] == "hardcoded"
    assert folders[-1] == os.path.normpath(str(anchor))
    assert sources[-1] == "notebook folder"


def test_resolve_ebird_data_file_finds_first_match(tmp_path):
    from personal_ebird_explorer.explorer_paths import (
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    anchor = repo / "app"
    anchor.mkdir()
    csv_path = anchor / "MyEBirdData.csv"
    csv_path.write_text("Date,Time\n", encoding="utf-8")

    folders, sources = build_explorer_candidate_dirs(
        repo_root=str(repo),
        anchor_dir=str(anchor),
        anchor_label="streamlit app folder",
    )
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(path) == os.path.normpath(str(csv_path))
    assert src == "streamlit app folder"


def test_resolve_ebird_data_file_prefers_hardcoded_over_anchor(tmp_path):
    from personal_ebird_explorer.explorer_paths import (
        build_explorer_candidate_dirs,
        resolve_ebird_data_file,
    )

    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    hard = tmp_path / "data"
    hard.mkdir()
    anchor = repo / "app"
    anchor.mkdir()
    (hard / "MyEBirdData.csv").write_text("Date,Time\n", encoding="utf-8")
    (anchor / "MyEBirdData.csv").write_text("wrong\n", encoding="utf-8")

    folders, sources = build_explorer_candidate_dirs(
        repo_root=str(repo),
        anchor_dir=str(anchor),
        data_folder_hardcoded=str(hard),
        anchor_label="streamlit app folder",
    )
    path, folder, src = resolve_ebird_data_file("MyEBirdData.csv", folders, sources)
    assert os.path.normpath(folder) == os.path.normpath(str(hard))
    assert src == "hardcoded"


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
    p2 = settings_yaml_path_for_source(str(repo), "config_template")
    p3 = settings_yaml_path_for_source(str(repo), "hardcoded")

    assert p1 and p1.endswith("scripts/config_secret.py")
    assert p2 and p2.endswith("scripts/config_template.py")
    assert p3 is None
