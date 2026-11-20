#!/usr/bin/env python3
"""Import the results from the copy of the old Weebly site into data/.

Run once (and again only if the importer changes):

    python3 -I tools/import_weebly.py

It reads the season pages in the Weebly archive (read only), writes one JSON file
per season under data/club/ and data/opens/, writes the site's own record lists to
data/records_site.json, and copies the pictures and PDFs those pages use into
archive/. Standard library only.

What it does not do: read numbers out of pictures. A season whose results are
pictures gets a JSON file that lists the pictures and words in page order.
"""
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import weebly  # noqa: E402

UP = 'uploads/1/1/3/6/11368969/'
CLUB_YEARS = range(2004, 2027)
OPEN_YEARS = range(2013, 2027)
SOURCE_DATE = '2026-11-20'

NAME_HDR = re.compile(r'^(participants?|anglers?|teams?)$', re.I)
HDR_WORD = re.compile(r'(?i)^(place|overall place|#?\s*fish|total|wgt\.?|weight|#\s*\d|tx\s*\d|pts\.?|points|'
                      r'best|day\s*\d|tournament scores)')
SUB_HDR = re.compile(r'^(#?\s*fish|weight|wgt\.?|b/f|penalty|lunker)$', re.I)
LABELISH = re.compile(r'(?i)^(overall\s+|day\s*\d\s+)?(total\b|average\b|avg\b|teams? fished|teams?:?$|'
                      r'#\s*of\b|#\s*fish|number\b|anglers?:?$)')
PLACE = re.compile(r'[\[(]?[\dA-Za-z]{0,6}[\])]?\.?')
NUMISH = re.compile(r'^\$?[\d,]*\.?\d+\*?$')
DATE_TOKEN = re.compile(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?')
TOURN_MARK = re.compile(r'(?i)tournament report|team tournament results|ccbm tx\s*#')
DECOR = re.compile(r'(?i)^(divider|bluefish)')
OFF_LIMITS = re.compile(r'(?i)(off-limits|screen-shot-2019-01-29-at-11-20-32)')

WATERS = [  # (what to look for, name used on the site)
    ('north east', 'North East'), ('northeast', 'North East'), ('nanticoke', 'Nanticoke'),
    ('conowingo', 'Conowingo'), ('marshyhope', 'Marshyhope'), ('sassafras', 'Sassafras'),
    ('potomac', 'Potomac'), ('gunpowder', 'Gunpowder'), ('wicomico', 'Wicomico'),
    ('choptank', 'Choptank'), ('hudson', 'Hudson'),
]

OPENS_DROP = re.compile(
    r'(?i)^(chester county bass masters open|your browser does not support|all participants, please read|'
    r'"?.?like it never|\d{3}-\d{3}-\d{4}$|download file|mail entry form|online entry|open details|'
    r'side (option )?pot|other prizes|\$ ?80\.00other prizes|4 lunkers|_{5,}|'
    r'open north east river in north east|sponsored by|sponsors$|contingency cash awards|'
    r'open photos can be found|other future events|ccbm open - northeast river)')
RULES_END = re.compile(r'(?i)(schedule|results|standings)')

# What a reader should know about a season's page. Written by hand after looking at the pages.
SEASON_NOTES = {
    ('club', 2020): 'Nine tournaments are tables. The result of the two-day Classic (November 7 and 8) is '
                    'three pictures on the old page, shown here as they are.',
    ('club', 2019): 'The results of this season are pictures and Google Sheets that the old page showed in '
                    'frames. The pictures are shown as they are; the sheets are linked and are outside this site.',
    ('opens', 2020): 'The season standings are a table. Each Open\'s result is lines of text on the old page, '
                     'kept here as written.',
    ('opens', 2023): 'Only the season standings are on the old page for 2023. The result of each Open was '
                     'posted on the Opens Facebook group.',
}

warnings = []


def warn(msg):
    warnings.append(msg)
    print('  WARNING: ' + msg)


def find_source():
    env = os.environ.get('CCBM_WEEBLY_ARCHIVE')
    if env:
        return env
    pat = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-*/My Drive/CCBM/website/'
                             'weebly_2026-11-20/weebly_archive')
    hits = [p for p in sorted(glob.glob(pat)) if os.path.isfile(os.path.join(p, '2026-club-results.html'))]
    return hits[0] if hits else None


