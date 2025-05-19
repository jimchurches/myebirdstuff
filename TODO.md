# TODO: eBird Checklist Automation

Tracking outstanding work and future enhancements for the eBird automation workflow.

---

## 🔧 Outstanding Tasks

### 📘 README Drafting and Editing

- Location naming macro section: mostly complete, needs review
- Checklist creation macro:
  - Needs a clear overview and example use case
  - Explain input variables and conditional flags
  - Describe assumptions (e.g., user manually enters bird data)
- Important note:
  - The Apple Shortcut dictation is *not* parsed into individual species
  - The macro exists to streamline checklist creation, not record birds
  - Intended for use while driving or casual observation — not a field data tool (use the eBird app instead)

---

### ⚠️ Add README Warnings and Disclaimers

Add a prominent note at the top of the README:

> **Warning**  
> This macro interacts with the live eBird system.  
> - Do not upload fake or test data  
> - Clean up test checklists and locations immediately  
> - Avoid bulk automation that floods eBird with submissions  
> - Respect eBird’s role in science and community birding  


### 🗺️ Improve GPS Location Naming Logic

- Continue refining the logic used to generate location names from GPS coordinates
- Focus areas:
  - Handle Canberra suburb edge cases more consistently (if required, learn from experiance)
  - Improve fallback behaviour when Google Maps returns vague or broad names
- This is an ongoing area of improvement as new naming inconsistencies are discovered
- Canberra centric nature of the suburb handling code is only because I know when an error is made and could see a way past it
  - would rather remove the Canberra centric nature of that approach and deal with the situations I see in Canberra more broadly
  - understanding the quirks of what I can extract from the Google API data and how my script works with that data will just
    take experiance.
  - eBird's default naming and what I get from Google will show me where there is a mismatch.
 
---

### 🧪 Batch Processing of Apple Shortcut Data (Future Idea)

- Currently not planned, but may revisit
- Potential use case: long trips with many voice notes
- Idea:
  - Paste multiple dictation entries into the clipboard
  - Loop through and create checklists one by one
- eBird has a bulk upload format, but that's a much more complex project