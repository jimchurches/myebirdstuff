# myebirdstuff
eBird Automation

Various tools and utilities I've written to help me with eBird.

# Location naming

I create a lot of personal locations. I think the fidelity of personal locations is more scientifically relevant than using a generalised hotspot. Don’t get me wrong — if I’m at a location with an obvious hotspot, I’ll use it. But Australia is big, and I avoid using hotspots if they’re too broad or not actually near where I’m birding. eBird encourages this — they want you to be precise. You’ll find this in various help pages and articles, including this one:

[Using accurate and specific eBird locations](https://ebird.org/news/sitespecificity/)

The default name eBird gives a new personal location is technically accurate but messy. It doesn’t sort well, and it's hard to read quickly in the app. For example, when selecting a location in the mobile app, these names make scanning and choosing locations frustrating — especially if, like me, you have dozens clustered around the places you visit regularly. The web interface is also cluttered, particularly in trip reports.

Most people probably don’t care. But I do. I don’t like messy. I like neat. I want to quickly see where I’ve been without reading a full address. A locality name is all I need. So I’ve come up with a personal naming scheme for my hotspots: `Locality ( GPS )`. For example: `Baldivis ( -32.276319, 115.840975 )`.

I don’t try to do this in the field. Often someone else is creating the checklist anyway. Instead, I’d come home and manually fix the names. It wasn’t hard — just tedious, and a little error prone. For a day trip, it was quick and might take me a few minutes. But for a longer trip, it could take much longer, especially when birding with mates who log everything and also use personal locations.

So I solved it. I wrote a macro in UI.Vision that does it for me. I go to My eBird, open each new location manually, and run the macro. Done. It renames any personal location, or if it’s a shared one, it edits the checklist and creates a new personal location using my naming scheme. That doesn’t affect the original owner — once a checklist is shared, they become separate (photos are still shared, but not the location).

This setup is tailored to my quirks. I don’t expect anyone else to use it. But maybe it’ll give someone a few clues about how to automate eBird tasks with UI.Vision if they’ve got their own itch to scratch.  There might also be clues in the helper script, written in Python, around working with goelocation data.

## What is UI.Vision?

UI.Vision is a Robotic Process Automaton (RPA) tool for browsers.  You can find details here:

[UI.Vision](https://ui.vision)

I'm not going to try and explain what this sort of tool does, follow the link and you will get the idea quickly.

I have written the solution using Edge on macOS as UI.Vision is not supported in Safari.   I picked Edge as I use a Windows laptop that is sometimes with me in the field.  I haven't yet tested the solution on my Windows machine, but both UI.Vision and Python are cross platform.  In anticipation of putting the solution on my laptop, I've included some code in the UI.Vision macro to help this cross platform use (paths on the two operating systems are different).

## Google Geocoding

I use Google's Geocoding API for reverse geocoding (gps --> name).  Its free for low volumes of queries, and low volumes is thousands a month so for this purpose I'm never going to get close to the volume of queries where I could be charged.  An API key is required and is removed from my code here as that is private (like a password).  You'll find how to get one with a quick Google search.  You'll need to drop your key into the code; look at the Python script and you'll find where to do that easy enough.

#  Bird data Apple Shortcut

I have a shortcut that with a `Hey Siri - Log bird data` will capture some dication (obviously I just say the name of the bird I can see or short sentance with some extra info) that will take that dication, turn it into text and save it to a log in Notes.  It appends date/time and GPS info to each dication.  I use it when driving to capture details about birds I want to record in eBird.  I've logged a $450 Wedge-tailed Eagle (a camera caught me touching my phone) so I don't try to log when driving any more.  I don't try to record every single bird I see when driving, but I do like to capture at least the raptors and occationaly other interesting birds.  This will help.  A bit of manual messing around when home, but it means I capture birds I'm interested in.

I hope to figure out how to share that shortcut here, even if a document so someone can take the idea and use it (not here yet).  Happy to share if you reach out to me.
