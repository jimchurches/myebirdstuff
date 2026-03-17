# Installing the eBird Data Explorer (Jupyter + Voila)

This guide walks you through setting up Python, Jupyter, Voila, and the **personal eBird explorer** notebook on your machine so you can explore your own eBird data on an interactive map. It covers **Windows** and **macOS**.

The explorer is a Jupyter notebook (`personal_ebird_explorer.ipynb`) that loads your eBird CSV export, lets you search for species, filter by date, and view everything on a map. You can run it in Jupyter (Notebook or JupyterLab) or as a clean dashboard using Voila.

> **No installation?** You can run the notebook on [Binder](https://mybinder.org) — just upload your CSV and go. See the **[Explorer README](README.md)** for the Binder quick-start.

---

## What you need before you start

- **Your eBird data**  
  Download your full eBird data export from [eBird.org](https://ebird.org) (My eBird → Manage My Data → Download My Data). You get a CSV file. The notebook expects it to be named `MyEBirdData.csv` by default (you can change this in the notebook).

- **This code**  
  Clone or download the `myebirdstuff` repo so you have the `notebooks` and `scripts` folders.

---

## 1. Install Python

You need Python 3.8 or newer (3.10 or 3.11 is a good choice).

### Windows

**Option A — Microsoft Store (simplest)**  
1. Open **Microsoft Store**.  
2. Search for **Python 3.11** (or 3.10).  
3. Click **Get** / **Install**.  
4. Confirm that **Python** and **pip** are available: open **Command Prompt** or **PowerShell** and run:
   ```bat
   python --version
   pip --version
   ```

**Option B — python.org**  
1. Go to [python.org/downloads](https://www.python.org/downloads/).  
2. Download the latest **Windows installer** for Python 3.  
3. Run the installer.  
4. **Important:** check **“Add Python to PATH”** before clicking Install.  
5. Finish the installer, then in Command Prompt or PowerShell run:
   ```bat
   python --version
   pip --version
   ```

### macOS

**Option A — python.org**  
1. Go to [python.org/downloads](https://www.python.org/downloads/).  
2. Download the **macOS installer** for Python 3.  
3. Run the `.pkg` and complete the steps.  
4. Open **Terminal** and run:
   ```bash
   python3 --version
   pip3 --version
   ```
   On macOS the commands are often `python3` and `pip3`.

**Option B — Homebrew**  
1. Install Homebrew if you don’t have it: [brew.sh](https://brew.sh).  
2. In Terminal:
   ```bash
   brew install python
   ```
3. Then:
   ```bash
   python3 --version
   pip3 --version
   ```

---

## 2. (Recommended) Create a virtual environment

A virtual environment keeps this project’s packages separate from the rest of your system.

**Windows (Command Prompt or PowerShell)**  
From the folder where you have the repo (e.g. `myebirdstuff`):

```bat
python -m venv venv
venv\Scripts\activate
```

Your prompt should start with `(venv)`.

**macOS (Terminal)**  
From the repo folder:

```bash
python3 -m venv venv
source venv/bin/activate
```

Your prompt should start with `(venv)`.

Keep this terminal open and use it for the steps below. To leave the environment later, run `deactivate`.

---

## 3. Install Jupyter, Voila, and required packages

With your virtual environment activated (or using your system Python if you skipped the venv), install everything in one go.

**Option A — from requirements file (recommended):**

```bat
python -m pip install -r requirements-explorer.txt
```

(On Windows, `python -m pip` is more reliable than `pip` when you have multiple Python installs. On macOS, use `pip3` if needed. Run from the repo root.)

**Option B — install packages directly:**

**Windows:**

```bat
python -m pip install jupyter jupyterlab voila pandas folium ipywidgets whoosh scikit-learn
```

**macOS:**

```bash
pip3 install jupyter jupyterlab voila pandas folium ipywidgets whoosh scikit-learn
```

(If you’re in a venv, you can use `pip` on macOS too.)

What these are for:

| Package      | Purpose |
|-------------|--------|
| `jupyter`   | Run the notebook in the browser (Notebook interface). |
| `jupyterlab`| Optional; alternative Jupyter interface. |
| `voila`     | Run the notebook as a dashboard (hides code and most text). |
| `pandas`    | Load and work with the eBird CSV. |
| `folium`    | Draw the interactive map. |
| `ipywidgets`| Search box and other controls in the notebook. |
| `whoosh`    | Fast species name search (autocomplete). |
| `scikit-learn` | BallTree for Map maintenance tab (duplicate/close location detection). |

**Note:** `branca` (used by folium for map elements) is installed automatically as a dependency of `folium`. `IPython` comes with `jupyter`.

---

## 4. Configure the data folder and CSV

The notebook looks for your eBird CSV in this order until it finds the file: (1) hardcoded path in User Variables, (2) config_secret.py, (3) config_template.py, (4) notebook folder (e.g. Binder uploads).

**Option A: Hardcoded path** — In the first code cell, set `DATA_FOLDER_HARDCODED = r"C:\Users\You\Documents\eBirdData"` (Windows) or `"/Users/you/Documents/eBirdData"` (macOS).

**Option B: Config file**

1. Open the **scripts** folder in the repo.  
2. Copy `config_template.py` to `config_secret.py` (so your personal paths aren’t in the template).  
3. Edit **scripts/config_secret.py** and set `DATA_FOLDER` to the folder that contains (or will contain) your eBird CSV.

**Examples:**

**Windows** (use raw string `r"..."` or forward slashes — no need to escape backslashes):

```python
DATA_FOLDER = r"C:\Users\YourName\Documents\eBirdData"
# or: DATA_FOLDER = "C:/Users/YourName/Documents/eBirdData"
```

**macOS:**

```python
DATA_FOLDER = "/Users/yourname/Documents/eBirdData"
```

4. Put your eBird export CSV in that folder and name it **MyEBirdData.csv** (or change the `EBIRD_DATA_FILE_NAME` variable in the first code cell of the notebook to match your filename).

**Species links and locale** — The notebook can add clickable eBird species links by fetching the eBird taxonomy once at startup (no API key). In the notebook’s **User Variables** cell, set **EBIRD_TAXONOMY_LOCALE** so common names match your export (e.g. `"en_AU"` for Australian English, `"en_GB"` for British; leave `""` for the API default). If the API is unavailable, the notebook runs without links.

The `config_template.py` file also has an example `GOOGLE_API_KEY`; that’s only used by the separate location-naming script in this repo, not by the explorer notebook. You can ignore it for the explorer.

---

## 5. Run the notebook

You need to run Jupyter (or Voila) from the **notebooks** folder so the notebook can find `../scripts/config_secret.py`.

**Windows:**

```bat
cd path\to\myebirdstuff\notebooks
jupyter notebook
```

Or with JupyterLab:

```bat
cd path\to\myebirdstuff\notebooks
jupyter lab
```

**macOS:**

```bash
cd /path/to/myebirdstuff/notebooks
jupyter notebook
```

Or:

```bash
cd /path/to/myebirdstuff/notebooks
jupyter lab
```

A browser window will open. Click **personal_ebird_explorer.ipynb**. Use **Run → Run All Cells** (or run cells from top to bottom). Once everything has run, scroll down to the search box and map and start exploring.

---

## 6. (Optional) Run as a Voila dashboard

Voila runs the same notebook as a clean dashboard: only the controls and map, no code or long instructions.

From the **notebooks** folder:

**Windows:**

```bat
cd path\to\myebirdstuff\notebooks
voila personal_ebird_explorer.ipynb --config=voila.json
```

**macOS:**

```bash
cd /path/to/myebirdstuff/notebooks
voila personal_ebird_explorer.ipynb --config=voila.json
```

The `voila.json` in the notebooks folder hides the documentation cells so only the search UI and map are shown. A browser tab will open with the dashboard.

---

## Quick reference

| Step | What to do |
|------|------------|
| 1 | Install Python 3.8+ (Windows: Store or python.org; macOS: python.org or Homebrew). |
| 2 | (Optional) Create and activate a virtual environment. |
| 3 | `python -m pip install -r requirements-explorer.txt` (or install packages individually; see step 3). |
| 4 | Set `DATA_FOLDER_HARDCODED` in the notebook, or copy `config_template.py` → `config_secret.py`, set `DATA_FOLDER`, put `MyEBirdData.csv` there. |
| 5 | From **notebooks** folder: `jupyter notebook` or `jupyter lab`, open `personal_ebird_explorer.ipynb`, Run All Cells. |
| 6 | (Optional) From **notebooks** folder: `voila personal_ebird_explorer.ipynb --config=voila.json` |

---

## Troubleshooting

- **“No module named …”**  
  Install the missing package, e.g. `python -m pip install pandas` (or `pip3 install pandas` on macOS). The list in step 3 should cover everything the notebook uses. The notebook will show the exact command if a dependency is missing.

- **Config or CSV not found**  
  Make sure you’re starting Jupyter/Voila from the **notebooks** folder so `../scripts/config_secret.py` points to the repo’s scripts folder.  
  Check that `DATA_FOLDER` in `config_secret.py` uses the correct path and that `MyEBirdData.csv` (or your chosen filename) is in that folder.

- **Windows path in config**  
  Use a raw string: `r"C:\Users\You\Documents\eBirdData"` or forward slashes: `"C:/Users/You/Documents/eBirdData"`.

- **macOS: `python` vs `python3`**  
  Use `python3` and `pip3` if that’s what your install provides; inside a venv, `python` and `pip` are usually enough.

If you hit something else, the error message and the step you were on (e.g. “first time running the notebook”, “running Voila”) are usually enough to narrow it down.
