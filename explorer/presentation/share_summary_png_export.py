"""
PNG export for share-summary cards (#275) — HTML layouts → Playwright screenshot.

Requires the ``playwright`` package and Chromium binaries
(``python -m playwright install chromium``).

On Streamlit Community Cloud, ``pip install`` alone does not download browsers.
This module installs Chromium into the user cache on first use when the
executable is missing (#345). System libraries still need ``packages.txt``.

Chromium is kept warm on a **dedicated worker thread** across exports (#344).
Playwright's sync API is greenlet-bound: close/screenshot must run on the
thread that started Playwright. A single worker owns that lifetime so
``atexit`` / :func:`shutdown_shared_chromium` can tear down safely from any
thread. Pages are closed after each screenshot.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import queue
import re
import struct
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact
from explorer.presentation.share_summary_layouts import render_share_summary_export_html
from explorer.presentation.share_summary_theme import (
    _FORMAT_PX,
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
)

if TYPE_CHECKING:
    from explorer.core.share_summary_compute import (
        ShareSummaryAllTimeStats,
        ShareSummaryGeoScope,
        ShareSummaryStats,
    )

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# One install attempt per process — avoids install loops if download fails.
_chromium_install_lock = threading.Lock()
_chromium_install_attempted = False

# Bounds the Chromium download so a stalled connection cannot hang the export
# thread forever (~170 MB download; generous for slow Cloud egress).
_CHROMIUM_INSTALL_TIMEOUT_SECONDS = 300


@dataclass
class _WarmChromiumSession:
    """Owns a long-lived ``sync_playwright`` context and Chromium browser."""

    playwright_cm: Any
    browser: Any

    def is_connected(self) -> bool:
        try:
            return bool(self.browser.is_connected())
        except Exception:
            return False

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.browser.close()
        with contextlib.suppress(Exception):
            self.playwright_cm.__exit__(None, None, None)


class _ChromiumWorker:
    """Single thread that owns Playwright sync greenlets and warm Chromium."""

    def __init__(self) -> None:
        self._jobs: queue.Queue[Any] = queue.Queue()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._atexit_registered = False

    def _ensure_running(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run,
                name="share-summary-chromium",
                daemon=True,
            )
            self._thread.start()
            if not self._atexit_registered:
                atexit.register(shutdown_shared_chromium)
                self._atexit_registered = True

    def run_with_browser(self, fn: Callable[[Any], _T]) -> _T:
        """Run ``fn(browser)`` on the worker thread; propagate errors."""
        self._ensure_running()
        done = threading.Event()
        outcome: dict[str, Any] = {}
        self._jobs.put(("call", fn, outcome, done))
        done.wait()
        if "error" in outcome:
            raise outcome["error"]
        return outcome["value"]

    def shutdown(self) -> None:
        """Close Chromium on the worker thread, then stop the worker."""
        with self._lock:
            thread = self._thread
            if thread is None or not thread.is_alive():
                self._thread = None
                return
        done = threading.Event()
        self._jobs.put(("shutdown", done))
        if not done.wait(timeout=30):
            _logger.warning("Chromium worker shutdown timed out")
        thread.join(timeout=5)
        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _run(self) -> None:
        session: _WarmChromiumSession | None = None
        try:
            # Jobs: ("shutdown", done) or ("call", fn, outcome, done).
            while True:
                job = self._jobs.get()
                if job[0] == "shutdown":
                    done_event: threading.Event = job[1]
                    if session is not None:
                        session.close()
                        session = None
                    done_event.set()
                    return

                _, fn, outcome, done_event = job
                try:
                    if session is None or not session.is_connected():
                        if session is not None:
                            session.close()
                            session = None
                        session = _start_warm_chromium_session()
                    outcome["value"] = fn(session.browser)
                except BaseException as exc:
                    outcome["error"] = exc
                    if session is not None and not session.is_connected():
                        with contextlib.suppress(Exception):
                            session.close()
                        session = None
                finally:
                    done_event.set()
        finally:
            if session is not None:
                session.close()


_chromium_worker = _ChromiumWorker()


def png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    """Read width and height from PNG bytes (IHDR chunk)."""
    if len(png_bytes) < 24 or png_bytes[:8] != _PNG_SIGNATURE:
        raise ValueError("Not a valid PNG image")
    width, height = struct.unpack(">II", png_bytes[16:24])
    return width, height


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    if not slug:
        return "birding-summary"
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug


def share_summary_png_filename(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId | None = None,
    fmt: FormatId | None = None,
) -> str:
    """Suggested download filename, e.g. ``2025-birding-summary.png``."""
    del layout, fmt  # reserved for future disambiguation in filename
    base = _slugify(stats.trip_title or stats.period_label)
    return f"{base}-birding-summary.png"


def _chromium_executable_missing(exc: BaseException) -> bool:
    """True when Playwright reports browsers were never installed."""
    return "Executable doesn't exist" in str(exc)


def _install_chromium() -> None:
    """Download Playwright Chromium into the user cache (no apt / no sudo)."""
    _logger.info("Installing Playwright Chromium for share-summary PNG export")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_CHROMIUM_INSTALL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Timed out installing Playwright Chromium for PNG export "
            f"(waited {_CHROMIUM_INSTALL_TIMEOUT_SECONDS}s). "
            "Check the network connection and try Export again."
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        # Prefer the last Error: line from Playwright's downloader over full logs.
        for line in reversed(detail.splitlines()):
            stripped = line.strip()
            if stripped.startswith("Error:"):
                detail = stripped
                break
        else:
            if len(detail) > 280:
                detail = detail[-280:]
        raise RuntimeError(
            "Failed to install Playwright Chromium for PNG export. "
            f"{detail or 'Unknown error.'}"
        )


def _ensure_chromium_installed() -> None:
    """Install Chromium once per process if launch reported it missing."""
    global _chromium_install_attempted
    with _chromium_install_lock:
        if _chromium_install_attempted:
            return
        _chromium_install_attempted = True
        _install_chromium()


def _chromium_missing_message() -> str:
    return (
        "Playwright Chromium is not available for PNG export. "
        "Locally run: python -m playwright install chromium. "
        "On Streamlit Cloud, confirm packages.txt is at the repo root "
        "and redeploy the app if PNG export was recently enabled."
    )


def _system_deps_missing(exc: BaseException) -> bool:
    """True when Chromium cannot start due to missing OS libraries."""
    return "Host system is missing dependencies" in str(exc)


def _raise_launch_failure(exc: BaseException) -> None:
    """Translate Playwright launch failures into user-facing RuntimeError."""
    if _system_deps_missing(exc):
        raise RuntimeError(
            "PNG export needs system libraries for Chromium. "
            "On Streamlit Cloud, ensure packages.txt is at the repo root "
            "and redeploy the app after updating system dependencies."
        ) from exc
    if _chromium_executable_missing(exc):
        raise RuntimeError(_chromium_missing_message()) from exc
    raise exc


def _launch_browser(playwright: Any) -> Any:
    """Launch Chromium, installing binaries once when the executable is missing."""
    try:
        return playwright.chromium.launch()
    except Exception as exc:
        if not _chromium_executable_missing(exc):
            _raise_launch_failure(exc)
        try:
            _ensure_chromium_installed()
            return playwright.chromium.launch()
        except RuntimeError:
            raise
        except Exception as retry_exc:
            _raise_launch_failure(retry_exc)


def _start_warm_chromium_session() -> _WarmChromiumSession:
    """Start Playwright and launch Chromium (must run on the worker thread)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && "
            "python -m playwright install chromium"
        ) from exc

    playwright_cm = sync_playwright()
    playwright = playwright_cm.__enter__()
    try:
        browser = _launch_browser(playwright)
    except Exception:
        with contextlib.suppress(Exception):
            playwright_cm.__exit__(*sys.exc_info())
        raise
    return _WarmChromiumSession(playwright_cm=playwright_cm, browser=browser)


