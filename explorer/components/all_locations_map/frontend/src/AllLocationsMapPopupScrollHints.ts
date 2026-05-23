/**
 * Scroll-region overflow hints for map popups (Settings → Popup scroll hint).
 * Ported from Folium-era ``popup_scroll_script`` in ``map_renderer.py``.
 */

export type PopupScrollHintMode = "chevron" | "shading" | "both" | "";

function normalizeHint(hint: string | null | undefined): PopupScrollHintMode {
  const h = String(hint ?? "").trim();
  if (h === "chevron" || h === "shading" || h === "both") {
    return h;
  }
  return "";
}

function updateScrollHints(
  scrollable: HTMLElement,
  wrapper: HTMLElement,
  hint: PopupScrollHintMode,
): void {
  const st = scrollable.scrollTop;
  const maxScroll = scrollable.scrollHeight - scrollable.clientHeight;
  const hasMoreAbove = st > 0;
  const hasMoreBelow = st < maxScroll - 1;

  if (hint === "chevron" || hint === "both") {
    const upEl = wrapper.querySelector<HTMLElement>(".popup-scroll-up");
    const downEl = wrapper.querySelector<HTMLElement>(".popup-scroll-down");
    if (upEl) upEl.style.visibility = hasMoreAbove ? "visible" : "hidden";
    if (downEl) downEl.style.visibility = hasMoreBelow ? "visible" : "hidden";
  }
  if (hint === "shading" || hint === "both") {
    const topShade = wrapper.querySelector<HTMLElement>(".popup-scroll-shade-top");
    const botShade = wrapper.querySelector<HTMLElement>(".popup-scroll-shade-bot");
    if (topShade) topShade.style.visibility = hasMoreAbove ? "visible" : "hidden";
    if (botShade) botShade.style.visibility = hasMoreBelow ? "visible" : "hidden";
  }
}

function setupScrollablePopup(
  scrollable: HTMLElement,
  wrapper: HTMLElement,
  hint: PopupScrollHintMode,
  scrollToBottom: boolean,
): void {
  if (!hint) {
    return;
  }
  const hasOverflow = scrollable.scrollHeight > scrollable.clientHeight;
  if (!hasOverflow) {
    return;
  }

  scrollable.scrollTop = scrollToBottom ? scrollable.scrollHeight : 0;

  const scrollTop = scrollable.offsetTop;
  if (hint === "chevron" || hint === "both") {
    const up = document.createElement("div");
    up.className = "popup-scroll-up";
    up.style.cssText =
      `position:absolute;top:${scrollTop}px;left:50%;transform:translateX(-50%);` +
      "font-size:10px;color:#888;pointer-events:none;z-index:10;";
    up.textContent = "\u25B2";
    const down = document.createElement("div");
    down.className = "popup-scroll-down";
    down.style.cssText =
      "position:absolute;bottom:8px;left:50%;transform:translateX(-50%);" +
      "font-size:10px;color:#888;pointer-events:none;z-index:10;";
    down.textContent = "\u25BC";
    wrapper.appendChild(up);
    wrapper.appendChild(down);
  }
  if (hint === "shading" || hint === "both") {
    const topShade = document.createElement("div");
    topShade.className = "popup-scroll-shade-top";
    topShade.style.cssText =
      `position:absolute;top:${scrollTop}px;left:0;right:0;height:24px;` +
      "pointer-events:none;z-index:5;" +
      "background:linear-gradient(to bottom,rgba(250,252,250,0.97),transparent);";
    const botShade = document.createElement("div");
    botShade.className = "popup-scroll-shade-bot";
    botShade.style.cssText =
      "position:absolute;bottom:0;left:0;right:0;height:24px;" +
      "pointer-events:none;z-index:5;" +
      "background:linear-gradient(to top,rgba(250,252,250,0.97),transparent);";
    wrapper.appendChild(topShade);
    wrapper.appendChild(botShade);
  }

  const onScroll = () => updateScrollHints(scrollable, wrapper, hint);
  updateScrollHints(scrollable, wrapper, hint);
  scrollable.addEventListener("scroll", onScroll);
  wrapper.dataset.popupScrollSetup = "1";
}

/**
 * Attach chevron/shading hints to the open Leaflet popup's scroll region.
 * Call after popup HTML is in the DOM (e.g. from ``popupopen``, post width shrink).
 */
export function setupPopupScrollHintsFromLeafletPopup(
  popup: L.Popup,
  scrollHint: string | null | undefined,
  scrollToBottom: boolean,
): void {
  const hint = normalizeHint(scrollHint);
  if (!hint) {
    return;
  }
  const el = popup.getElement?.();
  if (!el) {
    return;
  }
  const scrollable = el.querySelector<HTMLElement>(".pebird-map-popup__scroll");
  if (!scrollable) {
    return;
  }
  const wrapper = scrollable.parentElement as HTMLElement | null;
  if (!wrapper || wrapper.dataset.popupScrollSetup === "1") {
    return;
  }
  setupScrollablePopup(scrollable, wrapper, hint, scrollToBottom);
}

/** Schedule hint setup after Leaflet lays out popup content (matches Folium ``setTimeout(100)``). */
export function schedulePopupScrollHints(
  popup: L.Popup,
  scrollHint: string | null | undefined,
  scrollToBottom: boolean,
): void {
  window.setTimeout(() => {
    setupPopupScrollHintsFromLeafletPopup(popup, scrollHint, scrollToBottom);
  }, 100);
}
