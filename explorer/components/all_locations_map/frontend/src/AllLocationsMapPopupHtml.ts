/** Popup HTML builders and structured payload parsers (R14 split). */

import { POPUP_LOCATION_HEADING_MARGIN_PX } from "./AllLocationsMapPopupSizing";
import type { PopupLinkV1, PopupPayloadV1 } from "./allLocationsMapTypes";


function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/** Keep trailing ``)`` / ``]`` from wrapping onto a line alone (typography, not lat/long-specific). */
function preventOrphanClosingPunctuation(text: string): string {
  return text.replace(/\s+([)\]}"'»])\s*$/u, "\u00a0$1");
}

function locationHeadingHtml(name: string, lifelistUrl: string): string {
  const inner = escapeHtml(preventOrphanClosingPunctuation(name));
  const hlSafe = safeHttpUrlForAnchor(lifelistUrl.trim());
  if (hlSafe.length > 0) {
    return `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hlSafe)}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
  }
  return `<span class="pebird-map-popup__location-heading">${inner}</span>`;
}

/** Allow only http(s) in popup anchors — blocks ``javascript:``, ``data:``, etc.  . */
function safeHttpUrlForAnchor(raw: string): string {
  const t = raw.trim();
  if (!t) {
    return "";
  }
  try {
    const u = new URL(t);
    if (u.protocol === "https:" || u.protocol === "http:") {
      return u.href;
    }
  } catch {
    /* ignore */
  }
  return "";
}

function parsePopupV1(raw: unknown): PopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const summary_lines = Array.isArray(o.summary_lines)
    ? o.summary_lines.filter((x): x is string => typeof x === "string")
    : undefined;
  const linksRaw = Array.isArray(o.links) ? o.links : [];
  const links: PopupLinkV1[] = linksRaw
    .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "",
      href: typeof item.href === "string" ? item.href : "",
    }));
  let visited: PopupPayloadV1["visited"];
  const visRaw = o.visited;
  if (visRaw && typeof visRaw === "object") {
    const vo = visRaw as Record<string, unknown>;
    const vLabel = typeof vo.label === "string" ? vo.label : "Visited:";
    const entRaw = Array.isArray(vo.entries) ? vo.entries : [];
    const entries: PopupLinkV1[] = entRaw
      .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
      .map((item) => ({
        label: typeof item.label === "string" ? item.label : "",
        href: typeof item.href === "string" ? item.href : "",
      }));
    visited = { label: vLabel, entries };
  }
  return { v: 1, summary_lines, links, visited };
}

/** Lifer map — structured lines from ``lifer_locations_geojson.py``. */
interface LiferPopupLineV1 {
  label: string;
  date: string;
  checklist_href: string;
}

interface LiferPopupPayloadV1 {
  v: 1;
  lines: LiferPopupLineV1[];
}

function parseLiferPopupV1(raw: unknown): LiferPopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const linesRaw = Array.isArray(o.lines) ? o.lines : [];
  const lines: LiferPopupLineV1[] = [];
  for (const row of linesRaw) {
    if (!row || typeof row !== "object") {
      continue;
    }
    const r = row as Record<string, unknown>;
    lines.push({
      label: typeof r.label === "string" ? r.label : "",
      date: typeof r.date === "string" ? r.date : "?",
      checklist_href: typeof r.checklist_href === "string" ? r.checklist_href : "#",
    });
  }
  return { v: 1, lines };
}

/** Family map — location heading + species common-name lines (``family_locations_geojson.py``). */
interface FamilySpeciesLineV1 {
  name: string;
  species_href: string;
}

interface FamilyPopupPayloadV1 {
  v: 1;
  species_lines: FamilySpeciesLineV1[];
}

function parseFamilyPopupV1(raw: unknown): FamilyPopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const linesRaw = Array.isArray(o.species_lines) ? o.species_lines : [];
  const species_lines: FamilySpeciesLineV1[] = [];
  for (const row of linesRaw) {
    if (!row || typeof row !== "object") {
      continue;
    }
    const r = row as Record<string, unknown>;
    species_lines.push({
      name: typeof r.name === "string" ? r.name : "",
      species_href: typeof r.species_href === "string" ? r.species_href : "",
    });
  }
  return { v: 1, species_lines };
}

/** Species map — structured sections from ``species_locations_geojson.py``. */
interface SpeciesObservationV1 {
  datetime_label: string;
  checklist_href: string;
  observed_count: string;
  media_href: string;
}

interface SpeciesSectionV1 {
  common_name: string;
  observation_count: number;
  open_by_default: boolean;
  observations: SpeciesObservationV1[];
}

interface SpeciesVisitsBlockV1 {
  summary_label: string;
  entries: PopupLinkV1[];
  open_by_default: boolean;
}

interface SpeciesPopupPayloadV1 {
  v: 1;
  location_heading_margin_px?: number;
  species_sections: SpeciesSectionV1[];
  visits: SpeciesVisitsBlockV1;
}

function parseSpeciesPopupV1(raw: unknown): SpeciesPopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const sectionsRaw = Array.isArray(o.species_sections) ? o.species_sections : [];
  const species_sections: SpeciesSectionV1[] = [];
  for (const sec of sectionsRaw) {
    if (!sec || typeof sec !== "object") {
      continue;
    }
    const s = sec as Record<string, unknown>;
    const obsRaw = Array.isArray(s.observations) ? s.observations : [];
    const observations: SpeciesObservationV1[] = [];
    for (const row of obsRaw) {
      if (!row || typeof row !== "object") {
        continue;
      }
      const r = row as Record<string, unknown>;
      observations.push({
        datetime_label: typeof r.datetime_label === "string" ? r.datetime_label : "",
        checklist_href: typeof r.checklist_href === "string" ? r.checklist_href : "",
        observed_count: typeof r.observed_count === "string" ? r.observed_count : "",
        media_href: typeof r.media_href === "string" ? r.media_href : "",
      });
    }
    species_sections.push({
      common_name: typeof s.common_name === "string" ? s.common_name : "",
      observation_count:
        typeof s.observation_count === "number" && Number.isFinite(s.observation_count)
          ? s.observation_count
          : observations.length,
      open_by_default: s.open_by_default === true,
      observations,
    });
  }
  const visRaw = o.visits;
  if (!visRaw || typeof visRaw !== "object") {
    return null;
  }
  const vo = visRaw as Record<string, unknown>;
  const entRaw = Array.isArray(vo.entries) ? vo.entries : [];
  const entries: PopupLinkV1[] = entRaw
    .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "",
      href: typeof item.href === "string" ? item.href : "",
    }));
  const visits: SpeciesVisitsBlockV1 = {
    summary_label: typeof vo.summary_label === "string" ? vo.summary_label : "Visited:",
    entries,
    open_by_default: vo.open_by_default === true,
  };
  const margin =
    typeof o.location_heading_margin_px === "number" && Number.isFinite(o.location_heading_margin_px)
      ? o.location_heading_margin_px
      : 6;
  return { v: 1, location_heading_margin_px: margin, species_sections, visits };
}

/** Species-map matching pin — mirrors ``assemble_species_map_location_popup_html``. */
function popupHtmlSpeciesLayout(
  name: string,
  lifelistUrl: string,
  payload: SpeciesPopupPayloadV1,
): string {
  const margin =
    typeof payload.location_heading_margin_px === "number" &&
    Number.isFinite(payload.location_heading_margin_px)
      ? payload.location_heading_margin_px
      : 6;
  const locHeading = locationHeadingHtml(name, lifelistUrl);

  const sectionParts: string[] = [];
  for (const sec of payload.species_sections) {
    const openAttr = sec.open_by_default ? " open" : "";
    const summaryLabel = `${sec.common_name}: (${sec.observation_count})`;
    const obsLines: string[] = [];
    for (const obs of sec.observations) {
      const hrefSafe = safeHttpUrlForAnchor(obs.checklist_href.trim());
      const dt = escapeHtml(obs.datetime_label.trim() || "—");
      const count = escapeHtml(obs.observed_count.trim());
      let line =
        hrefSafe.length > 0
          ? `<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${dt}</a>`
          : `<span>${dt}</span>`;
      line += ` <span class="pebird-map-popup__obs-count">(Observed: ${count})</span>`;
      const mediaSafe = safeHttpUrlForAnchor(obs.media_href.trim());
      if (mediaSafe) {
        line += ` <a class="pebird-map-popup__media-link" href="${escapeHtml(mediaSafe)}" target="_blank" rel="noopener noreferrer" title="media">↗</a>`;
      }
      obsLines.push(`<div class="pebird-map-popup__obs-line">${line}</div>`);
    }
    sectionParts.push(
      `<details class="pebird-map-popup__species-seen"${openAttr}>` +
        `<summary class="pebird-map-popup__section-label">${escapeHtml(summaryLabel)}</summary>` +
        `<div class="pebird-map-popup__obs-list">${obsLines.join("")}</div>` +
        `</details>`,
    );
  }

  const visitAnchors: string[] = [];
  for (const e of payload.visits.entries) {
    const href = e.href?.trim() ?? "";
    const linkLabel = e.label?.trim() || href;
    if (href) {
      const hrefSafe = safeHttpUrlForAnchor(href);
      if (hrefSafe) {
        visitAnchors.push(
          `<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(linkLabel)}</a>`,
        );
      } else {
        visitAnchors.push(`<span class="pebird-map-popup__visit-link-text">${escapeHtml(linkLabel)}</span>`);
      }
    }
  }
  const visitsOpen = payload.visits.open_by_default ? " open" : "";
  const visitsBlock =
    `<details class="pebird-map-popup__all-visits"${visitsOpen}>` +
    `<summary class="pebird-map-popup__section-label">${escapeHtml(payload.visits.summary_label)}</summary>` +
    `<div class="pebird-map-popup__visit-list-inner">${visitAnchors.join("<br>")}</div>` +
    `</details>`;

  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">` +
    sectionParts.join("") +
    visitsBlock +
    `</div></div>`
  );
}

