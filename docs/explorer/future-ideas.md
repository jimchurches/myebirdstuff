# eBird Explorer: Future Ideas

Notes for when you come back to this—perhaps on a cold Canberra winter weekend. Documented after a discussion about sharing the personal eBird explorer with non-technical friends, especially across platforms (Windows was problematic).

---

## Decision

Use **Streamlit** as the primary front end moving forward.

## Rationale

The modular refactor has made the codebase much easier to evolve, and there are still many higher-value feature improvements to deliver before a front-end migration would pay off.

The current UI is functional but not yet as modern or accessible as a future packaged application could be. However, installation, usability, and polish can still be improved incrementally without committing to a rewrite.

The map remains the centre of the product and the recent refactor means the core logic is now portable if a future front-end migration becomes worthwhile.

## Near-term direction

- Continue feature development on the current platform.
- Improve usability and install/run experience.
- Avoid hosting costs and major front-end rework for now.

## Reassess when

Revisit the front-end/platform decision if installation friction, user growth, or UI limitations become a clear blocker.

---

## Background and options (for when you revisit)

The sections below capture earlier thinking and options that may be useful when revisiting the decision.

---

## Would a Web Page for Others Change the Answer?

Somewhat. Sharing with others usually means either:

- Hosting something somewhere, or
- Creating a zero-install, in-browser experience.

The tool (Streamlit vs alternatives) matters less than how you distribute it.

---

## Making It Easy for Non-Technical People

The main friction is: Python installation, pip, config paths, and the many small setup differences between Windows and macOS.

### Option 1: Self-Contained HTML File (Easiest for Recipients)

- **What:** One HTML file the user opens in a browser. A “Choose file” button lets them select their MyEBirdData.csv. Everything runs client-side (no server, no install).
- **Tech:** Leaflet (maps), PapaParse or similar (CSV), vanilla JS or a small framework.
- **Pros:** Zero install, no Python, works on any OS. “Put the HTML and your CSV in the same folder, double-click the HTML.”
- **Cons:** Requires reimplementing the logic in JavaScript. Species search can be simpler (e.g. prefix match) rather than Whoosh-level fuzzy search.

This is the most “just works” option for friends who don’t want to install anything.

### Option 2: Hosted Web App

- **What:** You host the app (Streamlit Community Cloud, a VPS, etc.). Users get a URL and upload their CSV in the browser.
- **Pros:** Zero install for them.
- **Cons:** Privacy (data goes through your server), hosting cost and maintenance.

### Option 3: Simpler Python Packaging

- **What:** One script, clear `pip install` instructions, no config file, sensible default paths.
- **Pros:** Fewer “little stupid things” that break.
- **Cons:** Still requires Python and pip; doesn’t remove the install step.

### Option 4: Installer Script (Python Does Everything After Step 1)

- **What:** (1) Document for installing Python on Windows and macOS (already exists). (2) A Python script that installs everything else: pip packages, prompts for DATA_FOLDER, creates config_secret.py, sets up launcher scripts (`.command` on macOS, `.bat` on Windows) to run the app.
- **Feasibility:** Very realistic. Once Python is installed, a single cross-platform script can: run `pip install` via subprocess; create config files with pathlib; write launcher scripts that `cd` to the project and run the app.
- **What the script can’t do:** Install Python itself, or fix antivirus blocking pip. On macOS, avoid system Python; script should assume user has installed Python (python.org or pyenv).
- **When to do it:** If you get more requests from friends to help them install this, it’s worth the time to build and test the installer on Windows.

---

## Summary

| Goal | Approach |
|------|----------|
| Personal use | Streamlit app is fine; no need to change. |
| Share with non-technical friends | Self-contained HTML file = no install, works everywhere. |
| Share as a public web page | Hosted app; consider privacy and hosting. |

For “friend on Windows, no fuss”: single HTML file with a CSV file picker is the most friction-free option. The trade-off is reimplementing the app in JavaScript, but the core features (search, filters, map) are all achievable.
