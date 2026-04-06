# UI.Vision Macros for eBird

Browser automation tools for working with eBird checklists and locations.

These macros are designed for a personal workflow and interact directly with the live eBird system.

Target audience: users comfortable with basic scripting and browser automation.

---

## What these macros do

- Create incidental checklists from structured clipboard data  
- Rename and manage personal locations  
- Integrate with a GPS → location naming script  

---

## ⚠️ Responsible use

These tools interact directly with the live eBird system.

eBird is a global citizen-science platform. Data submitted becomes part of a shared scientific dataset.

Use responsibly:

- Do not submit fake or incomplete test data  
- Do not create unnecessary or misleading locations  
- Do not flood the system with automated submissions  

Always:

- Test carefully and clean up test data  
- Ensure submissions are accurate  
- Use automation to assist, not replace, observation  

---

## How it works

This workflow combines:

- Apple Shortcut → captures observations (voice + GPS + time)  
- UI.Vision macro → processes clipboard data  
- Python script → converts GPS to readable location names  

These components work together but can also be used independently if required.

---

## Setup (high level)

- Install UI.Vision in your browser (see https://ui.vision)  
- Install Python and required packages  
- Configure the GPS script (API key)  
- Load macros into UI.Vision  

---

## Configuration and usage notes

The macros are currently configured for safe testing by default.

Before using them for regular (“live”) use, you will likely need to review and adjust a small number of parameters in the macro code. These control behaviours such as:

- whether a checklist is automatically submitted  
- whether the macro stops before final submission (for review)  
- whether dictation text is added to checklist comments  

You will also need to update environment-specific settings, including:

- the path to your Python installation (used by the GPS script)  
- any OS-specific path handling (macOS vs Windows)  

The incidental checklist macro has more configurable options than the location naming macro.

These settings are defined near the top of each macro and are intended to be easy to adjust.

No detailed setup is provided here — users are expected to review and modify the macros to suit their own workflow.

---

## GPS naming script

Location: `scripts/eBirdChecklistNameFromGPS.py`

This script:

- Converts GPS coordinates to readable location names  
- Uses the Google Geocoding API  
- Is called by the UI.Vision macros  

It can also serve as a simple example of using Python with the Google Maps API.

### Requirements

Install dependencies:

```bash
pip install -r requirements-gps-script.txt
```

or:

```bash
pip install requests pyperclip
```

### Notes

- An API key is required for Google Geocoding  
- The key is not included in this repository  
- You will need to add your own key to the script  

---

## Available macros

### Incidental checklist creation

Creates a new checklist from structured clipboard data:

- Extracts:
  - date and time  
  - GPS coordinates  
  - dictation text  

### Location naming

- Renames personal locations using GPS coordinates  
- Applies a consistent naming format  

---

## Checklist Creation Workflow Example

1. Record observation using the Apple Shortcut  
2. Copy a log entry from Notes (to the clipboard)  
3. Open the eBird “Submit” page  
4. Run the macro  
5. Review and complete the checklist  

**Notes**

- The macro does **not** enter bird observation data. Speech-to-text is too variable for reliable species entry.  
- The macro creates a new checklist with:
  - date and time  
  - GPS-based location (always a new personal location)  

- You are responsible for entering the bird list.

Two workflow options:

- **Auto-submit enabled**  
  - The checklist is created and submitted  
  - Dictation text can be stored in checklist comments to assist later editing  

- **Auto-submit disabled (recommended)**  
  - The macro stops before final submission  
  - You enter bird data manually, then submit  
  - Dictation comments can be disabled if not required  

---

## Location naming

eBird’s default naming for personal locations is functional but can become difficult to read and sort when you have many locations.

For most users this is not an issue. However, if you prefer a consistent and sortable naming scheme, the macros implement a simple format: `Locality ( lat, long )`.

Example:

`Ungarie ( -33.477482, 146.758874 )`

This aligns with eBird’s guidance on using specific locations.

See: [Using accurate and specific eBird locations](https://ebird.org/news/sitespecificity/)

Personal locations can multiply quickly, especially when mixing hotspots and personal locations.

**Behaviour**

- Renames personal locations using the standard format  
- Can also update shared locations (with some caveats)

**Notes**

- If another user owns the original location:
  - your checklist is updated  
  - a new personal location is created  
  - the original location is not modified  

- In rare cases, updating shared locations can cause minor issues with shared checklists  
  - no data loss has been observed  
  - exact conditions are not fully understood  

**Geographic coverage**

- Tested primarily in:
  - Australia  
  - Indonesia  
  - India  
  - Spain  

- May require adjustment for other regions depending on how locality names are returned

---

## Notes

- These tools are designed for a specific personal workflow  
- You may need to adapt them for your own use  
- The GPS naming approach is opinionated and optional  

---

## Summary

- UI.Vision macros automate parts of eBird workflows  
- The GPS script supports location naming  
- Use carefully and responsibly  
