#!/usr/bin/env python3
"""Build the Chester County Bass Masters site into docs/.

    python3 build.py

Reads   templates/   the six front pages and the shared header and footer
        content/     the few plain files people change (sponsors, captions, meeting,
                     officers, schedule)
        data/        one results file for each season, and the old site's record lists
        photos/, archive/, files/, assets/
Writes  docs/               the finished site (the folder GitHub Pages serves)
        records_check.md    the records worked out from data/, against the old lists

Standard library only. Nothing is fetched from anywhere.
"""
import datetime
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import records  # noqa: E402

DOCS = os.path.join(ROOT, 'docs')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
          'October', 'November', 'December']
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
WATER_LONG = records.WATER_LONG
esc = html.escape
problems = []


def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def num(s):
    return records.num(s)


# ------------------------------------------------------------------ content/

def load_sponsors():
    out = []
    for line in read('content/sponsors.md').splitlines():
        if line.startswith('- '):
            parts = [p.strip() for p in line[2:].split('|')]
            out.append({'name': parts[0], 'link': parts[1] if len(parts) > 1 and parts[1] else ''})
    return out


def load_members():
    out = []
    for line in read('content/members.md').splitlines():
        if line.startswith('- '):
            p = [x.strip() for x in line[2:].split('|')]
            if p[0]:
                out.append({'photo': p[0], 'name': p[1] if len(p) > 1 else '', 'line': p[2] if len(p) > 2 else ''})
    return out


def load_slots():
    slots, cur = {}, None
    for line in read('content/photo-captions.md').splitlines():
        m = re.match(r'^##\s+(\S+)', line)
        if m:
            cur = slots.setdefault(m.group(1), {})
            continue
        m = re.match(r'^(photo|shows|caption):\s*(.*)$', line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip()
    return slots


def load_pairs(path):
    out = []
    for line in read(path).splitlines():
        m = re.match(r'^([A-Za-z][^:#]{0,60}):\s*(.+)$', line)
        if m and not line.startswith(' ') and len(m.group(1).split()) <= 7:
            out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def notice_html(section):
    """A season's "notice:" line as a tinted block; its first sentence is shown in bold."""
    text = section.get('notice', '')
    if not text:
        return ''
    head, sep, rest = text.partition('. ')
    head = head + ('.' if sep else '')
    return ('<span style="display: block; margin-top: 10px; padding: 10px 12px; background: #FFF6E3; '
            'border-radius: 8px; font-size: 15px; color: #13202E"><strong>%s</strong>%s</span>'
            % (esc(head), (' ' + esc(rest)) if rest else ''))


def load_schedule():
    """{'Club 2026': {'rows': [...], 'text': [...], 'short': '', 'notice': ''}, ...} in file order."""
    out, cur = {}, None
    for line in read('content/schedule.md').splitlines():
        m = re.match(r'^##\s+(.+?)\s*$', line)
        if m:
            cur = out.setdefault(m.group(1), {'rows': [], 'text': [], 'short': '', 'notice': ''})
            continue
        if cur is None or not line.strip() or line.startswith(' '):
            continue
        if line.startswith('short:'):
            cur['short'] = line[6:].strip()
        elif line.startswith('notice:'):
            cur['notice'] = line[7:].strip()
        elif '|' in line:
            p = [x.strip() for x in line.split('|')]
            water, note = p[1], ''
            m = re.match(r'^(.*?)\s*\((.+)\)\s*$', water)
            if m:
                water, note = m.group(1), m.group(2)
            cur['rows'].append({'date': p[0], 'water': water, 'small': note, 'ramp': p[2] if len(p) > 2 else '',
                                'status': p[3] if len(p) > 3 else ''})
        else:
            cur['text'].append(line.strip())
    return out


# ------------------------------------------------------------------ data/

def load_seasons():
    seasons = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '*', '[0-9]*.json'))):
        with open(f, encoding='utf-8') as fh:
            d = json.load(fh)
        seasons[(d['series'], d['year'])] = d
    return seasons


def season_file(series, year):
    return '%s-%d.html' % (series, year)


def long_date(iso, year=True):
    y, m, d = [int(x) for x in iso.split('-')]
    return '%s %d%s' % (MONTHS[m - 1], d, ', %d' % y if year else '')


def short_date(iso):
    y, m, d = [int(x) for x in iso.split('-')]
    return '%s %d' % (MON[m - 1], d)


def date_span(t, short=False, year=False):
    ds = t['dates']
    if not ds:
        return t.get('title', '')
    f = short_date if short else (lambda x: long_date(x, False))
    y = ', %s' % ds[0][:4] if year else ''
    if len(ds) == 2 and ds[0][:7] == ds[1][:7]:
        return '%s and %d%s' % (f(ds[0]), int(ds[1][8:]), y)
    if len(ds) == 2:
        return '%s and %s%s' % (f(ds[0]), f(ds[1]), y)
    return f(ds[0]) + y


def water_long(w):
    return WATER_LONG.get(w, w or '')


def waters_text(t, classic_prefix=False):
    ws = [w for w in t.get('waters', []) if w]
    if t.get('two_day'):
        if classic_prefix:
            return 'Classic: ' + ' and '.join(ws)
        return ' and '.join(water_long(w) for w in ws)
    return water_long(ws[0]) if ws else ''


def weight_of(t, r):
    roles = [c['role'] for c in t['columns']]
    return r.get('total_weight') if 'total_weight' in roles else r.get('weight', '')


def fish_of(t, r):
    return r.get('total_fish') if t.get('two_day') else r.get('fish', '')


def winner(t):
    for r in t['results']:
        if r.get('place', '').strip('.') == '1' and not r.get('guest'):
            return r
    return t['results'][0] if t['results'] else None


def stat(t, pattern, exclude=None):
    for p in t['summary']:
        if re.search(pattern, p['label'], re.I) and not (exclude and re.search(exclude, p['label'], re.I)):
            return p['value']
    return ''


def participants(t):
    v = stat(t, r'^(overall )?total (participants|anglers|teams)$|^teams fished$|^teams$|^# of teams$|^anglers$')
    return v if v else str(len(t['results']))


def total_fish(t):
    return stat(t, r'^(overall )?total fish weighed$|^number fish weighed$|^# fish weighed$|^# of fish$|^total #fish$')


def total_weight(t):
    return stat(t, r'^(overall )?total (fish )?weight$')


def big_fish(t):
    best = None
    for r in t['results']:
        for k in ('big_fish', 'd1_big_fish', 'd2_big_fish'):
            v = num(r.get(k))
            if v and (best is None or v > best[0]):
                best = (v, r['name'], r.get(k))
    return best


