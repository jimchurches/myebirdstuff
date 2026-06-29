"""
Rough drag-and-drop playground for tuning circle card layouts (#275).

Self-contained HTML for ``st.iframe`` in the design studio. Supports Statistics Tiles
and Spotlight circle presentations at square, portrait, and story sizes.
"""

from __future__ import annotations

import html
import json
from typing import Any, Literal

from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEMES,
    SHARE_SUMMARY_LAYOUT_LABELS,
)
from explorer.presentation.share_summary_circles_preview import (
    _HAND_TUNED_CIRCLE_MAX_DIAMETER_PX,
    CIRCLE_VARIANT_SPECS,
    SPOTLIGHT_CIRCLE_LABEL_PX,
    TILES_CIRCLE_CLUSTER_DEFAULT,
    TILES_CIRCLE_CLUSTER_VARIANT,
    TILES_CIRCLE_DIAMETER_SEARCH_START,
    _circle_canvas_size,
    _hand_tuned_body_bounds,
    _hand_tuned_template_diameter,
    _spotlight_circle_diameter,
    _spotlight_circle_max_fit_diameter,
    _tiles_circle_body_insets,
    _tiles_circle_canvas_size,
    circle_card_template,
    circle_card_template_diameters,
    circle_card_template_positions,
    hand_tuned_circle_typography_px,
    place_circle_centers,
    tiles_circle_cluster_max,
)
from explorer.presentation.share_summary_preview import (
    FORMAT_LABELS,
    FORMAT_PIXELS,
    FormatId,
)

PlaygroundCardType = Literal["tiles", "spotlight"]
PLAYGROUND_CARD_TYPES: tuple[PlaygroundCardType, ...] = ("tiles", "spotlight")
PLAYGROUND_CARD_LABELS: dict[PlaygroundCardType, str] = {
    card_type: SHARE_SUMMARY_LAYOUT_LABELS[card_type]
    for card_type in PLAYGROUND_CARD_TYPES
}
PLAYGROUND_FORMATS: tuple[FormatId, ...] = ("square", "portrait_post", "story")

PLAYGROUND_SAMPLE_STATS: tuple[tuple[str, str], ...] = (
    ("287", "Total species"),
    ("6", "Lifers"),
    ("854", "Total checklists"),
    ("766", "Unique locations"),
    ("82", "Birding days"),
    ("1", "Countries"),
    ("215", "Families in eBird taxonomy"),
    ("329", "Completed checklists"),
    ("2.6%", "Observed species (%)"),
    ("65,064", "Total individuals"),
)
SPOTLIGHT_SAMPLE_STAT: tuple[str, str] = ("6", "Lifers")

_STORY_TOP_CLEARANCE = 20
_STORY_BOTTOM_CLEARANCE = 52
_SHADOW_PAD = 12
_CLUSTER_UP_BIAS = 0.07
_MIN_CLUSTER_DIAMETER = 96
_MIN_SPOTLIGHT_DIAMETER = 200
_TILES_CIRCLE_VALUE_FONT_MIN = 32
_TILES_CIRCLE_VALUE_FONT_MAX = 200
_TILES_CIRCLE_LABEL_FONT_MIN = 14
_TILES_CIRCLE_LABEL_FONT_MAX = 36

PLAYGROUND_TILES_MIN_COUNT = 1
PLAYGROUND_TILES_DEFAULT_COUNT = TILES_CIRCLE_CLUSTER_DEFAULT

CIRCLE_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX = 1000


def _playground_scheme() -> dict[str, str]:
    return SHARE_SUMMARY_COLOR_SCHEMES[0]


def _card_frame(fmt: FormatId) -> dict[str, int]:
    card_w, card_h = FORMAT_PIXELS[fmt]
    if fmt == "story":
        header_reserve, footer_reserve = 200, 210
    else:
        header_reserve, footer_reserve = 192, 178
    return {
        "card_w": card_w,
        "card_h": card_h,
        "header_reserve": header_reserve,
        "footer_reserve": footer_reserve,
        "side_pad": 48,
    }


def _cluster_norm_positions(
    centres: list[tuple[float, float]],
    canvas_w: int,
    canvas_h: int,
    *,
    diameter: int,
) -> list[list[float]]:
    pad = diameter / 2 + _SHADOW_PAD
    x_min, x_max = pad, canvas_w - pad
    y_min, y_max = pad, canvas_h - pad
    span_x = max(1e-6, x_max - x_min)
    span_y = max(1e-6, y_max - y_min)
    return [
        [round((x - x_min) / span_x, 4), round((y - y_min) / span_y, 4)]
        for x, y in centres
    ]


def _algorithmic_layout(
    count: int,
    canvas_w: int,
    canvas_h: int,
    *,
    variant: str,
    diameter_start: int,
) -> tuple[list[list[float]], int]:
    centres, diameter = place_circle_centers(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter_start,
        variant=variant,  # type: ignore[arg-type]
    )
    norms = _cluster_norm_positions(
        centres,
        canvas_w,
        canvas_h,
        diameter=diameter,
    )
    return norms, diameter


def _spotlight_center_norm(canvas_w: int, canvas_h: int, *, diameter: int) -> list[float]:
    pad = diameter / 2 + _SHADOW_PAD
    cx = canvas_w / 2
    cy = canvas_h / 2 - canvas_h * _CLUSTER_UP_BIAS
    span_x = max(1e-6, canvas_w - 2 * pad)
    span_y = max(1e-6, canvas_h - 2 * pad)
    return [round((cx - pad) / span_x, 4), round((cy - pad) / span_y, 4)]