/** Family composition popup — mirrors ``format_family_location_popup_html``. */
function popupHtmlFamilyLayout(name: string, lifelistUrl: string, payload: FamilyPopupPayloadV1): string {
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading = locationHeadingHtml(name, lifelistUrl);
  const lineParts: string[] = [];
  for (const ln of payload.species_lines) {
    const n = ln.name.trim();
    if (!n) {
      continue;
    }
    const hrefSafe = safeHttpUrlForAnchor(ln.species_href.trim());
    if (hrefSafe) {
      lineParts.push(
        `<div class="pebird-map-popup__species-line"><a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(n)}</a></div>`,
      );
    } else {
      lineParts.push(`<div class="pebird-map-popup__species-line">${escapeHtml(n)}</div>`);
    }
  }
  const bodyHtml =
    lineParts.length > 0
      ? lineParts.join("")
      : '<div class="pebird-map-popup__summary-line">No species lines</div>';
  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">${bodyHtml}</div>` +
    `</div>`
  );
}

/** Lifer popup: location heading + species checklist lines (parity with ``format_lifer_popup_lines``). */
function popupHtmlLiferLayout(name: string, lifelistUrl: string, payload: LiferPopupPayloadV1): string {
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading = locationHeadingHtml(name, lifelistUrl);
  const lineParts: string[] = [];
  for (let i = 0; i < payload.lines.length; i += 1) {
    const ln = payload.lines[i];
    const prefix = i > 0 ? "<br>" : "";
    const hrefRaw = ln.checklist_href.trim() || "#";
    const hrefSafe = safeHttpUrlForAnchor(hrefRaw);
    const label = ln.label.trim() || "—";
    const dateStr = ln.date.trim() || "?";
    if (hrefSafe) {
      lineParts.push(
        `${prefix}<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          label,
        )} : ${escapeHtml(dateStr)}</a>`,
      );
    } else {
      lineParts.push(`${prefix}<span>${escapeHtml(label)} : ${escapeHtml(dateStr)}</span>`);
    }
  }
  const inner = lineParts.join("");
  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">` +
    `<div class="pebird-map-popup__visited-block">` +
    `<div class="pebird-map-popup__visit-dates">${inner}</div>` +
    `</div></div></div>`
  );
}

