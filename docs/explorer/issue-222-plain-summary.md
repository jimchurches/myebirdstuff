# Issue #222 — Plain-language performance summary

**Audience:** Future you, reviewers, and anyone not deep in the Leaflet cutover.  
**Technical tables & re-run commands:** [`issue-222-section-8-baseline.md`](issue-222-section-8-baseline.md) · prior art: [`issue-222-section-8-prior-art.md`](issue-222-section-8-prior-art.md)

---

## Headline: The map is the same app, but the engine underneath changed

Explorer’s maps used to be built one way (Folium: big HTML pages assembled in Python and stuffed into the page). They now use a **custom Leaflet map** (lighter data sent to the browser; the map draws pins and popups there).

**What you still get:** All locations, species, lifer, and family maps, with the same kinds of popups, banners, legends, clustering, and export ideas you cared about.

**What changed behind the scenes:** Less repeated heavy work on each refresh, and a clearer split between “prepare the data once” vs “show the map.”

---

## The big wins (things that genuinely got better)

### 1. Switching back to a map you already opened is much faster

On your **real** eBird file (~5,600 places):

- **First time** opening “All locations” in a session: about **6 seconds** of server work to prepare pin + popup data.
- **Switch away** (e.g. to Lifer), then **come back to All locations**: about **a tenth of a millisecond** for that prep step — effectively instant on the server side, because the app **remembers** the bundle it already built.

That’s one of the most important practical wins: **browsing between map modes doesn’t keep paying the full “build everything again” cost** when nothing important changed.

### 2. The old “embed the map” bottleneck is largely gone (on the server)

In the old setup, a step often called “put the map in the page” could sit around **~7 seconds** on a large file — and it happened repeatedly during a session.

On Leaflet, the equivalent **server** step is now on the order of **tens of milliseconds**, not seconds. The slow part moved to **first load** and **first time you build a given view**, not “every time we slot the map into Streamlit.”

**In everyday terms:** the app is no longer spending many seconds over and over on “packaging the map for the iframe” the way it used to.

### 3. First full load is somewhat better — but still not “instant”

On your real data, **time until the All locations banner appears** was roughly:

| | Rough time |
|---|------------|
| **Old Folium era** (similar-sized file) | ~**25 seconds** |
| **Leaflet now** | ~**19 seconds** |

So: **noticeably better on cold open**, but still **tens of seconds**, not a snap. A chunk of that is still “load your big CSV, warm up species links, build thousands of popup records,” not the map widget itself.

### 4. Popups are built smarter, not as thousands of mini web pages

Before: the server could spend a huge share of time generating **HTML for every pin**, even if you only opened a few popups.

Now: the server sends **structured facts** (names, links, visit lists) and the map **renders the popup when you click**. On your file, the first All-locations build still takes ~**6 seconds** because it still prepares visit lists for every location — but it’s a different, more maintainable kind of work, and it **caches** for return visits.

### 5. You’re less likely to break the map without noticing

We added **guardrails** so changes don’t silently regress:

- Automated checks that the map **still builds**, **tests run**, and **dependency audits** run in CI.
- Performance logging you can turn on (`EXPLORER_PERF`) records **named steps** (load data, build All locations bundle, switch to Lifer, etc.) so “it feels slower” can be compared to numbers later.
- A **repeatable script** on your machine: small test file (~15 places) vs your real `MyEBirdData.csv` in `tests/fixtures/` (gitignored).

---

## The “in betweens” (better, but not magic)

### Cold start is still heavy on a full life list

**~19 seconds** to first map banner on ~46k rows is **real progress** vs ~25s, but it’s still “go make a coffee” territory. Most of that isn’t “Leaflet vs Folium” alone — it’s **loading and preparing a large personal dataset**.

### Lifer view’s first visit is still slow on a big file

First switch to **Lifer locations** on your export: about **9 seconds** of prep (hundreds of pins, not thousands). Fine once cached in the same session pattern, but **the first hop to Lifers still hurts** on a big export.

### We only auto-measured two map modes in the robot test

The standard perf journey exercises **All locations** and **Lifer**, then **back to All** (to prove the cache). **Species** and **Family** maps weren’t in that automated run — they’re documented for **manual** timing if you care later.

### “Embed” time in the logs ≠ “map feels finished”

The tables distinguish:

- **Server prep** (Python timers) — now often tiny except on first build.
- **First paint** (browser test) — what you actually wait for, including Streamlit, iframes, and the browser drawing **thousands of clustered pins**.

So a row showing **~29 ms** for “component embed” does **not** mean the map finished drawing in 29 ms — it means **that one server bookkeeping step** is fast. The **~19 s** “first paint” row is closer to what you felt waiting for the banner.

---

## Losses or trade-offs (honest list)

| Area | Reality |
|------|--------|
| **Absolute cold load** | Still long on a full export; we didn’t turn a huge CSV into a 2-second app. |
| **All-locations first build** | Still ~6 s of server work on ~5.6k pins — visit lists for every site add up. |
| **Historical comparison** | Old numbers were Folium + different bottlenecks; we compare **narratively**, not as a strict apples-to-apples benchmark lab. |
| **Cloud vs laptop** | Your “feels ~33% faster on beta” observation is subjective; the **logged** cold numbers are what we can defend in an issue. |
| **Species / Family perf** | Not in the automated “headline” table yet. |

Nothing here suggests we **threw away** richness (popups, links, banners) for speed — the project explicitly kept **like-for-like behaviour** and measured after.

---

## One-sentence summary for future you

**Leaflet didn’t make a huge eBird export feel instant, but it removed the old multi-second “embed the map again” tax, made returning to All locations after another view nearly free on the server, shaved roughly a few seconds off the first full load, and gave you tests + logs so the next slowdown is easier to spot — without giving up the detailed map you wanted.**

---

## Where the numbers live (when you want them again)

- **Issue #222** on GitHub — comment threads with small test file vs real `MyEBirdData.csv` tables.
- **`docs/explorer/issue-222-section-8-baseline.md`** — same story with tables and how to re-run.
- **Re-run on your machine:** `./scripts/run_post_leaflet_perf_baseline.sh` (fixture) or `./scripts/run_post_leaflet_perf_baseline.sh --real` (uses `tests/fixtures/MyEBirdData.csv`).
