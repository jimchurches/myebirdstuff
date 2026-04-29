"""Shared helpers for Streamlit + Playwright E2E tests (real subprocess, deterministic config).

Map embedding uses ``streamlit_folium.st_folium`` (nested iframes), not legacy ``components.html``
``srcdoc`` — banner detection scans all ``page.frames``.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import threading
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import IO, Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ENTRYPOINT = REPO_ROOT / "explorer" / "app" / "streamlit" / "app.py"
INTEGRATION_FIXTURE_CSV = REPO_ROOT / "tests" / "fixtures" / "ebird_integration_fixture.csv"


def free_tcp_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_http_ready(url: str, timeout_s: float = 45.0) -> None:
    import time
    from urllib.error import URLError
    from urllib.request import urlopen

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:  # nosec B310 - local ephemeral test server
                if 200 <= int(resp.status) < 500:
                    return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.25)
    raise TimeoutError(f"Streamlit app did not become ready: {url}")


def wait_for_pebird_map_markup(
    page: Any,
    *,
    must_contain: Sequence[str],
    timeout_ms: int = 45000,
) -> str:
    """Return frame HTML that contains ``pebird-map-banner`` and all *must_contain* substrings."""
    import time

    deadline = time.time() + timeout_ms / 1000.0
    last_hint = ""
    while time.time() < deadline:
        for frame in list(page.frames):
            try:
                html = frame.content()
            except Exception as exc:
                last_hint = str(exc)[:200]
                continue
            if "pebird-map-banner" not in html:
                continue
            if all(s in html for s in must_contain):
                return html
            last_hint = "banner without required substrings"
        page.wait_for_timeout(150)
    raise AssertionError(
        f"Map banner / content not found in time (last_hint={last_hint!r}); need {must_contain!r}"
    )


def sidebar_map_view_select(page: Any) -> Any:
    """Return the sidebar **Map view** Streamlit ``stSelectbox`` locator (always first selectbox)."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    return sidebar.locator('[data-testid="stSelectbox"]').first


def choose_map_view_mode(page: Any, label: str) -> None:
    """Pick a sidebar **Map view** option (*All locations*, *Lifer locations*, …)."""
    sidebar_map_view_select(page).click()
    page.get_by_role("option", name=label).click()


@contextlib.contextmanager
def launch_chromium_or_skip():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright Python package missing; pip install playwright")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:
            msg = str(exc)
            if "Executable doesn't exist" in msg:
                pytest.skip(
                    "Playwright browser binaries unavailable; run `python -m playwright install chromium`."
                )
            raise
        try:
            yield browser
        finally:
            browser.close()


def stream_readlines_thread(pipe: IO[str], bucket: list[str]) -> threading.Thread:
    def _run() -> None:
        for line in iter(pipe.readline, ""):
            bucket.append(line)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


@contextlib.contextmanager
def streamlit_http_server(
    *,
    cwd: Path,
    port: int,
    env_extra: dict[str, str | None],
    capture_stdio: bool = False,
):
    """Start ``streamlit run`` ; merge stderr into stdout when *capture_stdio*."""
    import os
    import sys

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    for k, v in env_extra.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    stdout_arg: int | Any = subprocess.DEVNULL
    stderr_arg: int | Any = subprocess.DEVNULL
    log_bucket: list[str] = []
    reader_thread: threading.Thread | None = None
    if capture_stdio:
        stdout_arg = subprocess.PIPE
        stderr_arg = subprocess.STDOUT

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_ENTRYPOINT),
            "--server.headless=true",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
        ],
        cwd=str(cwd),
        env={k: v for k, v in env.items() if v is not None},
        stdout=stdout_arg,
        stderr=stderr_arg,
        text=True,
    )
    try:
        if capture_stdio and proc.stdout is not None:
            reader_thread = stream_readlines_thread(proc.stdout, log_bucket)
        yield proc, log_bucket
    finally:
        if reader_thread is not None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
            reader_thread.join(timeout=3)
        else:
            with contextlib.suppress(Exception):
                proc.terminate()
                proc.wait(timeout=8)
            with contextlib.suppress(Exception):
                if proc.poll() is None:
                    proc.kill()


def parse_perf_json_objects_from_log_lines(lines: Iterable[str]) -> list[dict[str, Any]]:
    """Extract perf records when ``EXPLORER_PERF_LOG=1`` prepends log formatting to JSON."""
    dec = json.JSONDecoder()
    out: list[dict[str, Any]] = []
    for raw in lines:
        line = raw if raw.endswith("\n") else raw + "\n"
        idx = 0
        while idx < len(line):
            brace = line.find("{", idx)
            if brace < 0:
                break
            try:
                obj, end = dec.raw_decode(line, brace)
            except json.JSONDecodeError:
                idx = brace + 1
                continue
            if isinstance(obj, dict) and "stage" in obj and "elapsed_ms" in obj:
                out.append(obj)
            idx = end
    return out


def max_elapsed_ms_by_stage(events: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Maximum ``elapsed_ms`` per ``stage`` (ignores synthetic zero-duration point events unless max stays 0)."""
    highs: defaultdict[str, float] = defaultdict(float)
    for ev in events:
        stage = ev.get("stage")
        if not isinstance(stage, str):
            continue
        try:
            ms = float(ev.get("elapsed_ms", 0.0))
        except (TypeError, ValueError):
            continue
        kind = ev.get("run_kind")
        if ms <= 0.0 and kind == "point":
            continue
        if ms > highs[stage]:
            highs[stage] = ms
    return dict(highs)


@contextlib.contextmanager
def temporary_ebird_csv_config(repo_root: Path, tmp_path: Path, csv_source: Path) -> Iterator[None]:
    """Point ``config/config.yaml`` + ``config_secret.yaml`` at *tmp_path* with *csv_source* copied as CSV."""
    import shutil

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = data_dir / "MyEBirdData.csv"
    shutil.copyfile(csv_source, dataset_path)

    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_yaml = config_dir / "config.yaml"
    config_secret_yaml = config_dir / "config_secret.yaml"
    original_cfg = config_yaml.read_text(encoding="utf-8") if config_yaml.exists() else None
    original_secret_cfg = (
        config_secret_yaml.read_text(encoding="utf-8") if config_secret_yaml.exists() else None
    )
    config_payload = f"data_folder: {data_dir.as_posix()}\n"
    config_yaml.write_text(config_payload, encoding="utf-8")
    config_secret_yaml.write_text(config_payload, encoding="utf-8")

    def _restore() -> None:
        if original_cfg is None:
            with contextlib.suppress(FileNotFoundError):
                config_yaml.unlink()
        else:
            config_yaml.write_text(original_cfg, encoding="utf-8")
        if original_secret_cfg is None:
            with contextlib.suppress(FileNotFoundError):
                config_secret_yaml.unlink()
        else:
            config_secret_yaml.write_text(original_secret_cfg, encoding="utf-8")

    try:
        yield
    finally:
        _restore()

