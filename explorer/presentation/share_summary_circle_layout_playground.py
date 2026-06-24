"""
Rough drag-and-drop playground for tuning story circle layouts (#275).

Self-contained HTML for ``st.iframe`` in the design studio. Normalised coordinates
match ``STORY_CIRCLE_LAYOUTS``; diameter exports match ``STORY_CIRCLE_LAYOUT_DIAMETERS``.
"""

from __future__ import annotations

import html
import json
from typing import Any

from explorer.core.share_summary_defaults import SHARE_SUMMARY_COLOR_SCHEMES
from explorer.presentation.share_summary_circles_preview import (
    STORY_CIRCLE_LAYOUT_DIAMETERS,
    STORY_CIRCLE_LAYOUTS,
    _story_circle_body_bounds,
    _story_circle_diameter,
    _tiles_circle_canvas_size,
)
from explorer.presentation.share_summary_preview import (
    FORMAT_LABELS,
    FORMAT_PIXELS,
    FormatId,
)

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

_STORY_TOP_CLEARANCE = 20
_STORY_BOTTOM_CLEARANCE = 52
_SHADOW_PAD = 12
_MIN_CIRCLE_DIAMETER = 96
_MAX_CIRCLE_DIAMETER = 340
_MIN_CIRCLE_COUNT = 6
_MAX_CIRCLE_COUNT = 10
_DISPLAY_SCALE = 0.38

CIRCLE_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX = 920


def _playground_scheme() -> dict[str, str]:
    return SHARE_SUMMARY_COLOR_SCHEMES[0]


def _story_card_layout(fmt: FormatId) -> dict[str, int]:
    width, height = FORMAT_PIXELS[fmt]
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        width,
        height,
        fmt,
        scope_label="World",
    )
    if fmt == "story":
        header_reserve = 200
        footer_reserve = 210
    else:
        header_reserve = 180
        footer_reserve = 160
    return {
        "card_w": width,
        "card_h": height,
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "header_reserve": header_reserve,
        "footer_reserve": footer_reserve,
        "side_pad": 48,
    }


def _layouts_payload() -> dict[str, list[list[float]]]:
    out: dict[str, list[list[float]]] = {}
    for count, positions in STORY_CIRCLE_LAYOUTS.items():
        out[str(count)] = [[x, y] for x, y in positions]
    return out


def _diameters_payload() -> dict[str, int]:
    return {str(count): diameter for count, diameter in STORY_CIRCLE_LAYOUT_DIAMETERS.items()}


def _auto_diameters_payload(canvas_w: int, canvas_h: int) -> dict[str, int]:
    return {
        str(count): _default_diameter(count, canvas_w, canvas_h)
        for count in STORY_CIRCLE_LAYOUTS
    }


def _default_diameter(count: int, canvas_w: int, canvas_h: int) -> int:
    gap_px = 18
    return _story_circle_diameter(count, canvas_w, canvas_h, gap_px=gap_px)


