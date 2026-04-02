from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("/mnt/data/AI_Context_Personal_eBird_Explorer.pdf")
styles = getSampleStyleSheet()

content = []

text = """
AI Context for Personal eBird Explorer

This document provides context and guardrails for AI coding assistants (Cursor, Copilot, ChatGPT) working in this repository.

Read this before suggesting architectural or structural changes.

Project Purpose

Personal eBird Explorer visualises a user's personal eBird data.

It supports exploration of:
- checklist locations (map-based)
- species-specific observations
- visit statistics
- first/last seen data

Primary interface: Streamlit app + Folium map

Core Principles (Follow These First)

1. Prefer small changes
- Make incremental improvements
- Avoid large rewrites unless explicitly requested

2. Keep logic out of the UI
- Streamlit = UI layer only
- Core logic belongs in modules
- Do not embed complex logic in UI code

3. Respect the data model
- CSV is loaded once
- Data is static during runtime
- Do not mutate the main dataframe

4. Do not break caching
- Preserve cache correctness when modifying grouping, filtering, or popups

5. Prefer readability over cleverness
- Code should be easy to understand later

6. Avoid unnecessary dependencies
- Do not introduce new frameworks or heavy libraries

7. Git discipline (IMPORTANT)
- Do not commit or push code without explicit user direction
- Always write clear commit messages
- Reference GitHub issues in commits when applicable

Architecture Overview

CSV (eBird export) -> data_loader -> canonical dataframe -> core logic -> map rendering -> Streamlit UI

Key rule: UI stays thin, logic stays in modules.

Streamlit Guidelines

- Use native components first
- Use shared HTML formatters when needed
- Do not duplicate HTML in UI code
- Keep eBird links intact

Defaults

All defaults must live in defaults.py. Do not hardcode values in UI files.

Data & External API

- Dataset is static
- Taxonomy fetched once
- App must not fail if taxonomy fails

Performance Approach

- Use simple in-memory caching
- Avoid recomputing heavy operations

Testing

- Place logic in testable modules
- Avoid logic in UI
- Run pytest tests/

Safe Changes

- Documentation
- Comments
- Tests
- Minor improvements

Use Caution With

- Data loading pipeline
- Caching model
- Map rendering structure

When Unsure

- Describe approach before implementing

Development Direction

- Streamlit remains primary UI
- Keep logic modular

Summary

- Data is static
- UI is thin
- Logic is modular
- Caching is simple
- Clarity over cleverness
"""

for line in text.split("\n"):
    content.append(Paragraph(line, styles["Normal"]))
    content.append(Spacer(1, 6))

doc.build(content)

"/mnt/data/AI_Context_Personal_eBird_Explorer.pdf"
