"""Explorer package root for the v3 structure.

- **Domain & data prep:** :mod:`explorer.core` — prefer ``from explorer.core.<module> import …``
  in new code. The package’s ``explorer.core`` *module* (``core/__init__.py``) also re-exports
  some presentation helpers for backward compatibility; see that module’s docstring.
- **HTML / map rendering:** :mod:`explorer.presentation`
- **Streamlit UI:** :mod:`explorer.app.streamlit`
"""

