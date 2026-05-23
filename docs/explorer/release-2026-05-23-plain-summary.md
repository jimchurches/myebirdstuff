# Release 2026-05-23 — Plain-language performance summary

**Audience:** Release notes, future you, reviewers.  
**Technical tables & re-run commands:** [`release-2026-05-23-baseline.md`](release-2026-05-23-baseline.md)  
**Leaflet cutover context:** [`issue-222-plain-summary.md`](issue-222-plain-summary.md)

---

## Headline

**Build `2026-05-23`** is the performance-themed beta promotion: custom Leaflet maps, session caching, faster tab prep, and hygiene refactors. A fresh automated baseline on your scale of data shows **the same story as issue #222** — not a second revolution, but **confirmation** that hygiene work did not regress the wins you already had.

---

## What still feels true on a full export (~46k rows, ~5.6k places)

### 1. Coming back to All locations is still effectively free (on the server)

After you have opened All locations once, switch to Lifer, then return to All:

- **Warm payload prep:** about **0.1 ms** (LRU cache hit).
- That matches the #222 baseline and is the behaviour you want day to day.

### 2. First full load is still “tens of seconds,” not instant

**Time until the All locations banner appears** on the real export in this run: about **20 seconds** (vs ~19 s in the #222 table). That is normal machine-to-machine noise, not a new slowdown.

Most of that is still: load CSV, warm taxonomy links, build thousands of popup records — not “the map widget is slow.”

### 3. First All-locations build is still ~5–6 seconds of server work

Cold build for ~5,594 pins: about **5.5 s**, with almost all of that in popup/visit preparation (~5.3 s). Same order of magnitude as #222 (~5.8 s).

### 4. First Lifer visit improved in this run

First Lifer payload on the real file: about **7.1 s** (338 pins) vs ~9.3 s in the #222 capture. Treat as **encouraging variance** unless a later run shows regression — not a guaranteed new product optimisation.

### 5. The old Folium “embed tax” is still gone

`component_embed` on the server remains **tens of milliseconds**, not multi-second Folium iframe packaging.

---

## What we measured extra for this release

| Check | Result |
|-------|--------|
| **Hygiene branch** re-run of the standard four-map perf journey | All / Lifer / warm All numbers align with #222 |
| **Fixture CSV** (15 places) | Cache hits and tiny payload times still sane for CI |
| **Species / Family in the robot test** | Run **stopped** on Species banner (Grey Teal not detected after searchbox) — **not** a sign the map modes are broken; see baseline doc |

So: **headline map performance for release sign-off is OK.** The gap is **automation completeness** for Species/Family banner waits, not user-visible All/Lifer regression.

---

## Honest “in betweens”

- **Cold start** on a life-list export is still long (~20 s to banner).
- **Warm `prep.map_context_prepare`** on mode switches was **~1.9 s** per hop on the real file in this run — higher than the single cold row quoted in #222; worth watching if mode switching feels heavier, but separate from payload LRU hits.
- **Exported HTML maps** and **popup scroll hints** were fixed/restored on the branch; they do not change the JSONL headline table.
- Numbers are from **one macOS dev run**; use [`release-2026-05-23-baseline.md`](release-2026-05-23-baseline.md) to re-run locally.

---

## One-sentence summary for release notes

**Release 2026-05-23 keeps the Leaflet performance profile: ~20 s to first map on a full export, ~5.5 s to build All locations once, nearly instant server prep when you return to All after another map mode, and no return of the old multi-second Folium embed bottleneck — with hygiene refactors showing no meaningful regression in those headline timings.**

---

## Where the numbers live

- **Tables:** [`release-2026-05-23-baseline.md`](release-2026-05-23-baseline.md)
- **Re-run:** `./scripts/run_release_perf_baseline.sh --real`
- **Gitignored archives:** `benchmarks/map_perf/snapshots/release-2026-05-23-*.jsonl`
