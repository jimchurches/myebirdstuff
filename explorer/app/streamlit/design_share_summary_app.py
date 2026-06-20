"""
Social summary **design** utility — prototype layouts for #157.

No integration with the main explorer app. Run from repo root::

    pip install -r requirements.txt
    streamlit run explorer/app/streamlit/design_share_summary_app.py

Upload an eBird CSV or use sample data; compare layout mockups at square post,
portrait post, and story aspect ratios. PNG export uses Playwright (headless Chromium).
"""

from __future__ import annotations

import os
import sys
from datetime import date

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd
import streamlit as st

from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.data_loader import add_datetime_column, load_dataset
from explorer.core.region_display import map_focus_key_for_display
from explorer.core.share_summary_compute import (
    PeriodAnchor,
    PeriodKind,
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
    compute_share_summary_all_time_stats,
    filter_df_by_geo_scope,
    geo_country_keys_from_df,
    geo_region_options_for_country,
    geo_scope_display_label,
    resolve_period,
    suggest_period_anchor,
)
from explorer.presentation.share_summary_png_export import (
    share_summary_png_filename,
    share_summary_to_png_bytes,
)
from explorer.presentation.share_summary_circles_preview import (
    TILES_CIRCLE_CLUSTER_MAX,
)
from explorer.presentation.share_summary_hex_preview import (
    HEX_VARIANT_IDS,
    HEX_VARIANT_LABELS,
    HexVariantId,
    render_hex_grid_preview_html,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
    SpotlightStyleId,
    TilesStyleId,
    FORMAT_LABELS,
    FORMAT_PIXELS,
    compute_share_summary_stats,
    default_card_stat_labels,
    layout_card_stat_max,
    layout_card_stat_storage_max,
    period_for_custom,
    period_for_lifetime,
    period_for_month,
    period_for_week_containing,
    period_for_year,
    render_share_summary_preview_html,
    sample_share_summary_stats,
    summary_status_metrics,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEME_IDS,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    SHARE_SUMMARY_STORY_MAX_STATS,
    share_summary_color_scheme_index,
    share_summary_color_scheme_label,
)


@st.cache_data(show_spinner="Generating PNG…")
def _cached_share_summary_png(
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    scope_label: str | None,
    geo_scope: ShareSummaryGeoScope,
    tiles_style: TilesStyleId = "grid",
    spotlight_style: SpotlightStyleId = "classic",
) -> bytes:
    return share_summary_to_png_bytes(
        stats,
        layout=layout,
        fmt=fmt,
        spotlight_label=spotlight_label,
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        scope_label=scope_label,
        geo_scope=geo_scope,
        tiles_style=tiles_style,
        spotlight_style=spotlight_style,
    )

_DESIGN_STUDIO_TITLE = "Social sharing design studio"
_SOCIAL_CARDS_TAB_LABEL = "Social Cards"
_HEX_EXPERIMENTS_TAB_LABEL = "Hex grid experiments"
_PREVIEW_SCALE_DEFAULT = 0.42
_PREVIEW_SCALE_FULL = 1.0
_TILES_STYLE_KEY = "design_tiles_style"
_SPOTLIGHT_STYLE_KEY = "design_spotlight_style"
_COLOR_THEME_KEY = "design_color_theme"
_STATISTICS_LABEL = "Statistics"
_CARD_STATS_SLOT_COUNT_PREFIX = "design_card_stat_slot_count_"
_CARD_STATS_PICKS_PREFIX = "design_card_stat_picks_"
_CARD_STATS_SCOPE_PREFIX = "design_card_stat_scope_"
_SPOTLIGHT_LABEL_KEY = "design_spotlight_label"
_CURRENT_CARD_LABEL = "Current card"
_CARD_HEADING_LABEL = "Card Heading (optional)"
_CARD_HEADING_PLACEHOLDER = "e.g. North Coast NSW Exploration"
_GEO_WORLD_OPTION = ""
_GEO_COUNTRY_SELECT_KEY = "design_geo_country"
_GEO_REGION_SELECT_KEY = "design_geo_region"


def _card_heading_or_none(text: str) -> str | None:
    """Normalize sidebar card heading; maps to ``trip_title`` on stats/period objects."""
    stripped = (text or "").strip()
    return stripped or None


@st.cache_data
def _design_sample_dataset(sample_year: int) -> pd.DataFrame:
    """Small multi-region export for sample mode (AU NSW/QLD, India Goa)."""
    y = int(sample_year)
    checklists: list[tuple[str, str, str, str, float, float, list[tuple[str, str]]]] = [
        (
            "S9001",
            "AU-NSW",
            f"{y}-06-05",
            "Royal National Park",
            -34.07,
            151.08,
            [
                ("Superb Fairywren", "Malurus cyaneus"),
                ("Laughing Kookaburra", "Dacelo novaeguineae"),
                ("Australian Magpie", "Gymnorhina tibicen"),
            ],
        ),
        (
            "S9002",
            "AU-NSW",
            f"{y}-06-12",
            "Blue Mountains",
            -33.71,
            150.31,
            [
                ("Crimson Rosella", "Platycercus elegans"),
                ("Eastern Yellow Robin", "Eopsaltria australis"),
                ("Willie Wagtail", "Rhipidura leucophrys"),
            ],
        ),
        (
            "S9003",
            "AU-QLD",
            f"{y}-05-20",
            "Roma Street Parkland",
            -27.46,
            153.02,
            [
                ("Rainbow Lorikeet", "Trichoglossus moluccanus"),
                ("Sulphur-crested Cockatoo", "Cacatua galerita"),
                ("Australian Pelican", "Pelecanus conspicillatus"),
            ],
        ),
        (
            "S9004",
            "IN-GA",
            f"{y}-11-28",
            "Arambol Beach",
            15.688,
            73.703,
            [
                ("Indian Pond-Heron", "Ardeola grayii"),
                ("House Crow", "Corvus splendens"),
                ("White-throated Kingfisher", "Halcyon smyrnensis"),
            ],
        ),
    ]
    records: list[dict] = []
    for sid, state, dt, loc_name, lat, lon, species in checklists:
        for common, scientific in species:
            records.append(
                {
                    "Submission ID": sid,
                    "Date": dt,
                    "Time": "08:00 AM",
                    "State/Province": state,
                    "Location ID": f"L_{sid}",
                    "Location": loc_name,
                    "Latitude": lat,
                    "Longitude": lon,
                    "Common Name": common,
                    "Scientific Name": scientific,
                    "Count": 2,
                    "Protocol": "eBird - Traveling Count",
                    "All Obs Reported": 1,
                    "Duration (Min)": 60.0,
                    "Number of Observers": 1.0,
                }
            )
    return add_datetime_column(pd.DataFrame(records))


