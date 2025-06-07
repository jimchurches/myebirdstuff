# myebirdstuff
eBird Automation

Various tools and utilities I've written to help me with eBird.

## Table of Contents
- [myebirdstuff](#myebirdstuff)
  - [Table of Contents](#table-of-contents)
  - [Bird Data Logging with Apple Shortcut](#bird-data-logging-with-apple-shortcut)
    - [What It Does](#what-it-does)
    - [Output Format](#output-format)
    - [Why This Exists](#why-this-exists)
    - [What Happens After Logging](#what-happens-after-logging)
    - [Customisation Tips](#customisation-tips)
  - [eBird Macros](#ebird-macros)
    - [What is UI.Vision?](#what-is-uivision)
      - [Responsible Use of eBird and These Tools](#responsible-use-of-ebird-and-these-tools)
        - [Do Not:](#do-not)
        - [Always:](#always)
        - [Recommendations:](#recommendations)
    - [Location naming](#location-naming)
      - [Google Geocoding](#google-geocoding)
    - [Incidental Checklist Creation from Clipboard Data](#incidental-checklist-creation-from-clipboard-data)
      - [Flow Control Options](#flow-control-options)
      - [Important Notes](#important-notes)
    - [eBird Data Visualisation Tool](#eBird_Data_Visualisation_Tool)


## Bird Data Logging with Apple Shortcut

**Download the Shortcut**  
👉 [https://www.icloud.com/shortcuts/4ec8448e19fc4d49b937ac392e1050b2](https://www.icloud.com/shortcuts/4ec8448e19fc4d49b937ac392e1050b2)

This Apple Shortcut captures voice dictation of bird sightings while driving or otherwise occupied.

It works on both **macOS** and **iOS**.

---

### What It Does

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

### Output Format

Each entry in the Notes log looks like this:

```
Date/time: 18 May 2025 at 06:15 | GPS: -35.3489, 149.0555 | Record(s): Pair of Gang-gangs in casuarinas
```

You can change the output format by editing the `Text` block in the Shortcut. Some of the steps look complex but are just for formatting — the core workflow is
simple and easy to follow.  It can be viewed, used and edited on both iOS and macOS.

---

### Why This Exists

Logging birds while driving is dangerous and illegal. I created this Shortcut after being fined $450 for
touching my phone to log a Wedge-tailed Eagle  with the eBird mobile app while driving.  Totally my
fault, I shouldn't have been doing that and knew I shouldn't be.

Now I can just speak

I don't try to log every bird — just key sightings (raptors, rarities, or personal notables).

Apple Car Play isn't required, but makes it easy, I don't need to remember to leave my phone where Siri can hear me.

---

### What Happens After Logging

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

### Customisation Tips

- You can edit the Shortcut to change the output format, note name, or structure
- The individual record format is machine-readable, not designed for beauty as I process it with UI.Vision (see above)
- You might want to improve or simplify based on your needs
- If you do, feel free to share your version
- If you have a good idea to improve it and would like me to consider rolling it into my version here, just ask.

The `.shortcuts` file is binary and can’t be edited directly. It’s best to customise inside the Shortcuts app (easier to do on macOS than iOS, usable on both)

---

## eBird Macros

I have written some UI.Vision macros to help me interact with eBird.  Details follow below.

### What is UI.Vision?

UI.Vision is a Robotic Process Automaton (RPA) tool for browsers.  You can find details here:

[UI.Vision](https://ui.vision)

I'm not going to try and explain what this sort of tool does or much about UI.Vision.  Follow the link and you will get the idea quickly.

I have written the macros below to help me maintain my eBird checklists and locations for UI.Vision.  I developed these macros using Edge
on macOS as UI.Vision is not supported in Safari.   I picked Edge as I use a Windows laptop that is sometimes with me in the field.  I
haven't yet tested the solution on my Windows machine, but both UI.Vision and Python are cross platform.  In anticipation of putting the
solution on my laptop, I've included some code in the UI.Vision macro to help this cross platform use (paths on the two operating systems
are different).

#### Responsible Use of eBird and These Tools

⚠️  **This automation interacts directly with the live eBird system. Please use it responsibly.** ⚠️ 

eBird is a global, citizen-science platform used by researchers, conservationists, and the birding community. Your data becomes part of that ecosystem — treat it with care.

##### Do Not:

🚫 🚫 🚫 

- Submit fake or incomplete test checklists
- Create personal locations that clutter the system or misrepresent observations
- Flood eBird with automated submissions or bulk uploads

##### Always:

✅ ✅ ✅ 

- **Test responsibly**: Use temporary data, submit sparingly, and delete test entries immediately
- **Check your data**: Ensure each submission is accurate and meaningful
- **Respect the purpose of eBird**: It’s a scientific and community tool, not a sandbox for experiments

##### Recommendations:

- Use `testingMode` in the checklist creation macro to **avoid real submissions during development**
- Clean up your locations and checklists after testing, don't leave test data in eBird
- Keep automation focused on saving time — not bypassing thoughtful observation

This project was built for my personal workflow and is shared here in case it’s useful to others. Please be mindful of eBird’s mission if you adapt it.

### Location naming

I create a lot of personal locations. I think the fidelity of personal locations is more scientifically relevant than using a generalised hotspot. Don’t get me wrong — if I’m at a location with an obvious hotspot, I’ll use it. But Australia is big, and I avoid using hotspots if they’re too broad or not actually near where I’m birding. eBird encourages this — they want you to be precise. You’ll find this in various help pages and articles, including this one:

[Using accurate and specific eBird locations](https://ebird.org/news/sitespecificity/)

The default name eBird gives a new personal location is technically accurate but messy. It doesn’t sort well, and it's hard to read quickly in the app. For example, when selecting a location in the mobile app, these names make scanning and choosing locations frustrating — especially if, like me, you have dozens clustered around the places you visit regularly. The web interface is also cluttered, particularly in trip reports.

Most people probably don’t care. But I do. I don’t like messy. I like neat. I want to quickly see where I’ve been without reading a full address. A locality name is all I need. So I’ve come up with a personal naming scheme for my hotspots: `Locality ( GPS )`. For example: `Baldivis ( -32.276319, 115.840975 )`.

I don’t try to do this in the field. Often someone else is creating the checklist anyway. Instead, I’d come home and manually fix the names. It wasn’t hard — just tedious, and a little error prone. For a day trip, it was quick and might take me a few minutes. But for a longer trip, it could take much longer, especially when birding with mates who log everything and also use personal locations.

So I solved it. I wrote a macro in UI.Vision that does it for me. I go to My eBird, open each new location manually, and run the macro. Done. It renames any personal location, or if it’s a shared one, it edits the checklist and creates a new personal location using my naming scheme. That doesn’t affect the original owner — once a checklist is shared, they become separate (photos are still shared, but not the location).

This setup is tailored to my quirks. I don’t expect anyone else to use it. But maybe it’ll give someone a few clues about how to automate eBird tasks with UI.Vision if they’ve got their own itch to scratch.  There might also be clues in the helper script, written in Python, around working with goelocation data.

#### Google Geocoding

I use Google's Geocoding API for reverse geocoding (gps --> name).  Its free for low volumes of queries, and low volumes is thousands a month so for this purpose I'm never going to get close to the volume of queries where I could be charged.  An API key is required and is removed from my code here as that is private (like a password).  You'll find how to get one with a quick Google search.  You'll need to drop your key into the code; look at the Python script and you'll find where to do that easy enough.

### Incidental Checklist Creation from Clipboard Data

This macro works alongside the [Apple Shortcut described above](#bird-data-logging-with-apple-shortcut) to streamline eBird checklist creation from dictated observations.

I created this workflow after getting a $450 fine for touching my phone to log a Wedge-tailed Eagle while driving. The Shortcut allows hands-free voice logging, and this macro helps me later turn those logs into proper eBird records.

> ‼️ You certainly don't need this macro to use the Apple Shortcut; you can manually create checklists based on the data recorded in Notes.

Here's how it works:

- You copy a single line of text from Notes into your clipboard  
- Navigate to the "Submit" page on eBird  
- Run the macro  
- The macro validates the clipboard content  
- It extracts:
  - Date and time
  - GPS coordinates
  - Your freeform dictation (e.g. "Two kites overhead; lots of cockatoos")  
- It creates an **Incidental Checklist** pre-filled with the correct details  
- The dictation text goes into the checklist comments (optional – see below)

Once the checklist is created, you just update it manually with the correct birds, remove the comment if you like (you should), and submit. Done.

The macro does **not** try to parse the bird list from the dictation — that’s too error-prone and outside the scope of what I need.

You have two choices on when to enter the actual list of birds for the checkist:

* If `autoSubmit` is false (see below), the checklist creation process will stop on the final page, the bird list, and you can enter the bird(s) before manually
  submitting the checklist.

* If `autoSubmit` is true, the checklist will be created and submitted.  You can then open the checklist and your dictation text from Notes will be in
  the checklist comments.  You can edit the checklist and add your bird(s) and you should now delete the checklist comment (it is there to help you list
  the correct bird(s))

#### Flow Control Options

The macro uses three variables at the start to control its behaviour:

- `testingMode`:  
  When `true`, the macro skips the final checklist submission to avoid uploading test data.  
  A location is still created, so warnings will remind you to clean up after testing.  The 
  location gets creted as you step through the checklist creation Wizard so can't be avoided
  (only an issue when testing).

- `autoSubmit`:  
  When `true`, the checklist is automatically submitted.  
  When `false`, the macro stops before submission, so you can review or edit the list manually.
  The dictatoin text for your data will always be written to the checklist comment so you can
  use it to update the bird list later.  `skipComment` is ignored.

- `skipComment`:  
  Only relevant when `autoSubmit` is `false`.  
  If `true`, the dictation text is not inserted as a comment.  
  Useful if you're entering bird data directly and don’t want the voice log text included.

You can set these variables inside the macro before running it, depending on your workflow.

#### Important Notes

- The macro always creates a new personal location using the GPS coordinates from your dictation log 

- Hotspots are not supported — this is intended for sightings while driving or otherwise on the move  

- The location name is formatted using a separate Python script (see [Location Naming](#location-naming))

This setup suits my personal workflow and naming preferences, but you're welcome to adapt it.

The location naming in particular is my own quirk.  You might want to find your own solution to that and
avoid my script. All the other steps should be fairly common to anyone creating a new checklist from the
data created by the [Apple Shortcut described above](#bird-data-logging-with-apple-shortcut).

Just don’t forget: the macro interacts with the live eBird system. Respect the data.


## eBird Data Visualisation Tool

This repository includes a Jupyter notebook called `personal_ebird_explorer.ipynb` that lets you explore your personal eBird data with an interactive map.

You can search for species, filter by date, mark lifers, and view detailed popups for every checklist location.

> 📘 For full details and instructions, open the notebook: `eBirdDataPlay.ipynb`

