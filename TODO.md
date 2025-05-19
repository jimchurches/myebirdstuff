# TODO: eBird Checklist Automation

Tracking outstanding work and future enhancements for the eBird automation workflow.

---

## 🔧 Outstanding Tasks

### 📘 README Drafting and Editing

- Review the README file for content and clarity
- Written peacemeal as I sat working on my ideas, may not flow
- Best to do that after using the tools for a bit

---

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
- 

### Analyse Personal Locations for Duplicates and Clusters

- Use the [eBird API](https://documenter.getpostman.com/view/664302/ebird-api-20/2HTbHW) to fetch all personal locations
- Research if this is even possible and if possible ...
- Identify:
  - Exact duplicate coordinates with different names
  - Same or similar names with slightly different coordinates
  - Locations within a small radius of each other (e.g. 50–200 metres)
- Consider:
  - Logging last used date for sorting or filtering
  - Exporting results to CSV or GeoJSON for visual review
- Goal is to manually clean up redundant locations in eBird
- This is a **manual clean-up aid**, not an automated merge tool
- Optional future step: script to pre-format the findings into a list of links for easy access in eBird
