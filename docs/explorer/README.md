# Personal eBird Explorer

Primary UI: **Streamlit** (map + tabs).

Start here:

- **Getting started**: [`docs/explorer/getting-started.md`](getting-started.md)
- **Streamlit app README** (details): [`streamlit_app/README.md`](../../streamlit_app/README.md)

## What it does

- **Map** — All checklist locations (green pins); optional species filter (red pins, lifer/last-seen highlights).
- **Search** — Type-ahead species search; “show only selected species” to hide other locations.
- **Tabs** — Map, Checklist Statistics, **Rankings & lists**, Yearly Summary, **Country**, Maintenance, **Settings** (duplicates / close locations, incomplete checklists, sex notation in comments; table limits and Country tab sort order).
- **Country** — Per-country yearly-style stats (sparse year columns). When the export resolves to a **2-letter country code** (from `Country` or `State/Province`), **Lifers (country)** has an **⧉** link to that region’s eBird life list (e.g. [Australia](https://ebird.org/lifelist?r=AU)) and **Total checklists** has **⧉** to [my checklists for that country](https://ebird.org/mychecklists/FR) (example: France). Unknown or non-ISO keys have no links.
- **Export** — “Export Map HTML” saves the current map view.
- **Date filter** — Optional date range.
- **Species links** — Species names in the map banner, rankings tables, and maintenance tab link to eBird species and lifelist pages. Names are resolved using the eBird taxonomy API (fetched once at startup; no API key). Set `STREAMLIT_EBIRD_TAXONOMY_LOCALE` / `EBIRD_TAXONOMY_LOCALE` for the first-visit default, or change **Settings → Taxonomy**.

## Missing checklist times (synthetic 23:59)

Some checklist rows in an eBird export have **no time** (blank time, or eBird uses `00:00` when no time was recorded). That can happen for example when:

- observations were entered via **Merlin** rather than the eBird app  
- a checklist was **generalised** to protect a sensitive location  
- occasional **data entry quirks** or older exports with incomplete times  

The explorer builds a single **`datetime`** column for sorting visits (map popups, banners, etc.). For rows with **no meaningful time**, the loader assigns a **synthetic time of 23:59** on that date so that:

- sorting stays stable and predictable  
- those rows sort **after** other observations on the **same calendar day**

**Important:** **23:59** in the app is often a **placeholder**, not proof that you birded at one minute to midnight. Treat it as “time unknown for this row.”

Implementation detail: see `add_datetime_column()` in `personal_ebird_explorer/data_loader.py`. A fuller testing narrative (fixture counts) is in [`tests/fixtures/ebird_integration_fixture_notes.md`](../../tests/fixtures/ebird_integration_fixture_notes.md).

**You need:** Your eBird data export (CSV). Download from [eBird.org](https://ebird.org) → My eBird → Manage My Data → Download My Data.

## Screenshot

<!-- Placeholder: add a screenshot of the map tab (e.g. map with search and pins) when available. -->

*Screenshot placeholder — add an image of the map tab when available.*

---

## Install / run

See [`streamlit_app/README.md`](../../streamlit_app/README.md) for:

- **Run locally**: venv + `pip install -r requirements.txt` + `streamlit run streamlit_app/app.py`
- **Streamlit Community Cloud**: set the main file path and the requirements file
