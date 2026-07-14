"""
Default colour schemes and stat selections for share-summary cards (#157).

Framework-neutral: no Streamlit imports. Presentation and PNG export read from here;
``explorer.app.streamlit.defaults`` re-exports these for developer tuning.
"""

from __future__ import annotations

# Index into :data:`SHARE_SUMMARY_COLOR_SCHEMES` used by card HTML previews / PNG export.
SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT = 0

# Each scheme: ``bg``, ``bg_alt``, ``text``, ``muted``, ``border``, ``accent``.
# Optional ``tile_bg``, ``tile_bg_alt``, ``tile_border`` lift Statistics Grid / circle tiles
# above the card surface (dark theme uses medium lift — #308).
# Add entries here to trial themes; flip ``SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT`` to test.
SHARE_SUMMARY_COLOR_SCHEMES: tuple[dict[str, str], ...] = (
    {
        "id": "light",
        "name": "Light",
        "bg": "#ffffff",
        "bg_alt": "#f9fafb",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#e5e7eb",
        "accent": "#2d6a4f",
    },
    {
        "id": "dark",
        "name": "Dark",
        "bg": "#0d120f",
        "bg_alt": "#161f19",
        "text": "#f0f3f1",
        "muted": "#8fa79a",
        "border": "#263329",
        "accent": "#74c69d",
        "tile_bg_alt": "#1e2a24",
        "tile_bg": "#243229",
    },
)


def share_summary_color_scheme_index(scheme_id: str) -> int:
    """Resolve a scheme id (e.g. ``light``) to its index in :data:`SHARE_SUMMARY_COLOR_SCHEMES`."""
    for i, scheme in enumerate(SHARE_SUMMARY_COLOR_SCHEMES):
        if scheme["id"] == scheme_id:
            return i
    return SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT


def share_summary_color_scheme_label(scheme_id: str) -> str:
    """Human label for a scheme id."""
    for scheme in SHARE_SUMMARY_COLOR_SCHEMES:
        if scheme["id"] == scheme_id:
            return scheme.get("name") or scheme_id
    return scheme_id


def share_summary_color_scheme_fingerprint(index: int) -> tuple[tuple[str, str], ...]:
    """Hashable snapshot of scheme values — invalidates PNG cache when palette edits land."""
    if not 0 <= index < len(SHARE_SUMMARY_COLOR_SCHEMES):
        index = SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT
    scheme = SHARE_SUMMARY_COLOR_SCHEMES[index]
    return tuple(sorted(scheme.items()))


SHARE_SUMMARY_COLOR_SCHEME_IDS: tuple[str, ...] = tuple(
    scheme["id"] for scheme in SHARE_SUMMARY_COLOR_SCHEMES
)

# Default stat label order for share cards (user-selectable stats planned for v1 integration).
# Four-stat set is the core period picker default; tiles/list extend it to six stats.
SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Total checklists",
    "Unique locations",
)
# Country/region scope — omits world-only stats such as Countries.
SHARE_SUMMARY_COUNTRY_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_COUNTRY_LIFETIME_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Total individuals",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Birding days",
    "Total individuals",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_TILES_DEFAULT_STATS: tuple[str, ...] = (
    SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS
    + (
        "Countries",
        "Birding days",
    )
)
# Lifetime (all data) — four-stat fallback omits lifers; tiles/list share the same six-stat order.
SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Countries",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Countries",
    "Birding days",
    "Total checklists",
    "Total individuals",
    "Longest streak (days)",
)
SHARE_SUMMARY_COUNTRY_LIFETIME_TILES_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Birding days",
    "Total individuals",
    "Total checklists",
    "Unique locations",
)
# Story format (1080×1920) — Circle cluster may show up to this many stats.
SHARE_SUMMARY_STORY_MAX_STATS = 10
# Statistics Grid (tiles + grid presentation) — separate from circle-cluster caps.
SHARE_SUMMARY_GRID_MIN_STATS = 4
SHARE_SUMMARY_GRID_SQUARE_MAX_STATS = 6
SHARE_SUMMARY_GRID_PORTRAIT_MAX_STATS = 8
SHARE_SUMMARY_GRID_STORY_MAX_STATS = 14
SHARE_SUMMARY_GRID_SQUARE_DEFAULT_SLOT_COUNT = 4
SHARE_SUMMARY_GRID_PORTRAIT_DEFAULT_SLOT_COUNT = 6
SHARE_SUMMARY_GRID_STORY_DEFAULT_SLOT_COUNT = 6
# Statistics List (minimal) on story — cap 18; slot count is min(available, cap).
SHARE_SUMMARY_MINIMAL_STORY_MAX_STATS = 18
# Display label on spotlight cards (matches Available statistics / card picker).
SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT = "Lifers"
# Spotlight species stat: short card title by period kind (picker stays "Total species").
SHARE_SUMMARY_SPOTLIGHT_SPECIES_LABEL_BY_PERIOD: dict[str, str] = {
    "year": "Year birds",
    "month": "Month birds",
    "week": "Week birds",
    "custom": "Species",
    "lifetime": "Species",
}
# Interesting Insights cards (#285): default fact id.
SHARE_SUMMARY_INSIGHT_FACT_DEFAULT = "most_common_checklist_species"