def _geo_country_select_label(country_key: str) -> str:
    if not country_key:
        return "World"
    return map_focus_key_for_display(country_key)


def _sidebar_geo_scope_controls(df: pd.DataFrame) -> ShareSummaryGeoScope:
    """Country and region pickers; World is the default (no filter)."""
    country_keys = geo_country_keys_from_df(df)
    country_options = [_GEO_WORLD_OPTION, *country_keys]
    country_key = st.selectbox(
        "Country",
        options=country_options,
        format_func=_geo_country_select_label,
        key=_GEO_COUNTRY_SELECT_KEY,
    )
    if not country_key:
        st.session_state.pop(_GEO_REGION_SELECT_KEY, None)
        return ShareSummaryGeoScope()

    region_pairs = geo_region_options_for_country(df, country_key)
    region_options = [_GEO_WORLD_OPTION, *[code for code, _ in region_pairs]]
    region_labels = {_GEO_WORLD_OPTION: "All regions"}
    region_labels.update({code: label for code, label in region_pairs})
    current_region = st.session_state.get(_GEO_REGION_SELECT_KEY, _GEO_WORLD_OPTION)
    if current_region not in region_options:
        st.session_state[_GEO_REGION_SELECT_KEY] = _GEO_WORLD_OPTION
    region_code = st.selectbox(
        "Region",
        options=region_options,
        format_func=lambda code: region_labels[code],
        key=_GEO_REGION_SELECT_KEY,
    )
    return ShareSummaryGeoScope(
        country_key=country_key,
        region_code=region_code or None,
    )


def _card_stat_picks_key(layout: LayoutId, period_kind: PeriodKind) -> str:
    return f"{_CARD_STATS_PICKS_PREFIX}{layout}_{period_kind}"


def _card_stat_slot_count_key(layout: LayoutId, period_kind: PeriodKind) -> str:
    return f"{_CARD_STATS_SLOT_COUNT_PREFIX}{layout}_{period_kind}"


def _card_stat_scope_key(layout: LayoutId, period_kind: PeriodKind) -> str:
    return f"{_CARD_STATS_SCOPE_PREFIX}{layout}_{period_kind}"


def _card_stat_data_scope(
    *,
    use_sample: bool,
    period_kind: PeriodKind,
    period_label: str,
    upload_name: str | None,
    geo_scope: ShareSummaryGeoScope | None = None,
) -> str:
    """Session scope token — when this changes, card-stat picks re-initialize."""
    source = "sample" if use_sample else (upload_name or "csv")
    geo_token = (geo_scope or ShareSummaryGeoScope()).scope_token()
    return f"{source}|{period_kind}|{period_label}|{geo_token}"


def _period_has_checklist_data(stats: ShareSummaryStats) -> bool:
    """False when the selected period has no checklists in the loaded export."""
    return stats.checklists is not None and stats.checklists > 0


def _card_stat_selectbox_key(layout: LayoutId, index: int) -> str:
    return f"design_card_stat_sel_{layout}_{index}"


def _clear_card_stat_selectbox_keys(layout: LayoutId) -> None:
    """Drop stale selectbox widget state so Reset / session picks take effect."""
    for i in range(layout_card_stat_storage_max(layout)):
        st.session_state.pop(_card_stat_selectbox_key(layout, i), None)


def _resolve_card_stat_selectbox_value(
    *,
    session_value: object,
    desired: str,
    options: list[str],
) -> str:
    """Pick a valid selectbox value, preferring the widget over stale session picks."""
    if session_value is not None:
        value = session_value.strip() if isinstance(session_value, str) else str(session_value).strip()
        if value in options:
            return value
    fallback = desired.strip() if isinstance(desired, str) else str(desired).strip()
    return fallback if fallback in options else ""


def _sync_card_stat_selectbox_value(
    layout: LayoutId,
    index: int,
    *,
    options: list[str],
    desired: str,
) -> str:
    """Align selectbox session state without clobbering a valid user choice."""
    key = _card_stat_selectbox_key(layout, index)
    value = _resolve_card_stat_selectbox_value(
        session_value=st.session_state.get(key),
        desired=desired,
        options=options,
    )
    st.session_state[key] = value
    return value


def _story_format_stat_picker(fmt: FormatId, layout: LayoutId) -> bool:
    """Fixed stat rows on story format for grid and list layouts."""
    return fmt == "story" and layout in ("minimal", "tiles")


def _tiles_circle_cluster_picker(layout: LayoutId, tiles_style: TilesStyleId) -> bool:
    return layout == "tiles" and tiles_style == "circles"


