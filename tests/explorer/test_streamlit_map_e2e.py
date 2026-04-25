"""Minimal browser E2E smoke tests for Streamlit map defaults.

These tests are intentionally small and educational:
- launch the real Streamlit app in a subprocess,
- point it at a fixture CSV via temporary config/config.yaml,
- assert high-value map UI contracts in a real browser.

If Playwright is not installed locally, this module is skipped.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ENTRYPOINT = REPO_ROOT / "explorer" / "app" / "streamlit" / "app.py"
FIXTURE_CSV = REPO_ROOT / "tests" / "fixtures" / "ebird_integration_fixture.csv"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http_ready(url: str, timeout_s: float = 45.0) -> None:
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


def _wait_for_map_srcdoc(page, timeout_ms: int = 45000) -> str:
    """Return the map iframe ``srcdoc`` HTML once banner markup appears.

    Streamlit renders ``components.html`` content in an iframe with ``srcdoc``.
    Reading that attribute is more stable than traversing nested frames.
    """
    deadline = time.time() + (timeout_ms / 1000)
    last_iframe_debug: list[str] = []
    while time.time() < deadline:
        try:
            iframe_handles = page.locator("iframe").element_handles()
            if iframe_handles:
                debug_rows: list[str] = []
                for h in iframe_handles:
                    src = h.get_attribute("src") or ""
                    srcdoc = h.get_attribute("srcdoc") or ""
                    title = h.get_attribute("title") or ""
                    debug_rows.append(
                        "title="
                        f"{title[:40]!r} src={src[:80]!r} "
                        f"srcdoc_len={len(srcdoc)} has_banner={'pebird-map-banner' in srcdoc}"
                    )
                    if "pebird-map-banner" in srcdoc:
                        return srcdoc
                    try:
                        frame = h.content_frame()
                        if frame is not None:
                            html = frame.content()
                            if "pebird-map-banner" in html:
                                return html
                    except Exception:
                        # Frame may still be mounting; keep polling.
                        pass
                last_iframe_debug = debug_rows
        except Exception:
            pass
        page.wait_for_timeout(150)
    debug_text = " | ".join(last_iframe_debug) if last_iframe_debug else "no iframes detected"
    page_html = page.content()
    has_export_btn = "Export map HTML" in page_html
    raise AssertionError(
        "Map iframe with banner was not found in time "
        f"({debug_text}); export_button_visible={has_export_btn}"
    )


@contextlib.contextmanager
def _launch_chromium_or_skip():
    """Launch Chromium for E2E, or skip when browser binaries are unavailable."""
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:
            msg = str(exc)
            if "Executable doesn't exist" in msg:
                pytest.skip("Playwright browser binaries unavailable; run `python -m playwright install chromium`.")
            raise
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def streamlit_app_url(tmp_path: Path):
    """Run Streamlit against a temporary, config-backed dataset."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = data_dir / "MyEBirdData.csv"
    shutil.copyfile(FIXTURE_CSV, dataset_path)

    config_dir = REPO_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_yaml = config_dir / "config.yaml"
    config_secret_yaml = config_dir / "config_secret.yaml"
    original_cfg = config_yaml.read_text(encoding="utf-8") if config_yaml.exists() else None
    original_secret_cfg = (
        config_secret_yaml.read_text(encoding="utf-8")
        if config_secret_yaml.exists()
        else None
    )
    config_payload = f"data_folder: {data_dir.as_posix()}\n"
    # ``config_secret.yaml`` has higher precedence than ``config.yaml`` for data resolution.
    # Write both so local machine configs cannot interfere with deterministic E2E fixtures.
    config_yaml.write_text(config_payload, encoding="utf-8")
    config_secret_yaml.write_text(config_payload, encoding="utf-8")

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

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
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_http_ready(url)
        yield url
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()
            proc.wait(timeout=8)
        with contextlib.suppress(Exception):
            if proc.poll() is None:
                proc.kill()
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


def test_map_default_view_with_config_shows_all_locations_banner(streamlit_app_url: str):
    with _launch_chromium_or_skip() as browser:
        page = browser.new_page()
        page.goto(streamlit_app_url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        sidebar = page.locator('[data-testid="stSidebar"]')
        expect = playwright.expect
        expect(sidebar.get_by_text("Map view")).to_be_visible()
        expect(sidebar.get_by_text("All locations")).to_be_visible()

        srcdoc = _wait_for_map_srcdoc(page)
        assert "pebird-map-banner" in srcdoc
        assert "pebird-map-banner__title\">All locations</span>" in srcdoc


def test_all_locations_map_shows_legend_and_focused_default(streamlit_app_url: str):
    with _launch_chromium_or_skip() as browser:
        page = browser.new_page()
        page.goto(streamlit_app_url, wait_until="domcontentloaded")
        page.get_by_text("Personal eBird Explorer").wait_for(timeout=20000)

        sidebar = page.locator('[data-testid="stSidebar"]')
        expect = playwright.expect
        expect(sidebar.get_by_text("Map focus")).to_be_visible()
        expect(
            sidebar.get_by_text("Focused view shows your main birding regions.")
        ).to_be_visible()

        srcdoc = _wait_for_map_srcdoc(page)
        assert "pebird-map-legend" in srcdoc

