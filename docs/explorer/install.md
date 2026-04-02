# Installing the Personal eBird Explorer (Local)

#### Documentation

- *Personal eBird Explorer*: [`docs/explorer/README.md`](README.md)
- *Getting started*: [`docs/explorer/getting-started.md`](getting-started.md)
- *Install*: [`docs/explorer/install.md`](install.md)
- *Feedback*:[`docs/explorer/install.md`](feedback.md)

## Install

This guide covers a **local installation** of the Streamlit app on:

- macOS  
- Windows  

It focuses only on getting the app running locally.

### Overview

You will:

1. Install Python (external documentation)
2. (Optional) Create a virtual environment
3. Download the application from GitHub
4. Install required Python packages
5. Configure your eBird data file (optional but recommended)
6. Run the Streamlit app

---

### 1. Install Python

Python installation is outside the scope of this project.

Follow the official documentation:

- macOS: https://docs.python.org/3/using/mac.html#using-python-for-macos-from-python-org  
- Windows: https://docs.python.org/3/using/windows.html#python-install-manager  

#### Notes

- Install a recent Python 3 version (3.11+ recommended)
- More advanced users may prefer tools like Homebrew (macOS) or package managers on Windows

---

### 2. (Optional but Recommended) Virtual Environment

A virtual environment keeps project dependencies isolated from your system Python.

Official documentation:
https://docs.python.org/3/library/venv.html

#### Create and activate

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate
```

---

### 3. Download the Application

You can obtain the code from GitHub:

#### Option A — Download a release (recommended)
- Download the `.zip` from the Releases page

#### Option B — Download from a branch
- Use the "Code → Download ZIP" option

#### Option C — Git (developers)
- Clone the repository
- Assumes you already understand Git workflows

---

### 4. Extract the Files

Unzip the downloaded archive to any folder.

The application does **not** need to be installed system-wide.

---

### 5. Install Python Requirements

Using your local command line console, `terminal` or `powershell`, install requirements from
the root of the new application directory:

```bash
pip install -r requirements.txt
```

This installs all required dependencies for the Streamlit app.

---

### 6. Configure Your Data (Optional but Recommended)

The app can run without configuration, but you will need to upload your eBird CSV each time.

To enable automatic loading and saved settings, create a config file.

---

#### Option A — Standard users (recommended)

1. Copy:
```
config/config_template.yaml
```

2. Create:
```
config/config.yaml
```

3. Edit `config.yaml` and set:

```yaml
data_folder: /path/to/your/ebird/data
```

- This folder should contain your eBird export CSV
- The CSV does **not** need to be in the project directory

---

#### Option B — Git users / developers

Use:
```
config/config_secret.yaml
```

This avoids accidentally committing personal paths.

Note:
- Both config files are excluded via `.gitignore`
- `config_secret.yaml` is optional but retained as a safety measure

---

### 7. Run the Application

From the downloaded application root:

```bash
streamlit run explorer/app/streamlit/app.py
```

This will:

- start a local web server  
- open the app in your browser  

---

### Notes

- If no config file is present:
  - you must upload your eBird CSV manually each time
  - settings are not persisted

- If configuration is set:
  - your dataset loads automatically
  - app settings can persist between sessions

---

