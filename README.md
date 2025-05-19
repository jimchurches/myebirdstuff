# myebirdstuff
eBird Automation

Various tools and utilities I've written to help me with eBird.

## Location naming

I create a lot of personal locations. I think the fidelity of personal locations is more scientifically relevant than using a generalised hotspot. Don’t get me wrong — if I’m at a location with an obvious hotspot, I’ll use it. But Australia is big, and I avoid using hotspots if they’re too broad or not actually near where I’m birding. eBird encourages this — they want you to be precise. You’ll find this in various help pages and articles, including this one:

[Using accurate and specific eBird locations](https://ebird.org/news/sitespecificity/)

The default name eBird gives a new personal location is technically accurate but messy. It doesn’t sort well, and it's hard to read quickly in the app. For example, when selecting a location in the mobile app, these names make scanning and choosing locations frustrating — especially if, like me, you have dozens clustered around the places you visit regularly. The web interface is also cluttered, particularly in trip reports.

Most people probably don’t care. But I do. I don’t like messy. I like neat. I want to quickly see where I’ve been without reading a full address. A locality name is all I need. So I’ve come up with a personal naming scheme for my hotspots: `Locality ( GPS )`. For example: `Baldivis ( -32.276319, 115.840975 )`.

I don’t try to do this in the field. Often someone else is creating the checklist anyway. Instead, I’d come home and manually fix the names. It wasn’t hard — just tedious, and a little error prone. For a day trip, it was quick and might take me a few minutes. But for a longer trip, it could take much longer, especially when birding with mates who log everything and also use personal locations.

So I solved it. I wrote a macro in UI.Vision that does it for me. I go to My eBird, open each new location manually, and run the macro. Done. It renames any personal location, or if it’s a shared one, it edits the checklist and creates a new personal location using my naming scheme. That doesn’t affect the original owner — once a checklist is shared, they become separate (photos are still shared, but not the location).

This setup is tailored to my quirks. I don’t expect anyone else to use it. But maybe it’ll give someone a few clues about how to automate eBird tasks with UI.Vision if they’ve got their own itch to scratch.  There might also be clues in the helper script, written in Python, around working with goelocation data.

### What is UI.Vision?

UI.Vision is a Robotic Process Automaton (RPA) tool for browsers.  You can find details here:

[UI.Vision](https://ui.vision)

I'm not going to try and explain what this sort of tool does, follow the link and you will get the idea quickly.

I have written the solution using Edge on macOS as UI.Vision is not supported in Safari.   I picked Edge as I use a Windows laptop that is sometimes with me in the field.  I haven't yet tested the solution on my Windows machine, but both UI.Vision and Python are cross platform.  In anticipation of putting the solution on my laptop, I've included some code in the UI.Vision macro to help this cross platform use (paths on the two operating systems are different).

### Google Geocoding

I use Google's Geocoding API for reverse geocoding (gps --> name).  Its free for low volumes of queries, and low volumes is thousands a month so for this purpose I'm never going to get close to the volume of queries where I could be charged.  An API key is required and is removed from my code here as that is private (like a password).  You'll find how to get one with a quick Google search.  You'll need to drop your key into the code; look at the Python script and you'll find where to do that easy enough.

## Incidental Checklist Creation from Clipboard Data

I have writeen an Apple Shortcut that will log birds by voice and store the information in Notes on my phone.  Notes also syncs to my Mac Studio at home, and I could easily get the Notes data onto my Windows machine also (it is just text).  The shortcut is explained below somewhere.  I have written a Macro for UI.Vision to read the data that shortcut creates and to create an incidental checklist.  The macro can't populate birds, the Apple dication, and my own abiltiy to clearly name birds 100% correctly every time procludes that.   The shortcut captures dicated text, is is freeform and unstructured. For example, the logged text might be "Ringneck, two of them; also a black soldier kite" and that is not really something I can program around to log in a structured list that eBird requires. However, the shortcut does tag the entry with GPS, Date and Time information.

So how do I use this data?  I could manually transpose the date from Notes into eBird.  Easy enough to do.  But, I can't help myself ... 

The UI.Vision macro reads a single data entry from the clipboard, creates an incidental checklist using the GPS and date/time info, and puts the captured text into the checlist comments.  I can then update the checklist with accurate information (the dictated data is right ther in the comments), delete the comments, re-submit the checklist and the job is done.  These checklist will always be linked to a new personal location (no hotspots or existing personal location support), but I log most birds seen when driving to a personal location, so no problem for me there.   My workflow:  Copy an entry from notes into the clipboard; navigate to 'Submit' in eBird; run the macro; update the checklist with the bird(s) seen; delete the checklist comment; re-submit the updated checklist.   Easy.   

I have no intention of using this method when out walking or when I have access to my phone to log a checklist on the spot.  The purpose of the Apple shortcut is explained below somewhere, but my idea is to use it when driving to capture birds I'm interested in. Raptors are the obvious candiates for me, but anything seen when driving that is interesting enough to log.


## 🎙️ Bird Data Logging with Apple Shortcut

**Download the Shortcut**  
👉 [https://www.icloud.com/shortcuts/4ec8448e19fc4d49b937ac392e1050b2](https://www.icloud.com/shortcuts/4ec8448e19fc4d49b937ac392e1050b2)

This Apple Shortcut captures voice dictation of bird sightings while driving or otherwise occupied.

It works on both **macOS** and **iOS**.

---

### ✅ What It Does

When triggered (e.g. with `Hey Siri, log bird data`), the Shortcut:

- Listens to your voice
- Converts it to text
- Captures current GPS coordinates
- Captures the current date and time
- Formats everything into one structured line
- Appends the result to a note in Apple Notes
- Creates the note if required (new note every day)

It gives you a time-stamped log of sightings, ready for later.

---

### 📄 Output Format

Each entry in the Notes log looks like this:

```
Date/time: 18 May 2025 at 06:15 | GPS: -35.3489, 149.0555 | Record(s): Pair of Gang-gangs in casuarinas
```

You can change the output format by editing the `Text` block in the Shortcut. Some of the steps look complex but are just for formatting — the core workflow is
simple and easy to follow.  It can be viewed, used and edited on both iOS and macOS.

---

### 🧠 Why This Exists

Logging birds while driving is dangerous and illegal. I created this Shortcut after being fined $450 for
touching my phone to log a Wedge-tailed Eagle  with the eBird mobile app while driving.  Totally my
fault, I shouldn't have been doing that and knew I shouldn't be.

Now I can just speak

I don't try to log every bird — just key sightings (raptors, rarities, or personal notables).

Apple Car Play isn't required, but makes it easy, I don't need to remember to leave my phone where Siri can hear me.

---

### 📝 What Happens After Logging

Later, you can manually transfer the log entry into a proper eBird checklist.  I envisioned this as a manual process and it probably will be if you use this little tool.

However, having spent a career automating stuff, I couldn't help myself and have done some work in UI.Vision to help me import the data into eBird quickly.  You will find
more details about that UI.Vision macro somewhere eles here.

If you're using this Shortcut in combination with my UI.Vision macro (`eBird Incidental Checklist Create`), the process becomes semi-automated:

- Copy a individual log entry from Notes to the clipboard
- Run the macro
- It validates the data
- Extracts date, time, GPS, and your dictation
- Creates a blank checklist with those details pre-filled

It does **not** attempt to log the actual birds. Speech-to-text is too variable for that. Instead, once the checklist is created, you can manually
fill in the bird list from your voice notes.

The macro is designed for my personal workflow, but you’re welcome to explore or adapt it for your own purposes.  For the most part is it should work
for anyone.  My custom location naming might be a step to far for you and may not work for you.

---

### ⚙️ Customisation Tips

- You can edit the Shortcut to change the output format, note name, or structure
- The individual record format is machine-readable, not designed for beauty as I process it with UI.Vision (see above)
- You might want to improve or simplify based on your needs
- If you do, feel free to share your version
- If you have a good idea to improve it and would like me to consider rolling it into my version here, just ask.

The `.shortcuts` file is binary and can’t be edited directly. It’s best to customise inside the Shortcuts app (easier to do on macOS than iOS, usable on both)

---
