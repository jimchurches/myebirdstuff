# myebirdstuff
eBird Automation

Various tools and utilities I've written to help me with eBird.


# Location naming
I create a lot of personal locations, I think the fidelity of personal locations is more scientificly relevent than a generalised hotspot.  Don't get me wrong, if I'm at a location where there is an obvious hotspot I use it.  But Australia is big, so I avoid using hotspots if they are too general or if the are not really close to where I am birding. eBird encourages your to do this, they want you to do this.   You'll find this encouragement in various help pages and articles on eBird and elswhere.  This is a good explaination:

[Using accurate and specific eBird locations](https://ebird.org/news/sitespecificity/)

The default name eBird gives a new personal location is accurate and full of detail, but I find it messy and doesn't sort well and is long and difficult to read in the app. An example is when you are selecting a personal locaton or hotspot for a checklist in the eBird mobile app; the default names are messy and hard to quickly see in the app.  In practice I'm more interested in where the closet hotspot or personal location is and don't really look for a specific name, but I still find the interface messy due to the number of personal hotspots I have, particuarly areound areas I visit reguarly.   The web site can also be messy with the big detailed default names, an example is trip reports. 

Most will think I'm nuts and why care.  Well.  I don't luck messy.  I like neat.  I like to quickly see where I've been and not have to read a full address with numbers or street names.  The local town or rural locality is all I care about.  So I've come up with my own naming scheme for my personal hotspots.  I simply name then with 'locality ( GPS )'.  Some something like this: `Baldivis ( -32.276319, 115.840975 )`

I don't try to do this in the field.  I can't even if I wanted to as often a companion is creating the list.  So instead, I use to come home and fix all the location names.   It was tedious but a bit of meditation and wouldn't take long for a day trip but could take ages for a week long trip, especially when a few of the guys I bird with are like me and log everything and also like the fidelity of personal locations.   I'd watch YouTube and work through them.  Not hard on the web site, easy actually, but a little error prone and lots of clicking.   

I've solve this have written a macro in UI.Vision that will do this for me.  I now go to locations in `My Ebird` and work through the new locations created on a trip/day, open each one, run the macro.  Easy.  It will update the location name of any personal location or if the personal location is shared with me, it edits the checklist location and creates a new personal location using my naming scheme; this doesn't flow through to the other birders on the list, once a list is submitted they are seperate (except for photos that remain shared on both lists).

This is very unique to me and my own quirks and I don't expect anyone elese to use it.  However, perhaps it might one day give someone some clues on how to us UI.Vsion with eBird if they have their own 'thing' they'd like to solve.

#  Bird data Apple Shortcut

I have a shortcut that with a `Hey Siri - Log bird data` will capture some dication (obviously I just say the name of the bird I can see or short sentance with some extra info) that will take that dication, turn it into text and save it to a log in Notes.  It appends date/time and GPS info to each dication.  I use it when driving to capture details about birds I want to record in eBird.  I've logged a $450 Wedge-tailed Eagle (a camera caught me touching my phone) so I don't try to log when driving any more.  I don't try to record every single bird I see when driving, but I do like to capture at least the raptors and occationaly other interesting birds.  This will help.  A bit of manual messing around when home, but it means I capture birds I'm interested in.

I hope to figure out how to share that shortcut here, even if a document so someone can take the idea and use it (not here yet).  Happy to share if you reach out to me.