def _template_diameters_payload(template) -> dict[str, int]:
    return {str(count): diameter for count, diameter in circle_card_template_diameters(template).items()}


def _template_auto_diameters(template, canvas_w: int, canvas_h: int) -> dict[str, int]:
    gap_px = CIRCLE_VARIANT_SPECS[TILES_CIRCLE_CLUSTER_VARIANT].gap_px
    return {
        str(count): _hand_tuned_template_diameter(
            template,
            count,
            canvas_w,
            canvas_h,
            gap_px=gap_px,
        )
        for count in template.counts
    }


def _cluster_layouts_for_counts(
    canvas_w: int,
    canvas_h: int,
    *,
    counts: range,
    variant: str,
    diameter_start: int,
) -> dict[str, list[list[float]]]:
    out: dict[str, list[list[float]]] = {}
    for count in counts:
        norms, _ = _algorithmic_layout(
            count,
            canvas_w,
            canvas_h,
            variant=variant,
            diameter_start=diameter_start,
        )
        out[str(count)] = norms
    return out


def _cluster_auto_diameters(
    canvas_w: int,
    canvas_h: int,
    *,
    counts: range,
    variant: str,
    diameter_start: int,
) -> dict[str, int]:
    out: dict[str, int] = {}
    for count in counts:
        _, diameter = _algorithmic_layout(
            count,
            canvas_w,
            canvas_h,
            variant=variant,
            diameter_start=diameter_start,
        )
        out[str(count)] = diameter
    return out


def _playground_body_frame(
    card_type: PlaygroundCardType,
    fmt: FormatId,
) -> dict[str, int]:
    if card_type == "tiles" and fmt != "story":
        top, bottom, left, right = _tiles_circle_body_insets(fmt, scope_label="World")
        return {
            "body_top": top,
            "body_bottom": bottom,
            "body_left": left,
            "body_right": right,
        }
    return {}


def _tiles_playground_max_count(fmt: FormatId) -> int:
    return tiles_circle_cluster_max(fmt)


def _tiles_playground_count_range(fmt: FormatId) -> range:
    return range(PLAYGROUND_TILES_MIN_COUNT, _tiles_playground_max_count(fmt) + 1)


def _tiles_circle_typography_config() -> dict[str, int]:
    """Slider ranges for circle typography tuning in the playground."""
    return {
        "min_value_font_px": _TILES_CIRCLE_VALUE_FONT_MIN,
        "max_value_font_px": _TILES_CIRCLE_VALUE_FONT_MAX,
        "min_label_font_px": _TILES_CIRCLE_LABEL_FONT_MIN,
        "max_label_font_px": _TILES_CIRCLE_LABEL_FONT_MAX,
    }


def _spotlight_playground_value_font_px(fmt: FormatId, diameter: int) -> int:
    """Match production spotlight circle value sizing."""
    card_w, card_h = FORMAT_PIXELS[fmt]
    classic = 200 if card_h > card_w else 160
    inner_w = max(68, diameter - 44)
    max_by_width = int(inner_w / 0.58)
    return min(classic, max_by_width)


def _typography_defaults_for_count(
    count: int,
    diameter: int,
    *,
    bounds: str,
    fmt: FormatId,
) -> dict[str, int]:
    """Match production tier defaults in share_summary_circles_preview."""
    tuned = hand_tuned_circle_typography_px(fmt, count)
    if tuned is not None:
        value_px, label_px = tuned
        return {"value_font_px": value_px, "label_font_px": label_px}
    compact_threshold = 10 if bounds == "story" else 7
    if count >= compact_threshold:
        value_px, label_px = 40, 16
    elif diameter >= 260:
        value_px, label_px = 52, 19
    elif diameter >= 240:
        value_px, label_px = 46, 17
    else:
        value_px, label_px = 48, 18
    return {"value_font_px": value_px, "label_font_px": label_px}


