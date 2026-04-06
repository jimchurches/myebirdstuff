#!/usr/bin/env python3
"""Emit GitHub Actions workflow warnings for enabled Streamlit debug toggles in defaults.py.

Always exits 0 (informational only). Run from repo root in CI after tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from explorer.app.streamlit.defaults import debug_defaults_enabled


def main() -> None:
    for name in debug_defaults_enabled():
        msg = (
            f"explorer/app/streamlit/defaults.py — {name}=True "
            "(debug; set False for production)"
        )
        print(f"::warning::{msg}", file=sys.stderr)


if __name__ == "__main__":
    main()