# User-visible layout and presentation names (design studio; future main app).
SHARE_SUMMARY_LAYOUT_LABELS: dict[str, str] = {
    "tiles": "Statistics Tiles",
    "minimal": "Statistics List",
    "spotlight": "Spotlight",
    "insight": "Interesting Insights",
}
SHARE_SUMMARY_TILES_PRESENTATION_LABELS: dict[str, str] = {
    "grid": "Statistics Grid",
    "circles": "Circle cluster",
}
SHARE_SUMMARY_SPOTLIGHT_PRESENTATION_LABELS: dict[str, str] = {
    "classic": "Classic",
    "circle": "Circle",
}

# Card green subtitle headings (tunable without editing layout code).
# Tiles / minimal / spotlight use layout subtitles unless period_kind is ``lifetime``,
# when :data:`SHARE_SUMMARY_LIFETIME_SUBTITLE` applies to all layouts.
SHARE_SUMMARY_PERIOD_SUBTITLE_YEAR = "Birding year in review"
SHARE_SUMMARY_PERIOD_SUBTITLE_MONTH = "Monthly birding summary"
SHARE_SUMMARY_PERIOD_SUBTITLE_WEEK = "Weekly birding summary"
SHARE_SUMMARY_PERIOD_SUBTITLE_LIFETIME = "My Birding Stats"
SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM = "Birding summary"
SHARE_SUMMARY_LIFETIME_SUBTITLE = "My Birding Stats"
SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES = "My birding stats"
SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL = "Summary"
SHARE_SUMMARY_LAYOUT_SUBTITLE_SPOTLIGHT = "My birding stats"
SHARE_SUMMARY_LAYOUT_SUBTITLE_INSIGHT = "My birding stats"

_PERIOD_SUBTITLE_BY_KIND: dict[str, str] = {
    "year": SHARE_SUMMARY_PERIOD_SUBTITLE_YEAR,
    "month": SHARE_SUMMARY_PERIOD_SUBTITLE_MONTH,
    "week": SHARE_SUMMARY_PERIOD_SUBTITLE_WEEK,
    "lifetime": SHARE_SUMMARY_PERIOD_SUBTITLE_LIFETIME,
    "custom": SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM,
}

_LAYOUT_SUBTITLE_BY_LAYOUT: dict[str, str] = {
    "tiles": SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES,
    "minimal": SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL,
    "spotlight": SHARE_SUMMARY_LAYOUT_SUBTITLE_SPOTLIGHT,
    "insight": SHARE_SUMMARY_LAYOUT_SUBTITLE_INSIGHT,
}


def share_summary_period_subtitle(period_kind: str) -> str:
    """Period-based green subtitle (year in review, monthly summary, etc.)."""
    if period_kind == "lifetime":
        return SHARE_SUMMARY_LIFETIME_SUBTITLE
    return _PERIOD_SUBTITLE_BY_KIND.get(
        period_kind, SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM
    )


def share_summary_layout_label(layout_id: str) -> str:
    """Human label for a share card layout id (``tiles``, ``minimal``, ``spotlight``, ``insight``)."""
    return SHARE_SUMMARY_LAYOUT_LABELS.get(layout_id, layout_id)


def share_summary_tiles_presentation_label(presentation_id: str) -> str:
    """Human label for Statistics Tiles presentation (``grid`` or ``circles``)."""
    return SHARE_SUMMARY_TILES_PRESENTATION_LABELS.get(presentation_id, presentation_id)


def share_summary_spotlight_presentation_label(presentation_id: str) -> str:
    """Human label for Spotlight presentation (``classic`` or ``circle``)."""
    return SHARE_SUMMARY_SPOTLIGHT_PRESENTATION_LABELS.get(
        presentation_id, presentation_id
    )


def share_summary_card_subtitle(
    *,
    layout: str,
    period_kind: str,
    trip_title: str | None = None,
) -> str | None:
    """Green subtitle heading for a card layout; ``None`` when trip title replaces it."""
    if trip_title:
        return None
    if period_kind == "lifetime":
        return SHARE_SUMMARY_LIFETIME_SUBTITLE
    return _LAYOUT_SUBTITLE_BY_LAYOUT.get(layout, SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM)