# ---------------------------------------------------------------- small helpers

def is_blank(row):
    return not any(c.strip() for c in row)


def is_label(s):
    s = s.strip()
    return bool(s) and (s.endswith(':') or LABELISH.match(s) is not None)


def num(s):
    """A weight or count as a number, or None. '11.10*' is 11.10."""
    s = (s or '').strip().rstrip('*').replace(',', '').lstrip('$')
    try:
        return float(s)
    except ValueError:
        return None


def water_name(text):
    low = text.lower()
    found = []
    for key, name in WATERS:
        i = low.find(key)
        if i >= 0 and name not in [n for _, n in found]:
            found.append((i, name))
    return [n for _, n in sorted(found)]


def tidy_name(name):
    """PAUL SIROCHMAN -> Paul Sirochman. Mixed-case names are left alone."""
    name = ' '.join(name.split())
    if name.isupper():
        def cap(m):
            w = m.group(0)
            return w if w in ('JC', 'JW', 'JT', 'II', 'III', 'IV') else w.capitalize()
        return re.sub(r"[A-Za-z']+", cap, name)
    return name


# ---------------------------------------------------------------- tables into sections

def find_sections(rows):
    """Split one table into sections, each starting at its title rows.

    Returns (sections, kind_of_table). A section is a dict with first, top, head, sub,
    body_start, end (row numbers) and title (list of title lines)."""
    def is_head(r):
        cells = [c.strip() for c in r if c.strip()]
        return len(cells) >= 3 and any(NAME_HDR.match(c) for c in cells) \
            and any(HDR_WORD.search(c) for c in cells if not NAME_HDR.match(c))
    heads = [i for i, r in enumerate(rows) if is_head(r)]
    sections = []
    prev_end = -1
    for h in heads:
        if sections and h < sections[-1]['body_start']:
            continue
        top, group = h, None
        if h > 0 and re.search(r'(?i)day\s*1', ' '.join(rows[h - 1])) \
                and not any(NAME_HDR.match(c.strip()) for c in rows[h - 1]):
            group, top = h - 1, h - 1
        sub = None
        if h + 1 < len(rows):
            cells = [c.strip() for c in rows[h + 1] if c.strip()]
            if len(cells) >= 4 and all(SUB_HDR.match(c) or is_label(c) or NUMISH.match(c) for c in cells) \
                    and sum(1 for c in cells if SUB_HDR.match(c)) >= 4:
                sub = h + 1
        title, i, gap = [], top - 1, 0
        # some pages leave an empty row between the title rows and the header row
        while i > prev_end and gap < 2 and is_blank(rows[i]):
            i -= 1
            gap += 1
        while i > prev_end and len(title) < 4 and not is_blank(rows[i]):
            cells = [c.strip() for c in rows[i] if c.strip()]
            if len(cells) != 1 or cells[0].startswith('*'):
                break
            title.insert(0, cells[0])
            i -= 1
        if not title:
            gap = 0
        first = top - gap - len(title)
        sections.append({'first': first, 'top': top, 'group': group, 'head': h, 'sub': sub, 'gap': gap,
                         'body_start': (sub if sub is not None else h) + 1, 'title': title})
        prev_end = sections[-1]['body_start'] - 1
    for k, s in enumerate(sections):
        s['end'] = sections[k + 1]['first'] if k + 1 < len(sections) else len(rows)
    return sections


