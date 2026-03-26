"""
Personal eBird Explorer — Streamlit entrypoint (compatibility shim, refs #70).

Run from repo root::

    pip install -r requirements.txt
    streamlit run streamlit_app/app.py

Implementation lives in :mod:`explorer.app.streamlit.app`.
"""

from __future__ import annotations

import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_APP_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from explorer.app.streamlit.app import main  # noqa: E402

if __name__ == "__main__":
    main()
