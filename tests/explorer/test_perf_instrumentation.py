"""Tests for optional Explorer performance instrumentation (refs #179)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from explorer.app.streamlit.app_constants import (
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAIN_SCRIPT_RUN_ID_KEY,
    EXPLORER_PERF_EVENTS_KEY,
)


@pytest.fixture
def mock_st(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    m = MagicMock()
    m.session_state = {}
    m.secrets = {}
    monkeypatch.setattr("explorer.app.streamlit.perf_instrumentation.st", m)
    return m


def test_explorer_perf_enabled_false_by_default(mock_st: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPLORER_PERF", raising=False)
    from explorer.app.streamlit import perf_instrumentation as p

    assert p.explorer_perf_enabled() is False


def test_explorer_perf_enabled_true_from_env(mock_st: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_PERF", "1")
    from explorer.app.streamlit import perf_instrumentation as p

    assert p.explorer_perf_enabled() is True


def test_perf_span_records_when_enabled(mock_st: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_PERF", "1")
    from explorer.app.streamlit import perf_instrumentation as p

    mock_st.session_state[EXPLORER_MAIN_SCRIPT_RUN_ID_KEY] = 2
    mock_st.session_state[EBIRD_DATA_SIG_KEY] = "sigtest"

    with p.perf_span("unit.test_stage", extra={"k": "v"}):
        pass

    events = mock_st.session_state[EXPLORER_PERF_EVENTS_KEY]
    assert len(events) == 1
    row = events[0]
    assert row["stage"] == "unit.test_stage"
    assert row["run_kind"] == "full_run"
    assert row["fragment"] is None
    assert row["main_run_id"] == 2
    assert row["session_warmth"] == "warm"
    assert row["extra"] == {"k": "v"}
    assert row["elapsed_ms"] >= 0.0


def test_perf_log_file_appends_jsonl(
    mock_st: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    log_path = tmp_path / "out.jsonl"
    monkeypatch.setenv("EXPLORER_PERF", "1")
    monkeypatch.setenv("EXPLORER_PERF_LOG_FILE", str(log_path))

    mock_st.session_state[EXPLORER_MAIN_SCRIPT_RUN_ID_KEY] = 1
    mock_st.session_state[EBIRD_DATA_SIG_KEY] = "sig-file"

    from explorer.app.streamlit import perf_instrumentation as p

    with p.perf_span("unit.file_probe"):
        pass

    text = log_path.read_text(encoding="utf-8").strip()
    assert text
    record = json.loads(text.splitlines()[0])
    assert record["stage"] == "unit.file_probe"
    assert record["dataset_sig"] == "sig-file"


def test_perf_fragment_records(mock_st: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_PERF", "1")
    from explorer.app.streamlit import perf_instrumentation as p

    mock_st.session_state[EXPLORER_MAIN_SCRIPT_RUN_ID_KEY] = 1

    with p.perf_fragment("country"):
        pass

    events = mock_st.session_state[EXPLORER_PERF_EVENTS_KEY]
    assert len(events) == 1
    assert events[0]["run_kind"] == "fragment"
    assert events[0]["fragment"] == "country"
    assert events[0]["stage"] == "fragment.country"


def test_perf_dataset_context_dict_minimal() -> None:
    import pandas as pd

    from explorer.app.streamlit.perf_instrumentation import perf_dataset_context_dict

    df = pd.DataFrame(
        {
            "Common Name": ["A", "A", "B"],
            "Location ID": [1, 1, 2],
            "Submission ID": [10, 11, 12],
        }
    )
    ctx = perf_dataset_context_dict(df)
    assert ctx["rows"] == 3
    assert ctx["cols"] == 3
    assert ctx["unique_species"] == 2
    assert ctx["unique_locations"] == 2
    assert ctx["unique_checklists"] == 3
