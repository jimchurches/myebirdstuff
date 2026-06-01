"""Shared helpers for Streamlit + Playwright E2E tests (real subprocess, deterministic config).

Map embedding uses the Leaflet custom component (nested iframes), not legacy ``components.html``
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

# Optional: absolute path to ``MyEBirdData.csv`` — copied into pytest ``tmp_path`` (default: integration fixture).
EXPLORER_E2E_DATASET_CSV_ENV = "EXPLORER_E2E_DATASET_CSV"
EXPLORER_E2E_HTTP_TIMEOUT_ENV = "EXPLORER_E2E_HTTP_TIMEOUT_S"
EXPLORER_E2E_MAP_TIMEOUT_MS_ENV = "EXPLORER_E2E_MAP_TIMEOUT_MS"


def resolve_e2e_dataset_csv_source() -> Path:
    """Return integration fixture path, or a real export when ``EXPLORER_E2E_DATASET_CSV`` is set."""
    import os

    raw = str(os.environ.get(EXPLORER_E2E_DATASET_CSV_ENV, "")).strip()
    if not raw:
        return INTEGRATION_FIXTURE_CSV
    p = Path(raw).expanduser().resolve()
    if not p.is_file():
        pytest.fail(f"{EXPLORER_E2E_DATASET_CSV_ENV} must point to an existing file (got {p})")
    return p


def e2e_http_ready_timeout_s() -> float:
    """Streamlit HTTP readiness: longer when ``EXPLORER_E2E_DATASET_CSV`` points at a large export."""
    import os

    raw = str(os.environ.get(EXPLORER_E2E_HTTP_TIMEOUT_ENV, "")).strip()
    if raw:
        return max(15.0, float(raw))
    if str(os.environ.get(EXPLORER_E2E_DATASET_CSV_ENV, "")).strip():
        return 120.0
    return 45.0


def e2e_map_markup_timeout_ms() -> int:
    """Wait for Leaflet component iframe banner (``pebird-map-banner``) in frames; large exports may need >45s."""
    import os

    raw = str(os.environ.get(EXPLORER_E2E_MAP_TIMEOUT_MS_ENV, "")).strip()
    if raw:
        return max(5_000, int(float(raw)))
    if str(os.environ.get(EXPLORER_E2E_DATASET_CSV_ENV, "")).strip():
        return 180_000
    return 45_000


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
    timeout_ms: int | None = None,
) -> str:
    """Return frame HTML that contains ``pebird-map-banner`` and all *must_contain* substrings."""
    import time

    if timeout_ms is None:
        timeout_ms = e2e_map_markup_timeout_ms()
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


def measure_first_paint_ms(
    page: Any,
    url: str,
    *,
    must_contain: Sequence[str] | None = None,
    timeout_ms: int | None = None,
) -> dict[str, float]:
    """Time ``page.goto`` → first appearance of ``pebird-map-banner`` in any frame.

    Returns ``{"goto_ms", "banner_ms"}``. ``goto_ms`` is navigation-complete wall time
    (``page.goto(... wait_until="domcontentloaded")`` return); ``banner_ms`` is the
    user-experienced first-paint, end-to-end (subprocess pipeline: data load → prep →
    map build → Streamlit render → iframe DOM paint).

    *must_contain* (optional) lets callers refine "banner observed" to a specific
    banner (e.g. ``All locations`` vs ``Lifer locations``); default just waits for
    *any* ``pebird-map-banner``.
    """
    import time

    t0 = time.monotonic()
    page.goto(url, wait_until="domcontentloaded")
    t_goto = time.monotonic()
    wait_for_pebird_map_markup(
        page,
        must_contain=list(must_contain or []),
        timeout_ms=timeout_ms,
    )
    t_banner = time.monotonic()
    return {
        "goto_ms": round((t_goto - t0) * 1000.0, 1),
        "banner_ms": round((t_banner - t0) * 1000.0, 1),
    }


def append_e2e_first_paint_record(log_file: Path, payload: dict[str, Any]) -> None:
    """Append one ``stage="e2e.first_paint"`` JSONL record to *log_file*.

    Uses the same JSONL shape as ``EXPLORER_PERF_LOG_FILE`` events so the aggregator
    (:mod:`scripts.aggregate_perf_jsonl`) can join app-side perf events with E2E-side
    first-paint timings. Run-side identifier (``main_run_id``) is unknown from the
    Playwright process, so callers should embed dataset / mode labels in *payload*.
    Synthetic event uses ``run_kind="e2e"`` and ``fragment=None``.
    """
    import json
    from datetime import datetime, timezone

    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": "e2e.first_paint",
        "run_kind": "e2e",
        "fragment": None,
    }
    rec.update(payload)
    with open(log_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, default=str) + "\n")


def choose_map_view_mode(page: Any, label: str) -> None:
    """Pick a sidebar **Map view** option (*All locations*, *Lifer locations*, …)."""
    sidebar_map_view_select(page).click()
    page.get_by_role("option", name=label).click()


def map_banner_must_contain(title_fragment: str) -> list[str]:
    """Substrings for :func:`wait_for_pebird_map_markup` (title may be plain or an eBird link)."""
    return ["pebird-map-banner__title", title_fragment]


# Integration fixture species (Whoosh + map banner title use common name).
E2E_FIXTURE_SPECIES_COMMON = "Grey Teal"


def choose_species_by_common_name(page: Any, common_name: str) -> None:
    """Select a species in **Species locations** via the sidebar searchbox."""
    from explorer.app.streamlit.streamlit_ui_constants import SPECIES_SEARCH_PLACEHOLDER

    choose_map_view_mode(page, "Species locations")
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text("Show only selected species", exact=True).wait_for(timeout=20_000)
    with contextlib.suppress(Exception):
        page.locator('[data-testid="stSpinner"]').wait_for(state="detached", timeout=180_000)
    page.locator('iframe[title="streamlit_searchbox.searchbox"]').wait_for(
        state="attached", timeout=30_000
    )
    # streamlit-searchbox renders inside its own iframe (not the main sidebar DOM).
    searchbox_frame = page.frame_locator('iframe[title="streamlit_searchbox.searchbox"]')
    search = searchbox_frame.get_by_placeholder(SPECIES_SEARCH_PLACEHOLDER)
    if search.count() == 0:
        search = searchbox_frame.get_by_role("combobox")
    search.wait_for(state="visible", timeout=20_000)
    search.click()
    search.fill(common_name)
    # Match app debounce (SPECIES_SEARCH_DEBOUNCE_MS) before expecting suggestions.
    page.wait_for_timeout(800)
    picked = False
    for candidate in (
        searchbox_frame.get_by_text(common_name, exact=True),
        searchbox_frame.locator('[role="option"]', has_text=common_name),
        searchbox_frame.locator('[role="option"]:visible', has_text=common_name),
    ):
        if candidate.count() > 0:
            candidate.first.click(timeout=10_000)
            picked = True
            break
    if not picked:
        search.press("ArrowDown")
        page.wait_for_timeout(250)
        search.press("Enter")
    page.wait_for_timeout(500)
    search.press("Enter")
    # Fragment rerun + map prep on large exports can take tens of seconds.
    with contextlib.suppress(Exception):
        page.locator('[data-testid="stSpinner"]').wait_for(state="detached", timeout=120_000)
    wait_for_pebird_map_markup(
        page,
        must_contain=map_banner_must_contain(common_name),
        timeout_ms=e2e_map_markup_timeout_ms(),
    )


def choose_family_by_label(page: Any, family_label: str) -> None:
    """Pick *family_label* in **Family locations** (sidebar Family selectbox)."""
    choose_map_view_mode(page, "Family locations")
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text("Family", exact=True).wait_for(timeout=20_000)
    family_select = sidebar.locator('[data-testid="stSelectbox"]').nth(1)
    family_select.click()
    page.get_by_role("option", name=family_label).click()


def choose_first_recorded_family(page: Any) -> str:
    """Select the first non-empty **Family** in **Family locations**; return its label."""
    choose_map_view_mode(page, "Family locations")
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text("Family", exact=True).wait_for(timeout=20_000)
    # Map view is the first sidebar selectbox; Family picker is the second in this mode.
    family_select = sidebar.locator('[data-testid="stSelectbox"]').nth(1)
    family_select.click()
    options = page.get_by_role("option")
    count = options.count()
    for i in range(count):
        label = (options.nth(i).inner_text() or "").strip()
        if label and not label.startswith("—"):
            options.nth(i).click()
            return label
    raise AssertionError("No family options in sidebar (taxonomy may not have loaded)")


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
def temporary_ebird_csv_config(tmp_path: Path, csv_source: Path) -> Iterator[dict[str, str]]:
    """Point the Streamlit app at *csv_source* via an isolated temp config directory.

    Writes ``config.yaml`` under ``tmp_path/config/`` only. Returns env overrides
    (``EXPLORER_CONFIG_DIR``) for the Streamlit subprocess — the repo ``config/`` tree
    (including ``config_secret.yaml``) is never read or written.
    """
    import shutil

    from explorer.core.explorer_paths import EXPLORER_CONFIG_DIR_ENV

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = data_dir / "MyEBirdData.csv"
    shutil.copyfile(csv_source, dataset_path)

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_yaml = config_dir / "config.yaml"
    config_payload = f"data_folder: {data_dir.as_posix()}\n"
    config_yaml.write_text(config_payload, encoding="utf-8")

    yield {EXPLORER_CONFIG_DIR_ENV: str(config_dir)}