def render_circle_layout_playground_html(
    *,
    fmt: FormatId = "story",
    initial_count: int = 10,
    initial_diameter: int | None = None,
) -> str:
    """Full HTML document for the circle layout playground iframe."""
    layout = _story_card_layout(fmt)
    count = max(_MIN_CIRCLE_COUNT, min(initial_count, _MAX_CIRCLE_COUNT))
    diameter = initial_diameter
    if diameter is None:
        diameter = _default_diameter(count, layout["canvas_w"], layout["canvas_h"])
    diameter = max(_MIN_CIRCLE_DIAMETER, min(diameter, _MAX_CIRCLE_DIAMETER))

    scheme = _playground_scheme()
    config: dict[str, Any] = {
        "fmt": fmt,
        "fmt_label": FORMAT_LABELS.get(fmt, fmt),
        "count": count,
        "diameter": diameter,
        "min_count": _MIN_CIRCLE_COUNT,
        "max_count": _MAX_CIRCLE_COUNT,
        "min_diameter": _MIN_CIRCLE_DIAMETER,
        "max_diameter": _MAX_CIRCLE_DIAMETER,
        "display_scale": _DISPLAY_SCALE,
        "top_clearance": _STORY_TOP_CLEARANCE,
        "bottom_clearance": _STORY_BOTTOM_CLEARANCE,
        "shadow_pad": _SHADOW_PAD,
        "layouts": _layouts_payload(),
        "diameters": _diameters_payload(),
        "auto_diameters": _auto_diameters_payload(layout["canvas_w"], layout["canvas_h"]),
        "stats": list(PLAYGROUND_SAMPLE_STATS),
        "colors": scheme,
        **layout,
    }
    config_json = json.dumps(config)
    title = html.escape(f"Circle layout — {FORMAT_LABELS.get(fmt, fmt)}")

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
  .toolbar button {{
    padding: 7px 12px;
    border: 1px solid {scheme["border"]};
    border-radius: 8px;
    background: {scheme["bg_alt"]};
    color: {scheme["text"]};
    cursor: pointer;
    font-size: 13px;
  }}
  .toolbar button:hover {{ border-color: {scheme["accent"]}; }}
  .hint {{
    margin: 0 0 10px;
    font-size: 12px;
    color: {scheme["muted"]};
    line-height: 1.45;
  }}
  .stage-wrap {{
    overflow: auto;
    padding: 8px 0 12px;
  }}
  .card-shell {{
    transform-origin: top left;
  }}
  .card {{
    position: relative;
    overflow: hidden;
    background: {scheme["bg"]};
    color: {scheme["text"]};
    border: 1px solid {scheme["border"]};
    box-shadow: 0 10px 28px rgba(0,0,0,0.08);
  }}
  .card-header {{
    padding: 28px 48px 0;
    text-align: center;
  }}
  .card-header .subtitle {{
    margin: 0;
    font-size: 22px;
    letter-spacing: 0.06em;
    color: {scheme["accent"]};
    font-weight: 600;
  }}
  .card-header .title {{
    margin: 8px 0 0;
    font-size: 56px;
    font-weight: 800;
    line-height: 1.05;
  }}
  .card-body-wrap {{
    padding: 0 48px;
    display: flex;
    justify-content: center;
  }}
  .card-body {{
    position: relative;
    background: repeating-linear-gradient(
      -45deg,
      transparent,
      transparent 11px,
      rgba(45,106,79,0.03) 11px,
      rgba(45,106,79,0.03) 22px
    );
    border: 1px dashed {scheme["border"]};
    touch-action: none;
  }}
  .card-footer {{
    margin-top: 0;
    padding: 18px 24px 22px;
    text-align: center;
    border-top: 1px solid {scheme["border"]};
    background: {scheme["bg_alt"]};
    color: {scheme["muted"]};
  }}
  .card-footer .scope {{
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }}
  .card-footer .brand {{
    margin: 6px 0 0;
    font-size: 14px;
  }}
  .circle {{
    position: absolute;
    transform: translate(-50%, -50%);
    cursor: grab;
    user-select: none;
    touch-action: none;
  }}
  .circle.dragging {{
    cursor: grabbing;
    z-index: 20;
  }}
  .circle-inner {{
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 16px;
    box-shadow: 0 8px 18px rgba(0,0,0,0.12);
    border: 2px solid {scheme["border"]};
    background: linear-gradient(145deg, {scheme["bg_alt"]}, {scheme["bg"]});
  }}
  .circle-value {{
    font-weight: 700;
    line-height: 1;
    white-space: nowrap;
    letter-spacing: -0.02em;
  }}
  .circle-label {{
    margin-top: 6px;
    color: {scheme["muted"]};
    line-height: 1.12;
  }}
  .output {{
    margin-top: 8px;
    padding: 10px 12px;
    border: 1px solid {scheme["border"]};
    border-radius: 10px;
    background: {scheme["bg"]};
  }}
  .output h3 {{
    margin: 0 0 6px;
    font-size: 13px;
  }}
  .output pre {{
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    line-height: 1.45;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  .meta {{
    margin-top: 6px;
    font-size: 11px;
    color: {scheme["muted"]};
  }}
</style>
</head>
<body>
  <p class="hint">
    Drag circles on the story body canvas. Coordinates are normalised 0–1 for
    <code>STORY_CIRCLE_LAYOUTS</code>; copy includes <code>diameter_px</code> for
    <code>STORY_CIRCLE_LAYOUT_DIAMETERS</code>.
  </p>
  <div class="toolbar">
    <label>Circle count
      <input type="number" id="count" min="{_MIN_CIRCLE_COUNT}" max="{_MAX_CIRCLE_COUNT}" value="{count}"/>
    </label>
    <label>Diameter <span id="diameter-val">{diameter}</span>px
      <input type="range" id="diameter" min="{_MIN_CIRCLE_DIAMETER}" max="{_MAX_CIRCLE_DIAMETER}" value="{diameter}"/>
    </label>
    <label>Preset
      <select id="preset">
        <option value="">—</option>
        {"".join(f'<option value="{n}">{n} circles (code)</option>' for n in sorted(STORY_CIRCLE_LAYOUTS))}
      </select>
    </label>
    <button type="button" id="reset-btn">Reset preset</button>
    <button type="button" id="copy-btn">Copy Python tuple</button>
  </div>
  <div class="stage-wrap">
    <div class="card-shell" id="card-shell">
      <div class="card" id="card">
        <div class="card-header">
          <p class="subtitle">MY BIRDING STATS</p>
          <p class="title">2026</p>
        </div>
        <div class="card-body-wrap">
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
  const card = document.getElementById("card");
  const cardShell = document.getElementById("card-shell");
  const countInput = document.getElementById("count");
  const diameterInput = document.getElementById("diameter");
  const diameterVal = document.getElementById("diameter-val");
  const presetSelect = document.getElementById("preset");
  const exportText = document.getElementById("export-text");
  const metaText = document.getElementById("meta-text");

  let count = CFG.count;
  let diameter = CFG.diameter;
  let norms = [];
  let drag = null;

  function clamp(n, lo, hi) {{ return Math.min(hi, Math.max(lo, n)); }}

  function bodyBounds() {{
    const pad = diameter / 2 + CFG.shadow_pad;
    return {{
      xMin: pad,
      xMax: CFG.canvas_w - pad,
      yMin: CFG.top_clearance / 2 + pad,
      yMax: CFG.canvas_h - CFG.bottom_clearance - CFG.shadow_pad - pad,
    }};
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
    return count > 6 ? "16px" : "18px";
  }}

  function valueFontBase() {{
    if (count > 9) return 40;
    if (diameter >= 260) return 52;
    if (diameter >= 240) return 46;
    return count > 6 ? 40 : 48;
  }}

  function defaultNorms(n) {{
    const preset = CFG.layouts[String(n)];
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

  function applyScale() {{
    const scale = CFG.display_scale;
    card.style.width = CFG.card_w + "px";
    card.style.height = CFG.card_h + "px";
    cardShell.style.transform = "scale(" + scale + ")";
    cardShell.style.width = (CFG.card_w * scale) + "px";
    cardShell.style.height = (CFG.card_h * scale) + "px";
    body.style.width = CFG.canvas_w + "px";
    body.style.height = CFG.canvas_h + "px";
  }}

  function renderCircles() {{
    body.innerHTML = "";
    const labelPx = labelFontPx();
    const baseVal = valueFontBase();
    norms.slice(0, count).forEach((pair, index) => {{
      const stat = CFG.stats[index % CFG.stats.length];
      const pos = normToPixel(pair[0], pair[1]);
      const el = document.createElement("div");
      el.className = "circle";
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
      el.addEventListener("pointerdown", onPointerDown);
      body.appendChild(el);
    }});
    updateExport();
  }}

  function onPointerDown(event) {{
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);
    target.classList.add("dragging");
    const rect = body.getBoundingClientRect();
    const scale = CFG.display_scale;
    const index = Number(target.dataset.index);
    const pair = norms[index];
    const pos = normToPixel(pair[0], pair[1]);
    drag = {{
      index,
      offsetX: (event.clientX - rect.left) / scale - pos.x,
      offsetY: (event.clientY - rect.top) / scale - pos.y,
      el: target,
    }};
    event.preventDefault();
  }}

  function onPointerMove(event) {{
    if (!drag) return;
    const rect = body.getBoundingClientRect();
    const scale = CFG.display_scale;
    const x = (event.clientX - rect.left) / scale - drag.offsetX;
    const y = (event.clientY - rect.top) / scale - drag.offsetY;
    const norm = pixelToNorm(x, y);
    norms[drag.index] = [norm.nx, norm.ny];
    drag.el.style.left = normToPixel(norm.nx, norm.ny).x + "px";
    drag.el.style.top = normToPixel(norm.nx, norm.ny).y + "px";
    updateExport();
  }}

  function onPointerUp(event) {{
    if (!drag) return;
    drag.el.classList.remove("dragging");
    drag.el.releasePointerCapture(event.pointerId);
    drag = null;
  }}

  function formatTuple() {{
    const lines = norms.slice(0, count).map((p) =>
      "        (" + p[0].toFixed(2) + ", " + p[1].toFixed(2) + "),"
    );
    return count + ": (\\n" + lines.join("\\n") + "\\n    ),\\n" +
      "diameter_px: " + diameter + ",";
  }}

  function presetDiameter(n) {{
    const fixed = CFG.diameters[String(n)];
    if (fixed) return fixed;
    const auto = CFG.auto_diameters[String(n)];
    if (auto) return auto;
    return diameter;
  }}

  function updateExport() {{
    exportText.textContent = formatTuple();
    const b = bodyBounds();
    metaText.textContent =
      "Canvas " + CFG.canvas_w + "×" + CFG.canvas_h + "px · " +
      "card " + CFG.card_w + "×" + CFG.card_h + " · " +
      "diameter " + diameter + "px · " +
      "usable body x=" + Math.round(b.xMin) + "–" + Math.round(b.xMax) +
      " y=" + Math.round(b.yMin) + "–" + Math.round(b.yMax);
  }}

  function setCount(n) {{
    count = clamp(n, CFG.min_count, CFG.max_count);
    countInput.value = String(count);
    const next = norms.slice(0, count);
    if (next.length < count) {{
      const defaults = defaultNorms(count);
      for (let i = next.length; i < count; i += 1) {{
        next.push(defaults[i]);
      }}
    }}
    norms = next;
    renderCircles();
  }}

  function setDiameter(d) {{
    diameter = clamp(d, CFG.min_diameter, CFG.max_diameter);
    diameterInput.value = String(diameter);
    diameterVal.textContent = String(diameter);
    renderCircles();
  }}

  function loadPreset(n) {{
    const preset = CFG.layouts[String(n)];
    if (!preset) return;
    count = n;
    countInput.value = String(count);
    norms = preset.map((p) => [p[0], p[1]]);
    setDiameter(presetDiameter(n));
  }}

  countInput.addEventListener("change", () => setCount(Number(countInput.value)));
  diameterInput.addEventListener("input", () => setDiameter(Number(diameterInput.value)));
  presetSelect.addEventListener("change", () => {{
    const val = presetSelect.value;
    if (val) loadPreset(Number(val));
    presetSelect.value = "";
  }});
  document.getElementById("reset-btn").addEventListener("click", () => {{
    norms = defaultNorms(count);
    setDiameter(presetDiameter(count));
  }});
  document.getElementById("copy-btn").addEventListener("click", async () => {{
    const text = formatTuple();
    try {{
      await navigator.clipboard.writeText(text);
      document.getElementById("copy-btn").textContent = "Copied!";
      setTimeout(() => {{
        document.getElementById("copy-btn").textContent = "Copy Python tuple";
      }}, 1200);
    }} catch (err) {{
      window.prompt("Copy layout tuple:", text);
    }}
  }});

  document.addEventListener("pointermove", onPointerMove);
  document.addEventListener("pointerup", onPointerUp);
  document.addEventListener("pointercancel", onPointerUp);

  norms = defaultNorms(count);
  applyScale();
  renderCircles();
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
    return _story_circle_body_bounds(canvas_w, canvas_h, diameter=diameter)


__all__ = [
    "CIRCLE_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX",
    "PLAYGROUND_SAMPLE_STATS",
    "render_circle_layout_playground_html",
    "story_circle_body_bounds_for_playground",
]
