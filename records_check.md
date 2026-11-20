# Records check

Written by `build.py` on 2026-11-20. It compares the lists on the old site's records page
(`top-bags-lunkers-aoys-etc.html`, copied 2026-11-20) with the results held in `data/`.
Nothing here changes a record. The records page shows the club's lists as they are, and marks
anything below under "Missing" as an addition found by this check, for Steve to confirm.

## What was checked

- Club seasons parsed from tables: 2020, 2021, 2022, 2023, 2024, 2025, 2026. 1475 bags and 481 big-fish weights were counted.
- One bag for each angler for each tournament day. A two-day Classic gives two bags, each on its own water and date.
- The weight is the total after penalties where the table has a total column.
- Not checked: every season whose results are pictures (2004 to 2019), the 2020 Classic (its result is three pictures),
  and whether a bag was a rider's (the tables do not say who rode).
- "Top Bass" is checked against the big-fish column of the tables. The 2020 tables have no such column, and an
  angler's big fish is in the table only if it was weighed, so that check is weaker than the bag check.

## Changes made to the club's lists since the copy

Made by hand in `data/records_site.json`, each at the Tournament Director's word. The lists below are
compared as they now stand.

- 2026-11-20, Top Bags on Nanticoke: added Steve Manista, 11.94, 11/7/2026 in place 8; Stephan Sirochman, 11.6, 4/22/2023 dropped off the end. Found missing by the records check (records_check.md). Confirmed by Steve Weimar on 11/20/26: "Manista's 11.94 is confirmed, add it to the list". Matches the club's live records page as Loren updated it the same day (as reported by the session that compared the live page with the morning's copy; the live page was not read again here).

## Summary

| List | On the site | Confirmed in tables | Missing from the list | Differences | Not checkable |
|---|---|---|---|---|---|
| Top Bags | 10 | 2 | 0 | 0 | 8 |
| Top Bags on North East | 10 | 3 | 0 | 0 | 7 |
| Top Bags on Nanticoke | 10 | 7 | 0 | 0 | 3 |
| Top Bags on Conowingo | 10 | 8 | 0 | 0 | 2 |
| Top Bags on Marshyhope | 10 | 10 | 0 | 0 | 0 |
| Top Bags on Sassafras | 10 | 2 | 0 | 0 | 8 |
| Top Bags on Potomac | 10 | 6 | 0 | 0 | 4 |
| Top Bags on Gunpowder | 10 | 2 | 0 | 0 | 8 |
| Top Bass | 10 | 0 | 0 | 0 | 10 |
| Top Rider Bags | 10 | 4 | not checked | 0 | 6 |

**0 missing entries found in all.**

## Top Bags

No missing entry found in the table seasons.

Confirmed in the tables: 2 of 10.
Not checkable (8): Stan Horne 21.49 on 5/26/2018; Lou Croce 20.08 on 5/26/2018; Stan Horne 19.35 on 5/28/2016; Lou Croce 19.31 on 6/9/2012; Mark Ely 19.04 on 6/6/2015; Stan Horne 18.84 on 6/5/2010; Lou Croce 18.82 on 5/4/2019; Jerry Gerlach 18.76 on 6/30/2012.

## Top Bags on North East

No missing entry found in the table seasons.

Confirmed in the tables: 3 of 10.
Not checkable (7): Stan Horne 21.49 on 5/26/2018; Lou Croce 20.08 on 5/26/2018; Stan Horne 19.35 on 5/28/2016; Lou Croce 19.31 on 6/9/2012; Mark Ely 19.04 on 6/6/2015; Stan Horne 18.84 on 6/5/2010; Jerry Gerlach 18.76 on 6/30/2012.

## Top Bags on Nanticoke

No missing entry found in the table seasons.

Confirmed in the tables: 7 of 10.
Not checkable (3): Lou Croce 12.61 on 4/13/2019; Sam Montalto 12.59 on 4/21/2018; Stan Horne 12.49 on 5/20/2017.

## Top Bags on Conowingo

No missing entry found in the table seasons.

Confirmed in the tables: 8 of 10.
Not checkable (2): Mark Ely 15.51 on 9/21/2013; Sean Geerlof 11.88 on 10/22/2011.

## Top Bags on Marshyhope

No missing entry found in the table seasons.

Confirmed in the tables: 10 of 10.

## Top Bags on Sassafras

No missing entry found in the table seasons.

