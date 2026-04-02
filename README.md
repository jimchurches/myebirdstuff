# myebirdstuff

A collection of tools and utilities to support personal eBird workflows.

This repository focuses on:

- exploring personal eBird data  
- capturing observations in the field  
- automating repetitive eBird tasks  

---

## Projects in this repository

| Tool | Description |
|------|------------|
| Personal eBird Explorer | Streamlit app for exploring your eBird data |
| Apple Shortcut (bird logging) | Voice-based logging of sightings to Notes |
| UI.Vision macros | Browser automation for eBird workflows |
| GPS naming script | Python helper for converting GPS → location names |

---

## Personal eBird Explorer

A Streamlit application for exploring your personal eBird data.

- Interactive map of checklist locations  
- Species search and filtering  
- Summary tables and rankings  
- Export map views  

👉 Start here:  
- Overview and usage: [`docs/explorer/README.md`](docs/explorer/README.md)  
- Getting started: [`docs/explorer/getting-started.md`](docs/explorer/getting-started.md)  
- Installation: [`docs/explorer/install.md`](docs/explorer/install.md)
---

## Apple Shortcut (Bird Logging)

A simple workflow for capturing bird sightings while driving or otherwise occupied.

- Voice dictation via Siri  
- Captures GPS, date, and time  
- Stores structured records in Apple Notes  

👉 Download:  
https://www.icloud.com/shortcuts/4ec8448e19fc4d49b937ac392e1050b2  

---

## UI.Vision Macros

Browser automation tools for working with eBird.

- Create incidental checklists from clipboard data  
- Rename and manage personal locations  
- Integrates with the GPS naming script  

⚠️ These tools interact with the live eBird system — use responsibly.

👉 Documentation:  
- See [`docs/ui-vision/README.md`](docs/ui-vision/README.md)

---

## GPS Naming Script

Python helper script used by the UI.Vision macros.

- Converts GPS coordinates to readable location names  
- Uses Google Geocoding API  
- Can be used independently for geolocation workflows  
- Maybe a useful example of Google Maps API usage for other developers

Location:  
`scripts/eBirdChecklistNameFromGPS.py`

---

## Notes

- These tools are designed for personal workflows and may require adaptation  
- The repository is evolving; documentation for some components is still being expanded  

---

## License

This repository is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 James Churches.