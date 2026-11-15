# Following one soldier between units: replacements and patients

A unit's morning reports follow the unit. A soldier who leaves it, as a replacement shipped overseas or as a casualty
evacuated to a hospital, passes through units no one would think to search: a port's staging camp, a shipment's
lettered companies, a replacement depot's casual detachments, a replacement battalion, a transit hospital, a hospital
plant's detachment of patients. Each kept papers that name him. This guide says what each step's paper looks like and
how to find it. The morning reports themselves are [MORNING-REPORTS.md](MORNING-REPORTS.md).

None of this goes into `records/`: a person's path through depots and hospitals stays in the family's own notes
(`CLAUDE.md`, "People"). The method is here; the findings are the family's.

## Start from the serial number

`python3 tools/morning_reports.py serial <ASN>` searches the catalog's OCR of every roll for the number and lists each
page that holds it, with the date, unit and station as far as the OCR goes. Most hits on a well-documented man are his
own unit's reports; the useful ones are the pages of units he passed through, which no unit search would reach. OCR
misreads digits and dates (a form's printed revision date often stands in for the report's), so every hit is read on
the scan before it counts. A roster that holds the number says nothing about the day until the report it is attached
to is found: rosters and orders are filmed after the morning report that cites them ("Roster atchd", "Copy of SO
atchd").

## The replacement pipeline (European theatre, 1944)

1. **The losing unit.** Its report sends men "trfd in gr" (transferred in grade) to a replacement depot at home, often
   a group at once, by name.
2. **The shipment.** Overseas replacements moved in numbered shipments (a code such as `GL-nnn`, sometimes with a letter
   suffix), organised in lettered companies and platoons. Each company kept morning reports at the port of embarkation's
   staging camp (for New York, Camp Kilmer and Camp Shanks; for Boston, Camp Myles Standish) and at sea, where the
   station is typed "At Sea" every day of the crossing; the ship and the ports are not named. Each company's
   **outgoing transport roster** lists its men by platoon, with name, serial number, grade, a two-character column
   (such as "C 2" or "D 1") and the military occupational specialty. The two-character column is not the company,
   which is in the roster's heading.
3. **The replacement depot overseas.** The depot's attachment memoranda put men into casual detachments and provisional
   companies at numbered camps. The camps are rarely named, so the place often can't be fixed from these pages.
4. **The marshalling depot.** Men bound for the Continent moved in groups to a marshalling depot's casual detachment.
   Each group arrives with a lettered roster ("Roster B-1 atchd"), which is the **packing sheet** of a numbered package,
   headed with the replacement company and battalion that made it up, and leaves "for destination unknown" by a
   paragraph of the depot's special orders. The orders' copies are sometimes filmed after the report and sometimes not;
   their rosters are the only way to tell which group left on which day.
5. **The replacement battalion on the Continent.** Its headquarters' report records bulk attachments ("EM atchd unasgd
   this orgn per VOCG First Army (Roster atchd)") with each replacement company's roster attached, and its special
   orders send men on: to a division against the division's numbered requisition ("asgd to the ... Inf Div ...
   Consolidated requisition No. ..."), or to a named unit. The battalion headquarters' own reports record its own
   crossing (embarkation, ship, landing beach), which shows the pattern but not a later group's route.
6. **The gaining company.** "Asgd & Jd fr Hq ... Repl Bn" closes the chain.

## The evacuation chain

1. **The company's report.** The day's wounded go "fr dy to abs LWA" (lightly wounded in action) or "SWA" to the
   division's clearing station, usually named. A man's own entry may be posted days or weeks later, when the company
   catches up, and the record of events' count for the day may not include him.
2. **Between the clearing station and England.** An evacuation hospital, then a ship or an aircraft. No online record
   found so far names patients at these steps; the company's report and the English hospital's are the two ends.
3. **The transit hospital.** Hospitals near the south-coast ports took in each day's casualties and sent most of them on
   within a day. They filed an **Admission & Disposition Report** (ETOUSA MD Form 3244) with their hospital plant's
   Detachment of Patients reports: one line per case, with name and serial number, grade and unit, cause (wound,
   injury, disease), condition, date of admission, disposition ("Evac" and the receiving hospital) and a brief diagnosis
   ("BC" for a battle casualty). The plant's own report gives the day's totals and where they went.
4. **Hospital plants.** In the United Kingdom patients were carried on the rolls of numbered **US Army Hospital
   Plants** ("Det of Pnts, <number> USA Hosp Plant"), filmed under the plant, not the hospital that ran it; the
   hospital is named on the transit hospital's dispositions and in orders. The receiving plant's record of events can
   give the arrival (by hospital train from which hospital, at what hour), and its daily supplements list the patients
   by name.
5. **Back to duty.** A hospital's special orders return men ("RTD") to a replacement control depot, and the next unit
   is found, if at all, in the depot's shipment rosters. A line struck through on a filmed copy of an order is usually
   the clerk's posting mark, not a revocation; check it against the report's count.
6. **The hospital admission cards.** The Army's hospital admission card files, one data file a year (Record Group 112:
   [1944](https://catalog.archives.gov/id/235111183), [1945](https://catalog.archives.gov/id/235111208)), hold one
   fixed-width record per admission, with the diagnosis, the wound's location, the causative agent, the disposition and
   the days lost. Each download carries its record layout and code lists; the serial number is written with a leading
   zero, so `grep '^0<ASN>'` finds a man's rows.

## What doesn't survive online

The ship and port of an Atlantic or Channel crossing; the patients of a field or evacuation hospital on the Continent;
and every morning report of 1945, which is on microfilm only at St. Louis. A discharge paper (WD AGO Form 53-55) names
the last unit, the campaigns and the decorations, and is often the only way past December 1944.
