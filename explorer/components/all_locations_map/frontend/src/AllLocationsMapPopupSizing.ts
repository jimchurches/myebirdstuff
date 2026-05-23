/** Leaflet popup width measurement, shrink-wrap, and viewport pan (R14 split). */

import L from "leaflet";

/** Matches ``MAP_POPUP_MAX_WIDTH_PX`` in ``explorer/app/streamlit/defaults.py`` (420). */
const POPUP_MAX_WIDTH_PX = 420;

/** Leaflet runs ``autoPan`` inside ``popup.update()`` — stacked updates caused large vertical pans. Disabled globally; ``maybePanPopupIntoView`` pans once when needed after layout settles. */
export const POPUP_BIND_OPTIONS: L.PopupOptions = {
  maxWidth: POPUP_MAX_WIDTH_PX,
  autoPan: false,
};

/** Go-to-GPS popup body (``map_leaflet_viewport`` ``go_to_gps`` viewport recipe). */
export const GO_TO_GPS_POPUP_HTML =
  "<div style='font-size:13px'><strong>Temporary GPS marker</strong></div>";

/** Default gap below location title row — matches ``build_location_popup_html(..., location_heading_margin_px=4)``. */
export const POPUP_LOCATION_HEADING_MARGIN_PX = 4;

/** Extra px on shrink width — ``scrollWidth`` can sit slightly under painted text (subpixel / fonts / padding). */
const POPUP_SHRINK_WIDTH_BUFFER_PX = 48;

/** Never apply a narrower content box than this — guards bad measures / font glitches. */
const POPUP_SHRINK_MIN_CONTENT_WIDTH_PX = 140;

/** Rows included when measuring intrinsic popup width (all map modes). */
const POPUP_WIDE_MEASURE_SELECTOR =
  ".pebird-map-popup__heading-row, .pebird-map-popup__visit-dates a, .pebird-map-popup__visit-list-inner a, " +
  ".pebird-map-popup__summary-line, " +
  ".pebird-map-popup__species-line, .pebird-map-popup__species-line a, .pebird-map-popup__obs-line, " +
  ".pebird-map-popup__species-seen > summary, " +
  ".pebird-map-popup__all-visits > summary";

const POPUP_LOCATION_HEADING_SELECTOR =
  "a.pebird-map-popup__location-heading, span.pebird-map-popup__location-heading";

/** ``.pebird-map-popup`` horizontal padding (6 + 14) + ``__heading-row`` close-button gutter (~2.25rem). */
const POPUP_HEADING_TEXT_INSET_PX = 56;

/** Intrinsic single-line width of location titles (off-DOM — matches painted bold popup font). */
function measureLocationHeadingWidthPx(inner: HTMLElement): number {
  let w = 0;
  inner.querySelectorAll(POPUP_LOCATION_HEADING_SELECTOR).forEach((el) => {
    const he = el as HTMLElement;
    const cs = window.getComputedStyle(he);
    const clone = he.cloneNode(true) as HTMLElement;
    clone.style.cssText =
      "position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;width:max-content;max-width:none;";
    clone.style.fontFamily = cs.fontFamily;
    clone.style.fontSize = cs.fontSize;
    clone.style.fontWeight = cs.fontWeight;
    clone.style.letterSpacing = cs.letterSpacing;
    document.body.appendChild(clone);
    w = Math.max(w, clone.scrollWidth, clone.getBoundingClientRect().width);
    document.body.removeChild(clone);
  });
  return Math.ceil(Math.max(w, 1));
}

function headingTextBudgetPx(contentWidthPx: number): number {
  return Math.max(1, contentWidthPx - POPUP_HEADING_TEXT_INSET_PX);
}

function committedPopupContentWidthPx(content: HTMLElement): number {
  const fromData = Number.parseInt(content.dataset.pebirdShrinkTarget ?? "", 10);
  if (Number.isFinite(fromData) && fromData > 0) {
    return fromData;
  }
  return Math.ceil(content.getBoundingClientRect().width);
}