def shutdown_shared_chromium() -> None:
    """Close the warm Chromium session on its owning worker thread."""
    _chromium_worker.shutdown()


def _run_with_shared_browser(fn: Callable[[Any], _T]) -> _T:
    """Execute ``fn(browser)`` on the Chromium worker (tests may patch this)."""
    return _chromium_worker.run_with_browser(fn)


@contextlib.contextmanager
def _launch_chromium():
    """Yield a warm Chromium via the dedicated worker (tests / thin wrappers).

    Playwright API calls must stay on the worker thread for real browsers.
    Prefer :func:`share_summary_to_png_bytes`, which screenshots on that thread.
    """

    def _identity(browser: Any) -> Any:
        return browser

    yield _run_with_shared_browser(_identity)


def share_summary_to_png_bytes(
    stats: ShareSummaryStats,
    *,
    layout: LayoutId = "tiles",
    fmt: FormatId = "square",
    spotlight_label: str | None = None,
    card_stat_labels: tuple[str, ...] = (),
    all_time: ShareSummaryAllTimeStats | None = None,
    color_scheme_index: int | None = None,
    scope_label: str | None = None,
    geo_scope: "ShareSummaryGeoScope | None" = None,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    insight_fact: ShareSummaryInsightFact | None = None,
) -> bytes:
    """Render a share card to PNG bytes at the layout's target pixel size."""
    width, height = _FORMAT_PX[fmt]
    labels = card_stat_labels if layout in ("tiles", "minimal") else ()
    html = render_share_summary_export_html(
        stats,
        layout=layout,
        fmt=fmt,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
        spotlight_label=spotlight_label,
        insight_fact=insight_fact,
        card_stat_labels=labels,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        geo_scope=geo_scope,
        scope_label=scope_label,
    )

    def _screenshot(browser: Any) -> bytes:
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        try:
            page.set_content(html, wait_until="load")
            return page.screenshot(
                type="png",
                clip={"x": 0, "y": 0, "width": width, "height": height},
            )
        finally:
            page.close()

    return _run_with_shared_browser(_screenshot)


__all__ = [
    "png_dimensions",
    "share_summary_png_filename",
    "share_summary_to_png_bytes",
    "shutdown_shared_chromium",
]
