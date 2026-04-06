"""Tests for :mod:`explorer.core.repo_git`."""

from pathlib import Path

import pytest


def test_github_blob_ref_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from explorer.core.repo_git import github_blob_ref_for_readme

    monkeypatch.setenv("EXPLORER_README_GITHUB_BRANCH", "release/test")
    assert github_blob_ref_for_readme() == "release/test"


def test_github_blob_ref_main_when_no_git_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from explorer.core import repo_git
    from explorer.core.repo_git import github_blob_ref_for_readme

    monkeypatch.delenv("EXPLORER_README_GITHUB_BRANCH", raising=False)
    monkeypatch.setattr(repo_git, "_repo_root", lambda: tmp_path)
    assert github_blob_ref_for_readme() == "main"


def test_explorer_readme_url_encodes_branch_with_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    from explorer.core import repo_git
    from explorer.core.repo_git import explorer_readme_github_page_url

    monkeypatch.setattr(repo_git, "github_blob_ref_for_readme", lambda: "feature/my-branch")
    url = explorer_readme_github_page_url("https://github.com/org/repo")
    assert url == "https://github.com/org/repo/blob/feature%2Fmy-branch/docs/explorer/README.md"
