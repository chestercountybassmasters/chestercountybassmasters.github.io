# Chester County Bass Masters — club website

The new club website, as a set of plain pages that GitHub Pages can serve from
the `docs/` folder. Started on 20 November 2026 from the first design and from
the copy of the old Weebly site taken that day.

**Not published.** This folder is a local git repository with no remote. Nothing
goes anywhere until Steve creates the public repository and says so.

People who only change sponsors, captions, the meeting line, officers or the
schedule: read [HOW_TO_UPDATE.md](HOW_TO_UPDATE.md). The rest of this page is for
whoever builds the site.

## Build and check

```bash
python3 build.py
```

writes the finished site into `docs/` and writes `records_check.md`. Then

```bash
python3 check.py
```

fails, loudly, if the data differs from the old site's pages, if any link or
picture address leads nowhere, or if a house rule is broken (see the top of
`check.py`). Open `docs/index.html` in a browser to look at the site.

Python 3, standard library only. No scripts on the pages; the only thing loaded
from another site is the two fonts from Google Fonts.

Every address inside the site is relative (`photos/logo.jpg`), never one that
starts with `/`, and no page names the repository. So the site works the same
opened from the folder, served under a sub-path
(`https://<organization>.github.io/<repository>/`) or served from the club's own
domain. `check.py` fails if an address starting with `/` appears. All pages sit
in one folder, which keeps this simple: do not move pages into sub-folders
without changing how `build.py` writes addresses.

## What is where

| Folder or file | What it holds | Who changes it |
|---|---|---|
| `content/` | Sponsors, photo captions, meeting line, officers, schedule: five plain files | Sean, Stan, anyone |
| `photos/` | The photos the front pages use | Sean, Stan, anyone |
| `templates/` | The six front pages (their words and layout) and `base.html`, the one header, menu and footer | Whoever edits the wording |
| `data/club/`, `data/opens/` | One results file for each season | Added to as results come in |
| `data/records_site.json` | The club's record lists, as they stood on the old site | Steve, when a record is confirmed |
| `archive/` | Pictures and PDFs taken from the old site (results pictures, old photos) | Nobody |
| `files/` | The three PDFs the front pages link to | Replace a file to update it |
| `assets/site.css` | The one stylesheet | |
| `tools/` | The importer and helpers (below) | |
| `docs/` | **The built site. Never edit it by hand: `build.py` writes it afresh each time.** | `build.py` |
| `records_check.md` | The records worked out from the data, against the club's lists | `build.py` |

Pages built: the six front pages (`index`, `results`, `opens`, `club`, `records`,
`schedule`), one page for each club season 2004–2026 (`club-2026.html` …), one for
each Opens season 2013–2026 (`opens-2026.html` …), and three small pages the
footer links to (`gallery`, `links`, `upper-bay-tournament-directors`).

### Front pages

The six templates are the design pages with their header and footer taken off.
Two kinds of marker in them are filled by the build:

- `{{…}}` — words from `content/` or from the data (a caption, the meeting line,
  the name of the latest tournament).
- `<!--rows:name--> … <!--/rows:name-->` — rows the build writes from the data.
  The rows left between the markers are the design's own; the build copies their
  styling for the rows it writes. Leave at least the first two in place.

Headlines and sentences that are a matter of judgement are plain words in the
templates and are **not** worked out from the data: "The 2026 season, final",
"Paul Sirochman, his fifth title", "Hansford and Dravk take it", "Twelve
tournaments, ending with the two-day Classic", the four big numbers at the top of
the records page, the 2026 honors box. Change them by hand when a season turns.

`python3 -I tools/compare_design.py` lists every line of words that differs
between the built front pages and the design. On 20 November 2026 the home, Opens
and club pages matched word for word; the differences on the others are the
sections added here (below).

### Adding a result