def column_defs(rows, spans, s, row_offset=0):
    """Work out what each column of a section holds, from its header rows."""
    h, sub, g = s['head'], s['sub'], s['group']
    ncols = max(len(r) for r in rows[s['top']:s['end']])
    pad = lambda r: list(r) + [''] * (ncols - len(r))  # noqa: E731
    head = [c.strip() for c in pad(rows[h])]
    # a summary that sits to the right of the header row is not a column heading
    head = ['' if (c.endswith(':') or NUMISH.match(c)) else c for c in head]
    group = [''] * ncols
    if g is not None:
        cur = ''
        for c, text in enumerate(pad(rows[g])):
            if text.strip():
                cur = text.strip()
            group[c] = cur
    elif sub is not None:
        for (r, c, rs, cs) in spans:
            if r == h and cs > 1:
                for k in range(cs):
                    if c + k < ncols:
                        group[c + k] = head[c]
    base = list(head)
    if sub is not None:
        subrow = [c.strip() for c in pad(rows[sub])]
        for c in range(ncols):
            if group[c] and SUB_HDR.match(subrow[c]):
                base[c] = subrow[c]
            elif group[c] and not SUB_HDR.match(subrow[c]):
                group[c] = ''  # a merged header that the second row does not sit under
                if c > 0 and not head[c]:
                    base[c] = ''
    # a header cell merged across several columns with no second row: number the columns
    if sub is None and g is None:
        for (r, c, rs, cs) in spans:
            if r == h and cs > 1:
                for k in range(cs):
                    if c + k < ncols:
                        base[c + k] = '%s %d' % (head[c], k + 1)
    cols, day = [], None
    for c in range(ncols):
        gtxt, b = group[c], base[c]
        label = (gtxt + ' ' + b).strip() if gtxt and gtxt.lower() != b.lower() else b
        low, glow = b.lower(), gtxt.lower()
        both = (glow + ' ' + low).strip()
        total = False
        if re.search(r'day\s*1', both):
            day = 'd1'
        elif re.search(r'day\s*2', both):
            day = 'd2'
        elif glow.startswith('total') or low.startswith('total'):
            total = True
        kind = None
        if 'place' in low:
            kind = 'place'
        elif NAME_HDR.match(b):
            kind = 'name'
        elif 'fish' in low and 'b/f' not in low:
            kind = 'fish'
        elif low in ('weight', 'wgt', 'wgt.', 'total') or 'weight' in low:
            kind = 'weight'
        elif 'b/f' in low or 'lunker' in low:
            kind = 'big_fish'
        elif 'penal' in low or 'pnlty' in low:
            kind = 'penalty'
        elif 'points' in low or low in ('pts', 'pts.'):
            kind = 'points'
        if kind in ('place', 'name', 'points'):
            day = None
        role = kind
        if kind in ('fish', 'weight') and total:
            role = 'total_' + kind
        elif kind in ('fish', 'weight', 'big_fish', 'penalty') and day and not total:
            role = day + '_' + kind
        cols.append({'role': role, 'label': label})
    roles = [c['role'] for c in cols]
    if 'place' not in roles and 'name' in roles and roles.index('name') > 0 \
            and not cols[roles.index('name') - 1]['label']:
        cols[roles.index('name') - 1].update(role='place', label='Place')  # header cell left empty
    seen = {}
    for c in cols:
        if c['role']:
            seen[c['role']] = seen.get(c['role'], 0) + 1
            if seen[c['role']] > 1:
                c['role'] = None  # a second column of the same kind: keep its cells as extras
    return cols


def pairs_from_cells(cells, cols=None, two_day=False):
    """Turn the leftover cells of a row, [(column, text), ...], into summary pairs and notes."""
    pairs, notes, i = [], [], 0
    last_label = None
    while i < len(cells):
        c, t = cells[i]
        t = t.strip()
        nxt = cells[i + 1][1].strip() if i + 1 < len(cells) else None
        if is_label(t) and nxt is not None and not is_label(nxt) and len(nxt) < 60:
            pairs.append({'label': t.rstrip(':').strip(), 'value': nxt})
            last_label = t.rstrip(':').strip()
            i += 2
            continue
        m = re.match(r'^([^:]{2,40}):\s*(\S.*)$', t)
        if m and not NUMISH.match(t):
            pairs.append({'label': m.group(1).strip(), 'value': m.group(2).strip()})
        elif NUMISH.match(t) and last_label and cols and c < len(cols) and cols[c]['label']:
            pairs.append({'label': '%s, %s' % (last_label, cols[c]['label']), 'value': t})
        elif t:
            notes.append(t)
        i += 1
    if two_day:
        seen = {}
        for p in pairs:
            seen.setdefault(p['label'], []).append(p)
        for label, ps in seen.items():
            if len(ps) == 2:
                ps[0]['label'] = 'Day 1 ' + label
                ps[1]['label'] = 'Day 2 ' + label
    return pairs, notes