Confirmed in the tables: 2 of 10.
Not checkable (8): Lou Croce 18.82 on 5/4/2019; Mark Ely 17.51 on 11/8/2020; Lou Croce 17.43 on 5/5/2018; Sean Geerlof 17.23 on 11/8/2020; Paul Sirochman 16.18 on 11/8/2020; Ken Jester 15.31 on 11/8/2020; Sean Geerlof 14.4 on 5/5/2018; Steve Weimar 14.39 on 11/8/2020.

## Top Bags on Potomac

No missing entry found in the table seasons.

Confirmed in the tables: 6 of 10.
Not checkable (4): Stan Horne 14.81 on 5/5/2012; Jimmy Jeff Townsend 13.98 on 5/5/2012; Eli Amilani 12.88 on 4/26/2014; Dan Augustine 12.39 on 5/7/2011.

## Top Bags on Gunpowder

No missing entry found in the table seasons.

Confirmed in the tables: 2 of 10.
Not checkable (8): Sean Geerlof 14.08 on 8/18/2012; Stan Horne 13.47 on 9/26/2009; Dave Bolesta 10.97 on 5/26/2007; Bill Meisle 8.61 on 6/7/2008; George Waeckel 7.65 on 6/7/2008; Ryan Mcnicholas 6.97 on 9/26/2009; Lou Croce 6.47 on 9/26/2009; Lou Croce 6.08 on 5/9/2009.

## Top Bass

No missing entry found in the table seasons.

Confirmed in the tables: 0 of 10.
Not checkable (10): Jerry Gerlach 7.18 on 5/24/2014; Mark Ely 6.72 on 5/23/2015; Jimmy Pitcherello 6.7 on 6/14/2014; Jerry Gerlach 6.55 on 5/26/2018; Bill Allison 6.41 on 8/4/2012; Lou Croce 6.21 on 5/4/2019; Lou Croce 6.15 on 5/7/2016; Tom Best 5.98 on 5/23/2015; Steve Weimar 5.91 on 11/7/2015; Steve Manista 5.9 on 5/23/2020.

## Top Rider Bags

Missing rider bags cannot be found from the tables: they do not say who was a rider.

Confirmed in the tables: 4 of 10.
Not checkable (6): Kyle Clevenger 17.76 on 6/30/2012; JW Wade 16.20 on 9/8/2018; Dave Curci 15.01 on 10/1/2016; Dan Augustine 14.33 on 6/1/2013; Ryan Sweeney 13.90 on 6/30/2018; Tom Best 13.75 on 5/28/2016.

## Slips in the tables

A "big fish" heavier than the angler's whole bag. Left out of the Top Bass check; shown on the season page as the table has it.

- Rick Orlando, 10/22/2022: big fish written as 2,21, bag 7.96. `data/club/2022.json`, tournament `2022-10-22`.

## Waters with no list on the site

The tables hold club tournaments on these waters, and the old records page has no list for them.
The heaviest bags in the table seasons, for information:

- **Choptank:** Travis Nale 8.16 (8/9/2025); Loren Meckle 2.95 (8/9/2025); Joe Wesley 2.27 (8/9/2025); Sam Montalto 2.22 (8/9/2025); JC Henry 2.18 (8/9/2025)
- **Wicomico:** Tom Yaw 9.29 (7/25/2020); Tom Wood 8.39 (7/25/2020); Ryan Sweeney 7.39 (6/5/2021); JC Henry 6.76 (7/25/2020); Jim (Woo) Hauck 6.43 (6/5/2021)

## Champions

What the tables can confirm of the champions lists (a first row of a standings table, a first row of a Classic).

| Year | Title | The site's list | The tables | Agree |
|---|---|---|---|---|
| 2020 | Classic winner | Sean Geerlof | no table | not checkable |
| 2020 | Angler of the Year | Stan Horne | no table | not checkable |
| 2021 | Classic winner | Paul Sirochman | Paul Sirochman | yes |
| 2021 | Angler of the Year | Paul Sirochman | Paul | yes |
| 2022 | Classic winner | Lou Croce | Lou Croce | yes |
| 2022 | Angler of the Year | Paul Sirochman | Paul | yes |
| 2023 | Classic winner | Paul Sirochman | Paul Sirochman | yes |
| 2023 | Angler of the Year | Paul Sirochman | Paul | yes |
| 2024 | Classic winner | Paul Sirochman | Paul Sirochman | yes |
| 2024 | Angler of the Year | Travis Nale | Travis | yes |
| 2025 | Classic winner | Pavlo Fenik | Pavlo Fenik | yes |
| 2025 | Angler of the Year | Paul Sirochman | Paul Sirochman | yes |
| 2026 | Classic winner | Steve Manista | Steve Manista | yes |
| 2026 | Angler of the Year | Paul Sirochman | Paul Sirochman | yes |
