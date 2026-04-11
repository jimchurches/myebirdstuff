"""
Non-tunable Streamlit UI literals: tab labels, species-search widget params, spinner copy/emoji strip,
export filenames, and footer links.

**Developer tweakables** (map pin size, cluster options, theme hex, basemap list, layout widths) live in
:mod:`explorer.app.streamlit.defaults`. **Persisted settings schema defaults** live in
:mod:`explorer.core.settings_schema_defaults`.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Data / export
# ---------------------------------------------------------------------------

DEFAULT_EBIRD_DATA_FILENAME = "MyEBirdData.csv"
MAP_EXPORT_HTML_FILENAME = "ebird_map.html"

# Checklist Statistics tab payload (not the same slider as Rankings Top N).
CHECKLIST_STATS_TOP_N_TABLE_LIMIT = 200

# ---------------------------------------------------------------------------
# Species search (``streamlit-searchbox`` fragment)
# ---------------------------------------------------------------------------

SPECIES_SEARCH_MAX_OPTIONS = 12
SPECIES_SEARCH_MIN_QUERY_LEN = 3
SPECIES_SEARCH_DEBOUNCE_MS = 500
SPECIES_SEARCH_PLACEHOLDER = "Type species name…"
# Map sidebar “Search tips” expander: paragraphs separated by blank lines; rendered with ``st.caption``.
SPECIES_SEARCH_CAPTION = """Start typing to search for a species.

You can use common names, scientific names, or bird groups (e.g. Australasian Robins).

Tip: "Show only selected species" defaults to on for performance; turn it off to see all locations with the selected species highlighted."""
# Sidebar expander title (Map → Species locations); body is SPECIES_SEARCH_CAPTION.
SPECIES_SEARCH_HELP_EXPANDER_LABEL = "Search tips"
SPECIES_SEARCH_EDIT_AFTER_SUBMIT = "option"
SPECIES_SEARCH_RERUN_SCOPE = "fragment"

# ---------------------------------------------------------------------------
# Main tab strip (``st.tabs`` order)
# ---------------------------------------------------------------------------

NOTEBOOK_MAIN_TAB_LABELS: tuple[str, ...] = (
    "Map",
    "Checklist Statistics",
    "Ranking & Lists",
    "Yearly Summary",
    "Country",
    "Maintenance",
    "Settings",
)

# ---------------------------------------------------------------------------
# Checklist-stats spinner + emoji strip (refs #74)
# ---------------------------------------------------------------------------

CHECKLIST_STATS_SPINNER_TEXT = "Doing interesting things with your eBird data"

CHECKLIST_STATS_SPINNER_EMOJIS: tuple[str, ...] = (
    "🐣",
    "🐥",
    "🐧",
    "🦆",
    "🦉",
    "🦢",
    "🦅",
    "🦃",
    "🐔",
    "🐓",
    "🐤",
    "🐦",
    "🕊️",
    "🪶",
    "🦩",
    "🦚",
    "🦜",
    "🐦‍⬛",
    "🪿",
    "🦤",
)

CHECKLIST_STATS_SPINNER_EMOJI_BATCH_SIZE = 5
CHECKLIST_STATS_SPINNER_EMOJI_BATCH_MS = 750

# ---------------------------------------------------------------------------
# Sidebar footer
# ---------------------------------------------------------------------------

# GitHub / eBird / Instagram / Explorer docs — outline pill + export button use the same (refs #127).
SIDEBAR_FOOTER_LINK_HEX = "#868e96"

GITHUB_REPO_URL = "https://github.com/jimchurches/myebirdstuff"
EBIRD_PROFILE_URL = "https://ebird.org/profile/MjkxNDYyNQ"


def explorer_readme_github_url() -> str:
    """``docs/explorer/README.md`` on GitHub for the current git branch (or ``main``).

    See :func:`explorer.core.repo_git.explorer_readme_github_page_url` and
    ``EXPLORER_README_GITHUB_BRANCH`` for overrides when ``.git`` is absent.
    """
    from explorer.core.repo_git import explorer_readme_github_page_url

    return explorer_readme_github_page_url(GITHUB_REPO_URL)
INSTAGRAM_PROFILE_URL = "https://www.instagram.com/jimchurches/"

# Optional “Support this project” (Buy Me a Coffee). Override or hide with env ``STREAMLIT_BUYMEACOFFEE_URL``
# (set to ``""`` in the environment to hide the block when the constant would otherwise show; refs #127).
BUY_ME_A_COFFEE_URL = "https://buymeacoffee.com/jimchurches"
