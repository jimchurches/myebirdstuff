# Getting started — Personal eBird Explorer

#### Documentation

- *Getting started*: [`docs/explorer/getting-started.md`](getting-started.md)
- *Install*: [`docs/explorer/install.md`](install.md)
- *Personal eBird Explorer*: [`docs/explorer/README.md`](README.md)

## Getting Started

The Personal eBird Explorer is a *Streamlit app* for exploring your personal eBird export (CSV) with interactive maps and a rich summarised table views of various statistics.

---

## Try it first (recommended): Streamlit Community Cloud

If you just want to try it without installing anything locally, use the hosted app:

- **Streamlit Community Cloud app**: https://personal-ebird-explorer.streamlit.app/

### Trade-offs vs local run

**Pros**
- No local install required  
- Quick way to explore the app  

**Cons**
- Slower for large datasets  
- You must upload your CSV each session (no saved state)

---

### Run locally

For local installation and setup, follow:

👉 [`docs/explorer/install.md`](install.md)

Running locally provides:

- Automatic dataset loading (via config file)  
- Saved application state between runs  
- No need to re-upload your CSV each session  
- Better performance for large datasets (depending on local hardware)

---

## Download / update the app code

### Option A — Download ZIP (simplest)

- Download a `.zip` from GitHub
- Extract it to a folder of your choice

👉 [`docs/explorer/install.md`](install.md)

### Option B — Git (developers)

- Clone the repository
- Use your normal Git workflow

If using ZIP downloads, update by replacing the folder with a newer version  
(keep your `config/config.yaml` or `config/config_secret.yaml`).

---

## Summary

- Streamlit Cloud → quick demo, no install, casual and occational use  
- Local install → faster, persistent, better experience  (depending on local hardware)

