"""
Dev-only iframe tuner for rich Spotlight fact typography (#285).

Copy export into ``share_summary_rich_fact_layout.py`` (``RICH_FACT_LAYOUT_SPECS``).
"""

from __future__ import annotations

import json

from explorer.core.share_summary_defaults import SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES
from explorer.presentation.share_summary_preview import (
    FORMAT_LABELS,
    FORMAT_PIXELS,
    FormatId,
)
from explorer.presentation.share_summary_rich_fact_layout import rich_fact_layout_spec

RICH_FACT_PLAYGROUND_FORMATS: tuple[FormatId, ...] = ("square", "portrait_post", "story")

RICH_FACT_PLAYGROUND_SAMPLES: dict[str, dict[str, str]] = {
    "most_common": {
        "label": "Most common checklist species",
        "primary": "Indian Pond-Heron",
        "metric": "1 checklists",
    },
    "species_count": {
        "label": "Species count",
        "primary": "Australasian Shoveler",
        "metric": "1,053 individuals",
    },
    "biggest_checklist": {
        "label": "Biggest single-checklist count",
        "primary": "Wedge-tailed Shearwater",
        "metric": "4,200 on one checklist",
    },
}

RICH_FACT_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX = 980

_HEADER_RESERVE_PX = 210
_FOOTER_RESERVE_PX = 150

_SCHEME = {
    "bg": "#ffffff",
    "bg_alt": "#f9fafb",
    "text": "#111827",
    "muted": "#6b7280",
    "border": "#e5e7eb",
    "accent": "#2d6a4f",
    "tile_bg": "#ffffff",
    "tile_bg_alt": "#f9fafb",
    "tile_border": "#e5e7eb",
}


def _offset_range_for_format(fmt: FormatId) -> tuple[int, int]:
    """Vertical offset limits — enough to place the block near the card midline."""
    _, height = FORMAT_PIXELS[fmt]
    span = max(120, height - _HEADER_RESERVE_PX - _FOOTER_RESERVE_PX)
    half = span // 2
    return (-half, half)


def _body_min_height_for_format(fmt: FormatId) -> int:
    _, height = FORMAT_PIXELS[fmt]
    return max(200, height - _HEADER_RESERVE_PX - _FOOTER_RESERVE_PX)


def _spec_to_playground_dict(fmt: FormatId) -> dict[str, object]:
    spec = rich_fact_layout_spec(fmt)
    return {
        "label": {
            "size": spec.label.font_size_px,
            "weight": spec.label.font_weight,
            "color": _SCHEME[spec.label.color_role],
            "lineHeight": spec.label.line_height,
            "marginBottom": spec.label.margin_bottom_px,
        },
        "primary": {
            "size": spec.primary.font_size_px,
            "weight": spec.primary.font_weight,
            "color": _SCHEME[spec.primary.color_role],
            "lineHeight": spec.primary.line_height,
        },
        "metric": {
            "size": spec.metric.font_size_px,
            "weight": spec.metric.font_weight,
            "color": _SCHEME[spec.metric.color_role],
            "lineHeight": spec.metric.line_height,
            "marginTop": spec.metric.margin_top_px,
        },
        "blockOffsetY": spec.block_offset_y_px,
        "maxWidth": spec.max_width_px,
    }


def _playground_bootstrap() -> dict[str, object]:
    return {
        "formats": {
            fmt: {
                "label": FORMAT_LABELS[fmt],
                "width": FORMAT_PIXELS[fmt][0],
                "height": FORMAT_PIXELS[fmt][1],
                "bodyMinHeight": _body_min_height_for_format(fmt),
                "offsetMin": _offset_range_for_format(fmt)[0],
                "offsetMax": _offset_range_for_format(fmt)[1],
                "defaults": _spec_to_playground_dict(fmt),
            }
            for fmt in RICH_FACT_PLAYGROUND_FORMATS
        },
        "samples": RICH_FACT_PLAYGROUND_SAMPLES,
        "scheme": _SCHEME,
        "headerSubtitle": SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES,
        "headerHeadline": "Lifetime",
        "scopeLabel": "World",
    }