def parse_tournament(rows, spans, s, year, series, rows_nl=None):
    cols = column_defs(rows, spans, s)
    roles = [c['role'] for c in cols]
    two_day = 'd1_weight' in roles
    try:
        pc, nc = roles.index('place'), roles.index('name')
    except ValueError:
        pc, nc = (roles.index('name') - 1 if 'name' in roles and roles.index('name') > 0 else None), \
                 (roles.index('name') if 'name' in roles else None)
    t = {'title_lines': s['title'], 'columns': [c for c in cols if c['role']], 'results': [],
         'summary': [], 'notes': []}
    counts = {'title': len(s['title']), 'header': s['body_start'] - s['top'], 'results': 0,
              'other': 0, 'blank': s['gap']}
    # summary cells that sit beside the header rows (2025 club pages)
    for r in range(s['top'], s['body_start']):
        left = [(c, x) for c, x in enumerate(rows[r]) if x.strip() and (c >= len(cols) or not cols[c]['label'])]
        left = [(c, x) for c, x in left if x.strip().endswith(':') or NUMISH.match(x.strip()) or ':' in x]
        p, n = pairs_from_cells(left, cols, two_day)
        t['summary'] += p
    guest_section = False
    for r in range(s['body_start'], s['end']):
        row = rows[r]
        if is_blank(row):
            counts['blank'] += 1
            continue
        get = lambda c: row[c].strip() if c is not None and c < len(row) else ''  # noqa: E731
        place, name = get(pc), get(nc)
        others = [x for c, x in enumerate(row) if x.strip() and c not in (pc, nc)]
        is_result = bool(name) and not is_label(name) and not is_label(place) \
            and PLACE.fullmatch(place) is not None and (place or others)
        if is_result:
            res = {}
            for c, col in enumerate(cols):
                if col['role']:
                    res[col['role']] = get(c)
            res['name'] = tidy_name(name)
            if res['name'] != name:
                res['name_as_written'] = name
            left = [(c, x) for c, x in enumerate(row) if x.strip() and (c >= len(cols) or not cols[c]['role'])]
            pair_cells, extra = [], []
            k = 0
            while k < len(left):
                c, x = left[k]
                if is_label(x) and k + 1 < len(left):
                    pair_cells += [left[k], left[k + 1]]
                    k += 2
                elif re.match(r'^(Day ?\d|Overall|Total|Average|Avg)[^:]*:\s*\S', x):
                    pair_cells.append(left[k])
                    k += 1
                else:
                    extra.append(x.strip())
                    k += 1
            p, n = pairs_from_cells(pair_cells, cols, two_day)
            t['summary'] += p
            extra += n
            if extra:
                res['extra'] = extra
            low = (place + ' ' + name).lower()
            if guest_section or 'guest' in low:
                res['guest'] = True
            t['results'].append(res)
            counts['results'] += 1
        else:
            counts['other'] += 1
            src = rows_nl[r] if rows_nl else row
            cells = [(c, part) for c, x in enumerate(src) for part in x.split('\n') if part.strip()]
            if len(cells) == 1 and cells[0][1].strip().lower().rstrip(':') in ('guests', 'guest'):
                guest_section = True
                continue
            p, n = pairs_from_cells(cells, cols, two_day)
            t['summary'] += p
            t['notes'] += n
    t['source_rows'] = counts
    # --- title: dates and water
    title = ' '.join(x for x in s['title'] if not re.fullmatch(r'(?i)ccbm|tournament report|team tournament results', x.strip()))
    t['title'] = title
    dates = []
    for m in DATE_TOKEN.finditer(title):
        mo, d, y = int(m.group(1)), int(m.group(2)), m.group(3)
        y = year if y is None else (int(y) + 2000 if len(y) == 2 else int(y))
        try:
            dates.append(datetime.date(y, mo, d).isoformat())
        except ValueError:
            warn('%s %d: bad date in title %r' % (series, year, title))
    if not dates:
        warn('%s %d: no date found in title %r' % (series, year, title))
    t['dates'] = dates
    waters = water_name(title)
    if two_day:
        day_waters = []
        for d in ('d1', 'd2'):
            lab = ' '.join(c['label'] for c in cols if c['role'] and c['role'].startswith(d))
            w = water_name(lab)
            day_waters.append(w[0] if w else None)
        if not all(day_waters) and len(waters) >= 2:
            day_waters = waters[:2]
        t['two_day'] = True
        t['waters'] = day_waters
        if len(dates) != 2:
            warn('%s %d: two-day tournament with %d dates in title %r' % (series, year, len(dates), title))
    else:
        t['waters'] = waters[:1]
        if not waters:
            rest = DATE_TOKEN.sub('', title)
            rest = re.sub(r'(?i)ccbm|tx\s*#\s*\d+|open\b|cash prizes-only|-', ' ', rest).strip()
            t['waters'] = [rest] if rest else []
            if rest:
                warn('%s %d: water %r is not one the importer knows' % (series, year, rest))
    if re.search(r'(?i)classic', title) or two_day:
        t['classic'] = True
    if re.search(r'(?i)cash', title):
        t['cash_only'] = True
    return t