def team(name):
    return re.sub(r'\s*/\s*', ' / ', name)


def tournament_name(t, series):
    if t.get('two_day') or t.get('classic'):
        return 'Club Classic'
    return waters_text(t)


def rank(values):
    """1, 2, 3, 4, 5, 5, 7 for a list already in order."""
    out, last, place = [], None, 0
    for i, v in enumerate(values):
        if v != last:
            place, last = i + 1, v
        out.append(place)
    return out


def standings_cols(st):
    """Column numbers of the name, the total and the place in a standings table."""
    name = total = place = None
    for i, c in enumerate(st['columns']):
        low = c.lower()
        if place is None and 'place' in low:
            place = i
        if name is None and re.match(r'^(participant|angler|team)s?$', low):
            name = i
        if re.match(r'^total|^best 4$|^total-best', low):
            total = i
    return name, total, place


def find_standings(d, pattern):
    for st in d['standings']:
        if re.search(pattern, ' '.join(st['title_lines']), re.I):
            return st
    return d['standings'][0] if d['standings'] and pattern == '' else None


# ------------------------------------------------------------------ filling the design's rows

def get_block(page, name):
    m = re.search(r'<!--rows:%s-->(.*?)<!--/rows:%s-->' % (name, name), page, re.S)
    if not m:
        raise SystemExit('templates: rows block %r is missing' % name)
    return m.group(1)


def put_block(page, name, new):
    return re.sub(r'<!--rows:%s-->.*?<!--/rows:%s-->' % (name, name), lambda m: new.strip('\n'), page, flags=re.S)


def elements(block, tag):
    return re.findall(r'<%s\b[^>]*>.*?</%s>' % (tag, tag), block, re.S)


def fill(pattern, tag, values):
    """Copy one of the design's rows, putting new values into its cells.

    A value is text, or {'href': ..., 'text': ...} for a cell that holds a link, or
    {'spans': [...]} for a cell that holds several <span>s, or {'html': ...}."""
    it = iter(values)

    def cell(m):
        try:
            v = next(it)
        except StopIteration:
            return m.group(0)
        open_tag, inner, close = m.group(1), m.group(2), m.group(3)
        if isinstance(v, dict) and 'html' in v:
            return open_tag + v['html'] + close
        if isinstance(v, dict) and 'spans' in v:
            spans = iter(v['spans'])
            return open_tag + re.sub(r'(<span\b[^>]*>)(.*?)(</span>)',
                                     lambda s: s.group(1) + esc(next(spans, '')) + s.group(3), inner, flags=re.S) + close
        if isinstance(v, dict):
            a = re.search(r'<a\b[^>]*>', inner)
            a_open = re.sub(r'href="[^"]*"', 'href="%s"' % esc(v['href']), a.group(0)) if a else '<a href="%s">' % esc(v['href'])
            return open_tag + a_open + esc(v['text']) + '</a>' + close
        return open_tag + esc(v) + close
    return re.sub(r'(<%s\b[^>]*>)(.*?)(</%s>)' % (tag, tag), cell, pattern, flags=re.S)


def rows_from(block, rows, classic=None):
    """Rows for a <tbody>: the design's first row is the pattern for the first row, its
    second for the rest, and its tinted row (if it has one) for rows flagged classic."""
    pats = elements(block, 'tr')
    first, rest = pats[0], pats[1] if len(pats) > 1 else pats[0]
    tinted = [p for p in pats if 'background: #FFF6E3' in p]
    out = []
    for i, r in enumerate(rows):
        p = first if i == 0 else rest
        if classic and classic[i] and tinted:
            p = tinted[0]
        out.append(fill(p, 'td', r))
    return '\n' + '\n'.join(out) + '\n'


# ------------------------------------------------------------------ the site