def _build_tiles_playground_mode(
    frame: dict[str, int],
    fmt: FormatId,
    export_meta: dict[str, str],
) -> dict[str, Any]:
    """Playground config for Statistics Tiles circles — counts 1–10, default six."""
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        frame["card_w"],
        frame["card_h"],
        fmt,
        scope_label="World",
    )
    counts = _tiles_playground_count_range(fmt)
    variant = TILES_CIRCLE_CLUSTER_VARIANT
    diameter_start = TILES_CIRCLE_DIAMETER_SEARCH_START

    layouts = _cluster_layouts_for_counts(
        canvas_w,
        canvas_h,
        counts=counts,
        variant=variant,
        diameter_start=diameter_start,
    )
    auto_diameters = _cluster_auto_diameters(
        canvas_w,
        canvas_h,
        counts=counts,
        variant=variant,
        diameter_start=diameter_start,
    )

    template = circle_card_template("tiles", fmt)
    bounds = "cluster"
    diameters: dict[str, int] = {}
    code_presets = False

    if template is not None:
        bounds = template.bounds
        allowed_counts = set(counts)
        for count, positions in circle_card_template_positions(template).items():
            if count not in allowed_counts:
                continue
            layouts[str(count)] = [[x, y] for x, y in positions]
        diameters = {
            count: diameter
            for count, diameter in _template_diameters_payload(template).items()
            if int(count) in allowed_counts
        }
        for count_str, diameter in _template_auto_diameters(template, canvas_w, canvas_h).items():
            if int(count_str) not in allowed_counts:
                continue
            auto_diameters[count_str] = diameter
        for count_str, diameter in diameters.items():
            auto_diameters[count_str] = diameter
        code_presets = True

    default_count = PLAYGROUND_TILES_DEFAULT_COUNT
    max_count = _tiles_playground_max_count(fmt)
    mode: dict[str, Any] = {
        **frame,
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "bounds": bounds,
        "draggable": True,
        "min_count": PLAYGROUND_TILES_MIN_COUNT,
        "max_count": max_count,
        "default_count": default_count,
        "min_diameter": _MIN_CLUSTER_DIAMETER,
        "max_diameter": _HAND_TUNED_CIRCLE_MAX_DIAMETER_PX,
        "default_diameter": diameters.get(
            str(default_count),
            auto_diameters[str(default_count)],
        ),
        "layouts": layouts,
        "diameters": diameters,
        "auto_diameters": auto_diameters,
        "code_presets": code_presets,
        "circle_typography": _tiles_circle_typography_config(),
        "typography_defaults": {
            str(count): _typography_defaults_for_count(
                count,
                diameters.get(str(count), auto_diameters[str(count)]),
                bounds=bounds,
                fmt=fmt,
            )
            for count in counts
        },
        **_playground_body_frame("tiles", fmt),
        **export_meta,
    }
    if bounds == "story":
        mode["top_clearance"] = _STORY_TOP_CLEARANCE
        mode["bottom_clearance"] = _STORY_BOTTOM_CLEARANCE
    return mode


def _export_meta(card_type: PlaygroundCardType, fmt: FormatId) -> dict[str, str]:
    if card_type == "tiles":
        template = circle_card_template("tiles", fmt)
        if template is not None:
            target = f'CIRCLE_CARD_TEMPLATES[("tiles", "{fmt}")]'
        else:
            target = "tiles circle cluster (algorithm today — add CIRCLE_CARD_TEMPLATES entry)"
        presentation_key = "tiles_presentation"
    else:
        target = "_SINGLE_CIRCLE_DIAMETER_PX"
        presentation_key = "spotlight_presentation"
    return {
        "layout_id": card_type,
        "layout_label": PLAYGROUND_CARD_LABELS[card_type],
        "format_id": fmt,
        "format_label": FORMAT_LABELS[fmt],
        "presentation": "circles",
        "presentation_key": presentation_key,
        "target_code": target,
    }


def _build_mode_config(card_type: PlaygroundCardType, fmt: FormatId) -> dict[str, Any]:
    frame = _card_frame(fmt)
    export_meta = _export_meta(card_type, fmt)
    if card_type == "spotlight":
        canvas_w, canvas_h = _circle_canvas_size(
            frame["card_w"],
            frame["card_h"],
            fmt,
            scope_label="World",
        )
        diameter = _spotlight_circle_diameter(canvas_w, canvas_h, fmt=fmt)
        center_norm = _spotlight_center_norm(canvas_w, canvas_h, diameter=diameter)
        max_diameter = min(
            _HAND_TUNED_CIRCLE_MAX_DIAMETER_PX,
            _spotlight_circle_max_fit_diameter(canvas_w, canvas_h),
        )
        return {
            **frame,
            "canvas_w": canvas_w,
            "canvas_h": canvas_h,
            "bounds": "cluster",
            "draggable": False,
            "min_count": 1,
            "max_count": 1,
            "default_count": 1,
            "min_diameter": _MIN_SPOTLIGHT_DIAMETER,
            "max_diameter": max_diameter,
            "default_diameter": diameter,
            "layouts": {"1": [center_norm]},
            "diameters": {},
            "auto_diameters": {"1": diameter},
            "center_norm": center_norm,
            "code_presets": False,
            "circle_typography": _tiles_circle_typography_config(),
            "typography_defaults": {
                "1": {
                    "value_font_px": _spotlight_playground_value_font_px(fmt, diameter),
                    "label_font_px": SPOTLIGHT_CIRCLE_LABEL_PX,
                }
            },
            **export_meta,
        }

    return _build_tiles_playground_mode(frame, fmt, export_meta)


def _modes_payload() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        card_type: {fmt: _build_mode_config(card_type, fmt) for fmt in PLAYGROUND_FORMATS}
        for card_type in PLAYGROUND_CARD_TYPES
    }


