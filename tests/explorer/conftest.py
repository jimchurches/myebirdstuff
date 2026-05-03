"""Fixtures shared by Streamlit Playwright E2E modules under ``tests/explorer/``."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from tests.explorer.e2e_support import (
    REPO_ROOT,
    e2e_http_ready_timeout_s,
    free_tcp_port,
    resolve_e2e_dataset_csv_source,
    streamlit_http_server,
    temporary_ebird_csv_config,
    wait_for_http_ready,
)

# After perf E2E tests, copy JSONL here if set (same machine; keeps data outside pytest tmp).
EXPLORER_E2E_PERF_JSONL_ARCHIVE_ENV = "EXPLORER_E2E_PERF_JSONL_ARCHIVE"


def _archive_perf_jsonl_if_requested(log_file: Path) -> None:
    dest = str(os.environ.get(EXPLORER_E2E_PERF_JSONL_ARCHIVE_ENV, "")).strip()
    if not dest or not log_file.is_file():
        return
    out = Path(dest).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(log_file, out)


@pytest.fixture
def streamlit_app_url(tmp_path):
    """Run Streamlit against temp config; CSV from integration fixture unless ``EXPLORER_E2E_DATASET_CSV``."""
    port = free_tcp_port()
    url = f"http://127.0.0.1:{port}"
    csv_src = resolve_e2e_dataset_csv_source()
    with temporary_ebird_csv_config(REPO_ROOT, tmp_path, csv_src):
        with streamlit_http_server(cwd=REPO_ROOT, port=port, env_extra={}, capture_stdio=False) as (_proc, _logs):
            wait_for_http_ready(url, timeout_s=e2e_http_ready_timeout_s())
            yield url


@pytest.fixture
def streamlit_perf_url_and_logfile(tmp_path):
    """Like ``streamlit_app_url`` but enables perf events + JSONL appended to *tmp_path* (``EXPLORER_PERF_LOG_FILE``)."""
    port = free_tcp_port()
    url = f"http://127.0.0.1:{port}"
    log_file = tmp_path / "explorer_perf.jsonl"
    env_extra = {
        "EXPLORER_PERF": "1",
        "EXPLORER_PERF_LOG_FILE": str(log_file),
    }
    csv_src = resolve_e2e_dataset_csv_source()
    with temporary_ebird_csv_config(REPO_ROOT, tmp_path, csv_src):
        with streamlit_http_server(cwd=REPO_ROOT, port=port, env_extra=env_extra, capture_stdio=False) as (_proc, _logs):
            wait_for_http_ready(url, timeout_s=e2e_http_ready_timeout_s())
            try:
                yield url, log_file
            finally:
                _archive_perf_jsonl_if_requested(log_file)