class Site:
    def __init__(self):
        self.seasons = load_seasons()
        self.sponsors = load_sponsors()
        self.slots = load_slots()
        self.meeting = dict(load_pairs('content/meeting.md'))
        self.officers = load_pairs('content/officers.md')
        self.members = load_members()
        self.schedule = load_schedule()
        self.site_records = json.loads(read('data/records_site.json'))
        self.pages = json.loads(read('data/pages.json'))
        # the stylesheet's address carries a mark that changes when the file does, so a browser
        # never shows new pages with an old copy of the stylesheet
        import hashlib
        mark = hashlib.sha256(read('assets/site.css').encode('utf-8')).hexdigest()[:10]
        self.base = read('templates/base.html').replace('href="assets/site.css"', 'href="assets/site.css?v=%s"' % mark)
        if 'site.css?v=' not in self.base:
            problems.append('templates/base.html: the link to assets/site.css was not found')
        self.club_years = sorted(y for (s, y) in self.seasons if s == 'club')
        self.opens_years = sorted(y for (s, y) in self.seasons if s == 'opens')
        self.club = self.seasons[('club', max(y for y in self.club_years if self.seasons[('club', y)]['tournaments']))]
        self.opens = self.seasons[('opens', max(y for y in self.opens_years if self.seasons[('opens', y)]['standings']))]
        self.rec = records.run(self.seasons, self.site_records)
        self.used_archive = set()
        self.written = []

    # -- helpers
    def page(self, filename, title, body, nav=''):
        out = self.base.replace('{{title}}', esc(title)).replace('{{content}}', body)
        for key in ('results', 'schedule', 'opens', 'club'):
            out = out.replace('{{nav:%s}}' % key, ' aria-current="page"' if key == nav else '')
        left = re.findall(r'\{\{[^}]*\}\}|<!--/?rows:[^>]*-->', out)
        if left:
            problems.append('%s: markers left unfilled: %s' % (filename, sorted(set(left))[:6]))
        with open(os.path.join(DOCS, filename), 'w', encoding='utf-8') as f:
            f.write(out)
        self.written.append(filename)

    def template(self, name):
        text = read('templates/%s.html' % name)
        m = re.match(r'<!-- title: (.*?) -->\n', text)
        return (m.group(1) if m else 'Chester County Bass Masters'), text[m.end():] if m else text

    def common(self, body):
        """Markers that mean the same on every front page."""
        club, opens = self.club, self.opens
        latest = self.latest()
        body = body.replace('{{club_season_url}}', season_file('club', club['year']))
        body = body.replace('{{opens_season_url}}', season_file('opens', opens['year']))
        body = body.replace('{{latest_tournament_url}}', '%s#t-%s' % (season_file('club', club['year']), latest['id']))

        def photo(m):
            s = self.slots.get(m.group(1), {})
            if not s.get('photo') or not os.path.isfile(os.path.join(ROOT, 'photos', s['photo'])):
                problems.append('content/photo-captions.md: no picture for %s (%r)' % (m.group(1), s.get('photo')))
            return 'src="photos/%s" alt="%s"' % (esc(s.get('photo', '')), esc(s.get('shows', '')))
        body = re.sub(r'\{\{photo:([^}]+)\}\}', photo, body)
        body = re.sub(r'\{\{caption:([^}]+)\}\}', lambda m: esc(self.slots.get(m.group(1), {}).get('caption', '')), body)
        body = re.sub(r'<(figcaption|p)\b[^>]*></\1>\n?', '', body)     # an empty caption shows nothing
        mt = self.meeting
        when = mt.get('when', '')
        body = body.replace('{{meeting.sentence}}', esc('%s at %s.' % (when[:1].upper() + when[1:], mt.get('place', ''))))
        body = body.replace('{{meeting.when}}', esc(when))
        body = body.replace('{{meeting.where}}', esc('%s, %s. %s' % (mt.get('place', ''), mt.get('address', ''), mt.get('directions', ''))))
        body = body.replace('{{meeting.next}}', esc(mt.get('next', '')))
        # schedule words
        nxt_key, nxt = self.next_schedule('Club')
        body = body.replace('{{schedule.next_year}}', esc(nxt_key.split()[-1]))
        body = body.replace('{{schedule.year}}', esc(self.current_schedule()[0].split()[-1]))
        if '{{schedule.next}}' in body:
            body = body.replace('{{schedule.next}}', self.next_words(nxt, ' The dates and ramps are on the schedule page.'))
        okey, onext = self.next_schedule('Opens')
        onotice = notice_html(onext)
        body = body.replace('{{schedule.opens_next_year}}', esc(okey.split()[-1]))
        body = body.replace('{{schedule.opens_next}}', esc(' '.join(onext['text']) or ', '.join(r['date'] for r in onext['rows']))
                            + onotice)
        body = body.replace('{{schedule.opens_next_short}}', esc(onext['short'] or ' '.join(onext['text'])
                                                                 or ', '.join(r['date'] for r in onext['rows'])) + onotice)
        return body

    def next_words(self, nxt, where):
        """The sentence about next season's club dates, with the season's notice (if any) under it."""
        if nxt['rows']:
            # the two-day Classic is one tournament on two lines
            n = len([r for r in nxt['rows'] if not r['water'].lower().startswith('classic, day 2')])
            words = '%d tournaments, from %s to %s.%s' % (n, nxt['rows'][0]['date'], nxt['rows'][-1]['date'], where)
        else:
            words = ' '.join(nxt['text'])
        return esc(words) + notice_html(nxt)

    def next_schedule(self, kind):
        keys = [k for k in self.schedule if k.startswith(kind + ' ')]
        if not keys:
            raise SystemExit('content/schedule.md has no "## %s <year>" section' % kind)
        key = max(keys, key=lambda k: int(k.split()[-1]))
        return key, self.schedule[key]

    def current_schedule(self):
        keys = [k for k in self.schedule if k.startswith('Club ') and self.schedule[k]['rows']]
        if not keys:
            raise SystemExit('content/schedule.md has no club season with dates')
        with_results = [k for k in keys if int(k.split()[-1]) <= self.club['year']]
        key = max(with_results or keys, key=lambda k: int(k.split()[-1]))
        return key, self.schedule[key]

    def latest(self):
        ts = [t for t in self.club['tournaments'] if t['dates']]
        return max(ts, key=lambda t: t['dates'][-1])

    def champions(self):
        c = self.rec['site']['champions']
        year = self.club['year']
        st = find_standings(self.opens, 'standings')
        name_c, total_c, place_c = standings_cols(st)
        top = st['rows'][0][name_c]
        lasts = ' / '.join(p.strip().split(' ')[-1] for p in top.split('/'))
        return {'year': str(year), 'aoy': c['Angler of the Year'].get(year, '–'),
                'classic': c['Club Classic Winners'].get(year, '–'),
                'rider': c['Rider of the Year'].get(year, '–'), 'opens': lasts}

    def aoy_top(self, n):
        st = find_standings(self.club, 'aoy')
        name_c, total_c, place_c = standings_cols(st)
        rows = st['rows'][:n]
        places = rank([r[total_c] for r in st['rows']])[:n]
        return [[str(p), r[name_c], r[total_c]] for p, r in zip(places, rows)]

    def opens_top(self, n, scores=False):
        st = find_standings(self.opens, 'standings')
        name_c, total_c, place_c = standings_cols(st)
        out = []
        for r in st['rows'][:n]:
            row = [r[place_c], team(r[name_c]), r[total_c]]
            if scores:
                row += [(r[i] if r[i] != '' else '–') for i in range(len(r)) if i not in (name_c, total_c, place_c)]
            out.append(row)
        return out

    # -- front pages
    def home(self):
        title, body = self.template('home')
        body = self.common(body)
        t = self.latest()
        ch = self.champions()
        body = body.replace('{{latest.name}}', esc(tournament_name(t, 'club')))
        body = body.replace('{{latest.when_where}}', esc('%s · %s' % (date_span(t), waters_text(t))))
        rows = [[r.get('place', ''), r['name'], fish_of(t, r) or '', weight_of(t, r) or ''] for r in t['results'][:5]]
        body = put_block(body, 'latest_top5', rows_from(get_block(body, 'latest_top5'), rows))
        bf = big_fish(t)
        body = body.replace('{{latest.summary}}', esc('%s anglers, %s fish, %s pounds.%s' % (
            participants(t), total_fish(t), total_weight(t), ' Big fish: %s, %s.' % (bf[1], bf[2]) if bf else '')))
        body = put_block(body, 'aoy_top7', rows_from(get_block(body, 'aoy_top7'), self.aoy_top(7)))
        body = put_block(body, 'opens_top5', rows_from(get_block(body, 'opens_top5'), self.opens_top(5)))
        for k, v in ch.items():
            body = body.replace('{{champ.%s}}' % k, esc(v))
        # season chips
        blk = get_block(body, 'home_seasons')
        div_open = re.match(r'\s*(<div\b[^>]*>)', blk).group(1)
        anchors = elements(blk, 'a')
        cur, other, last = anchors[0], anchors[1], anchors[-1]
        chips = []
        for y in sorted([y for y in self.club_years if y >= 2013], reverse=True):
            a = cur if y == self.club['year'] else other
            a = re.sub(r'href="[^"]*"', 'href="%s"' % season_file('club', y), a)
            chips.append(re.sub(r'>[^<]*</a>', '>%d</a>' % y, a))
        chips.append(last)
        body = put_block(body, 'home_seasons', div_open + '\n' + '\n'.join(chips) + '\n</div>')
        # sponsors
        li = elements(get_block(body, 'sponsors'), 'li')[0]
        style = re.search(r'style="([^"]*)"', li).group(1)
        items = []
        for s in self.sponsors:
            if s['link']:
                st2 = re.sub(r'padding:[^;]*;?\s*', '', style)
                items.append('<li style="%s"><a href="%s" style="display: block; padding: 11px 14px; color: #13202E; '
                             'text-decoration: none">%s</a></li>' % (st2, esc(s['link']), esc(s['name'])))
            else:
                items.append('<li style="%s">%s</li>' % (style.replace('padding: 10px 14px', 'padding: 11px 14px'), esc(s['name'])))
        body = put_block(body, 'sponsors', '\n'.join(items) + '\n')
        self.page('index.html', title, body)

    def season_index_rows(self, d, link_classic=None):
        rows, classic = [], []
        f = season_file(d['series'], d['year'])
        for t in d['tournaments']:
            w = winner(t)
            href = '%s#t-%s' % (f, t['id'])
            if link_classic and t['id'] == link_classic:
                href = '#classic'
            rows.append([{'href': href, 'text': date_span(t, short=True)},
                         waters_text(t, classic_prefix=True), w['name'] if w else '',
                         (weight_of(t, w) or '') if w else '', participants(t)])
            classic.append(bool(t.get('two_day')))
        return rows, classic

    def results(self):
        title, body = self.template('results')
        body = self.common(body)
        d = self.club
        body = body.replace('{{season.year}}', str(d['year']))
        # season picker
        blk = get_block(body, 'club_picker')
        anchors = elements(blk, 'a')
        cur, other, last = anchors[0], anchors[1], anchors[-1]
        chips = [cur.replace('>%s<' % re.search(r'>([^<]*)</a>', cur).group(1), '>%d<' % d['year'])]
        for y in sorted([y for y in self.club_years if y < d['year']], reverse=True)[:6]:
            a = re.sub(r'href="[^"]*"', 'href="%s"' % season_file('club', y), other)
            chips.append(re.sub(r'>[^<]*</a>', '>%d</a>' % y, a))
        chips.append(last)
        body = put_block(body, 'club_picker', '\n'.join(chips) + '\n')
        # the featured tournament: the Classic if the season has one, else the latest
        classics = [t for t in d['tournaments'] if t.get('two_day')]
        feat = classics[-1] if classics else self.latest()
        rows, classic = self.season_index_rows(d, link_classic=feat['id'])
        body = put_block(body, 'season_index', rows_from(get_block(body, 'season_index'), rows, classic))
        body = body.replace('{{featured.title}}', esc('%s, %s' % (tournament_name(feat, 'club'), date_span(feat, year=True))))
        frows = [[r.get('place', ''), r['name'], fish_of(feat, r) or '', weight_of(feat, r) or ''] for r in feat['results']]
        body = put_block(body, 'featured_rows', rows_from(get_block(body, 'featured_rows'), frows))
        summ = '%s fish for %s pounds.' % (total_fish(feat), total_weight(feat))
        l1, l2 = stat(feat, r'^day ?1 lunker'), stat(feat, r'^day ?2 lunker')
        if l1 and l2:
            summ += ' Day 1 lunker: %s. Day 2 lunker: %s.' % (l1.replace(' - ', ', '), l2.replace(' - ', ', '))
        elif big_fish(feat):
            summ += ' Big fish: %s, %s.' % big_fish(feat)[1:]
        body = body.replace('{{featured.summary}}', esc(summ))
        body = put_block(body, 'aoy_top7', rows_from(get_block(body, 'aoy_top7'), self.aoy_top(7)))
        body += self.every_season()
        self.page('results.html', title, body, nav='results')

    def every_season(self):
        def chips(series, years):
            return '<div class="chips light">%s</div>' % ''.join(
                '<a href="%s">%d</a>' % (season_file(series, y), y) for y in sorted(years, reverse=True))
        return ('\n<section id="seasons" class="wrap" style="padding-top: 0">\n<article class="card">\n'
                '<h2>Every season</h2>\n<p class="sub">Club tournaments, %d to %d</p>\n%s\n'
                '<p class="sub" style="margin-top: 22px">Open team series, %d to %d</p>\n%s\n'
                '<p class="small" style="margin: 18px 0 0">From 2020 on, the club results are tables of text. '
                'Earlier seasons are pictures of the tables from the old site, shown as they are.</p>\n</article>\n</section>\n') % (
            self.club_years[0], self.club_years[-1], chips('club', self.club_years),
            self.opens_years[0], self.opens_years[-1], chips('opens', self.opens_years))

    def opens_page(self):
        title, body = self.template('opens')
        body = self.common(body)
        d = self.opens
        body = body.replace('{{opens.year}}', str(d['year']))
        blk = get_block(body, 'opens_picker')
        anchors = elements(blk, 'a')
        cur, other, last = anchors[0], anchors[1], anchors[-1]
        chips = [re.sub(r'href="[^"]*"', 'href="opens.html#standings"', re.sub(r'>[^<]*</a>', '>%d</a>' % d['year'], cur))]
        for y in sorted([y for y in self.opens_years if y < d['year']], reverse=True)[:2]:
            a = re.sub(r'href="[^"]*"', 'href="%s"' % season_file('opens', y), other)
            chips.append(re.sub(r'>[^<]*</a>', '>%d</a>' % y, a))
        chips.append(last)
        body = put_block(body, 'opens_picker', '\n'.join(chips) + '\n')
        body = put_block(body, 'opens_top10', rows_from(get_block(body, 'opens_top10'), self.opens_top(10, scores=True)))
        li = elements(get_block(body, 'opens_each'), 'li')[0]
        items = []
        # the points Opens first, newest first as the season file has them; then any cash-only Open
        for t in [x for x in d['tournaments'] if not x.get('cash_only')] + [x for x in d['tournaments'] if x.get('cash_only')]:
            w = winner(t)
            label = long_date(t['dates'][0], False) + (', cash Open' if t.get('cash_only') else '')
            a = re.search(r'<a\b[^>]*>', li).group(0)
            a = re.sub(r'href="[^"]*"', 'href="%s#t-%s"' % (season_file('opens', d['year']), t['id']), a)
            spans = re.findall(r'<span\b[^>]*>', li)
            items.append('%s%s%s</a>%s%s</span>%s%s</span></li>' % (
                re.match(r'<li\b[^>]*>', li).group(0), a, esc(label), spans[0],
                esc('%s, %s pounds' % (team(w['name']), weight_of(t, w))), spans[1], esc('%s teams' % participants(t))))
        body = put_block(body, 'opens_each', '\n'.join(items) + '\n')
        self.page('opens.html', title, body, nav='opens')

    def club_page(self):
        title, body = self.template('club')
        body = self.common(body)
        div = elements(get_block(body, 'officers'), 'div')[0]
        items = []
        for office, name in self.officers:
            x = re.sub(r'(<dt\b[^>]*>).*?(</dt>)', lambda m: m.group(1) + esc(office) + m.group(2), div, flags=re.S)
            x = re.sub(r'(<dd\b[^>]*>).*?(</dd>)', lambda m: m.group(1) + esc(name) + m.group(2), x, flags=re.S)
            items.append(x)
        body = put_block(body, 'officers', '\n'.join(items) + '\n')
        self.page('club.html', title, body, nav='club')

    def schedule_page(self):
        title, body = self.template('schedule')
        body = body.replace('{{schedule.next}}', self.next_words(self.next_schedule('Club')[1], ''))
        body = self.common(body)
        key, cur = self.current_schedule()
        year = int(key.split()[-1])
        d = self.seasons.get(('club', year))
        by_date = {}
        if d:
            for t in d['tournaments']:
                for iso in t['dates']:
                    by_date[short_date(iso)] = t['id']
        blk = get_block(body, 'schedule_rows')
        pats = elements(blk, 'tr')
        plain = pats[0]
        tinted = [p for p in pats if 'background: #FFF6E3' in p and 'rowspan' in p]
        tinted2 = [p for p in pats if 'background: #FFF6E3' in p and 'rowspan' not in p]
        small = re.search(r'<span\b[^>]*>', blk)
        small_open = small.group(0) if small else '<span>'
        out, rows = [], cur['rows']
        for i, r in enumerate(rows):
            tid = by_date.get(r['date'])
            water = {'html': esc(r['water']) + (small_open + esc(r['small']) + '</span>' if r['small'] else '')}
            if r['status']:
                result = r['status']
            elif tid:
                result = {'href': '%s#t-%s' % (season_file('club', year), tid), 'text': 'Result'}
            else:
                result = ''
            is_classic = r['water'].lower().startswith('classic')
            nxt_same = i + 1 < len(rows) and tid and by_date.get(rows[i + 1]['date']) == tid
            prev_same = i > 0 and tid and by_date.get(rows[i - 1]['date']) == tid
            if is_classic and prev_same and tinted2:
                out.append(fill(tinted2[0], 'td', [r['date'], water, r['ramp']]))
            elif is_classic and nxt_same and tinted:
                out.append(fill(tinted[0], 'td', [r['date'], water, r['ramp'], result]))
            elif is_classic and tinted:
                out.append(fill(tinted[0].replace(' rowspan="2"', ''), 'td', [r['date'], water, r['ramp'], result]))
            else:
                out.append(fill(plain, 'td', [r['date'], water, r['ramp'], result]))
        body = put_block(body, 'schedule_rows', '\n' + '\n'.join(out) + '\n')
        # next season, once its dates are in content/schedule.md
        nkey, nxt = self.next_schedule('Club')
        if nxt['rows'] and nkey != key:
            trs = '\n'.join(fill(plain, 'td', [r['date'], {'html': esc(r['water']) + (small_open + esc(r['small']) + '</span>' if r['small'] else '')},
                                               r['ramp'], r['status']]) for r in nxt['rows'])
            table = re.search(r'<div style="overflow-x: auto">\s*<table\b.*?</table>\s*</div>', body, re.S).group(0)
            table = re.sub(r'<tbody>.*?</tbody>', lambda m: '<tbody>\n' + trs + '\n</tbody>', table, flags=re.S)
            body = body.replace('</article>', table + '\n</article>', 1)
        self.page('schedule.html', title, body, nav='schedule')

    def records_page(self):
        title, body = self.template('records')
        body = self.common(body)
        site = self.rec['site']
        ch = site['champions']
        years = sorted(set(ch['Angler of the Year']) | set(ch['Club Classic Winners']), reverse=True)
        rows = []
        for y in years:
            first = {'href': season_file('club', y), 'text': str(y)} if ('club', y) in self.seasons else str(y)
            rows.append([first, ch['Angler of the Year'].get(y, '–'), ch['Club Classic Winners'].get(y, '–'),
                         ch['Rider of the Year'].get(y, '–'), ch['Rookie of the Year'].get(y, '–')])
        body = put_block(body, 'champions', rows_from(get_block(body, 'champions'), rows))
        newest = str(self.club['year'])

        def top_rows(entries):
            out = []
            for e in entries:
                where = '%s, %s' % (e['water'], e['date_text'])
                if e['date_text'].endswith('/' + newest):
                    where += ' · new this year'
                out.append(['%.2f' % e['weight'], {'spans': [e['name'].replace('(Guest)', '(guest)'), where]}])
            return out
        for name, key in (('top_bags', 'bags'), ('top_bass', 'bass'), ('top_rider_bags', 'rider')):
            blk = get_block(body, name)
            pat = elements(blk, 'tr')[0]
            body = put_block(body, name, '\n' + '\n'.join(fill(pat, 'td', r) for r in top_rows(site[key])) + '\n')
            body = self.additions_after(body, name, key)
        best = sorted(((entries[0], water) for water, entries in site['waters'].items()), key=lambda x: -x[0]['weight'])
        rows = [[{'href': '#water-%s' % slug(w), 'text': water_long(w)}, '%.2f' % e['weight'], e['name'], e['date_text']] for e, w in best]
        body = put_block(body, 'best_by_water', rows_from(get_block(body, 'best_by_water'), rows))
        body += self.water_lists(best)
        self.page('records.html', title, body, nav='results')

    def additions_for(self, key):
        for l in self.rec['lists']:
            if l['key'] == key:
                return l
        return None

    def additions_html(self, key):
        l = self.additions_for(key)
        if not l or not l['missing']:
            return ''
        rows = ''.join(
            '<tr class="added"><td class="num"><strong>%.2f</strong></td><td class="name">%s<br><span class="small">%s, %s · would be number %d</span></td></tr>'
            % (c['weight'], esc(c['name']), esc(c['water']), records.us_date(c['date']), c['rank']) for c in l['missing'])
        return ('<div class="note" style="margin: 14px 0 0"><p style="margin: 0 0 8px"><span class="tag">Addition found by the records check</span></p>'
                '<p style="margin: 0 0 8px">Not on the club\'s list. Found in the tournament results, and to be confirmed by the Tournament Director before it counts.</p>'
                '<div class="scroll"><table class="data">%s</table></div></div>') % rows

    def additions_after(self, body, block_name, key):
        add = self.additions_html(key)
        if not add:
            return body
        # put the note after the table that held this block
        i = body.index('</table>', body.index(get_marker_anchor(body, block_name)))
        return body[:i + 8] + '\n' + add + body[i + 8:]

    def water_lists(self, best):
        site = self.rec['site']
        cards = []
        for e, water in best:
            entries = site['waters'][water]
            rows = ''.join('<tr><td class="num"><strong>%.2f</strong></td><td class="name">%s</td><td>%s</td></tr>' % (
                x['weight'], esc(x['name'].replace('(Guest)', '(guest)')), esc(x['date_text'])) for x in entries)
            cards.append('<article class="card" id="water-%s" style="flex: 1 1 320px; margin: 0">\n<h2>%s</h2>\n'
                         '<p class="sub">Top ten bags</p>\n<div class="scroll"><table class="data">'
                         '<thead><tr><th class="num">Pounds</th><th>Angler</th><th>Date</th></tr></thead><tbody>%s</tbody></table></div>\n%s\n</article>'
                         % (slug(water), esc(water_long(water)), rows, self.additions_html('water:' + water)))
        note = ('<p class="small" style="max-width: 820px; margin: 16px 0 0">These lists are the club\'s own, as they stood on the old site on '
                'November 20, 2026. A check of the 2020 to 2026 results against them is in the site\'s records check; '
                'anything it found is marked as an addition and is not a record until confirmed. Seasons before 2020 '
                'have not been checked.</p>')
        return ('\n<section style="max-width: 1180px; margin: 0 auto; padding: 0 24px 56px">\n'
                '<h2 style="margin: 0 0 16px; font-family: \'Barlow Condensed\', Inter, sans-serif; font-weight: 700; '
                'font-size: 34px; line-height: 1.05; text-transform: uppercase">Top ten on each water</h2>\n'
                '<div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start">\n%s\n</div>\n%s\n</section>\n') % ('\n'.join(cards), note)

    # -- season pages
    def band(self, series, year, form_note):
        tabs = [('results.html', 'Club tournaments', series == 'club'), ('opens.html', 'Open team series', series == 'opens'),
                ('records.html', 'Records and champions', False)]
        years = self.club_years if series == 'club' else self.opens_years
        pick = ''.join('<a href="%s"%s>%d</a>' % (season_file(series, y), ' aria-current="true"' if y == year else '', y)
                       for y in sorted(years, reverse=True))
        what = 'club tournaments' if series == 'club' else 'Open team series'
        return ('<section class="band"><div class="band-in">\n<p class="eyebrow">Results and standings</p>\n'
                '<h1>%d %s</h1>\n<div class="tabs">%s</div>\n<div class="picker"><span>Season</span>%s</div>\n</div></section>\n') % (
            year, esc(what), ''.join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if c else '', t) for h, t, c in tabs), pick)

    def tournament_card(self, d, t):
        series = d['series']
        who = 'Team' if series == 'opens' else 'Angler'
        roles = [c['role'] for c in t['columns']]
        has_extra = any(r.get('extra') for r in t['results'])
        label = {'place': 'Place', 'name': who, 'fish': 'Fish', 'weight': 'Pounds', 'big_fish': 'Big fish',
                 'penalty': 'Penalty', 'total_weight': 'Total', 'points': 'Points', 'total_fish': 'Fish'}
        if 'weight' not in roles and not t.get('two_day'):
            label['total_weight'] = 'Pounds'
        numeric = lambda role: role not in ('name',)  # noqa: E731
        if t.get('two_day'):
            d1 = [r for r in roles if r.startswith('d1_')]
            d2 = [r for r in roles if r.startswith('d2_')]
            lead = [r for r in roles if r in ('place', 'name')]
            tail = [r for r in roles if r in ('total_fish', 'total_weight', 'points')]
            ws = t.get('waters') or ['', '']
            h1 = ''.join('<th rowspan="2"%s>%s</th>' % ('' if r == 'name' else ' class="num"', label[r]) for r in lead)
            h1 += '<th class="grp" colspan="%d">Day 1 · %s</th><th class="grp" colspan="%d">Day 2 · %s</th>' % (
                len(d1), esc(water_long(ws[0])), len(d2), esc(water_long(ws[1] if len(ws) > 1 else '')))
            h1 += ''.join('<th rowspan="2" class="num">%s</th>' % {'total_fish': 'Total fish', 'total_weight': 'Total pounds',
                                                                'points': 'Points'}[r] for r in tail)
            h2 = ''.join('<th class="num">%s</th>' % label[r[3:]] for r in d1 + d2)
            head = '<tr>%s%s</tr><tr>%s</tr>' % (h1, '<th rowspan="2">Note</th>' if has_extra else '', h2)
            order = lead + d1 + d2 + tail
        else:
            order = roles
            head = '<tr>%s%s</tr>' % (''.join('<th%s>%s</th>' % (' class="num"' if numeric(r) else '', label.get(r, r)) for r in order),
                                      '<th>Note</th>' if has_extra else '')
        body = []
        for i, r in enumerate(t['results']):
            tds = []
            for role in order:
                v = r.get(role, '')
                if role == 'name':
                    v = team(v) if series == 'opens' else v
                    tds.append('<td class="name">%s</td>' % esc(v))
                else:
                    tds.append('<td class="num">%s</td>' % esc(v))
            if has_extra:
                tds.append('<td class="small">%s</td>' % esc('; '.join(r.get('extra', []))))
            body.append('<tr%s>%s</tr>' % (' class="first"' if i == 0 else '', ''.join(tds)))
        summary = ''.join('<li><strong>%s:</strong> %s</li>' % (esc(p['label']), esc(p['value'])) for p in t['summary'])
        notes = ''.join('<p class="notes">%s</p>' % esc(n) for n in t['notes'])
        if t.get('added', {}).get('shown'):
            notes += '<p class="notes">%s</p>' % esc(t['added']['shown'])
        name = ('Club Classic' if series == 'club' else 'Open') if (t.get('two_day') or t.get('classic')) else waters_text(t)
        if series == 'opens':
            name = 'Cash Open' if t.get('cash_only') else 'Open'
        sub = waters_text(t) if (series == 'opens' or t.get('two_day')) else ''
        return ('<article class="card" id="t-%s">\n<p class="eyebrow">%s</p>\n<h2>%s</h2>\n%s'
                '<div class="scroll"><table class="data"><thead>%s</thead><tbody>\n%s\n</tbody></table></div>\n%s%s\n</article>\n') % (
            t['id'], esc(date_span(t, year=True)), esc(name), '<p class="sub">%s</p>\n' % esc(sub) if sub else '',
            head, '\n'.join(body), '<ul class="summary">%s</ul>' % summary if summary else '', notes)

    def standings_card(self, d, st, first):
        cols = st['columns']
        numeric = [all(re.fullmatch(r'[\d.,]*\*?|–', r[i]) for r in st['rows']) for i in range(len(cols))]
        head = ''.join('<th%s>%s</th>' % (' class="num"' if numeric[i] else '', esc(c)) for i, c in enumerate(cols))
        rows = []
        for r in st['rows']:
            rows.append('<tr>%s</tr>' % ''.join(
                '<td class="%s">%s</td>' % ('num' if numeric[i] else 'name', esc(team(v) if d['series'] == 'opens' and not numeric[i] else v))
                for i, v in enumerate(r)))
        title = st['title_lines'][0] if st['title_lines'] else 'Standings'
        sub = ' '.join(st['title_lines'][1:])
        notes = ''.join('<p class="notes">%s</p>' % esc(n) for n in st['notes'])
        return ('<article class="card"%s>\n<h2>%s</h2>\n%s<div class="scroll"><table class="data"><thead><tr>%s</tr></thead><tbody>\n%s\n</tbody></table></div>\n%s</article>\n') % (
            ' id="standings"' if first else '', esc(title.title() if title.isupper() else title),
            '<p class="sub">%s</p>\n' % esc(sub.capitalize() if sub.isupper() else sub) if sub else '', head, '\n'.join(rows), notes)

    def link_html(self, l):
        if 'season' in l:
            series, year = l['season']
            if (series, year) in self.seasons:
                return season_file(series, year)
            return None
        if 'file' in l:
            self.used_archive.add(l['file'])
            return l['file']
        return l.get('href')

    def text_html(self, item, tag='p'):
        lines = [esc(x) for x in item['lines']]
        text = '<br>'.join(lines)
        extra = []
        for l in item.get('links', []):
            href = self.link_html(l)
            if not href:
                continue
            label = l['text']
            if label.strip().lower() == 'download file' and 'file' in l:
                label = 'Download %s' % os.path.basename(l['file'])
                text = text.replace('Download File', '', 1)
            a = '<a href="%s">%s</a>' % (esc(href), esc(label))
            if esc(l['text']) in text and text.count(esc(l['text'])) == 1 and label == l['text']:
                text = text.replace(esc(l['text']), a)
            else:
                extra.append(a)
        if extra:
            text = (text + ' ' if text.strip() else '') + ' · '.join(extra)
        return '<%s>%s</%s>' % (tag, text, tag)

    def flow_html(self, d, alt_base):
        """Everything on the old page, in its order: words, pictures, result tables."""
        flow = d['flow']
        has_words = any(x['kind'] == 'text' and len(' '.join(x['lines'])) > 80 for x in flow)
        by_id = {t['id']: t for t in d['tournaments']}
        out, i, npic, first_st = [], 0, 0, True
        total_pics = sum(1 for x in flow if x['kind'] == 'image')
        while i < len(flow):
            x = flow[i]
            k = x['kind']
            if k == 'image':
                run = []
                while i < len(flow) and flow[i]['kind'] == 'image':
                    run.append(flow[i])
                    i += 1
                imgs = []
                for im in run:
                    npic += 1
                    self.used_archive.add(im['file'])
                    full = im.get('full') or im['file']
                    self.used_archive.add(full)
                    imgs.append('<a href="%s"><img src="%s" alt="%s" loading="lazy"></a>' % (
                        esc(full), esc(im['file']), esc('%s, picture %d of %d' % (alt_base, npic, total_pics))))
                if len(run) >= 2 and has_words:
                    out.append('<div class="pics">%s</div>' % ''.join(imgs))
                else:
                    out.extend('<p class="pic">%s</p>' % im for im in imgs)
                continue
            if k == 'heading':
                out.append(self.text_html(x, 'h3'))
            elif k == 'text':
                out.append(self.text_html(x))
            elif k == 'rule':
                out.append('<hr class="sep">')
            elif k == 'external':
                out.append('<p><a href="%s">%s</a></p>' % (esc(x['href']), esc(x['text'])))
            elif k == 'tournament':
                out.append('</div>' + self.tournament_card(d, by_id[x['id']]) + '<div class="writeup">')
            elif k == 'standings':
                out.append('</div>' + self.standings_card(d, d['standings'][x['index']], first_st) + '<div class="writeup">')
                first_st = False
            elif k == 'schedule':
                lines = d['schedule']
                out.append('</div><article class="card"><h2>%s</h2><p class="sub" style="margin: 0">%s</p></article><div class="writeup">' % (
                    esc(lines[0]), '<br>'.join(esc(l) for l in lines[1:])))
            elif k == 'table':
                rows = ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % esc(c) for c in r) for r in x['rows'])
                out.append('</div><div class="card"><div class="scroll"><table class="data">%s</table></div></div><div class="writeup">' % rows)
            elif k == 'missing_image':
                out.append('<p class="small">[A picture that was on the old page is not in the copy of the site.]</p>')
            i += 1
        html_out = '<div class="writeup">' + '\n'.join(out) + '</div>'
        return re.sub(r'<div class="writeup">\s*</div>', '', html_out)

    def season_page(self, d):
        series, year = d['series'], d['year']
        what = 'club tournaments' if series == 'club' else 'Open team series'
        body = [self.band(series, year, '')]
        body.append('<section class="wrap">')
        form = d['results_form']
        if d.get('note'):
            body.append('<p class="note">%s</p>' % esc(d['note']))
        elif form == 'pictures':
            body.append('<p class="note">The results of this season are pictures of the tables on the old club site. '
                        'They are shown as they are, in the order of the old page; pick a picture to open it full size.</p>')
        if d['tournaments']:
            rows, _ = self.season_index_rows(d)
            trs = ''.join('<tr><td><a href="%s">%s</a></td><td>%s</td><td class="name">%s</td><td class="num">%s</td><td class="num">%s</td></tr>' % (
                esc(r[0]['href']), esc(r[0]['text']), esc(r[1]), esc(team(r[2]) if series == 'opens' else r[2]), esc(r[3]), esc(r[4])) for r in rows)
            links = ''
            if d['standings']:
                links = '<p style="margin: 14px 0 0"><a href="#standings" style="display: inline-flex; align-items: center; min-height: 44px; font-weight: 600">Season standings</a></p>'
            body.append('<article class="card">\n<h2>%d %s</h2>\n<p class="sub">%d tournaments with results. Pick a date for the full result.</p>\n'
                        '<div class="scroll"><table class="data"><thead><tr><th>Date</th><th>Water</th><th>Winner</th>'
                        '<th class="num">Pounds</th><th class="num">%s</th></tr></thead><tbody>%s</tbody></table></div>%s\n</article>'
                        % (year, esc(what), len(d['tournaments']), 'Teams' if series == 'opens' else 'Anglers', trs, links))
        body.append(self.flow_html(d, '%d %s, from the old club site' % (year, what)))
        body.append('<p class="small" style="margin-top: 28px">Taken from the old club site as it stood on November 20, 2026 (%s).</p>' % esc(d['source']['page']))
        body.append('</section>')
        title = 'Chester County Bass Masters: %d %s' % (year, what)
        self.page(season_file(series, year), title, '\n'.join(body), nav='results' if series == 'club' else 'opens')

    # -- the three plain pages
    def plain_band(self, eyebrow, h1, lead=''):
        return '<section class="band"><div class="band-in">\n<p class="eyebrow">%s</p>\n<h1>%s</h1>\n%s</div></section>\n' % (
            esc(eyebrow), esc(h1), '<p>%s</p>\n' % lead if lead else '')

    def gallery(self):
        imgs = []
        for m in self.members:
            if os.path.isfile(os.path.join(ROOT, 'photos', m['photo'])):
                src = 'photos/' + m['photo']
            else:
                src = 'archive/' + m['photo']
                self.used_archive.add(src)
            imgs.append('<figure class="member"><img src="%s" alt="%s" loading="lazy">'
                        '<figcaption><strong>%s</strong>%s</figcaption></figure>' % (
                            esc(src), esc(m['name'] or 'Club member'), esc(m['name']),
                            '<span>%s</span>' % esc(m['line']) if m['line'] else ''))
        body = self.plain_band('The club', 'Member gallery',
                               'Our members, their boats, and their names on the message board.') + \
            '<section class="wrap"><div class="gallery">%s</div>\n<p style="margin-top: 24px">More photos are on ' \
            '<a href="https://www.facebook.com/Chester-County-Bass-Masters-185365004836120/">the club Facebook page</a>.</p></section>' % '\n'.join(imgs)
        self.page('gallery.html', 'Chester County Bass Masters: member gallery', body, nav='club')

    def links_page(self):
        groups, cur = [], None
        for item in self.pages['links']:
            by_text = {l['text']: l for l in item.get('links', [])}
            for line in item['lines']:
                if line in by_text:
                    if cur is None:
                        cur = ['Links', []]
                        groups.append(cur)
                    cur[1].append(by_text[line])
                else:
                    cur = [line, []]
                    groups.append(cur)
        cards = []
        for title, links in groups:
            if not links:
                continue
            cards.append('<article class="card" style="flex: 1 1 300px; margin: 0"><h2>%s</h2><div class="linklist">%s</div></article>' % (
                esc(title.replace('Favorite Bass Fishing Resources/Links', 'Bass fishing resources').replace('CCBM Affiliations', 'Our affiliations')),
                ''.join('<a href="%s">%s</a>' % (esc(self.link_html(l)), esc(l['text'])) for l in links)))
        body = self.plain_band('More', 'Bass fishing links') + \
            '<section class="wrap"><div class="cols">%s</div></section>' % '\n'.join(cards)
        self.page('links.html', 'Chester County Bass Masters: bass fishing links', body)

    def upper_bay(self):
        flow = self.pages['upper_bay']
        out = []
        for x in flow[1:]:
            if x['kind'] == 'text':
                txt = ' '.join(x['lines'])
                if re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December) \d', txt):
                    out.append('<hr class="sep">')
                out.append(self.text_html(x))
            elif x['kind'] == 'external':
                out.append('<p><a href="%s">%s</a></p>' % (esc(x['href']), esc(x['text'])))
        lead = esc(' '.join(flow[0]['lines'])) if flow and flow[0]['kind'] == 'text' else ''
        body = self.plain_band('More', 'Upper Bay tournament directors', lead) + \
            '<section class="wrap"><article class="card writeup">%s</article></section>' % '\n'.join(out).replace('<hr class="sep">', '', 1)
        self.page('upper-bay-tournament-directors.html', 'Chester County Bass Masters: Upper Bay tournament directors', body)

    # -- files
    def copy_tree(self, name):
        src, dst = os.path.join(ROOT, name), os.path.join(DOCS, name)
        for base, dirs, files in os.walk(src):
            for f in files:
                if f.startswith('.'):
                    continue
                s = os.path.join(base, f)
                t = os.path.join(dst, os.path.relpath(s, src))
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.copyfile(s, t)

    def copy_archive(self):
        n = 0
        for rel in sorted(self.used_archive):
            s, t = os.path.join(ROOT, rel), os.path.join(DOCS, rel)
            if not os.path.isfile(s):
                problems.append('archive file named in data/ is missing: %s' % rel)
                continue
            os.makedirs(os.path.dirname(t), exist_ok=True)
            shutil.copyfile(s, t)
            n += 1
        return n

    def build(self):
        if os.path.isdir(DOCS):
            shutil.rmtree(DOCS)
        os.makedirs(DOCS)
        open(os.path.join(DOCS, '.nojekyll'), 'w').close()   # so GitHub Pages serves files whose names start with _
        self.home()
        self.results()
        self.opens_page()
        self.club_page()
        self.records_page()
        self.schedule_page()
        for key in sorted(self.seasons):
            self.season_page(self.seasons[key])
        self.gallery()
        self.links_page()
        self.upper_bay()
        for name in ('assets', 'photos', 'files'):
            self.copy_tree(name)
        n = self.copy_archive()
        records.write_report(os.path.join(ROOT, 'records_check.md'), self.rec, datetime.date.today().isoformat())
        return n


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def get_marker_anchor(body, block_name):
    """A string that sits where a filled rows block was: the first row of that block."""
    # after filling, the marker comments are gone; find the table by its heading instead
    heading = {'top_bags': '>Top ten bags</h2>', 'top_bass': '>Top ten bass</h2>', 'top_rider_bags': '>Top ten rider bags</h2>'}[block_name]
    return heading


def main():
    site = Site()
    n = site.build()
    print('Built %d pages into docs/ (%d club seasons, %d Opens seasons), %d pictures and files from archive/.' % (
        len(site.written), len(site.club_years), len(site.opens_years), n))
    missing = sum(len(l['missing']) for l in site.rec['lists'])
    print('records_check.md written: %d missing %s found.' % (missing, 'entry' if missing == 1 else 'entries'))
    if problems:
        print('\nPROBLEMS (%d):' % len(problems))
        for p in problems:
            print('  ' + p)
        sys.exit(1)


if __name__ == '__main__':
    main()
