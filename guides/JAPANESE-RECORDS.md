# The Japanese records: finding the other side of an attack

The strongest check on an attack data sheet is the target's own record. This guide says which
Imperial Navy records hold it, how to find and read them, where they mislead, and how US radio
intelligence's picture of the same day (the FRUPAC war maps) is read beside them. The skill
`find-the-other-side` is this guide as a checklist; position codes in the records are decoded in
[JAPANESE-GRID.md](JAPANESE-GRID.md).

## Where the records are

JACAR, the Japan Center for Asian Historical Records (National Archives of Japan), puts the
Imperial Navy records held by the National Institute for Defense Studies, Ministry of Defense,
online free (`records/SOURCES.yml`, `jacar`): war diaries, action reports, convoy escort
statistics, and the movement tables kept for navy-controlled merchant ships. A record is cited by
its reference code and page (`jacar:C08030140600 p23`). `tools/jacar.py` searches the collection
and downloads a record as a PDF of page scans, with no text layer.

## The records, by type

| Record | What it gives | Where it falls short |
|---|---|---|
| Designated-ship movement tables (指定船舶行動表) | One ship's ports, dates and cargo; for a lost ship, the master's or a survivor's account of the sinking, with time and position | One ship only; kept for navy-controlled merchant ships |
| Escort command war diaries (海上護衛隊戦時日誌) | The month's narrative; a day-by-day chart of each escort's convoy; monthly route charts that mark each attack with time and position; an attached table of the convoys that met submarines and every ship lost, with tonnage | Each command covers its own routes (below) |
| An escort's own war diary and battle report (戦闘詳報) | The attack logged minute by minute | Found by the escort's name, not the convoy's |
| Guard district war diaries (警備府戦時日誌) | The radio log: air patrols, convoy cover, weather | Context more often than the attack itself |
| Telegram logs (三、令達報告等) in a squadron's or fleet's war diary | Each signal's day, sender, addressees, times sent and received, and text | The signals are filed under the command that received them, not the ship that sent them |
| The Navy's daily summary of attacks on shipping, 大東亜戦争経過概要（護衛対潜関係） | A handwritten day-by-day list, Navy-wide, of ships attacked: time, ship, tonnage, speed, place given from a base ("トラックノNW二五〇′"), torpedoes taken, outcome | Compiled from signals; see "The daily summary" below |

### Which command kept the convoy

Trunk convoys (HI-, MI-, TAMA-) are in the 1st Surface Escort Division's diary, whose monthly
route charts mark each attack with time and position. Local convoys off Formosa and the Nansei
Shoto (TAKA-, KATA-) are in the 4th Surface Escort Division's diary and in the war diaries and
battle reports of the individual escorts.

### A ship sailing alone