/** Drop a too-narrow width commit when the single-line title needs a wider card (or the max cap). */
function popupWidthCommitTooNarrowForHeading(
  inner: HTMLElement,
  content: HTMLElement,
  cap: number,
): boolean {
  const committed = committedPopupContentWidthPx(content);
  const headingW = measureLocationHeadingWidthPx(inner);
  return headingW > headingTextBudgetPx(committed) && committed < cap;
}

/** Max of inner and wide text rows while inner is ``max-content`` for measure. */
function measurePebirdPopupInnerWidthPx(inner: HTMLElement): number {
  void inner.offsetWidth;
  let w = Math.max(inner.scrollWidth, inner.getBoundingClientRect().width);
  w = Math.max(w, measureLocationHeadingWidthPx(inner));
  const wideEls = inner.querySelectorAll(POPUP_WIDE_MEASURE_SELECTOR);
  wideEls.forEach((el) => {
    const he = el as HTMLElement;
    w = Math.max(w, he.scrollWidth, he.getBoundingClientRect().width);
  });
  return Math.ceil(Math.max(w, 1));
}

/** Shrink-wrap Leaflet popup width to ``.pebird-map-popup`` intrinsic width (TS-only; export viewer uses ``leaflet_map_export.js``).

Uses map pixel width (not ``window``) for cap. Parents use ``cap`` px during measure so ``width:100%`` rows do not collapse.
After width changes, callers invoke ``popup.update()`` to keep the tip on the marker (#145).
*/
function capPopupInnerWidthPxForMap(map: L.Map): number {
  const px = Math.max(1, map.getSize().x);
  return Math.min(POPUP_MAX_WIDTH_PX, Math.max(80, px - 24));
}

/** Once width is applied for a given map cap, skip remeasuring — avoids a second visible resize when
 * iframe/RFO bumps run later at ~50–500ms. Remeasure only when ``cap`` changes (map container width). */
const POPUP_WIDTH_COMMIT_ATTR = "data-pebird-popup-width-commit";
const POPUP_WIDTH_CAP_ATTR = "data-pebird-shrink-applied-cap";

/** Shrink-wrap ``.leaflet-popup-content`` to intrinsic width; commit per (popup, map cap) to avoid repeat work. */
export function shrinkPebirdLeafletPopups(map: L.Map): void {
  const pops = document.querySelectorAll(".leaflet-popup-pane .leaflet-popup");
  const cap = capPopupInnerWidthPxForMap(map);
  const capStr = `${cap}`;
  pops.forEach((pop) => {
    const content = pop.querySelector(".leaflet-popup-content") as HTMLElement | null;
    const wrap = pop.querySelector(".leaflet-popup-content-wrapper") as HTMLElement | null;
    const inner = pop.querySelector(".pebird-map-popup") as HTMLElement | null;
    if (!content || !wrap || !inner) {
      return;
    }
    if (content.getAttribute(POPUP_WIDTH_COMMIT_ATTR) === "1" && content.getAttribute(POPUP_WIDTH_CAP_ATTR) === capStr) {
      if (popupWidthCommitTooNarrowForHeading(inner, content, cap)) {
        content.removeAttribute(POPUP_WIDTH_COMMIT_ATTR);
      } else {
        return;
      }
    }

    /* Shrink-to-fit cycle: inner has max-width:100% of .leaflet-popup-content while that node uses
     * width:fit-content — cyclic percentage resolves tiny, so scrollWidth was ~min-content  .
     * Size inner to max-content for measurement only, then restore so final layout still respects cap.
     *
     * Never strip content/wrapper width **without** substituting ``cap``: descendants such as
     * ``.pebird-map-popup__heading-row { width:100% }`` lose their percentage base and collapse to a
     * min-content column — ``scrollWidth`` then matches a character-wide strip. */
    inner.style.setProperty("max-width", "none", "important");
    inner.style.setProperty("width", "max-content", "important");
    content.style.setProperty("width", `${cap}px`, "important");
    content.style.setProperty("max-width", `${cap}px`, "important");
    wrap.style.setProperty("width", `${cap}px`, "important");
    wrap.style.setProperty("max-width", `${cap}px`, "important");
    content.style.removeProperty("white-space");
    const innerPx = measurePebirdPopupInnerWidthPx(inner);
    inner.style.removeProperty("max-width");
    inner.style.removeProperty("width");
    const target = Math.max(
      POPUP_SHRINK_MIN_CONTENT_WIDTH_PX,
      Math.min(innerPx + POPUP_SHRINK_WIDTH_BUFFER_PX, cap),
    );
    const nextTargetStr = `${target}`;
    const prevTargetStr = content.dataset.pebirdShrinkTarget ?? "";
    const changed = prevTargetStr !== nextTargetStr;

    if (changed) {
      content.dataset.pebirdShrinkTarget = nextTargetStr;
      content.style.setProperty("width", `${target}px`, "important");
      content.style.setProperty("max-width", `${cap}px`, "important");
      wrap.style.setProperty("width", `${target}px`, "important");
      wrap.style.setProperty("max-width", `${cap}px`, "important");
    }
    content.setAttribute(POPUP_WIDTH_COMMIT_ATTR, "1");
    content.setAttribute(POPUP_WIDTH_CAP_ATTR, capStr);
  });
}

