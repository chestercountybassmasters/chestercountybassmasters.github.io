# Chester County Bass Masters — club website

The new club website, as a set of plain pages that GitHub Pages can serve from
the `docs/` folder. Started on 20 November 2026 from the first design and from
the copy of the old Weebly site taken that day.

**Published from** the public repository
`chestercountybassmasters/chestercountybassmasters.github.io` (first pushed on
20 November 2026, at Steve's word). Its address is
`https://chestercountybassmasters.github.io/` until the club's domain is pointed
at it. GitHub Pages is to serve the `/docs` folder of `main` (repository
Settings, Pages). **Nothing is pushed unless Steve says so**: a commit here is
local until then.

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
`check.py`).

## Publishing

`.github/workflows/publish.yml` rebuilds the site on GitHub itself: on every push
to `main`, and from the "Run workflow" button on the Actions tab. It checks out
the repository, runs `python3 build.py`, runs `python3 check.py`, and only if both
succeed hands the freshly built `docs/` to GitHub Pages and publishes it. One run
at a time. If the build or a check fails, nothing is published and the site stays
as it was; GitHub e-mails whoever made the change.

So a change made on the GitHub website to a file in `content/` (or a photo added
to `photos/`) goes live by itself, with no one running the build.

**It needs one setting.** Repository Settings, Pages, "Build and deployment",
Source: **GitHub Actions**. Until then the source is "Deploy from a branch"
(`main`, `/docs`): the workflow's last step fails, and the site goes on being
served from the `docs/` folder as committed.

What the switch changes:

- Before: the site is whatever `docs/` holds in the last push. Someone has to run
  `build.py` and commit `docs/`, or the site does not change.
- After: the site is what the workflow builds from `content/`, `templates/`,
  `data/` and the rest. The `docs/` folder in the repository is no longer what is
  served, and goes out of date the first time someone edits `content/` on the
  GitHub website.

**For Steve to decide after the switch:** should `docs/` stop being tracked in
git? For: it would no longer be served, it would go stale and mislead, and it
doubles every commit that touches a page. Against: with `docs/` tracked, switching
the source back to "Deploy from a branch" is a one-click fallback if Actions ever
gives trouble. It is tracked for now.

GitHub's own machine has no access to the club's Drive, so there `check.py` cannot
compare `data/` with the old site's pages. It prints a line starting `SKIPPED` for
that one part and runs everything else: each season file against its own counts,
every link and picture address (spelled letter for letter as the file is, since
GitHub's servers tell capitals from small letters and a Mac does not), no address
starting with `/`, `.nojekyll`, and contrast. The comparison with the old pages
still runs on Steve's Mac, where it matters: when `data/` is changed by the
importer. `python3 check.py --require-source` fails if the old pages are absent.

The Pages upload leaves out files whose names start with a dot, so `.nojekyll` is
not in what the workflow publishes; that is harmless, because a workflow publish
does not run Jekyll (inferred from GitHub's documentation, not yet seen in a run).

GitHub Pages runs Jekyll over what it serves unless the folder holds a file named
`.nojekyll`, and Jekyll leaves out every file whose name starts with `_` (337 of
the old pictures do). So `build.py` writes an empty `docs/.nojekyll` each time,
and `check.py` fails if it is missing. The `.nojekyll` and `index.html` at the top
of the repository are a safety net for the case where Pages is set to serve the
top of the repository instead of `/docs`: the page there only sends the visitor
on to `docs/index.html`. Open `docs/index.html` in a browser to look at the site.

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
| `content/` | Sponsors, photo captions, meeting line, officers, schedule, members: six plain files | Sean, Stan, anyone |
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
- Home page, top (Steve, 20 November 2026): the club logo as a round badge at the
  bottom middle of the photo, clear of the fish tails; no caption under that photo (the caption
  line in `content/photo-captions.md` is empty, and an empty caption shows
  nothing); and the bottom of the photo level with the last line of the words
  beside it. The layout is `.hero` in `assets/site.css`; the badge's size and
  place are on the element in `templates/home.html`.
- The footer on every page is the home page's full footer (the design's inner
  pages had a shorter one). The menu marks the page you are on in amber.

## Records

The records page shows the club's lists as they stood on the old site. `build.py`
also works the top bags out from the table seasons and writes every difference to
`records_check.md`. A bag the check finds that is not on a list is shown under
that list in a cream box marked "Addition found by the records check", and is not
a record until Steve confirms it. To accept one, add it to
`data/records_site.json` by hand and note it under `source.changes` there; the
box then goes away by itself, and the importer will not write over the file.

Done once so far: Steve Manista's 11.94 lb on the Nanticoke (11/7/2026), found by
the check, confirmed by Steve on 20 November 2026 and added in eighth place.

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
- **Taken out at Steve's word (20 November 2026):** the design's box "How this page
  would work" on the results page.
- **As the old site had them, and partly out of date:** the lines in
  `content/members.md` (the member gallery). On the old site they showed when the
  mouse was over a photo; here they are words under each photo, so they can be
  read on a phone. Three officer titles in them were changed on 20 November 2026 to
  match `content/officers.md` (Eli Amilani, Stan Horne, Sam Montalto), at Steve's
  word; the boats have not been checked. Greg Arrowood, the Vice President, has
  no photo in the gallery.
- **Placeholders left in square brackets**, as in the design: photo captions,
  sponsor logos and "the rest of the list", 2027 club and Opens dates, the next
  meeting date, 2027 dues totals, 2027 Team Championship rules, how boat numbers
  are given out, the 2026 prize list for 2027, the map of the off-limits line,
  the November 14 cash Open result. Added here in the same way: "[Map of the
  ramps we use: to come]" (the design linked to a map; the old site has none).
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

`check.py` skips the comparison with the old pages on a machine without the
club's Drive and says so; see "Publishing" above.