def render_circle_layout_playground_html(
    *,
    initial_card_type: PlaygroundCardType = "tiles",
    initial_fmt: FormatId = "story",
) -> str:
    """Full HTML document for the circle layout playground iframe."""
    scheme = _playground_scheme()
    modes = _modes_payload()
    start = modes[initial_card_type][initial_fmt]
    config: dict[str, Any] = {
        "card_type": initial_card_type,
        "fmt": initial_fmt,
        "modes": modes,
        "card_types": [
            {"id": card_type, "label": PLAYGROUND_CARD_LABELS[card_type]}
            for card_type in PLAYGROUND_CARD_TYPES
        ],
        "formats": [
            {"id": fmt, "label": FORMAT_LABELS[fmt]} for fmt in PLAYGROUND_FORMATS
        ],
        "stats": list(PLAYGROUND_SAMPLE_STATS),
        "spotlight_stat": list(SPOTLIGHT_SAMPLE_STAT),
        "shadow_pad": _SHADOW_PAD,
        "colors": scheme,
        "count": start["default_count"],
        "diameter": start["default_diameter"],
    }
    config_json = json.dumps(config)
    title = html.escape("Circle layout playground")

    card_type_options = "".join(
        f'<option value="{card_type}"'
        f'{" selected" if card_type == initial_card_type else ""}>'
        f"{html.escape(PLAYGROUND_CARD_LABELS[card_type])}</option>"
        for card_type in PLAYGROUND_CARD_TYPES
    )
    format_options = "".join(
        f'<option value="{fmt}"{" selected" if fmt == initial_fmt else ""}>'
        f"{html.escape(FORMAT_LABELS[fmt])}</option>"
        for fmt in PLAYGROUND_FORMATS
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 12px 14px 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    color: {scheme["text"]};
    background: {scheme["bg_alt"]};
  }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px 18px;
    align-items: flex-end;
    margin-bottom: 12px;
    padding: 10px 12px;
    border: 1px solid {scheme["border"]};
    border-radius: 10px;
    background: {scheme["bg"]};
  }}
  .toolbar label {{
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: {scheme["muted"]};
  }}
  .toolbar input[type="range"] {{ width: 140px; }}
  .toolbar input[type="number"] {{
    width: 64px;
    padding: 4px 6px;
    border: 1px solid {scheme["border"]};
    border-radius: 6px;
  }}
  .toolbar button, .toolbar select {{
    padding: 7px 10px;
    border: 1px solid {scheme["border"]};
    border-radius: 8px;
    background: {scheme["bg_alt"]};
    color: {scheme["text"]};
    font-size: 13px;
  }}
  .toolbar button {{ cursor: pointer; }}
  .toolbar button:hover {{ border-color: {scheme["accent"]}; }}
  .hint {{
    margin: 0 0 10px;
    font-size: 12px;
    color: {scheme["muted"]};
    line-height: 1.45;
  }}
  .stage-wrap {{ overflow: auto; padding: 8px 0 12px; }}
  .card-shell {{ transform-origin: top left; }}
  .card {{
    position: relative;
    overflow: hidden;
    background: {scheme["bg"]};
    color: {scheme["text"]};
    border: 1px solid {scheme["border"]};
    box-shadow: 0 10px 28px rgba(0,0,0,0.08);
  }}
  .card-header {{ padding: 48px 56px 24px; text-align: center; }}
  .card-header .subtitle {{
    margin: 0 0 8px; font-size: 28px; letter-spacing: 0.08em;
    text-transform: uppercase; color: {scheme["accent"]}; font-weight: 600;
  }}
  .card-header .title {{
    margin: 0; font-size: 72px; font-weight: 700; line-height: 1.08;
  }}
  .card-body-wrap {{ padding: 0 48px; display: flex; justify-content: center; }}
  .card-body-wrap.absolute-body {{
    position: absolute;
    padding: 0;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    overflow: hidden;
  }}
  .card-body {{
    position: relative;
    background: repeating-linear-gradient(
      -45deg, transparent, transparent 11px,
      rgba(45,106,79,0.03) 11px, rgba(45,106,79,0.03) 22px
    );
    border: 1px dashed {scheme["border"]};
    touch-action: none;
  }}
  .card-footer {{
    position: absolute; left: 0; right: 0; bottom: 0;
    padding: 22px 56px 26px; text-align: center;
    border-top: 1px solid {scheme["border"]};
    background: {scheme["bg_alt"]}; color: {scheme["muted"]};
  }}
  .card-footer .scope {{ margin: 0 0 7px; font-size: 36px; font-weight: 600; letter-spacing: 0.04em; }}
  .card-footer .brand {{ margin: 5px 0 0; font-size: 18px; }}
  .circle {{
    position: absolute; transform: translate(-50%, -50%);
    user-select: none; touch-action: none;
  }}
  .circle.draggable {{ cursor: grab; }}
  .circle.draggable.dragging {{ cursor: grabbing; z-index: 20; }}
  .circle.locked {{ cursor: default; }}
  .circle-inner {{
    border-radius: 50%;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    text-align: center; padding: 16px;
    box-shadow: 0 8px 18px rgba(0,0,0,0.12);
    border: 2px solid {scheme["border"]};
    background: linear-gradient(145deg, {scheme["bg_alt"]}, {scheme["bg"]});
  }}
  .circle-value {{ font-weight: 700; line-height: 1; white-space: nowrap; letter-spacing: -0.02em; }}
  .circle-label {{ margin-top: 6px; color: {scheme["muted"]}; line-height: 1.12; }}
  .output {{
    margin-top: 8px; padding: 10px 12px;
    border: 1px solid {scheme["border"]}; border-radius: 10px; background: {scheme["bg"]};
  }}
  .output h3 {{ margin: 0 0 6px; font-size: 13px; }}
  .output pre {{
    margin: 0; white-space: pre-wrap; word-break: break-word;
    font-size: 12px; line-height: 1.45;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  .meta {{ margin-top: 6px; font-size: 11px; color: {scheme["muted"]}; }}
  .hidden {{ display: none; }}
</style>
</head>
<body>
  <p class="hint">
    Dev tuner for circle presentations. Drag to reposition (except Spotlight — centred).
    For Statistics Tiles and Spotlight, use the value/label font sliders to tune typography
    before copying sizes into <code>share_summary_circles_preview.py</code>.
  </p>
  <div class="toolbar">
    <label>Layout
      <select id="card-type">{card_type_options}</select>
    </label>
    <label>Format
      <select id="format">{format_options}</select>
    </label>
    <label id="count-wrap">Circle count
      <input type="number" id="count" min="1" max="10" value="{start["default_count"]}"/>
    </label>
    <label>Diameter <span id="diameter-val">{start["default_diameter"]}</span>px
      <input type="range" id="diameter" min="{start["min_diameter"]}" max="{start["max_diameter"]}"
        value="{start["default_diameter"]}"/>
    </label>
    <label id="preset-wrap"{" class=\"hidden\"" if not start["code_presets"] else ""}>Preset
      <select id="preset">
        <option value="">Load code preset…</option>
      </select>
    </label>
    <label id="value-font-wrap" class="hidden">Value font <span id="value-font-val">48</span>px
      <input type="range" id="value-font" min="{_TILES_CIRCLE_VALUE_FONT_MIN}"
        max="{_TILES_CIRCLE_VALUE_FONT_MAX}" value="48"/>
    </label>
    <label id="label-font-wrap" class="hidden">Label font <span id="label-font-val">18</span>px
      <input type="range" id="label-font" min="{_TILES_CIRCLE_LABEL_FONT_MIN}"
        max="{_TILES_CIRCLE_LABEL_FONT_MAX}" value="18"/>
    </label>
    <button type="button" id="reset-btn">Reset layout</button>
    <button type="button" id="copy-btn">Copy export</button>
  </div>
  <div class="stage-wrap">
    <div class="card-shell" id="card-shell">
      <div class="card" id="card">
        <div class="card-header">
          <p class="subtitle">MY BIRDING STATS</p>
          <p class="title">2026</p>
        </div>
        <div class="card-body-wrap" id="body-wrap">
          <div class="card-body" id="body"></div>
        </div>
        <div class="card-footer">
          <p class="scope">World</p>
          <p class="brand">Personal eBird Explorer</p>
        </div>
      </div>
    </div>
  </div>
  <div class="output">
    <h3>Layout export</h3>
    <pre id="export-text"></pre>
    <p class="meta" id="meta-text"></p>
  </div>
<script>
(() => {{
  const CFG = {config_json};
  const body = document.getElementById("body");
  const bodyWrap = document.getElementById("body-wrap");
  const card = document.getElementById("card");
  const cardShell = document.getElementById("card-shell");
  const cardTypeSelect = document.getElementById("card-type");
  const formatSelect = document.getElementById("format");
  const countInput = document.getElementById("count");
  const countWrap = document.getElementById("count-wrap");
  const diameterInput = document.getElementById("diameter");
  const diameterVal = document.getElementById("diameter-val");
  const presetWrap = document.getElementById("preset-wrap");
  const presetSelect = document.getElementById("preset");
  const valueFontWrap = document.getElementById("value-font-wrap");
  const valueFontInput = document.getElementById("value-font");
  const valueFontVal = document.getElementById("value-font-val");
  const labelFontWrap = document.getElementById("label-font-wrap");
  const labelFontInput = document.getElementById("label-font");
  const labelFontVal = document.getElementById("label-font-val");
  const exportText = document.getElementById("export-text");
  const metaText = document.getElementById("meta-text");

  const FORMAT_LABELS = Object.fromEntries(CFG.formats.map((f) => [f.id, f.label]));
  const CARD_LABELS = Object.fromEntries(CFG.card_types.map((c) => [c.id, c.label]));

  let cardType = CFG.card_type;
  let fmt = CFG.fmt;
  let count = CFG.count;
  let diameter = CFG.diameter;
  let valueFontBasePx = 48;
  let labelFontPxNum = 18;
  let norms = [];
  let drag = null;
  let applyingDefaults = false;
  const sessionEdits = new Map();

  function circleTypography() {{
    return mode().circle_typography || null;
  }}

  function usesCircleFontSliders() {{
    return (cardType === "tiles" || cardType === "spotlight") && circleTypography() !== null;
  }}

  function defaultTypographyForCount(n) {{
    const defaults = mode().typography_defaults[String(n)];
    if (defaults) {{
      return {{
        valueFontPx: defaults.value_font_px,
        labelFontPx: defaults.label_font_px,
      }};
    }}
    return {{ valueFontPx: 48, labelFontPx: 18 }};
  }}

  function applyCircleTypographyWithoutSessionSave(valuePx, labelPx) {{
    applyingDefaults = true;
    setCircleTypography(valuePx, labelPx);
    applyingDefaults = false;
  }}

  function setCircleTypography(valuePx, labelPx) {{
    const t = circleTypography();
    if (!t) return;
    valueFontBasePx = clamp(valuePx, t.min_value_font_px, t.max_value_font_px);
    labelFontPxNum = clamp(labelPx, t.min_label_font_px, t.max_label_font_px);
    valueFontInput.min = String(t.min_value_font_px);
    valueFontInput.max = String(t.max_value_font_px);
    valueFontInput.value = String(valueFontBasePx);
    valueFontVal.textContent = String(valueFontBasePx);
    labelFontInput.min = String(t.min_label_font_px);
    labelFontInput.max = String(t.max_label_font_px);
    labelFontInput.value = String(labelFontPxNum);
    labelFontVal.textContent = String(labelFontPxNum);
    renderCircles();
  }}

  function layoutKeyFor(ct, format, n) {{
    const slots = ct === "spotlight" ? 1 : n;
    return ct + "|" + format + "|" + slots;
  }}

  function layoutKey() {{
    return layoutKeyFor(cardType, fmt, count);
  }}

  function codeDefaults(n) {{
    const defaults = {{
      norms: cloneNorms(layoutForCount(n)),
      diameter: presetDiameter(n),
    }};
    if (cardType === "tiles" || cardType === "spotlight") {{
      const typography = defaultTypographyForCount(n);
      defaults.valueFontPx = typography.valueFontPx;
      defaults.labelFontPx = typography.labelFontPx;
    }}
    return defaults;
  }}

  function cloneNorms(source) {{
    return source.map((p) => [p[0], p[1]]);
  }}

  function applyDiameterWithoutSessionSave(d) {{
    applyingDefaults = true;
    setDiameter(d);
    applyingDefaults = false;
  }}

  function saveSessionEdit() {{
    const edit = {{
      norms: cloneNorms(norms),
      diameter,
    }};
    if (usesCircleFontSliders()) {{
      edit.valueFontPx = valueFontBasePx;
      edit.labelFontPx = labelFontPxNum;
    }}
    sessionEdits.set(layoutKey(), edit);
  }}

  function clearSessionEdit(key) {{
    sessionEdits.delete(key);
  }}

  function clamp(n, lo, hi) {{ return Math.min(hi, Math.max(lo, n)); }}

  function mode() {{ return CFG.modes[cardType][fmt]; }}

  function displayScale(m) {{
    return Math.min(720 / m.card_h, 460 / m.card_w, 0.55);
  }}

  function bodyBounds() {{
    const m = mode();
    const pad = diameter / 2 + CFG.shadow_pad;
    if (m.bounds === "story") {{
      return {{
        xMin: pad,
        xMax: m.canvas_w - pad,
        yMin: m.top_clearance / 2 + pad,
        yMax: m.canvas_h - m.bottom_clearance - CFG.shadow_pad - pad,
      }};
    }}
    return {{ xMin: pad, xMax: m.canvas_w - pad, yMin: pad, yMax: m.canvas_h - pad }};
  }}

  function normToPixel(nx, ny) {{
    const b = bodyBounds();
    return {{
      x: b.xMin + nx * (b.xMax - b.xMin),
      y: b.yMin + ny * (b.yMax - b.yMin),
    }};
  }}

  function pixelToNorm(x, y) {{
    const b = bodyBounds();
    const spanX = Math.max(1e-6, b.xMax - b.xMin);
    const spanY = Math.max(1e-6, b.yMax - b.yMin);
    return {{
      nx: clamp((x - b.xMin) / spanX, 0, 1),
      ny: clamp((y - b.yMin) / spanY, 0, 1),
    }};
  }}

  function valueFontPx(value, basePx) {{
    const len = String(value).length;
    let px = basePx;
    if (len > 8) px -= 10;
    else if (len > 6) px -= 6;
    else if (len > 4) px -= 2;
    return Math.max(22, px);
  }}

  function labelFontPx() {{
    if (usesCircleFontSliders()) return labelFontPxNum + "px";
    return count > 6 ? "16px" : "18px";
  }}

  function valueFontBase() {{
    if (usesCircleFontSliders()) return valueFontBasePx;
    if (count > 9) return 40;
    if (diameter >= 260) return 52;
    if (diameter >= 240) return 46;
    return count > 6 ? 40 : 48;
  }}

  function layoutForCount(n) {{
    const m = mode();
    const preset = m.layouts[String(n)];
    if (preset && preset.length === n) {{
      return preset.map((p) => [p[0], p[1]]);
    }}
    const out = [];
    for (let i = 0; i < n; i += 1) {{
      const t = n <= 1 ? 0.5 : i / (n - 1);
      out.push([0.18 + 0.64 * (i % 2 === 0 ? 0.35 : 0.85), 0.12 + 0.78 * t]);
    }}
    return out;
  }}

  function presetDiameter(n) {{
    const m = mode();
    const fixed = m.diameters[String(n)];
    if (fixed) return fixed;
    const auto = m.auto_diameters[String(n)];
    if (auto) return auto;
    return diameter;
  }}

  function refreshPresetOptions() {{
    const m = mode();
    presetSelect.innerHTML = '<option value="">Load code preset…</option>';
    if (!m.code_presets) return;
    const counts = Object.keys(m.diameters).length
      ? Object.keys(m.diameters).map(Number).sort((a, b) => a - b)
      : Object.keys(m.layouts).map(Number).sort((a, b) => a - b);
    for (const n of counts) {{
      const opt = document.createElement("option");
      opt.value = String(n);
      opt.textContent = n + " circles (code)";
      presetSelect.appendChild(opt);
    }}
  }}

  function applyModeUi() {{
    const m = mode();
    countInput.min = String(m.min_count);
    countInput.max = String(m.max_count);
    diameterInput.min = String(m.min_diameter);
    diameterInput.max = String(m.max_diameter);
    countWrap.classList.toggle("hidden", cardType === "spotlight");
    presetWrap.classList.toggle("hidden", !m.code_presets);
    const showTypography = usesCircleFontSliders();
    valueFontWrap.classList.toggle("hidden", !showTypography);
    labelFontWrap.classList.toggle("hidden", !showTypography);
    refreshPresetOptions();
  }}

  function applyScale() {{
    const m = mode();
    const scale = displayScale(m);
    card.style.width = m.card_w + "px";
    card.style.height = m.card_h + "px";
    cardShell.style.transform = "scale(" + scale + ")";
    cardShell.style.width = (m.card_w * scale) + "px";
    cardShell.style.height = (m.card_h * scale) + "px";
    if (m.body_top != null) {{
      bodyWrap.classList.add("absolute-body");
      bodyWrap.style.top = m.body_top + "px";
      bodyWrap.style.bottom = m.body_bottom + "px";
      bodyWrap.style.left = m.body_left + "px";
      bodyWrap.style.right = m.body_right + "px";
    }} else {{
      bodyWrap.classList.remove("absolute-body");
      bodyWrap.style.top = "";
      bodyWrap.style.bottom = "";
      bodyWrap.style.left = "";
      bodyWrap.style.right = "";
    }}
    body.style.width = m.canvas_w + "px";
    body.style.height = m.canvas_h + "px";
  }}

  function circleStat(index) {{
    if (cardType === "spotlight") return CFG.spotlight_stat;
    return CFG.stats[index % CFG.stats.length];
  }}

  function renderCircles() {{
    body.innerHTML = "";
    const m = mode();
    const labelPx = labelFontPx();
    const baseVal = valueFontBase();
    const slots = cardType === "spotlight" ? 1 : count;
    for (let index = 0; index < slots; index += 1) {{
      const pair = cardType === "spotlight" ? m.center_norm : norms[index];
      const stat = circleStat(index);
      const pos = normToPixel(pair[0], pair[1]);
      const el = document.createElement("div");
      el.className = "circle" + (m.draggable ? " draggable" : " locked");
      el.dataset.index = String(index);
      el.style.left = pos.x + "px";
      el.style.top = pos.y + "px";
      const inner = document.createElement("div");
      inner.className = "circle-inner";
      inner.style.width = diameter + "px";
      inner.style.height = diameter + "px";
      const val = document.createElement("div");
      val.className = "circle-value";
      val.style.fontSize = valueFontPx(stat[0], baseVal) + "px";
      val.textContent = stat[0];
      const lab = document.createElement("div");
      lab.className = "circle-label";
      lab.style.fontSize = labelPx;
      lab.textContent = stat[1];
      inner.appendChild(val);
      inner.appendChild(lab);
      el.appendChild(inner);
      if (m.draggable) el.addEventListener("pointerdown", onPointerDown);
      body.appendChild(el);
    }}
    updateExport();
  }}

  function onPointerDown(event) {{
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);
    target.classList.add("dragging");
    const rect = body.getBoundingClientRect();
    const scale = displayScale(mode());
    const index = Number(target.dataset.index);
    const pair = norms[index];
    const pos = normToPixel(pair[0], pair[1]);
    drag = {{
      index,
      offsetX: (event.clientX - rect.left) / scale - pos.x,
      offsetY: (event.clientY - rect.top) / scale - pos.y,
      el: target,
      moved: false,
    }};
    event.preventDefault();
  }}

  function onPointerMove(event) {{
    if (!drag) return;
    const rect = body.getBoundingClientRect();
    const scale = displayScale(mode());
    const x = (event.clientX - rect.left) / scale - drag.offsetX;
    const y = (event.clientY - rect.top) / scale - drag.offsetY;
    const norm = pixelToNorm(x, y);
    norms[drag.index] = [norm.nx, norm.ny];
    drag.moved = true;
    drag.el.style.left = normToPixel(norm.nx, norm.ny).x + "px";
    drag.el.style.top = normToPixel(norm.nx, norm.ny).y + "px";
    updateExport();
  }}

  function onPointerUp(event) {{
    if (!drag) return;
    drag.el.classList.remove("dragging");
    drag.el.releasePointerCapture(event.pointerId);
    if (drag.moved) saveSessionEdit();
    drag = null;
  }}

  function formatExport() {{
    const m = mode();
    const lines = [
      "# Circle layout playground export",
      "# Implement this card design in share_summary_circles_preview.py",
      "",
      "card_type: " + cardType,
      "layout: " + m.layout_label,
      "format: " + fmt,
      "format_label: " + m.format_label,
      "card_px: " + m.card_w + "×" + m.card_h,
      "canvas_px: " + m.canvas_w + "×" + m.canvas_h,
      "presentation: circles",
      "presentation_key: " + m.presentation_key,
      "circle_count: " + (cardType === "spotlight" ? 1 : count),
      "positions: " + (m.draggable
        ? "draggable — normalised 0–1 within body bounds"
        : "fixed centre — canvas_w/2, canvas_h/2 − up_bias"),
      "target_code: " + m.target_code,
      "",
    ];
    if (cardType === "spotlight") {{
      lines.push("diameter_px: " + diameter + ",");
      lines.push("value_font_px: " + valueFontBasePx + ",");
      lines.push("label_font_px: " + labelFontPxNum + ",");
    }} else {{
      const posLines = norms.slice(0, count).map((p) =>
        "        (" + p[0].toFixed(2) + ", " + p[1].toFixed(2) + "),"
      );
      lines.push(count + ": (");
      lines.push(...posLines);
      lines.push("    ),");
      lines.push("diameter_px: " + diameter + ",");
      lines.push("value_font_px: " + valueFontBasePx + ",");
      lines.push("label_font_px: " + labelFontPxNum + ",");
    }}
    return lines.join("\\n");
  }}

  function updateExport() {{
    exportText.textContent = formatExport();
    const m = mode();
    const b = bodyBounds();
    metaText.textContent =
      CARD_LABELS[cardType] + " · " + FORMAT_LABELS[fmt] + " · " +
      "canvas " + m.canvas_w + "×" + m.canvas_h + "px · " +
      "card " + m.card_w + "×" + m.card_h + " · diameter " + diameter + "px · " +
      (usesCircleFontSliders()
        ? "value " + valueFontBasePx + "px · label " + labelFontPxNum + "px · "
        : "") +
      "body x=" + Math.round(b.xMin) + "–" + Math.round(b.xMax) +
      " y=" + Math.round(b.yMin) + "–" + Math.round(b.yMax);
  }}

  function loadLayoutState(n) {{
    const m = mode();
    const nextCount = clamp(n, m.min_count, m.max_count);
    const key = layoutKeyFor(cardType, fmt, nextCount);
    count = nextCount;
    countInput.value = String(count);

    const saved = sessionEdits.get(key);
    if (saved) {{
      norms = cloneNorms(saved.norms);
      applyDiameterWithoutSessionSave(saved.diameter);
      if (usesCircleFontSliders() && saved.valueFontPx != null) {{
        applyCircleTypographyWithoutSessionSave(
          saved.valueFontPx,
          saved.labelFontPx ?? defaultTypographyForCount(nextCount).labelFontPx,
        );
      }}
    }} else {{
      const defaults = codeDefaults(nextCount);
      norms = defaults.norms;
      applyDiameterWithoutSessionSave(defaults.diameter);
      if (usesCircleFontSliders()) {{
        applyCircleTypographyWithoutSessionSave(
          defaults.valueFontPx,
          defaults.labelFontPx,
        );
      }}
    }}
    applyModeUi();
  }}

  function setDiameter(d) {{
    const m = mode();
    diameter = clamp(d, m.min_diameter, m.max_diameter);
    diameterInput.value = String(diameter);
    diameterVal.textContent = String(diameter);
    renderCircles();
  }}

  function loadPreset(n) {{
    const preset = mode().layouts[String(n)];
    if (!preset) return;
    clearSessionEdit(layoutKeyFor(cardType, fmt, n));
    loadLayoutState(n);
  }}

  function activateMode() {{
    applyModeUi();
    applyScale();
    loadLayoutState(mode().default_count);
  }}

  cardTypeSelect.addEventListener("change", () => {{
    cardType = cardTypeSelect.value;
    activateMode();
  }});
  formatSelect.addEventListener("change", () => {{
    fmt = formatSelect.value;
    activateMode();
  }});
  countInput.addEventListener("change", () => loadLayoutState(Number(countInput.value)));
  diameterInput.addEventListener("input", () => {{
    setDiameter(Number(diameterInput.value));
    if (!applyingDefaults) saveSessionEdit();
  }});
  valueFontInput.addEventListener("input", () => {{
    setCircleTypography(Number(valueFontInput.value), labelFontPxNum);
    if (!applyingDefaults) saveSessionEdit();
  }});
  labelFontInput.addEventListener("input", () => {{
    setCircleTypography(valueFontBasePx, Number(labelFontInput.value));
    if (!applyingDefaults) saveSessionEdit();
  }});
  presetSelect.addEventListener("change", () => {{
    const val = presetSelect.value;
    if (val) loadPreset(Number(val));
    presetSelect.value = "";
  }});
  document.getElementById("reset-btn").addEventListener("click", () => {{
    clearSessionEdit(layoutKey());
    loadLayoutState(count);
  }});
  document.getElementById("copy-btn").addEventListener("click", async () => {{
    const text = formatExport();
    try {{
      await navigator.clipboard.writeText(text);
      document.getElementById("copy-btn").textContent = "Copied!";
      setTimeout(() => {{
        document.getElementById("copy-btn").textContent = "Copy export";
      }}, 1200);
    }} catch (err) {{
      window.prompt("Copy layout export:", text);
    }}
  }});

  document.addEventListener("pointermove", onPointerMove);
  document.addEventListener("pointerup", onPointerUp);
  document.addEventListener("pointercancel", onPointerUp);

  activateMode();
}})();
</script>
</body>
</html>"""


def story_circle_body_bounds_for_playground(
    canvas_w: int,
    canvas_h: int,
    *,
    diameter: int,
) -> tuple[float, float, float, float]:
    """Public wrapper for tests — matches story layout body bounds."""
    return _hand_tuned_body_bounds("story", canvas_w, canvas_h, diameter=diameter)


__all__ = [
    "CIRCLE_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX",
    "PLAYGROUND_CARD_LABELS",
    "PLAYGROUND_CARD_TYPES",
    "PLAYGROUND_FORMATS",
    "PLAYGROUND_SAMPLE_STATS",
    "SPOTLIGHT_SAMPLE_STAT",
    "PLAYGROUND_TILES_DEFAULT_COUNT",
    "PLAYGROUND_TILES_MIN_COUNT",
    "render_circle_layout_playground_html",
    "story_circle_body_bounds_for_playground",
]