/** Margin inside the map container when deciding if the popup clips (replaces Leaflet ``autoPan``). */
const POPUP_VIEWPORT_PAD_PX = 12;

/** Pan the map only when the open popup’s bounding box exceeds the container inset — minimal correction, no Leaflet ``autoPan`` stack. */
export function maybePanPopupIntoView(map: L.Map, popup: L.Popup): void {
  const mapEl = map.getContainer();
  const popupEl = popup.getElement();
  if (!popupEl) {
    return;
  }
  const mr = mapEl.getBoundingClientRect();
  const pr = popupEl.getBoundingClientRect();
  const insetLeft = mr.left + POPUP_VIEWPORT_PAD_PX;
  const insetTop = mr.top + POPUP_VIEWPORT_PAD_PX;
  const insetRight = mr.right - POPUP_VIEWPORT_PAD_PX;
  const insetBottom = mr.bottom - POPUP_VIEWPORT_PAD_PX;

  const overflowLeft = insetLeft - pr.left;
  const overflowRight = pr.right - insetRight;
  const overflowTop = insetTop - pr.top;
  const overflowBottom = pr.bottom - insetBottom;

  let dx = 0;
  let dy = 0;
  if (overflowLeft > 0 && overflowRight <= 0) {
    dx = -overflowLeft;
  } else if (overflowRight > 0 && overflowLeft <= 0) {
    dx = overflowRight;
  } else if (overflowLeft > 0 && overflowRight > 0) {
    dx = (overflowRight - overflowLeft) / 2;
  }
  if (overflowTop > 0 && overflowBottom <= 0) {
    dy = -overflowTop;
  } else if (overflowBottom > 0 && overflowTop <= 0) {
    dy = overflowBottom;
  } else if (overflowTop > 0 && overflowBottom > 0) {
    dy = (overflowBottom - overflowTop) / 2;
  }

  if (dx !== 0 || dy !== 0) {
    map.panBy(L.point(dx, dy), { animate: false });
  }
}

export function scheduleShrinkPebirdLeafletPopups(map: L.Map, popup?: L.Popup): void {
  /** Wait for web fonts before measuring — fallback metrics used to lock ``data-pebird-popup-width-commit``
   * produced cards that were tens of px too narrow (lines broke after commas, visit rows split date/time).
   * One double-rAF after ``fonts.ready`` keeps a single width commit with no follow-up resize. */
  const finalize = () => {
    shrinkPebirdLeafletPopups(map);
    if (popup && typeof popup.update === "function") {
      popup.update();
      maybePanPopupIntoView(map, popup);
    }
  };
  const runAfterLayout = () => {
    requestAnimationFrame(() => {
      requestAnimationFrame(finalize);
    });
  };
  try {
    const ready = document.fonts?.ready;
    if (ready && typeof ready.then === "function") {
      void ready.then(runAfterLayout).catch(runAfterLayout);
    } else {
      runAfterLayout();
    }
  } catch {
    runAfterLayout();
  }
}