def parse_standings(rows, spans, s):
    cols = column_defs(rows, spans, s)
    labels = [c['label'] for c in cols]
    body, notes, counts = [], [], {'title': len(s['title']), 'header': s['body_start'] - s['top'],
                                   'rows': 0, 'other': 0, 'blank': s['gap']}
    for r in range(s['body_start'], s['end']):
        row = [c.strip() for c in rows[r]] + [''] * (len(labels) - len(rows[r]))
        cells = [c for c in row if c]
        if not cells:
            counts['blank'] += 1
        elif len(cells) == 1:
            notes.append(cells[0])
            counts['other'] += 1
        else:
            body.append(row)
            counts['rows'] += 1
    width = max([len(labels)] + [len(r) for r in body])
    labels += [''] * (width - len(labels))
    body = [r + [''] * (width - len(r)) for r in body]
    keep = [c for c in range(width) if labels[c] or any(r[c] for r in body)]
    return {'title_lines': s['title'], 'columns': [labels[c] for c in keep],
            'rows': [[r[c] for c in keep] for r in body], 'notes': notes, 'source_rows': counts}


# ---------------------------------------------------------------- pictures and files

class Copier:
    def __init__(self, source):
        self.source = source
        self.public = os.path.join(os.path.dirname(source), 'public_copy')
        self.done = {}
        self.bytes = 0
        self.missing = []

    def copy(self, src, page):
        """Copy an uploaded file into archive/ and return its path there, or None."""
        src = src.split('?')[0].strip()
        if not src.startswith(UP):
            return None
        rel = src[len(UP):]
        if rel in self.done:
            return self.done[rel]
        found = None
        for base in (self.source, self.public):
            p = os.path.join(base, src)
            if os.path.isfile(p):
                found = p
                break
        if not found:
            self.missing.append('%s: %s' % (page, src))
            self.done[rel] = None
            return None
        out_rel = 'archive/' + rel
        out = os.path.join(ROOT, out_rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if not (os.path.isfile(out) and os.path.getsize(out) == os.path.getsize(found)):
            shutil.copyfile(found, out)
        self.bytes += os.path.getsize(out)
        self.done[rel] = out_rel
        return out_rel


def fix_links(links, copier, page):
    out = []
    for href, text in links or []:
        if not text or not href or href.startswith('mailto:'):
            continue
        m = re.search(r'(\d{4})-(club|open)-results\.html', href)
        if m:
            out.append({'text': text, 'season': [('club' if m.group(2) == 'club' else 'opens'), int(m.group(1))]})
        elif href.startswith(UP):
            if href.lower().split('?')[0].endswith('.pdf'):
                f = copier.copy(href, page)
                if f:
                    out.append({'text': text, 'file': f})
        elif href.startswith('http') and 'weebly.com' not in href and len(href) > 10:
            out.append({'text': text, 'href': href})
    return out


# ---------------------------------------------------------------- one page

def import_page(source, series, year, copier):
    page = '%d-%s-results.html' % (year, 'club' if series == 'club' else 'open')
    path = os.path.join(source, page)
    with open(path, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    blocks = weebly.read_blocks(path)
    season = {'series': series, 'year': year,
              'source': {'page': page, 'copied': SOURCE_DATE, 'sha256': sha},
              'tournaments': [], 'standings': [], 'schedule': [], 'flow': []}
    flow = season['flow']
    acct = {'table_rows': 0, 'tournament_rows': 0, 'standings_rows': 0, 'schedule_rows': 0,
            'summary_table_rows': 0, 'file_table_rows': 0, 'other_table_rows': 0, 'blank_outside': 0,
            'unassigned': 0}
    in_rules = False
    ids = set()
    for b in blocks:
        kind = b['kind']
        if kind in ('heading', 'text'):
            text = b['text']
            if series == 'opens':
                if in_rules and RULES_END.search(text[:70]) and not text.lower().startswith('rules'):
                    in_rules = False
                if text.lower().startswith('rules') and len(text) > 5 or text.strip().lower() == 'rules':
                    in_rules = True
                if in_rules or OPENS_DROP.match(text.strip()):
                    continue
            if series == 'club' and re.fullmatch(r'(?i)tournament rules', text.strip()):
                links = fix_links(b.get('links'), copier, page)
                if links:
                    flow.append({'kind': 'text', 'lines': ['Tournament Rules'], 'links': links})
                continue
            if re.match(r'(?i)^create a free web site', text):
                continue
            item = {'kind': kind, 'lines': b.get('lines') or [text]}
            links = fix_links(b.get('links'), copier, page)
            if links:
                item['links'] = links
            flow.append(item)
        elif kind == 'image':
            src = b['src'].strip()
            name = src.split('?')[0].rsplit('/', 1)[-1]
            if not src.startswith(UP) or name in ('_1',):
                continue
            if DECOR.match(name):
                if flow and flow[-1]['kind'] != 'rule':
                    flow.append({'kind': 'rule'})
                continue
            if series == 'opens' and (b['href'].startswith('http') or OFF_LIMITS.search(name) or in_rules):
                continue
            f = copier.copy(src, page)
            if not f:
                flow.append({'kind': 'missing_image', 'source': src})
                continue
            item = {'kind': 'image', 'file': f}
            href = b['href'].split('?')[0]
            if href.startswith(UP) and re.search(r'(?i)\.(png|jpe?g|gif|webp)$', href) and href != src.split('?')[0]:
                full = copier.copy(href, page)
                if full:
                    item['full'] = full
            flow.append(item)
        elif kind == 'iframe':
            src = b['src']
            if 'docs.google.com/spreadsheets' in src:
                flow.append({'kind': 'external', 'href': src,
                             'text': 'Result sheet on Google Sheets (outside this site)'})
            elif 'youtube.com' in src:
                flow.append({'kind': 'external', 'href': src, 'text': 'Video on YouTube'})
        elif kind == 'table':
            rows_nl, spans = b['rows'], b.get('spans', [])
            rows = [[' '.join(c.split()) for c in r] for r in rows_nl]
            acct['table_rows'] += len(rows)
            sections = find_sections(rows)
            if not sections:
                texts = [c.strip() for r in rows for c in r if c.strip()]
                nonblank = [r for r in rows if not is_blank(r)]
                if any(t == 'File Size:' for t in texts):
                    acct['file_table_rows'] += len(rows)
                elif texts and re.search(r'(?i)schedule', texts[0]):
                    season['schedule'] = texts
                    acct['schedule_rows'] += len(rows)
                    flow.append({'kind': 'schedule'})
                elif nonblank and season['tournaments'] and all(
                        len([c for c in r if c.strip()]) == 2 and (is_label(r[0]) or ':' in r[0]) for r in nonblank):
                    t = season['tournaments'][-1]
                    for r in nonblank:
                        cells = [c.strip() for c in r if c.strip()]
                        t['summary'].append({'label': cells[0].rstrip(':').strip(), 'value': cells[1]})
                    t['source_rows']['summary_tables'] = t['source_rows'].get('summary_tables', 0) + len(rows)
                    acct['summary_table_rows'] += len(rows)
                else:
                    acct['other_table_rows'] += len(rows)
                    flow.append({'kind': 'table', 'rows': [[c.strip() for c in r] for r in nonblank]})
                    warn('%s %d: a table of %d rows was not recognised and is kept as it is: %r'
                         % (series, year, len(rows), texts[:3]))
                continue
            # rows before the first section
            for r in rows[:sections[0]['first']]:
                if is_blank(r):
                    acct['blank_outside'] += 1
                else:
                    cells = [c.strip() for c in r if c.strip()]
                    if season['schedule'] == [] and re.search(r'(?i)schedule', cells[0]):
                        pass
                    acct['unassigned'] += 1
                    warn('%s %d: row outside any section: %r' % (series, year, cells[:4]))
            for s in sections:
                title = ' '.join(s['title'])
                n = s['end'] - s['first']
                if re.search(r'(?i)standings', title):
                    st = parse_standings(rows, spans, s)
                    season['standings'].append(st)
                    acct['standings_rows'] += n
                    flow.append({'kind': 'standings', 'index': len(season['standings']) - 1})
                elif TOURN_MARK.search(title) or DATE_TOKEN.search(title):
                    t = parse_tournament(rows, spans, s, year, series, rows_nl)
                    tid = t['dates'][0] if t['dates'] else '%d-x%d' % (year, len(season['tournaments']) + 1)
                    while tid in ids:
                        tid += 'b'
                    ids.add(tid)
                    t['id'] = tid
                    t['source_rows']['table_rows'] = n
                    season['tournaments'].append(t)
                    acct['tournament_rows'] += n
                    flow.append({'kind': 'tournament', 'id': tid})
                elif re.search(r'(?i)schedule', title):
                    lines = [title] + [' '.join(c.strip() for c in r if c.strip())
                                       for r in rows[s['top']:s['end']] if not is_blank(r)]
                    season['schedule'] = lines
                    acct['schedule_rows'] += n
                    flow.append({'kind': 'schedule'})
                else:
                    acct['other_table_rows'] += n
                    keep = [[c.strip() for c in r] for r in rows[s['first']:s['end']] if not is_blank(r)]
                    flow.append({'kind': 'table', 'rows': keep})
                    warn('%s %d: a table section titled %r was not recognised and is kept as it is'
                         % (series, year, title))
    while flow and flow[-1]['kind'] == 'rule':
        flow.pop()
    season['source']['rows'] = acct
    if season['tournaments']:
        season['results_form'] = 'tables'
    elif season['standings']:
        season['results_form'] = 'standings table only'
    else:
        season['results_form'] = 'pictures'
    note = SEASON_NOTES.get((series, year))
    if note:
        season['note'] = note
    season['pictures'] = [x['file'] for x in flow if x['kind'] == 'image']
    return season


# ---------------------------------------------------------------- the site's record lists

def import_records(source):
    path = os.path.join(source, 'top-bags-lunkers-aoys-etc.html')
    out = {'source': {'page': 'top-bags-lunkers-aoys-etc.html', 'copied': SOURCE_DATE}, 'lists': []}
    for b in weebly.read_blocks(path):
        if b['kind'] != 'table':
            continue
        cur = None
        for r in b['rows']:
            cells = [c.strip() for c in r if c.strip()]
            if len(cells) == 1:
                cur = {'title': cells[0], 'rows': []}
                out['lists'].append(cur)
            elif cells and cur is not None:
                cur['rows'].append(cells)
    return out


def import_plain(source, page, copier):
    """A page that is only words, pictures, links and files: kept in page order."""
    flow = []
    for b in weebly.read_blocks(os.path.join(source, page)):
        if b['kind'] in ('heading', 'text'):
            if re.match(r'(?i)^create a free web site', b['text']):
                continue
            item = {'kind': b['kind'], 'lines': b.get('lines') or [b['text']]}
            links = fix_links(b.get('links'), copier, page)
            if links:
                item['links'] = links
            flow.append(item)
        elif b['kind'] == 'image':
            src = b['src'].strip()
            if not src.startswith(UP):
                continue
            f = copier.copy(src, page)
            if f:
                item = {'kind': 'image', 'file': f}
                if b['href'].startswith('http'):
                    item['href'] = b['href']
                if b.get('title'):
                    item['caption'] = b['title']   # shown on the old site when the mouse was over the picture
                flow.append(item)
        elif b['kind'] == 'iframe' and 'youtube.com' in b['src']:
            flow.append({'kind': 'external', 'href': b['src'].replace('/embed/', '/watch?v='),
                         'text': 'Video of the meeting on YouTube'})
    return flow


def main():
    source = find_source()
    if not source:
        sys.exit('The Weebly archive was not found. Set CCBM_WEEBLY_ARCHIVE to the weebly_archive folder.')
    print('Reading', source)
    copier = Copier(source)
    report = []
    for series, years in (('club', CLUB_YEARS), ('opens', OPEN_YEARS)):
        os.makedirs(os.path.join(ROOT, 'data', series), exist_ok=True)
        for year in years:
            season = import_page(source, series, year, copier)
            with open(os.path.join(ROOT, 'data', series, '%d.json' % year), 'w', encoding='utf-8') as f:
                json.dump(season, f, indent=1, ensure_ascii=False)
                f.write('\n')
            nres = sum(len(t['results']) for t in season['tournaments'])
            report.append((series, year, season['results_form'], len(season['tournaments']), nres,
                           len(season['standings']), sum(len(s['rows']) for s in season['standings']),
                           len(season['pictures'])))
    rec = import_records(source)
    with open(os.path.join(ROOT, 'data', 'records_site.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write('\n')
    pages = {'copied': SOURCE_DATE}
    for key, page in (('gallery', 'member-gallery.html'), ('links', 'sponsors--links.html'),
                      ('upper_bay', 'upper-bay-tournament-directors.html')):
        pages[key] = import_plain(source, page, copier)
    # the links page: only the words and links at the foot of the old sponsors page
    pages['links'] = [x for x in pages['links'] if x['kind'] == 'text' and x.get('links')
                      and not re.match(r'(?i)^(servpro|\d{3}-)', x['lines'][0])]
    with open(os.path.join(ROOT, 'data', 'pages.json'), 'w', encoding='utf-8') as f:
        json.dump(pages, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print('\nseries year  form      tournaments  result rows  standings tables/rows  pictures')
    for r in report:
        print('%-6s %d  %-9s %6d %12d %10d / %-6d %8d' % r)
    print('\nPictures and PDFs copied into archive/: %d files, %.1f MB' % (
        len([v for v in copier.done.values() if v]), copier.bytes / 1e6))
    if copier.missing:
        print('Files the pages name that are in neither copy of the old site (%d):' % len(copier.missing))
        for m in copier.missing:
            print('  ' + m)
    with open(os.path.join(ROOT, 'data', 'import_report.txt'), 'w', encoding='utf-8') as f:
        f.write('Import of %s, run %s\n\n' % (SOURCE_DATE, datetime.date.today().isoformat()))
        f.write('series year  form      tournaments  result rows  standings tables/rows  pictures\n')
        for r in report:
            f.write('%-6s %d  %-9s %6d %12d %10d / %-6d %8d\n' % r)
        f.write('\nWarnings (%d):\n' % len(warnings))
        for w in warnings:
            f.write('  ' + w + '\n')
        f.write('\nFiles the pages name that are in neither copy of the old site (%d):\n' % len(copier.missing))
        for m in copier.missing:
            f.write('  ' + m + '\n')
    print('%d warnings; see data/import_report.txt' % len(warnings))


if __name__ == '__main__':
    main()