/** Classic All locations card — DOM mirrors ``assemble_location_popup_html`` / ``LocationPopupModel`` (``map_popup_models``). */
function popupHtmlVisitedLayout(
  name: string,
  lifelistUrl: string,
  visited: NonNullable<PopupPayloadV1["visited"]>,
): string {
  const label = visited.label?.trim() || "Visited:";
  const entries = visited.entries ?? [];
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading = locationHeadingHtml(name, lifelistUrl);

  const visitAnchors: string[] = [];
  for (const e of entries) {
    const href = e.href?.trim() ?? "";
    const linkLabel = e.label?.trim() || href;
    if (href) {
      const hrefSafe = safeHttpUrlForAnchor(href);
      if (hrefSafe) {
        visitAnchors.push(
          `<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(linkLabel)}</a>`,
        );
      } else {
        visitAnchors.push(`<span class="pebird-map-popup__visit-link-text">${escapeHtml(linkLabel)}</span>`);
      }
    }
  }
  /** Mirrors Folium ``build_visit_info_html``: ``<br>`` between *inline* checklist links — not ``display:block`` anchors. */
  const visitInner = visitAnchors.join("<br>");

  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">` +
    `<div class="pebird-map-popup__visited-block">` +
    `<div class="pebird-map-popup__section-label">${escapeHtml(label)}</div>` +
    `<div class="pebird-map-popup__visit-dates">${visitInner}</div>` +
    `</div>` +
    `</div></div>`
  );
}