A ship with no convoy and no escort has no escort diary. She is in the diaries of the ships sent
to help her. Kazahaya, an oiler on passage to Truk in October 1943, is the worked case:
`jacar.py search "風早"` did not find her. Her own signals ("three hits, ability to steam
doubtful", her list and speed, her positions, the boiler room torpedoed, the time she sank) and
the rescue totals are in the telegram log of the 2nd Destroyer Squadron's war diary, whose
destroyers were sent out to her (`jacar:C08030101300`, pp. 22–29).

### The daily summary

The summary says quickly whether an attack was reported at all, so it is the place to start.

- **Its volumes.** Two: December 1941 to December 1943 (`jacar:C16120655900`) and January 1944 to
  February 1945 (`jacar:C16120658900`), one code a month (October 1943 is `C16120658600`; June
  1944 `C16120659700` to February 1945 `C16120660500`). It stops at February 1945: for later
  attacks, search by command and month.
- **Its tables.** Some months add tables of ships sunk and damaged, with times. These can be
  filed in the next month's part (June 1944's opens with May's tables), and some months have
  none.
- **It is not independent of the ship's telegrams.** It compiles the Combined Fleet's signals, so
  it repeats the ship's own telegrams and counts once with them.
- **A ship damaged but still steaming may not be in it.** TINOSA's tanker of 4 October 1943 is
  not.
- **A bare tick-and-name line is dated when the loss was reported, not when it happened.** In
  February 1945 the narrative has "✓大暁丸 沈没" on the 9th; the 1st Escort Fleet's loss table
  (`jacar:C08030142100` p46) has her sunk on the 7th at 0450 off Indochina. So a line with no
  time or place may be days late: never pair it on its date alone. A line that gives its own
  time and place ("二九 〇二三〇 バーシー海峡E 香取丸 … 被雷沈") carries the event's date; pair
  that.
- **Its silence is not evidence**, in the last months above all. January and February 1945 have
  nothing in the Yellow Sea, though Kume and Sanuki Maru were sunk there on 28 January (her
  captain's telegram in the 103rd Squadron's diary, `jacar:C08030075600` pp. 13–14). The 1st
  Escort Fleet's loss tables cover its southern routes only and leave them out too. Say "no entry
  in the summary", not "nothing sank".
- **Its hand writes 9 like an f or a P** (Toyama Maru's "708f" is 7,089 tons): read tonnages with
  that in mind.

## Finding a record

1. **Identify the convoy from secondary sources.** combinedfleet.com's ship records name convoys,
   escorts and sinking times. They are finding aids: cite what is then read on the scan.
2. **Search for the command's diary and the ship's movement table**
   (`jacar.py search "日達丸"`). Search reaches OCR text but matches loosely, so check every hit.
3. **Search the escort when the merchant ship does not come up.** Get the escorts' names from
   combinedfleet.com, then search for the ship (`jacar.py search "第三十号海防艦"`). Merchant
   names written in kana (さらわく丸) are not in JACAR's search text.
4. **Search the commands, not only the ship.** JACAR's search text covers only part of a long
   record. Search the commands that would have handled the event (the base force, the fleet, the
   squadron that sent help) with the month as the date range
   (`jacar.py search "第２水雷戦隊" 1943-10 1943-10`), and read the record's contents page first:
   a fleet's monthly part can hold only its tables of ships' movements (the 4th Fleet's October
   1943, `jacar:C08030018500`).
5. **Use Japanese Wikipedia as a finding aid.** Its articles on Imperial Navy ships often quote
   primary records with the JACAR code and page, and published sources such as 戦史叢書 (the
   official war history) and the diary of Prince Takamatsu (高松宮日記). Use them to find pages
   and to read faint characters (罐室被雷, "boiler room torpedoed", on Kazahaya's last telegram),
   but cite the scan that was read, and label anything not read on the scan as secondary.
6. **Reference books.** Find a Japanese book's exact title in the National Diet Library's
   catalogue (`ndlsearch.ndl.go.jp`) and check its digital copy's access: open on the internet,
   in libraries only, or at the NDL only (`dl.ndl.go.jp/pid/<id>`; the NDL's copy service will
   send pages). `tools/gbooks.py search` finds Google Books volumes and snippets; a snippet is a
   lead, not a reading.

## Reading and transcribing

- **Read the page images.** Printed pages read well at 110 dpi. Handwritten tables need 200–300
  dpi crops, and a telegram log's columns 300–450 dpi; find the day with a contact sheet of the
  pages first.
- **Horizontal text of the period runs right to left**: `(七一マタ)` is タマ一七, TAMA-17.
- **Rendering.** `jacar.py fetch` renders pages only when poppler's `pdftoppm` is installed;
  without it, render the saved PDF with PyMuPDF. If pages cannot be rendered locally, read them
  in JACAR's own viewer, a PDF.js page at `/bundles/apps/pdfjs/web/viewer.html?file=…` (the path
  is in the iframe on `/das/image/<code>`). Its page numbers are the PDF's, the same as `pNN`.
- **Transcribe as written**, into the patrol's `japanese.yml`, with a translation and the page,
  and pair the records with attacks in its `claims.yml` (fields in `records/README.md`).
- **Check.** `tools/check_crossrefs.py` converts both sides to GMT and reports the gaps in
  minutes and miles.

### The clock

The Imperial Navy kept Tokyo time: zone I, nine hours ahead of GMT (−9 in the US Navy's zone
description; [METHODS.md](METHODS.md), "Conventions that matter"). With that assumption, Nittatsu
Maru's movement table and BANG's attack sheets agree to 1–7 minutes on four attacks; the table is
in `records/boats/ss-385-bang/README.md`. The one large gap (86 minutes, Attack 5) is against a
secondary source.

## US radio intelligence: the FRUPAC war maps

The picture kept by FRUPAC (Fleet Radio Unit, Pacific, the Navy's radio-intelligence unit at
Pearl Harbor) is in its war maps, held by the National Museum of the Pacific War and served
through the Portal to Texas History (`records/SOURCES.yml`, `frupac`). The maps are CC BY-NC-ND:
linked and read, never copied.

**Finding a map.** The portal's search pages are behind a bot check, but the catalogue is
harvestable through the library's OAI-PMH feed (`https://texashistory.unt.edu/oai/`, set
`collection:FRUPAC`). `tools/frupac.py` does that and finds maps by ship or date.

**Reading it.** Read the maps in the site's zoom viewer, which serves full-resolution tiles (the
page images are too small for the pencil). The zoom viewer sits behind a bot check for scripts as
well: find the map with `frupac.py date`, give a person the viewer's full address with its
`resolution`, `lat` and `lon` query (the viewer's own coordinates, in the full image's pixels),
and read their full-resolution screenshot.

**Recording a note.** For each note near an attack:

1. Copy the text as written into `frupac.yml`, with the message date-time group, the event time,
   and the zoom-viewer query that frames it.
2. Estimate the mark's position: against the printed 1-degree grid where the map has one; on bare
   tracing overlays, against the red meridian labels (`120`, `130`, …), assumed to sit on 20N.
   Where the labels are out of frame, place marks against two known places in the frame (Truk's
   dot and Chichi Jima on the October 1943 map). Write the position in decimal degrees and treat
   it as ±0.1–0.3°.
3. Tie it to an attack with `match`, `candidate` or `context`, and say why.
   `check_crossrefs.py` prints the gap, reading the note's time as zone I.

**Routes are plans.** The October 1943 map also plots routes from intercepted routing messages: a
line labelled with the message's date-time group (`271500`), its points numbered by day, ending
at the port. Those points are planned positions, not reported ones; a red star on one marks an
attack on that route.
