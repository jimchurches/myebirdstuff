"""CI helper: embedded build vs GitHub ``releases/latest`` (refs #189)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import scripts.verify_explorer_build_not_behind_github_latest as subject


class _FakeResp:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> None:
        return None


@pytest.fixture()
def version_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "explorer_build_version.txt"
    monkeypatch.setattr(subject, "_VERSION_FILE", p)
    return p


def test_main_passes_when_embedded_matches_latest(
    monkeypatch: pytest.MonkeyPatch, version_file
) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "2026-04-24")
    version_file.write_text("2026-04-24\n", encoding="utf-8")

    def _open(*_a, **_k):
        return _FakeResp({"tag_name": "2026-04-24-Beta"})

    monkeypatch.setattr("urllib.request.urlopen", _open)
    assert subject.main() == 0


def test_main_passes_same_day_suffix_when_release_today_matches_base(
    monkeypatch: pytest.MonkeyPatch, version_file
) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "2026-04-24")
    version_file.write_text("2026-04-24.2\n", encoding="utf-8")

    def _open(*_a, **_k):
        return _FakeResp({"tag_name": "2026-04-24-Beta"})

    monkeypatch.setattr("urllib.request.urlopen", _open)
    assert subject.main() == 0


def test_main_fails_when_embedded_behind_latest(
    monkeypatch: pytest.MonkeyPatch, version_file
) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "2026-04-22")
    version_file.write_text("2026-04-22\n", encoding="utf-8")

    def _open(*_a, **_k):
        return _FakeResp({"tag_name": "2026-04-24-Beta"})

    monkeypatch.setattr("urllib.request.urlopen", _open)
    assert subject.main() == 1


def test_main_fails_when_release_today_mismatch_before_github(
    monkeypatch: pytest.MonkeyPatch, version_file
) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "2026-04-26")
    version_file.write_text("2026-04-22\n", encoding="utf-8")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        MagicMock(side_effect=AssertionError("should not call GitHub when calendar gate fails")),
    )
    assert subject.main() == 1


def test_main_fails_on_invalid_release_today_env(
    monkeypatch: pytest.MonkeyPatch, version_file
) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "not-a-date")
    version_file.write_text("2026-04-24\n", encoding="utf-8")
    assert subject.main() == 1


def test_main_fails_on_missing_tag_name(monkeypatch: pytest.MonkeyPatch, version_file) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "2026-04-24")
    version_file.write_text("2026-04-24\n", encoding="utf-8")

    def _open(*_a, **_k):
        return _FakeResp({})

    monkeypatch.setattr("urllib.request.urlopen", _open)
    assert subject.main() == 1


def test_main_fails_on_http_error(monkeypatch: pytest.MonkeyPatch, version_file) -> None:
    monkeypatch.setenv("RELEASE_TODAY", "2026-04-24")
    version_file.write_text("2026-04-24\n", encoding="utf-8")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        MagicMock(side_effect=OSError("network down")),
    )
    assert subject.main() == 1


def test_main_passes_without_release_today_skips_calendar_gate(
    monkeypatch: pytest.MonkeyPatch, version_file
) -> None:
    monkeypatch.delenv("RELEASE_TODAY", raising=False)
    version_file.write_text("2026-04-24\n", encoding="utf-8")

    def _open(*_a, **_k):
        return _FakeResp({"tag_name": "2026-04-24-Beta"})

    monkeypatch.setattr("urllib.request.urlopen", _open)
    assert subject.main() == 0
