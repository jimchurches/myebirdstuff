# Map HTML export — UX design notes and alternative approach

**Audience:** Maintainers and coding agents (not end-user documentation).  
**Status:** The app ships the **one-click** flow described in §1. The **two-button** flow in §4 is a documented fallback if users report failed or confusing exports.

**Related:** [#222](https://github.com/jimchurches/myebirdstuff/issues/222) · `explorer/components/all_locations_map/TODO.md` (§18) · `explorer/app/streamlit/app_prep_map_ui.py` · `explorer/app/streamlit/app_map_ui.py`

---

## 1. Shipped behaviour (May 2026)

Sidebar control: single **`st.button`** labelled **“Export map HTML”**.

1. User clicks once.
2. If export bytes are not already in session or the Leaflet export LRU (`LEAFLET_EXPORT_HTML_CACHE_KEY`), build runs with **`st.spinner("Building map HTML…")`** via `_materialize_leaflet_export_html` (lazy — no export work on ordinary map reruns; recipe stored in `LEAFLET_EXPORT_RECIPE_KEY` by `_sync_leaflet_export_recipe` only).
3. Bytes are stored in `EXPLORER_MAP_HTML_BYTES_KEY` + `LEAFLET_EXPORT_BUILT_CACHE_KEY`.
4. `st.session_state[EXPORT_MAP_HTML_AUTO_DOWNLOAD_KEY]` is set and **`st.rerun()`** runs.
5. On the next run, a real **`st.download_button`** (same label) is rendered with the finished bytes; **`inject_auto_click_streamlit_download_js`** (in `app_map_ui.py`) programmatically clicks that button in **`window.parent.document`** (retries at 50 / 200 / 500 ms).
6. Caption **“Starting download…”** appears on the auto-download run; the download button stays visible as a manual fallback.

**Design goals preserved:**

| Goal | How |
|------|-----|
| Lazy export | HTML built only when the user uses Export, not on every map rerun |
| Map tab stays fast | Recipe sync is cheap; heavy `leaflet_map_to_html_bytes` only on export |
| Clear feedback | Spinner on build; caption on download pass; `st.error` via `EXPORT_MAP_HTML_ERROR_KEY` on failure |
| Repeat export | Session + LRU skip rebuild when the map recipe is unchanged |

---

## 2. Why Streamlit makes this awkward

- **`st.download_button`** needs file bytes when the widget is wired for that run. Building in an `on_click` callback on the *same* interaction often leaves users clicking again — the download for click *N* may still use empty or stale `data=` from before the build finished.
- The old **two-widget** pattern (`st.button` → build → `st.rerun()` → `st.download_button`) worked but felt like “nothing happened” because both steps used the **same label** (“Export map HTML”).
- **`st.components.v1.html`** runs in a **sandboxed iframe**. Creating a Blob and `<a download>` *inside* that iframe frequently produces **spinners with no file** (build succeeds; save does not). Do not revive that approach.

---

## 3. Approaches considered (history)

| Approach | Result |
|--------|--------|
| `st.button` + `st.rerun()` + `st.download_button` (same label) | Works; **confusing** (feels like broken double-click) |
| `st.download_button` + `on_click` build | Unreliable one-click; still often needs a second click |
| Blob / anchor inside `st.components.v1.html` | **Failed** in practice (iframe); high block risk |
| **Current:** build → rerun → `st.download_button` + parent-frame `.click()` | **Shipped**; one click on desktop Safari/macOS in maintainer testing |
| **Alternative (§4):** explicit Prepare + Download buttons | Not shipped; fallback design |

---

## 4. Alternative approach — two explicit buttons (fallback)

**Use this if users report:** export spins but no file; needing to click many times; confusion about whether anything ran; auto-download blocked in corporate/mobile browsers.

Two controls with **different verbs** — not two buttons both saying “Export”.

### Suggested labels

**Option A (preferred wording)**

| Control | Label | State |
|---------|--------|--------|
| 1 | **Prepare map export** | Always enabled (rebuild allowed) |
| 2 | **Download map HTML** | **Disabled** until build succeeded for current recipe |

Short caption under the pair: *“Prepare first, then download.”*

**Option B (shorter)**

| Control | Label |
|---------|--------|
| 1 | **Build export** |
| 2 | **Save HTML file** |

### UI behaviour

- **Initially:** Prepare enabled · Download disabled (greyed).
- **User clicks Prepare:** `st.spinner` during `_materialize_leaflet_export_html`; on success store session bytes + LRU; **enable Download**; optional `st.success("Export ready")` or caption with approximate size.
- **User clicks Download:** native `st.download_button` only — **no JavaScript**, no auto-click.
- **Map / recipe changes** (`_sync_leaflet_export_recipe` clears stale bytes): **disable Download** again until the next successful Prepare.
- **Build error:** Download stays disabled; show `st.error` on Prepare.
- **Unchanged map, already prepared:** Download stays enabled → **one click** for repeat save (same as today’s LRU/session benefit).

### Implementation sketch (when implementing)

- Replace `_render_leaflet_export_map_html_download` in `app_prep_map_ui.py`.
- Remove `EXPORT_MAP_HTML_AUTO_DOWNLOAD_KEY` and `inject_auto_click_streamlit_download_js` (or keep JS unused).
- Keys: e.g. `EXPORT_MAP_HTML_PREPARE_BTN_KEY`, `EXPORT_MAP_HTML_DOWNLOAD_BTN_KEY` in `app_constants.py`.
- Reuse `_leaflet_export_download_bytes`, `_materialize_leaflet_export_html`, `_sync_leaflet_export_recipe` — **no change** to lazy recipe or LRU policy.
- Style both with `inject_sidebar_outline_download_button_css` (extend selectors if Prepare is `st.button` only).

### Trade-offs vs shipped one-click

| | One-click (shipped) | Two-button (alternative) |
|--|---------------------|---------------------------|
| User gestures (cold) | 1 (when auto-click works) | 2 (always clear) |
| Browser / policy risk | Low–medium (see §5) | **Very low** |
| UX clarity | Excellent when it works | **Excellent always** |
| Maintenance | DOM label match + timing retries | Streamlit-native only |

---

## 5. Risk assessment — shipped auto-click script

The file is **not** saved by custom script logic. The script only **clicks Streamlit’s real download button**, which uses Streamlit’s normal server → browser download path (same as a manual click on that widget).

### Unlikely to block (typical desktop)

- macOS Safari, Chrome, Firefox (maintainer tested Safari — OK)
- Windows Chrome / Edge
- Repeat export in the same session when bytes are already built

### Higher risk (plan for §4 or manual second click)

| Scenario | Likelihood | Notes |
|----------|------------|--------|
| Strict corporate browser policy | Medium | May restrict programmatic clicks or downloads from embedded UIs |
| Mobile browsers / in-app WebViews | Medium–higher | Smaller targets, different gesture rules, sidebar layout |
| Privacy extensions | Low–medium | Rare; usually same-origin UI clicks are fine |
| “Download without user gesture” rules | Low here | User clicked Export; rerun + auto-click is chained in practice but **not guaranteed** across reruns by browsers |

### What was likely to block (avoid)

**Blob + `<a download>` inside `st.components.v1.html`** — common failure mode (sandboxed iframe, no user gesture on that document). That was abandoned for good reason.

### Residual risks — current script

1. **Timing** — Retries at 50 / 200 / 500 ms if the download button is not in the DOM yet; very slow runs might still miss → user can click the visible download control on the auto-download run.
2. **Label matching** — Script matches button text exactly `"Export map HTML"`; label changes break auto-click (manual download still works).
3. **Multiple download buttons** — Selects from all `[data-testid="stDownloadButton"] button` (last match with label); unusual duplicate labels could mis-fire.
4. **Streamlit DOM changes** — `data-testid="stDownloadButton"` is stable in practice but not a public API; major Streamlit UI changes could break auto-click.

### Bottom line

For the expected audience (desktop, normal settings): **blocking is unlikely**. Do not promise “one click everywhere” without qualification. The two-button design (§4) removes dependence on programmatic click if reports accumulate or if you want zero grey-area before a release.

---

## 6. Regression / support checklist

**Shipped flow — quick test**

1. Open Map tab with data loaded.
2. Click **Export map HTML** once (cold build).
3. Expect spinner, brief rerun, then browser save dialog / `ebird_map.html` (see `MAP_EXPORT_HTML_FILENAME` in `streamlit_ui_constants.py`).
4. Click again without changing map — should be fast (LRU/session).

**If user reports failure**

- Ask: browser, OS, corporate device?, did “Starting download…” appear?, second visible Export button?
- Consider switching to §4 two-button UX in a small PR.
- Do not reintroduce iframe Blob download.

---

## 7. Key code locations

| Piece | Location |
|-------|----------|
| Sidebar export UI | `explorer/app/streamlit/app_prep_map_ui.py` — `_render_leaflet_export_map_html_download` |
| Auto-click JS | `explorer/app/streamlit/app_map_ui.py` — `inject_auto_click_streamlit_download_js` |
| Session keys | `explorer/app/streamlit/app_constants.py` — `EXPORT_MAP_HTML_*`, `LEAFLET_EXPORT_*`, `EXPLORER_MAP_HTML_BYTES_KEY` |
| HTML build | `explorer/presentation/leaflet_map_html_export.py` — `leaflet_map_to_html_bytes` |
| Export LRU | `explorer/presentation/leaflet_map_export_cache.py` + `_leaflet_export_html_cache_*` in `app_prep_map_ui.py` |
| Backlog | `explorer/components/all_locations_map/TODO.md` — §18 |