A season is one JSON file. A tournament in it looks like the ones already there
(`data/club/2026.json` is the cleanest to copy from): an `id` (its date), `dates`,
`waters`, `columns`, `results`, `summary`, and an entry in `flow` (the order of
things on the season's page). A new season needs a new file and nothing else: the
menus, the season pickers and the front pages pick it up. The scripts that will
write these files from the tournament workbooks do not exist yet.

## Where the results came from

`tools/import_weebly.py` read the season pages of Weebly's own archive of the old
site (read only) and wrote `data/`. It was run on 20 November 2026.
`data/import_report.txt` is its report. It reads tables; **it never reads numbers
out of pictures.**

| Seasons | How the old site held the results | On the new site |
|---|---|---|
| Club 2020–2026 | Tables | Text, from `data/`: every tournament, its summary lines, and the season standings |
| Club 2020 Classic | Three pictures | The pictures, as they are |
| Club 2020 standings | Not on the page | — |
| Club 2019 | Pictures, and Google Sheets shown in frames | The pictures; the sheets are linked (they are on Google, not in the copy) |
| Club 2004–2018 | Pictures of tables, with write-ups and photos from 2013 on | The pictures and words, in the old page's order |
| Opens 2021, 2022, 2024, 2025, 2026 | Tables | Text, from `data/` |
| Opens 2020 | Standings table; each Open as lines of text | The standings as a table, the results as the lines of text |
| Opens 2023 | Standings table only | The standings |
| Opens 2013–2019 | Pictures, with write-ups in 2013–2015 | The pictures and words, in the old page's order |

Counts for the seasons parsed from tables (tournaments / result rows):
club 2020 9/194, 2021 12/270, 2022 12/286, 2023 11/312, 2024 12/289, 2025 12/234,
2026 12/207; Opens 2021 5/388, 2022 6/393, 2024 6/349, 2025 7/333, 2026 5/303.
`check.py` recounts the old pages with its own reader and compares.

What the importer keeps: names are shown as the old site wrote them, except that
names in capitals are put in ordinary case (the original is kept in the data as
`name_as_written`). A cell the importer could not name is kept with its row as a
note, not dropped. Every row of every table is accounted for; `check.py` fails if
one is not.

## Added to the design

- `results.html`: an "Every season" block at the foot, so every season from 2004
  is one step from the menu.
- `records.html`: "Top ten on each water" at the foot (the design's table of
  waters says "pick a water for its top ten"), and the additions box (below).
- The three small pages, built from the old site's Member Gallery, links and
  Upper Bay Tournament Directors pages.
- The footer on every page is the home page's full footer (the design's inner
  pages had a shorter one). The menu marks the page you are on in amber.

## Records

The records page shows the club's lists as they stood on the old site. `build.py`
also works the top bags out from the table seasons and writes every difference to
`records_check.md`. A bag the check finds that is not on a list is shown under
that list in a cream box marked "Addition found by the records check", and is not
a record until Steve confirms it. To accept one, add it to
`data/records_site.json` by hand; the box then goes away by itself.

## Not verified, and known gaps

Confirmed (a record or Steve said it), unless marked otherwise:

- **Inferred:** the links on sponsor names in `content/sponsors.md` are the
  addresses behind the logos on the old site's sponsor page, matched by the
  address itself. JB Jigz had none.
- **Inferred:** files named `divider…` and `bluefish…` on the old pages are
  decorative strips (3750 by 300 pixels) and are shown as a thin line.
- **Not verified:** that any link to another site still works. They are the old
  site's own addresses (`mdbass.com`, `mdbassnation.com/tournaments`, the message
  board, the old pictures on the club's host, Facebook, the 2019 Google Sheets).
  `check.py` checks links inside the site only.
- **Not verified:** every season before 2020, and the 2020 Classic. They are
  pictures and were not read. Which pictures are result tables and which are
  photographs was not looked at one by one.
- **Not checked:** rider bags (the tables do not say who rode) and, in effect, the
  Top Bass list (see `records_check.md`).
- **Kept as the design had it, and probably wants rewording:** the box "How this
  page would work" on the results page, which describes the site as a plan.
- **Placeholders left in square brackets**, as in the design: photo captions,
  sponsor logos and "the rest of the list", 2027 club and Opens dates, the next
  meeting date, 2027 dues totals, 2027 Team Championship rules, how boat numbers
  are given out, the 2026 prize list for 2027, the map of the off-limits line,
  the November 14 cash Open result. Added here in the same way: "[Map of the
  ramps we use: to come]" (the design linked to a map; the old site has none) and
  "[Names to come.]" on the gallery.
- **Missing from both copies of the old site:** the full-size versions of the 14
  pictures on the 2011 club page (the page-size versions are there and are shown),
  and one picture on the 2013 club page.
- **Size:** `archive/` is about 140 MB (848 pictures and PDFs), and `docs/` holds
  a second copy, because the built site has to stand on its own. Git stores the
  two copies once.
- The season picker on a season page lists every year, which is long on a phone.

## Tools

| Script | What it does |
|---|---|
| `tools/import_weebly.py` | The one-time import from the old site into `data/` and `archive/`. Needs the club's Drive, or `CCBM_WEEBLY_ARCHIVE` set to the `weebly_archive` folder. Run it with `python3 -I`. |
| `tools/weebly.py` | Reads an old page into words, pictures and tables. |
| `tools/convert_design.py` | The one-time conversion of the design pages into `templates/`. Refuses to run again without `--force`, since it would overwrite hand edits. |
| `tools/compare_design.py` | Lists the words that differ between the built front pages and the design. |
| `tools/records.py` | The records check. |

`check.py --no-source` skips the comparison with the old pages, for a machine
without the club's Drive.