def _card_stat_max_slots(
    layout: LayoutId,
    fmt: FormatId,
    *,
    tiles_style: TilesStyleId = "grid",
) -> int:
    if _tiles_circle_cluster_picker(layout, tiles_style):
        return TILES_CIRCLE_CLUSTER_MAX
    return layout_card_stat_max(layout, fmt)


def _card_stat_ui_row_count(
    layout: LayoutId,
    fmt: FormatId,
    *,
    slot_count: int,
    tiles_style: TilesStyleId = "grid",
) -> int:
    max_slots = _card_stat_max_slots(layout, fmt, tiles_style=tiles_style)
    if _story_format_stat_picker(fmt, layout):
        return max_slots
    return min(max(1, slot_count), max_slots)


def _effective_card_stat_labels(
    picks: list[str],
    layout: LayoutId,
    fmt: FormatId,
    *,
    tiles_style: TilesStyleId = "grid",
) -> tuple[str, ...]:
    max_slots = _card_stat_max_slots(layout, fmt, tiles_style=tiles_style)
    return tuple(label for label in picks if label)[:max_slots]


def _sanitize_card_stat_picks(
    picks: list[str],
    *,
    available: frozenset[str],
    max_slots: int,
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in picks:
        label = raw.strip() if isinstance(raw, str) else str(raw).strip()
        if label and label in available and label not in seen:
            seen.add(label)
            out.append(label)
        if len(out) >= max_slots:
            break
    return out


def _ensure_card_stat_picks(
    layout: LayoutId,
    status_metrics: list[tuple[str, str]],
    fmt: FormatId,
    period_kind: PeriodKind,
    *,
    data_scope: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_style: TilesStyleId = "grid",
) -> list[str]:
    """Initialize or sanitize session picks for *layout*; returns UI row values."""
    circle_cluster = _tiles_circle_cluster_picker(layout, tiles_style)
    max_slots = _card_stat_max_slots(layout, fmt, tiles_style=tiles_style)
    storage_max = (
        TILES_CIRCLE_CLUSTER_MAX
        if circle_cluster
        else layout_card_stat_storage_max(layout)
    )
    available = frozenset(label for label, _ in status_metrics)
    picks_key = _card_stat_picks_key(layout, period_kind)
    count_key = _card_stat_slot_count_key(layout, period_kind)
    scope_key = _card_stat_scope_key(layout, period_kind)
    fixed_rows = _story_format_stat_picker(fmt, layout)
    defaults = list(
        default_card_stat_labels(
            layout, status_metrics, period_kind=period_kind, geo_scope=geo_scope
        )
    )

    if st.session_state.get(scope_key) != data_scope:
        st.session_state[scope_key] = data_scope
        st.session_state.pop(picks_key, None)
        st.session_state.pop(count_key, None)
        _clear_card_stat_selectbox_keys(layout)

    if picks_key not in st.session_state:
        if fixed_rows:
            st.session_state[picks_key] = defaults + [""] * (max_slots - len(defaults))
            st.session_state[count_key] = max_slots
        else:
            st.session_state[picks_key] = defaults
            st.session_state[count_key] = max(1, len(defaults) if defaults else 1)

    sanitized = _sanitize_card_stat_picks(
        list(st.session_state[picks_key]),
        available=available,
        max_slots=storage_max,
    )
    if not sanitized and defaults:
        _clear_card_stat_selectbox_keys(layout)
        if fixed_rows:
            st.session_state[picks_key] = defaults + [""] * (max_slots - len(defaults))
            st.session_state[count_key] = max_slots
        else:
            st.session_state[picks_key] = defaults
            st.session_state[count_key] = max(1, len(defaults))
        sanitized = list(defaults)

    sanitized = _sanitize_card_stat_picks(
        list(st.session_state[picks_key]),
        available=available,
        max_slots=storage_max,
    )
    slot_count = int(st.session_state.get(count_key, max(1, len(sanitized))))
    ui_rows = _card_stat_ui_row_count(
        layout, fmt, slot_count=slot_count, tiles_style=tiles_style
    )

    raw = list(st.session_state[picks_key])
    if fixed_rows:
        picks = (raw + [""] * ui_rows)[:ui_rows]
    else:
        compact = [p for p in raw if p]
        picks = (compact + [""] * ui_rows)[:ui_rows]
        st.session_state[count_key] = ui_rows

    st.session_state[picks_key] = picks
    return picks


def _card_stat_slot_label(layout: LayoutId, index: int, *, total: int) -> str:
    """User-facing label for one card-stat picker row."""
    kind = "List item" if layout == "minimal" else "Tile"
    if total == 1:
        return kind
    return f"{kind} {index + 1}"


def _status_metrics_lookup(status_metrics: list[tuple[str, str]]) -> dict[str, str]:
    return dict(status_metrics)


def _stats_on_card(picks: list[str]) -> set[str]:
    return {label for label in picks if label}


def _card_can_accept_stat(
    layout: LayoutId,
    fmt: FormatId,
    picks: list[str],
    slot_count: int,
    *,
    tiles_style: TilesStyleId = "grid",
) -> bool:
    max_slots = _card_stat_max_slots(layout, fmt, tiles_style=tiles_style)
    fixed_rows = _story_format_stat_picker(fmt, layout)
    ui_rows = _card_stat_ui_row_count(
        layout, fmt, slot_count=slot_count, tiles_style=tiles_style
    )
    active = (picks + [""] * ui_rows)[:ui_rows]
    if any(not label for label in active):
        return True
    if fixed_rows:
        return False
    return ui_rows < max_slots


def _add_stat_to_card(
    label: str,
    *,
    layout: LayoutId,
    period_kind: PeriodKind,
    fmt: FormatId,
    tiles_style: TilesStyleId,
) -> None:
    """Fill the next empty card slot, or append a row when allowed."""
    picks_key = _card_stat_picks_key(layout, period_kind)
    count_key = _card_stat_slot_count_key(layout, period_kind)
    max_slots = _card_stat_max_slots(layout, fmt, tiles_style=tiles_style)
    fixed_rows = _story_format_stat_picker(fmt, layout)
    picks = list(st.session_state.get(picks_key, []))
    slot_count = int(st.session_state.get(count_key, 1))
    ui_rows = _card_stat_ui_row_count(
        layout, fmt, slot_count=slot_count, tiles_style=tiles_style
    )
    active = (picks + [""] * ui_rows)[:ui_rows]

    for i in range(ui_rows):
        if not active[i]:
            active[i] = label
            st.session_state[picks_key] = active + picks[ui_rows:]
            _clear_card_stat_selectbox_keys(layout)
            return

    if fixed_rows:
        padded = (picks + [""] * max_slots)[:max_slots]
        for i in range(max_slots):
            if not padded[i]:
                padded[i] = label
                st.session_state[picks_key] = padded
                _clear_card_stat_selectbox_keys(layout)
                return
        return

    if ui_rows < max_slots:
        active.append(label)
        st.session_state[count_key] = ui_rows + 1
        st.session_state[picks_key] = active
        _clear_card_stat_selectbox_keys(layout)


def _add_stat_to_card_on_click(
    stat_label: str,
    layout: LayoutId,
    period_kind: PeriodKind,
    fmt: FormatId,
    tiles_style: TilesStyleId,
) -> None:
    """Callback — runs before widgets so selectbox keys can be cleared safely."""
    _add_stat_to_card(
        stat_label,
        layout=layout,
        period_kind=period_kind,
        fmt=fmt,
        tiles_style=tiles_style,
    )


def _not_on_card_chip_strip(
    *,
    layout: LayoutId,
    period_kind: PeriodKind,
    fmt: FormatId,
    status_metrics: list[tuple[str, str]],
    picks: list[str],
    slot_count: int,
    metrics_lookup: dict[str, str],
    tiles_style: TilesStyleId = "grid",
) -> None:
    """Compact chips for stats not yet on the card; click to add."""
    on_card = _stats_on_card(picks)
    not_on_card = [
        (stat_label, metrics_lookup[stat_label])
        for stat_label, _ in status_metrics
        if stat_label not in on_card
    ]
    if not not_on_card:
        st.caption("All available stats are on the card.")
        return

    count = len(not_on_card)
    can_add = _card_can_accept_stat(
        layout, fmt, picks, slot_count, tiles_style=tiles_style
    )
    st.caption(
        f"{count} more stat{'s' if count != 1 else ''} available"
        + (" — click to add to the card." if can_add else " — card is full.")
    )

    cols_per_row = 3
    for row_start in range(0, len(not_on_card), cols_per_row):
        row_items = not_on_card[row_start : row_start + cols_per_row]
        cols = st.columns(len(row_items))
        for col_index, (stat_label, value) in enumerate(row_items):
            with cols[col_index]:
                chip_index = row_start + col_index
                st.button(
                    f"{stat_label} · {value}",
                    key=f"design_stat_chip_{layout}_{period_kind}_{chip_index}",
                    use_container_width=True,
                    disabled=not can_add,
                    help=(
                        f"Add {stat_label} to the card"
                        if can_add
                        else "Remove or clear a slot to add another stat"
                    ),
                    on_click=_add_stat_to_card_on_click,
                    args=(stat_label, layout, period_kind, fmt, tiles_style),
                )


def _card_stat_picker_ui(
    layout: LayoutId,
    status_metrics: list[tuple[str, str]],
    fmt: FormatId,
    period_kind: PeriodKind,
    *,
    data_scope: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_style: TilesStyleId = "grid",
) -> tuple[str, ...]:
    """Ordered stat picker for hero / tiles / list; hidden for spotlight."""
    if layout == "spotlight":
        return ()

    max_slots = _card_stat_max_slots(layout, fmt, tiles_style=tiles_style)
    fixed_rows = _story_format_stat_picker(fmt, layout)
    available_labels = [label for label, _ in status_metrics]
    metrics_lookup = _status_metrics_lookup(status_metrics)
    if not available_labels:
        st.caption("No statistics available for this period.")
        return ()

    picks_key = _card_stat_picks_key(layout, period_kind)
    count_key = _card_stat_slot_count_key(layout, period_kind)
    picks = _ensure_card_stat_picks(
        layout,
        status_metrics,
        fmt,
        period_kind,
        data_scope=data_scope,
        geo_scope=geo_scope,
        tiles_style=tiles_style,
    )
    ui_rows = _card_stat_ui_row_count(
        layout,
        fmt,
        slot_count=int(st.session_state[count_key]),
        tiles_style=tiles_style,
    )

    if fixed_rows:
        st.caption(
            f"Story format supports up to {max_slots} stats. "
            "Empty rows are ignored. Order matches the card."
        )
    else:
        st.caption(
            f"Choose up to {max_slots} stats for this layout. Order matches position on the card."
        )

    for i in range(ui_rows):
        current = picks[i] if i < len(picks) else ""
        other = {picks[j] for j in range(len(picks)) if j != i and picks[j]}
        options = [""] + [lab for lab in available_labels if lab not in other]
        current = _sync_card_stat_selectbox_value(
            layout, i, options=options, desired=current
        )
        picks[i] = current
        row_label = _card_stat_slot_label(layout, i, total=ui_rows)
        can_up = i > 0
        can_down = i < ui_rows - 1
        can_remove = bool(current) if fixed_rows else (i > 0 or bool(current))

        col_sel, col_val, col_actions = st.columns([7, 2, 3], vertical_alignment="bottom")
        with col_sel:
            choice = st.selectbox(
                row_label,
                options=options,
                format_func=lambda x: "—" if x == "" else x,
                key=_card_stat_selectbox_key(layout, i),
            )
            picks[i] = choice or ""
        with col_val:
            value = metrics_lookup.get(picks[i], "") if picks[i] else ""
            st.markdown(f"**{value}**" if value else "—")
        with col_actions:
            btn_up, btn_down, btn_rm = st.columns(3, gap="small")
            with btn_up:
                if st.button(
                    "↑",
                    key=f"design_card_stat_up_{layout}_{i}",
                    help="Move up",
                    disabled=not can_up,
                    use_container_width=True,
                ):
                    picks[i - 1], picks[i] = picks[i], picks[i - 1]
                    st.session_state[picks_key] = picks[:ui_rows]
                    _clear_card_stat_selectbox_keys(layout)
                    st.rerun()
            with btn_down:
                if st.button(
                    "↓",
                    key=f"design_card_stat_down_{layout}_{i}",
                    help="Move down",
                    disabled=not can_down,
                    use_container_width=True,
                ):
                    picks[i + 1], picks[i] = picks[i], picks[i + 1]
                    st.session_state[picks_key] = picks[:ui_rows]
                    _clear_card_stat_selectbox_keys(layout)
                    st.rerun()
            with btn_rm:
                if st.button(
                    "✕",
                    key=f"design_card_stat_rm_{layout}_{i}",
                    help="Remove this stat",
                    disabled=not can_remove,
                    use_container_width=True,
                ):
                    if fixed_rows:
                        picks[i] = ""
                    elif i == 0 and ui_rows == 1:
                        picks[0] = ""
                    elif i == 0:
                        picks.pop(0)
                        st.session_state[count_key] = ui_rows - 1
                    else:
                        picks.pop(i)
                        st.session_state[count_key] = ui_rows - 1
                    st.session_state[picks_key] = picks[:ui_rows]
                    st.rerun()

    col_sel_foot, col_val_foot, col_actions_foot = st.columns([7, 2, 3], vertical_alignment="bottom")
    with col_sel_foot:
        if not fixed_rows and ui_rows < max_slots and st.button(
            "Add stat",
            key=f"design_card_stat_add_{layout}",
        ):
            st.session_state[count_key] = ui_rows + 1
            st.rerun()
    with col_actions_foot:
        foot_up, foot_down, foot_rm = st.columns(3, gap="small")
        with foot_down:
            if st.button(
                "Reset",
                key=f"design_card_stat_reset_{layout}",
                help="Restore this layout's default stat list",
                use_container_width=True,
            ):
                defaults = list(
                    default_card_stat_labels(
                        layout,
                        status_metrics,
                        period_kind=period_kind,
                        geo_scope=geo_scope,
                    )
                )
                _clear_card_stat_selectbox_keys(layout)
                if fixed_rows:
                    st.session_state[picks_key] = defaults + [""] * (max_slots - len(defaults))
                    st.session_state[count_key] = max_slots
                else:
                    st.session_state[picks_key] = defaults
                    st.session_state[count_key] = max(1, len(defaults))
                st.rerun()

    st.session_state[picks_key] = picks[:ui_rows]
    final = _effective_card_stat_labels(
        picks,
        layout,
        fmt,
        tiles_style=tiles_style,
    )
    if not final:
        st.caption("Select at least one stat to show on the card.")

    st.divider()
    _not_on_card_chip_strip(
        layout=layout,
        period_kind=period_kind,
        fmt=fmt,
        status_metrics=status_metrics,
        picks=picks[:ui_rows],
        slot_count=int(st.session_state[count_key]),
        metrics_lookup=metrics_lookup,
        tiles_style=tiles_style,
    )
    return final


def _spotlight_label_from_session(
    status_metrics: list[tuple[str, str]],
) -> str:
    available = {label for label, _ in status_metrics}
    raw = st.session_state.get(_SPOTLIGHT_LABEL_KEY)
    if isinstance(raw, str) and raw.strip() in available:
        return raw.strip()
    if SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT in available:
        return SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT
    if status_metrics:
        return status_metrics[0][0]
    return SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT


def _select_spotlight_stat(stat_label: str) -> None:
    """Callback — runs before widgets so the selectbox key can be updated."""
    st.session_state[_SPOTLIGHT_LABEL_KEY] = stat_label


def _spotlight_alternate_chip_strip(
    status_metrics: list[tuple[str, str]],
    *,
    current: str,
    metrics_lookup: dict[str, str],
) -> None:
    """Quick-switch chips for stats not currently spotlighted."""
    others = [
        (label, metrics_lookup[label])
        for label, _ in status_metrics
        if label != current
    ]
    if not others:
        return
    count = len(others)
    st.caption(
        f"{count} other stat{'s' if count != 1 else ''} available — click to spotlight."
    )
    cols_per_row = 3
    for row_start in range(0, len(others), cols_per_row):
        row_items = others[row_start : row_start + cols_per_row]
        cols = st.columns(len(row_items))
        for col_index, (stat_label, value) in enumerate(row_items):
            with cols[col_index]:
                chip_index = row_start + col_index
                st.button(
                    f"{stat_label} · {value}",
                    key=f"design_spotlight_chip_{chip_index}",
                    use_container_width=True,
                    help=f"Spotlight {stat_label}",
                    on_click=_select_spotlight_stat,
                    args=(stat_label,),
                )


def _spotlight_stat_picker(status_metrics: list[tuple[str, str]]) -> None:
    labels = [label for label, _ in status_metrics]
    if not labels:
        st.caption("No statistics available for this period.")
        return
    metrics_lookup = _status_metrics_lookup(status_metrics)
    current = _spotlight_label_from_session(status_metrics)
    col_sel, col_val = st.columns([4, 1], vertical_alignment="bottom")
    with col_sel:
        st.selectbox(
            "Spotlight stat",
            options=labels,
            index=labels.index(current) if current in labels else 0,
            key=_SPOTLIGHT_LABEL_KEY,
            help="Single highlighted stat for the Spotlight layout.",
        )
    selected = _spotlight_label_from_session(status_metrics)
    with col_val:
        st.markdown(f"**{metrics_lookup.get(selected, '—')}**")

    st.divider()
    _spotlight_alternate_chip_strip(
        status_metrics,
        current=selected,
        metrics_lookup=metrics_lookup,
    )


def _preview_scale_caption(fmt: FormatId, scale: float) -> str | None:
    """Hint when preview is at or near export pixel size."""
    if scale < _PREVIEW_SCALE_FULL - 0.005:
        return None
    width, height = FORMAT_PIXELS[fmt]
    return (
        f"Export size ({width}×{height}px). "
        "Scroll the page to see the full card — story format is tall."
        if height > width
        else f"Export size ({width}×{height}px) — matches the PNG export."
    )


def _sidebar_preview_scale_controls(fmt: FormatId) -> float:
    """Preview scale slider from compact default up to export pixel size."""
    scale = st.slider(
        "Preview scale",
        min_value=_PREVIEW_SCALE_DEFAULT,
        max_value=_PREVIEW_SCALE_FULL,
        value=_PREVIEW_SCALE_DEFAULT,
        step=0.01,
        help="Drag right for full export size (100%). Default 0.42 is a compact preview.",
        key="design_preview_scale",
    )
    caption = _preview_scale_caption(fmt, scale)
    if caption:
        st.caption(caption)
    return scale


def _centered_card_download_button(
    *,
    label: str,
    data: bytes,
    file_name: str,
    mime: str,
    help_text: str,
) -> None:
    """Download control centred under the scaled card preview."""
    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        st.download_button(
            label,
            data=data,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
            help=help_text,
        )


@st.fragment
def _current_card_fragment(
    *,
    stats: ShareSummaryStats,
    all_time: ShareSummaryAllTimeStats | None,
    selected_layout: LayoutId,
    fmt: FormatId,
    scale: float,
    status_metrics: list[tuple[str, str]],
    color_scheme_index: int,
    card_stat_data_scope: str,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_style: TilesStyleId = "grid",
    spotlight_style: SpotlightStyleId = "classic",
) -> None:
    """Card statistics controls, live preview, and PNG export."""
    card_stat_labels: tuple[str, ...] = ()
    with st.expander(_STATISTICS_LABEL, expanded=False):
        if selected_layout == "spotlight":
            _spotlight_stat_picker(status_metrics)
        else:
            card_stat_labels = _card_stat_picker_ui(
                selected_layout,
                status_metrics,
                fmt,
                stats.period_kind,
                data_scope=card_stat_data_scope,
                geo_scope=geo_scope,
                tiles_style=tiles_style,
            )

    spotlight_label = _spotlight_label_from_session(status_metrics)

    st.subheader(_CURRENT_CARD_LABEL)
    st.markdown(
        render_share_summary_preview_html(
            stats,
            layout=selected_layout,
            fmt=fmt,
            tiles_style=tiles_style,
            spotlight_style=spotlight_style,
            scale=scale,
            spotlight_label=spotlight_label,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            geo_scope=geo_scope,
            scope_label=scope_label,
        ),
        unsafe_allow_html=True,
    )

    png_filename = share_summary_png_filename(stats, layout=selected_layout, fmt=fmt)
    try:
        png_bytes = _cached_share_summary_png(
            stats,
            selected_layout,
            fmt,
            card_stat_labels,
            spotlight_label,
            all_time,
            color_scheme_index,
            scope_label,
            geo_scope,
            tiles_style,
            spotlight_style,
        )
    except RuntimeError as exc:
        st.warning(str(exc))
    else:
        _centered_card_download_button(
            label="Export card",
            data=png_bytes,
            file_name=png_filename,
            mime="image/png",
            help_text="PNG of the current card above.",
        )


st.set_page_config(page_title=_DESIGN_STUDIO_TITLE, layout="wide")
st.title(_DESIGN_STUDIO_TITLE)
st.caption(
    "Exploratory tool only. Compare HTML mockups before choosing layouts for the main app."
)

df: pd.DataFrame | None = None
geo_scope = ShareSummaryGeoScope()

with st.sidebar:
    st.header("Data")
    use_sample = st.toggle("Use sample data", value=True)
    uploaded = None if use_sample else st.file_uploader("eBird CSV export", type=["csv"])
    if use_sample:
        df = _design_sample_dataset(date.today().year)
    elif uploaded is not None:
        with st.spinner("Loading CSV…"):
            df = load_dataset(uploaded)

    st.header("Scope")
    period_mode = st.selectbox(
        "Range",
        options=["year", "month", "week", "custom", "lifetime"],
        format_func=lambda x: {
            "year": "Yearly",
            "month": "Monthly",
            "week": "Weekly",
            "custom": "Custom date range",
            "lifetime": "Lifetime",
        }[x],
    )
    period_anchor: PeriodAnchor | None = None
    selected_year: int | None = None
    if period_mode == "year":
        selected_year = int(
            st.number_input(
                "Year",
                min_value=2000,
                max_value=2100,
                value=date.today().year,
                step=1,
                key="design_period_year",
            )
        )
    elif period_mode in ("month", "week"):
        default_anchor = suggest_period_anchor(period_mode, date.today())
        period_anchor = st.radio(
            "Period",
            options=["current", "previous"],
            index=0 if default_anchor == "current" else 1,
            format_func=lambda x: {
                "current": f"Current {period_mode}",
                "previous": f"Previous {period_mode}",
            }[x],
            help="Current vs previous calendar period (e.g. post May results on 2 June → previous month).",
        )

    sample_custom_start: date | None = None
    sample_custom_end: date | None = None
    sample_card_heading = ""
    if period_mode == "custom" and use_sample:
        sample_custom_start = st.date_input(
            "Start date",
            value=date(2025, 6, 1),
            key="design_sample_custom_start",
        )
        sample_custom_end = st.date_input(
            "End date",
            value=date(2025, 6, 7),
            key="design_sample_custom_end",
        )
        sample_card_heading = st.text_input(
            _CARD_HEADING_LABEL,
            value="",
            placeholder=_CARD_HEADING_PLACEHOLDER,
            key="design_sample_card_heading",
        )

    if df is not None and not df.empty:
        geo_scope = _sidebar_geo_scope_controls(df)
    elif not use_sample and uploaded is None:
        st.caption("Upload a CSV to choose country and region.")
    elif df is not None and df.empty:
        st.caption("No data in file.")

    st.header(_CURRENT_CARD_LABEL)
    selected_layout: LayoutId = st.selectbox(
        "Layout",
        options=["hero", "tiles", "minimal", "spotlight"],
        format_func=lambda x: {
            "hero": "Hero Grid",
            "tiles": "Statistics Grid",
            "minimal": "Statistics List",
            "spotlight": "Spotlight",
        }[x],
    )
    tiles_style: TilesStyleId = "grid"
    if selected_layout == "tiles":
        tiles_style = st.radio(
            "Statistics presentation",
            options=["grid", "circles"],
            format_func=lambda x: "Statistics Grid" if x == "grid" else "Circle cluster",
            key=_TILES_STYLE_KEY,
            horizontal=True,
        )
    spotlight_style: SpotlightStyleId = "classic"
    if selected_layout == "spotlight":
        spotlight_style = st.radio(
            "Spotlight presentation",
            options=["classic", "circle"],
            format_func=lambda x: "Classic" if x == "classic" else "Circle",
            key=_SPOTLIGHT_STYLE_KEY,
            horizontal=True,
        )
    fmt: FormatId = st.selectbox(
        "Aspect ratio",
        options=["square", "portrait_post", "story"],
        format_func=lambda x: FORMAT_LABELS[x],
    )
    color_theme_id = st.selectbox(
        "Theme",
        options=list(SHARE_SUMMARY_COLOR_SCHEME_IDS),
        format_func=share_summary_color_scheme_label,
        key=_COLOR_THEME_KEY,
    )
    color_scheme_index = share_summary_color_scheme_index(color_theme_id)
    scale = _sidebar_preview_scale_controls(fmt)

resolved_period = None
stats: ShareSummaryStats = sample_share_summary_stats()
all_time: ShareSummaryAllTimeStats | None = ShareSummaryAllTimeStats(
    total_species_taxa=10_800,
    total_families_taxa=248,
)

if not use_sample:
    if uploaded is None:
        st.info("Upload an eBird CSV in the sidebar, or enable **Use sample data**.")
        st.stop()
    if df is None or df.empty:
        st.warning("No data found in this file.")
        st.stop()

if df is not None:
    df_scoped = filter_df_by_geo_scope(df, geo_scope)
    dates = pd.to_datetime(df_scoped["Date"], errors="coerce").dropna()
    if dates.empty:
        st.warning("No dated checklists in this file.")
        st.stop()
    min_d = dates.min().date()
    max_d = dates.max().date()

    reference = date.today()
    if period_mode == "year":
        if selected_year is None:
            st.warning("Select a year in the sidebar.")
            st.stop()
        period = period_for_year(selected_year)
    elif period_mode == "month":
        if period_anchor is not None:
            period = resolve_period("month", anchor=period_anchor, reference=reference)
        else:
            month_options = sorted({(int(r.year), int(r.month)) for r in dates.dt.to_pydatetime()})
            labels = [date(y, m, 1).strftime("%B %Y") for y, m in month_options]
            pick = st.sidebar.selectbox("Month", options=range(len(labels)), format_func=lambda i: labels[i])
            y, m = month_options[pick]
            period = period_for_month(y, m)
    elif period_mode == "week":
        if period_anchor is not None:
            period = resolve_period("week", anchor=period_anchor, reference=reference)
        else:
            week_starts = sorted({period_for_week_containing(d).start for d in dates.dt.date})
            week_labels = [
                period_for_week_containing(ws).label for ws in week_starts
            ]
            pick = st.sidebar.selectbox("Week", options=range(len(week_labels)), format_func=lambda i: week_labels[i])
            period = period_for_week_containing(week_starts[pick])
    elif period_mode == "lifetime":
        period = period_for_lifetime(min_d, max_d)
    elif period_mode == "custom":
        if use_sample:
            start, end = sample_custom_start, sample_custom_end
            if start is None or end is None:
                st.warning("Choose custom dates in the sidebar.")
                st.stop()
            if end < start:
                start, end = end, start
            period = period_for_custom(
                start,
                end,
                trip_title=_card_heading_or_none(sample_card_heading),
            )
        else:
            start = st.sidebar.date_input(
                "Start date",
                value=min_d,
                min_value=min_d,
                max_value=max_d,
                key="design_csv_custom_start",
            )
            end = st.sidebar.date_input(
                "End date",
                value=max_d,
                min_value=min_d,
                max_value=max_d,
                key="design_csv_custom_end",
            )
            card_heading = st.sidebar.text_input(
                _CARD_HEADING_LABEL,
                value="",
                placeholder=_CARD_HEADING_PLACEHOLDER,
                key="design_csv_card_heading",
            )
            period = period_for_custom(start, end, trip_title=_card_heading_or_none(card_heading))

    resolved_period = period
    lifer_ref = df if not geo_scope.is_world else None
    computed = compute_share_summary_stats(
        df_scoped, period, lifer_reference_df=lifer_ref, geo_scope=geo_scope
    )
    if computed is None:
        st.warning("Could not compute stats for this period.")
        st.stop()
    stats = computed
    all_time = (
        compute_share_summary_all_time_stats(df_scoped, taxonomy_locale=TAXONOMY_LOCALE_DEFAULT)
        if geo_scope.is_world
        else None
    )

upload_name = uploaded.name if uploaded is not None else None
card_stat_data_scope = _card_stat_data_scope(
    use_sample=use_sample,
    period_kind=stats.period_kind,
    period_label=stats.period_label,
    upload_name=upload_name,
    geo_scope=geo_scope,
)
scope_label = geo_scope_display_label(geo_scope)

status_metrics = summary_status_metrics(stats, all_time=all_time, geo_scope=geo_scope)

if _SPOTLIGHT_LABEL_KEY not in st.session_state:
    st.session_state[_SPOTLIGHT_LABEL_KEY] = SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT

tab_social_cards, tab_hex_experiments = st.tabs(
    [_SOCIAL_CARDS_TAB_LABEL, _HEX_EXPERIMENTS_TAB_LABEL]
)

hex_card_stat_labels = default_card_stat_labels(
    "tiles",
    status_metrics,
    period_kind=stats.period_kind,
    geo_scope=geo_scope,
)
if fmt == "story" and len(hex_card_stat_labels) < SHARE_SUMMARY_STORY_MAX_STATS:
    picked = set(hex_card_stat_labels)
    extra: list[str] = []
    for label, _ in status_metrics:
        if label in picked:
            continue
        extra.append(label)
        if len(hex_card_stat_labels) + len(extra) >= SHARE_SUMMARY_STORY_MAX_STATS:
            break
    hex_card_stat_labels = hex_card_stat_labels + tuple(extra)
hex_preview_scale = min(scale, 0.32)

with tab_social_cards:
    if not use_sample and not _period_has_checklist_data(stats):
        st.warning(
            f"No checklists in **{stats.period_label}** in this export. "
            "Try **Previous month** (or another range) in the sidebar, or pick a period that includes your data."
        )

    _current_card_fragment(
        stats=stats,
        all_time=all_time,
        selected_layout=selected_layout,
        fmt=fmt,
        scale=scale,
        status_metrics=status_metrics,
        color_scheme_index=color_scheme_index,
        card_stat_data_scope=card_stat_data_scope,
        scope_label=scope_label,
        geo_scope=geo_scope,
        tiles_style=tiles_style,
        spotlight_style=spotlight_style,
    )

_DESIGN_HEX_SELECTED_KEY = "design_hex_selected_variant"

with tab_hex_experiments:
    st.markdown(
        "Uniform **hexicons** for the Statistics Grid. **Organic hive** samples (bottom half) "
        "use edge-to-edge tessellation in irregular, jagged clusters — like a natural honeycomb "
        "blob, not balanced rows or a dashboard grid. Legacy overlapping-row samples are kept "
        "for comparison only."
    )
    if _DESIGN_HEX_SELECTED_KEY not in st.session_state:
        st.session_state[_DESIGN_HEX_SELECTED_KEY] = HEX_VARIANT_IDS[0]
    selected_hex: HexVariantId = st.selectbox(
        "Enlarged preview",
        options=HEX_VARIANT_IDS,
        format_func=lambda v: HEX_VARIANT_LABELS[v],
        key=_DESIGN_HEX_SELECTED_KEY,
    )
    hex_cols = st.columns(2)
    for i, variant in enumerate(HEX_VARIANT_IDS):
        with hex_cols[i % 2]:
            title = HEX_VARIANT_LABELS[variant]
            if variant == selected_hex:
                title = f"{title} · selected"
            st.markdown(f"**{title}**")
            st.markdown(
                render_hex_grid_preview_html(
                    stats,
                    variant=variant,
                    fmt=fmt,
                    scale=hex_preview_scale,
                    card_stat_labels=hex_card_stat_labels,
                    all_time=all_time,
                    color_scheme_index=color_scheme_index,
                    geo_scope=geo_scope,
                    scope_label=scope_label,
                ),
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("Selected preview (larger)")
    st.caption(
        f"{HEX_VARIANT_LABELS[selected_hex]} — use **Preview scale** in the sidebar "
        f"(currently {scale:.0%} of export size)."
    )
    st.markdown(
        render_hex_grid_preview_html(
            stats,
            variant=selected_hex,
            fmt=fmt,
            scale=scale,
            card_stat_labels=hex_card_stat_labels,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            geo_scope=geo_scope,
            scope_label=scope_label,
        ),
        unsafe_allow_html=True,
    )
