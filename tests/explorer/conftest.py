"""Fixtures shared by Streamlit Playwright E2E modules under ``tests/explorer/``."""

from __future__ import annotations

import pytest

from tests.explorer.e2e_support import (
    INTEGRATION_FIXTURE_CSV,
    REPO_ROOT,
    free_tcp_port,
    streamlit_http_server,
    temporary_ebird_csv_config,
    wait_for_http_ready,
)


@pytest.fixture
def streamlit_app_url(tmp_path):
    """Run Streamlit against a temporary, config-backed integration fixture CSV."""
    port = free_tcp_port()
    url = f"http://127.0.0.1:{port}"
    with temporary_ebird_csv_config(REPO_ROOT, tmp_path, INTEGRATION_FIXTURE_CSV):
        with streamlit_http_server(cwd=REPO_ROOT, port=port, env_extra={}, capture_stdio=False) as (_proc, _logs):
            wait_for_http_ready(url)
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
    with temporary_ebird_csv_config(REPO_ROOT, tmp_path, INTEGRATION_FIXTURE_CSV):
        with streamlit_http_server(cwd=REPO_ROOT, port=port, env_extra=env_extra, capture_stdio=False) as (_proc, _logs):
            wait_for_http_ready(url)
            yield url, log_file
