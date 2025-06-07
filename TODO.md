# TODO: eBird Checklist Automation

Tracking outstanding work and future enhancements for the eBird automation workflow.

---

## 🔧 Outstanding Tasks

### 📘 README Drafting and Editing

- Review the README file for content and clarity
- Written peacemeal as I sat working on my ideas, may not flow
- Best to do that after using the tools for a bit

---

## Feature Improvement - Shortcut

- When interacting with Siri you say 'Log bird data' and then it pauses then asks 'whats the text'.  When driving 
  I've found I thin Siri has heard me wrong and wants to send a text.  Stupid, but that has happened several times.
  Can I change the prompt?  I've had a quick look at the shortcut and can't see an option, but need to investigate
  a little more.  A prompt 'What bird?' might be better.  Stupid little thing, not urgent

  > Note: As far as I can tell, that 'what's the text' can not be change.

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

---

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

✋  The eBird API doesn't give access to personal locations, but you can download your eBird data and pass it to
    ChatGPT and say "can you identify duplicate locations" and it spits back a list.  No coding required.  eBird
    has a `Locaton ID` in the data and ChatGPT was able to compare GPS information to the `Location ID` and 
    found the duplicates, even if names didn't match.  I then just manually cleaned up my duplicates in eBird.
    
    Easy to do:
       - Got to location page
       - Search for one of the names in the duplicate list (in my case most are duplicate names from my
         locaton name renaming activities, though a couple were completely different).
       - CLick through to the location details and find the My Checklists link and go to the checklist(s).
       - Click through to the actual checklist and using 'edit location' change the location using the 'Choose
         from your lcoation' link.  The one you are editing has a checkmark against it, in my case since most
         have the same name the alternative is immidately adjasent and easy to find.  (repeat if there is more
         than one checklist logged against the location).
       - Back on the locations page, search by the least used locations and unused lcoations show up with 0
         associated checklists. Delete the now unused location
       - Easy.

       Only reason to do this is to locaitons show up in the mobile app without duplicates or if you like clicking
       a location and getting your historical lists at that place.  I don't think these duplicates matter at all
       for research or the eBird DB, eBird would be using the locationID and researches the GPS data.

       And I like things neat ....

       Now, could I automate this duplicate clean-up.  Thinking about that, probably, but I think it is such a minor
       issue it is not worth doing.   My original aim with this task was to identify duplicates.

       I will see if ChatGPT can also identify locations that are perhaps less than 100m apart so I can consolidate
       them.  Again, not imporatnt, but makes reusing locations a little easier and is just intersting for a data
       nerd.