/** Single Leaflet popup layout for structured `popup_v1` (+ legacy fallback). */
export function popupHtmlFromFeatureProps(props: Record<string, unknown> | undefined): string {
  const name = String(props?.name ?? "Location");
  const lifelistUrl = String(props?.lifelist_url ?? "");
  const liferPop = parseLiferPopupV1(props?.lifer_popup_v1);
  if (liferPop) {
    return popupHtmlLiferLayout(name, lifelistUrl, liferPop);
  }
  const familyPop = parseFamilyPopupV1(props?.family_popup_v1);
  if (familyPop) {
    return popupHtmlFamilyLayout(name, lifelistUrl, familyPop);
  }
  const speciesPop = parseSpeciesPopupV1(props?.species_popup_v1);
  if (speciesPop) {
    return popupHtmlSpeciesLayout(name, lifelistUrl, speciesPop);
  }
  const popup = parsePopupV1(props?.popup_v1);
  if (popup?.visited) {
    return popupHtmlVisitedLayout(name, lifelistUrl, popup.visited);
  }
  if (popup) {
    const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
    const locHeading = locationHeadingHtml(name, lifelistUrl);
    let html =
      `<div class="pebird-map-popup">` +
      `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>`;
    for (const line of popup.summary_lines ?? []) {
      html += `<span class="pebird-map-popup__summary-line">${escapeHtml(line)}</span>`;
    }
    for (const link of popup.links ?? []) {
      const href = link.href?.trim() ?? "";
      const label = link.label?.trim() || "Link";
      if (href) {
        const hrefSafe = safeHttpUrlForAnchor(href);
        if (hrefSafe) {
          html += `<span class="pebird-map-popup__summary-line"><a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
            label,
          )}</a></span>`;
        } else {
          html += `<span class="pebird-map-popup__summary-line">${escapeHtml(label)}</span>`;
        }
      }
    }
    html += "</div>";
    return html;
  }
  const visits = props?.visit_checklists;
  const url = String(props?.lifelist_url ?? "").trim();
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading = locationHeadingHtml(name, url);
  let legacy =
    `<div class="pebird-map-popup">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>`;
  if (visits != null && visits !== "") {
    legacy += `<span class="pebird-map-popup__summary-line">Checklists: ${escapeHtml(String(visits))}</span>`;
  }
  legacy += "</div>";
  return legacy;
}