def render_rich_fact_layout_playground_html() -> str:
    """Self-contained HTML for ``st.iframe`` in the design studio."""
    bootstrap = json.dumps(_playground_bootstrap())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Rich fact layout playground</title>
<style>
  :root {{
    color-scheme: light;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: #eef1f4;
    color: #111827;
  }}
  .wrap {{
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 16px;
    padding: 16px;
    min-height: 100vh;
  }}
  .panel {{
    background: #fff;
    border: 1px solid #d8dee6;
    border-radius: 10px;
    padding: 14px 16px;
    overflow: auto;
  }}
  h1 {{
    margin: 0 0 4px;
    font-size: 18px;
  }}
  .hint {{
    margin: 0 0 14px;
    font-size: 12px;
    color: #6b7280;
    line-height: 1.35;
  }}
  fieldset {{
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin: 0 0 12px;
    padding: 10px 12px 12px;
  }}
  legend {{
    padding: 0 4px;
    font-size: 12px;
    font-weight: 600;
    color: #374151;
  }}
  label {{
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
    align-items: center;
    font-size: 12px;
    margin: 8px 0 0;
  }}
  label span.val {{
    min-width: 44px;
    text-align: right;
    color: #6b7280;
    font-variant-numeric: tabular-nums;
  }}
  select, input[type="color"] {{
    width: 100%;
    margin-top: 4px;
  }}
  input[type="range"] {{
    width: 100%;
  }}
  label.check-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 10px 0 0;
    font-size: 12px;
  }}
  label.check-row input {{
    width: auto;
    margin: 0;
  }}
  .preview-shell {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }}
  .card-viewport {{
    overflow: auto;
    max-width: 100%;
    padding: 8px;
    background: #f8fafc;
    border: 1px solid #d8dee6;
    border-radius: 10px;
  }}
  .card {{
    position: relative;
    overflow: hidden;
    background: var(--card-bg);
    color: var(--card-text);
    transform-origin: top center;
  }}
  .card-header {{
    padding: 48px 56px 24px;
    text-align: center;
  }}
  .card-header .sub {{
    margin: 0 0 8px;
    font-size: 28px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--card-accent);
    font-weight: 600;
  }}
  .card-header h2 {{
    margin: 0;
    font-size: 96px;
    font-weight: 700;
    line-height: 1.08;
  }}
  .card-body {{
    padding: 8px 48px 140px;
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    min-height: var(--body-min-height);
  }}
  .card-body-inner {{
    max-width: var(--rich-max-width);
    width: 100%;
    transform: translateY(var(--rich-offset-y));
  }}
  .card-body-inner.rich-tile {{
    padding: 32px 20px;
    border-radius: 12px;
    background: linear-gradient(145deg, var(--tile-bg-alt), var(--tile-bg));
    border: 1px solid var(--tile-border);
    box-sizing: border-box;
  }}
  .rich-label, .rich-primary, .rich-metric {{
    word-wrap: break-word;
  }}
  .card-footer {{
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 22px 56px 26px;
    text-align: center;
    border-top: 1px solid var(--card-border);
    background: var(--card-bg-alt);
  }}
  .card-footer .scope {{
    margin: 0 0 7px;
    font-size: 36px;
    font-weight: 600;
    line-height: 1.05;
    color: var(--card-muted);
    letter-spacing: 0.04em;
  }}
  .card-footer .brand {{
    margin: 5px 0 0;
    font-size: 18px;
    color: var(--card-muted);
  }}
  pre.export {{
    margin: 0;
    padding: 10px 12px;
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 8px;
    font-size: 11px;
    line-height: 1.45;
    white-space: pre-wrap;
    max-height: 220px;
    overflow: auto;
  }}
  .meta {{
    font-size: 12px;
    color: #6b7280;
  }}
  .row-actions {{
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }}
  button {{
    border: 1px solid #cbd5e1;
    background: #fff;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    cursor: pointer;
  }}
  button:hover {{ background: #f8fafc; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="panel">
    <h1>Rich fact layout</h1>
    <p class="hint">Tune the three data lines and vertical block offset. Copy export into
      <code>share_summary_rich_fact_layout.py</code>.</p>
    <label>Format
      <select id="format-select"></select>
    </label>
    <label>Sample content
      <select id="sample-select"></select>
    </label>
    <fieldset>
      <legend>Block position</legend>
      <label>Vertical offset (px)
        <span class="val" id="offset-val">0</span>
      </label>
      <input id="offset-input" type="range" min="0" max="240" step="2" value="0" />
      <p class="hint" id="offset-range-hint" style="margin:6px 0 0;"></p>
      <label class="check-row">
        <input id="tile-frame-input" type="checkbox" />
        <span>Rectangular tile frame (preview only)</span>
      </label>
    </fieldset>
    <fieldset>
      <legend>Line 1 — label</legend>
      <label>Size (px)<span class="val" id="label-size-val"></span></label>
      <input id="label-size" type="range" min="18" max="72" step="1" />
      <label>Weight<span class="val" id="label-weight-val"></span></label>
      <input id="label-weight" type="range" min="400" max="800" step="100" />
      <label>Colour</label>
      <input id="label-color" type="color" />
      <label>Margin below (px)<span class="val" id="label-margin-val"></span></label>
      <input id="label-margin" type="range" min="0" max="48" step="1" />
    </fieldset>
    <fieldset>
      <legend>Line 2 — primary</legend>
      <label>Size (px)<span class="val" id="primary-size-val"></span></label>
      <input id="primary-size" type="range" min="24" max="120" step="1" />
      <label>Weight<span class="val" id="primary-weight-val"></span></label>
      <input id="primary-weight" type="range" min="400" max="800" step="100" />
      <label>Colour</label>
      <input id="primary-color" type="color" />
    </fieldset>
    <fieldset>
      <legend>Line 3 — metric</legend>
      <label>Size (px)<span class="val" id="metric-size-val"></span></label>
      <input id="metric-size" type="range" min="18" max="72" step="1" />
      <label>Weight<span class="val" id="metric-weight-val"></span></label>
      <input id="metric-weight" type="range" min="400" max="800" step="100" />
      <label>Colour</label>
      <input id="metric-color" type="color" />
      <label>Margin above (px)<span class="val" id="metric-margin-val"></span></label>
      <input id="metric-margin" type="range" min="0" max="48" step="1" />
    </fieldset>
    <div class="row-actions">
      <button type="button" id="reset-btn">Reset format</button>
      <button type="button" id="copy-btn">Copy export</button>
    </div>
    <p class="meta" id="meta-text"></p>
    <pre class="export" id="export-text"></pre>
  </div>
  <div class="panel preview-shell">
    <div class="card-viewport">
      <div class="card" id="card">
        <div class="card-header">
          <p class="sub" id="hdr-sub"></p>
          <h2 id="hdr-headline"></h2>
        </div>
        <div class="card-body">
          <div class="card-body-inner" id="rich-body">
            <div class="rich-label" id="rich-label"></div>
            <div class="rich-primary" id="rich-primary"></div>
            <div class="rich-metric" id="rich-metric"></div>
          </div>
        </div>
        <div class="card-footer">
          <p class="scope" id="ftr-scope"></p>
          <p class="brand">Personal eBird Explorer</p>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
const BOOT = {bootstrap};
(function () {{
  const formats = BOOT.formats;
  const formatIds = Object.keys(formats);
  let fmt = "story";
  let sampleKey = "most_common";
  let tileFrame = false;
  let state = cloneState(formats[fmt].defaults);

  const els = {{
    formatSelect: document.getElementById("format-select"),
    sampleSelect: document.getElementById("sample-select"),
    card: document.getElementById("card"),
    richBody: document.getElementById("rich-body"),
    richLabel: document.getElementById("rich-label"),
    richPrimary: document.getElementById("rich-primary"),
    richMetric: document.getElementById("rich-metric"),
    hdrSub: document.getElementById("hdr-sub"),
    hdrHeadline: document.getElementById("hdr-headline"),
    ftrScope: document.getElementById("ftr-scope"),
    exportText: document.getElementById("export-text"),
    metaText: document.getElementById("meta-text"),
    offsetInput: document.getElementById("offset-input"),
    offsetVal: document.getElementById("offset-val"),
    labelSize: document.getElementById("label-size"),
    labelWeight: document.getElementById("label-weight"),
    labelColor: document.getElementById("label-color"),
    labelMargin: document.getElementById("label-margin"),
    primarySize: document.getElementById("primary-size"),
    primaryWeight: document.getElementById("primary-weight"),
    primaryColor: document.getElementById("primary-color"),
    metricSize: document.getElementById("metric-size"),
    metricWeight: document.getElementById("metric-weight"),
    metricColor: document.getElementById("metric-color"),
    metricMargin: document.getElementById("metric-margin"),
    tileFrameInput: document.getElementById("tile-frame-input"),
    offsetRangeHint: document.getElementById("offset-range-hint"),
  }};

  function currentMode() {{
    return formats[fmt];
  }}

  function clampOffset(value) {{
    const mode = currentMode();
    return Math.max(mode.offsetMin, Math.min(mode.offsetMax, value));
  }}

  function applyOffsetSliderLimits() {{
    const mode = currentMode();
    els.offsetInput.min = String(mode.offsetMin);
    els.offsetInput.max = String(mode.offsetMax);
    els.offsetRangeHint.textContent =
      "Range " + mode.offsetMin + " to " + mode.offsetMax + " px for " + mode.label;
  }}

  function cloneState(src) {{
    return JSON.parse(JSON.stringify(src));
  }}

  function colorRole(hex) {{
  const scheme = BOOT.scheme;
    if (hex.toLowerCase() === scheme.muted.toLowerCase()) return "muted";
    if (hex.toLowerCase() === scheme.accent.toLowerCase()) return "accent";
    return "text";
  }}

  function bindFormatSelect() {{
    els.formatSelect.innerHTML = "";
    formatIds.forEach((id) => {{
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = formats[id].label;
      els.formatSelect.appendChild(opt);
    }});
    els.formatSelect.value = fmt;
  }}

  function bindSampleSelect() {{
    els.sampleSelect.innerHTML = "";
    Object.keys(BOOT.samples).forEach((key) => {{
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = key.replaceAll("_", " ");
      els.sampleSelect.appendChild(opt);
    }});
    els.sampleSelect.value = sampleKey;
  }}

  function syncControlsFromState() {{
    state.blockOffsetY = clampOffset(state.blockOffsetY);
    els.offsetInput.value = String(state.blockOffsetY);
    els.offsetVal.textContent = String(state.blockOffsetY);
    els.labelSize.value = String(state.label.size);
    document.getElementById("label-size-val").textContent = String(state.label.size);
    els.labelWeight.value = String(state.label.weight);
    document.getElementById("label-weight-val").textContent = String(state.label.weight);
    els.labelColor.value = state.label.color;
    els.labelMargin.value = String(state.label.marginBottom || 0);
    document.getElementById("label-margin-val").textContent = String(state.label.marginBottom || 0);
    els.primarySize.value = String(state.primary.size);
    document.getElementById("primary-size-val").textContent = String(state.primary.size);
    els.primaryWeight.value = String(state.primary.weight);
    document.getElementById("primary-weight-val").textContent = String(state.primary.weight);
    els.primaryColor.value = state.primary.color;
    els.metricSize.value = String(state.metric.size);
    document.getElementById("metric-size-val").textContent = String(state.metric.size);
    els.metricWeight.value = String(state.metric.weight);
    document.getElementById("metric-weight-val").textContent = String(state.metric.weight);
    els.metricColor.value = state.metric.color;
    els.metricMargin.value = String(state.metric.marginTop || 0);
    document.getElementById("metric-margin-val").textContent = String(state.metric.marginTop || 0);
    els.tileFrameInput.checked = tileFrame;
  }}

  function readControlsIntoState() {{
    state.blockOffsetY = Number(els.offsetInput.value);
    state.label.size = Number(els.labelSize.value);
    state.label.weight = Number(els.labelWeight.value);
    state.label.color = els.labelColor.value;
    state.label.marginBottom = Number(els.labelMargin.value);
    state.primary.size = Number(els.primarySize.value);
    state.primary.weight = Number(els.primaryWeight.value);
    state.primary.color = els.primaryColor.value;
    state.metric.size = Number(els.metricSize.value);
    state.metric.weight = Number(els.metricWeight.value);
    state.metric.color = els.metricColor.value;
    state.metric.marginTop = Number(els.metricMargin.value);
  }}

  function previewScale(cardW) {{
    const viewport = document.querySelector(".card-viewport");
    const maxW = Math.max(280, (viewport?.clientWidth || 720) - 32);
    return Math.min(1, maxW / cardW);
  }}

  function applyPreview() {{
    const mode = currentMode();
    const sample = BOOT.samples[sampleKey];
    const scale = previewScale(mode.width);
    const scheme = BOOT.scheme;
    els.card.style.width = mode.width + "px";
    els.card.style.height = mode.height + "px";
    els.card.style.transform = "scale(" + scale.toFixed(3) + ")";
    els.card.style.setProperty("--card-bg", scheme.bg);
    els.card.style.setProperty("--card-text", scheme.text);
    els.card.style.setProperty("--card-muted", scheme.muted);
    els.card.style.setProperty("--card-border", scheme.border);
    els.card.style.setProperty("--card-accent", scheme.accent);
    els.card.style.setProperty("--card-bg-alt", scheme.bg_alt);
    els.card.style.setProperty("--tile-bg", scheme.tile_bg);
    els.card.style.setProperty("--tile-bg-alt", scheme.tile_bg_alt);
    els.card.style.setProperty("--tile-border", scheme.tile_border);
    els.card.style.setProperty("--rich-offset-y", state.blockOffsetY + "px");
    els.card.style.setProperty("--rich-max-width", (state.maxWidth || 920) + "px");
    els.card.style.setProperty("--body-min-height", mode.bodyMinHeight + "px");
    els.richBody.classList.toggle("rich-tile", tileFrame);
    els.hdrSub.textContent = BOOT.headerSubtitle;
    els.hdrHeadline.textContent = BOOT.headerHeadline;
    els.ftrScope.textContent = BOOT.scopeLabel;
    els.richLabel.textContent = sample.label;
    els.richPrimary.textContent = sample.primary;
    els.richMetric.textContent = sample.metric;
    els.richLabel.style.cssText =
      "font-size:" + state.label.size + "px;font-weight:" + state.label.weight +
      ";line-height:" + state.label.lineHeight + ";color:" + state.label.color +
      ";margin-bottom:" + (state.label.marginBottom || 0) + "px;";
    els.richPrimary.style.cssText =
      "font-size:" + state.primary.size + "px;font-weight:" + state.primary.weight +
      ";line-height:" + state.primary.lineHeight + ";color:" + state.primary.color + ";";
    els.richMetric.style.cssText =
      "font-size:" + state.metric.size + "px;font-weight:" + state.metric.weight +
      ";line-height:" + state.metric.lineHeight + ";color:" + state.metric.color +
      ";margin-top:" + (state.metric.marginTop || 0) + "px;";
    els.metaText.textContent =
      mode.label + " · " + mode.width + "×" + mode.height + "px · preview scale " +
      scale.toFixed(2);
    els.exportText.textContent = formatExport();
  }}

  function formatExport() {{
    const mode = formats[fmt];
    const lr = colorRole(state.label.color);
    const pr = colorRole(state.primary.color);
    const mr = colorRole(state.metric.color);
    return [
      "# Paste into share_summary_rich_fact_layout.py — RICH_FACT_LAYOUT_SPECS",
      'RICH_FACT_LAYOUT_SPECS["' + fmt + '"] = RichFactLayoutSpec(',
      "    label=RichFactLineStyle(",
      "        font_size_px=" + state.label.size + ",",
      "        font_weight=" + state.label.weight + ',',
      '        color_role="' + lr + '",',
      "        line_height=" + state.label.lineHeight + ",",
      "        margin_bottom_px=" + (state.label.marginBottom || 0) + ",",
      "    ),",
      "    primary=RichFactLineStyle(",
      "        font_size_px=" + state.primary.size + ",",
      "        font_weight=" + state.primary.weight + ',',
      '        color_role="' + pr + '",',
      "        line_height=" + state.primary.lineHeight + ",",
      "    ),",
      "    metric=RichFactLineStyle(",
      "        font_size_px=" + state.metric.size + ",",
      "        font_weight=" + state.metric.weight + ',',
      '        color_role="' + mr + '",',
      "        line_height=" + state.metric.lineHeight + ",",
      "        margin_top_px=" + (state.metric.marginTop || 0) + ",",
      "    ),",
      "    block_offset_y_px=" + state.blockOffsetY + ",",
      ")",
      "",
      "# " + mode.label + " · " + sampleKey,
    ].join("\\n");
  }}

  function onControlInput() {{
    readControlsIntoState();
    syncControlsFromState();
    applyPreview();
  }}

  els.formatSelect.addEventListener("change", () => {{
    fmt = els.formatSelect.value;
    state = cloneState(formats[fmt].defaults);
    applyOffsetSliderLimits();
    syncControlsFromState();
    applyPreview();
  }});
  els.sampleSelect.addEventListener("change", () => {{
    sampleKey = els.sampleSelect.value;
    applyPreview();
  }});
  [
    els.offsetInput, els.labelSize, els.labelWeight, els.labelColor, els.labelMargin,
    els.primarySize, els.primaryWeight, els.primaryColor,
    els.metricSize, els.metricWeight, els.metricColor, els.metricMargin,
  ].forEach((el) => el.addEventListener("input", onControlInput));
  els.tileFrameInput.addEventListener("change", () => {{
    tileFrame = els.tileFrameInput.checked;
    applyPreview();
  }});
  document.getElementById("reset-btn").addEventListener("click", () => {{
    state = cloneState(formats[fmt].defaults);
    tileFrame = false;
    applyOffsetSliderLimits();
    syncControlsFromState();
    applyPreview();
  }});
  document.getElementById("copy-btn").addEventListener("click", async () => {{
    const text = formatExport();
    try {{
      await navigator.clipboard.writeText(text);
      document.getElementById("copy-btn").textContent = "Copied!";
      setTimeout(() => {{ document.getElementById("copy-btn").textContent = "Copy export"; }}, 1200);
    }} catch (err) {{
      window.prompt("Copy export:", text);
    }}
  }});

  bindFormatSelect();
  bindSampleSelect();
  applyOffsetSliderLimits();
  syncControlsFromState();
  applyPreview();
  window.addEventListener("resize", applyPreview);
}})();
</script>
</body>
</html>"""


__all__ = [
    "RICH_FACT_LAYOUT_PLAYGROUND_IFRAME_HEIGHT_PX",
    "RICH_FACT_PLAYGROUND_FORMATS",
    "RICH_FACT_PLAYGROUND_SAMPLES",
    "render_rich_fact_layout_playground_html",
]
