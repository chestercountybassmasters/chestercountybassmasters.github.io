#!/usr/bin/env python3
"""Check the data and the built site. Exits with an error, loudly, if anything is wrong.

    python3 check.py                   everything this machine can check
    python3 check.py --require-source  fail if the old site's pages cannot be found
    python3 check.py --no-source       skip the comparison with the old site's pages

The old site's pages are in the club's Google Drive, not in this repository. On a
machine without them (GitHub's own, when it rebuilds the site) part 1 below cannot
compare with them: it says so in a line that starts "SKIPPED" and goes on. Every
other check still runs there.

1. Data against the source. For every season parsed from tables, the number of
   tournaments and the number of result rows in data/ must equal what the old
   site's page holds. The page is counted here with its own small reader, written
   separately from the importer, so that a slip in one shows against the other.
2. Links. Every link and picture address on every page in docs/ must lead to a
   file that exists, and every "#part" must exist on the page it points to.
3. Every page in docs/ can be reached from the home page, and every season from
   2004 on is linked from the results page.
4. House rules: no scripts, nothing loaded from another site except Google Fonts,
   a viewport line on every page, and the colour pairs in use have a contrast of
   at least 4.5 to 1.
5. Every address inside the site is relative ("photos/logo.jpg"), never one that
   starts with "/". GitHub Pages may serve the site under a sub-path
   (https://<organization>.github.io/<repository>/), and there an address that
   starts at the root of the host leads nowhere. The repository's name is not
   written into any page either, for the same reason.

Standard library only.
"""
import glob
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, 'docs')
errors = []
notes = []
skipped = []


def fail(msg):
    errors.append(msg)


# ------------------------------------------------------------------ 1. data against the source

MARK = re.compile(r'(?i)^(tournament report|team tournament results|ccbm tx\s*#\s*\d+|ccbm open results)$')
NAME = re.compile(r'(?i)^(participants?|anglers?|teams?)$')
HEADWORD = re.compile(r'(?i)^(#?\s*fish|weight|wgt\.?|b/f|penalty|pnlty\*?|lunkers?|place|total|points|pts\.?)$')
LABEL = re.compile(r'(?i)^(overall\s+|day\s*\d\s+)?(total|average|avg|teams|#|number|anglers?:)')


def find_source():
    env = os.environ.get('CCBM_WEEBLY_ARCHIVE')
    if env:
        return env
    hits = sorted(glob.glob(os.path.expanduser(
        '~/Library/CloudStorage/GoogleDrive-*/My Drive/CCBM/website/weebly_2026-11-20/weebly_archive')))
    hits = [h for h in hits if os.path.isfile(os.path.join(h, '2026-club-results.html'))]
    return hits[0] if hits else None


def source_tables(path):
    """Rows of every real table in the page's content area: [[[cell, ...], ...], ...].
    Weebly's column layouts (class wsite-multicol-table) are not tables of results."""
    with open(path, encoding='utf-8', errors='replace') as f:
        page = f.read()
    i = page.find('id="wsite-content"')
    body = page[i:]
    tables, stack, row, cell_start = [], [], None, None
    for m in re.finditer(r'<(/?)(table|tr|td|th)\b([^>]*)>', body, re.I):
        close, tag, rest = m.group(1), m.group(2).lower(), m.group(3)
        if tag == 'table':
            if not close:
                real = 'wsite-multicol-table' not in rest
                stack.append({'real': real, 'rows': []})
            elif stack:
                t = stack.pop()
                if t['real']:
                    tables.append(t['rows'])
        elif not stack or not stack[-1]['real']:
            continue
        elif tag == 'tr':
            if not close:
                row = []
            elif row is not None:
                stack[-1]['rows'].append(row)
                row = None
        else:
            if not close:
                cell_start = m.end()
            elif cell_start is not None and row is not None:
                text = re.sub(r'<[^>]+>', ' ', body[cell_start:m.start()])
                text = html.unescape(text).replace('​', '').replace('﻿', '').replace('\xa0', ' ')
                row.append(' '.join(text.split()))
                cell_start = None
    return tables


def count_source(path):
    """[(title, number of result rows), ...] for each tournament on the page, in order."""
    out = []
    for rows in source_tables(path):
        cur, name_col, in_body = None, None, False
        for r in rows:
            cells = [c for c in r if c]
            if len(cells) == 1 and MARK.match(cells[0]):
                if cur is None or in_body:
                    cur = ['', 0]
                    out.append(cur)
                    in_body, name_col = False, None
                continue
            if cur is None:
                continue
            if len(cells) == 1 and re.search(r'(?i)standings', cells[0]):
                cur = None
                continue
            if not in_body:
                if len(cells) == 1 and not cur[0]:
                    cur[0] = cells[0]
                hit = [k for k, c in enumerate(r) if NAME.match(c)]
                if hit and len(cells) >= 3:
                    name_col, in_body = hit[0], True
                continue
            if name_col >= len(r):
                continue
            name, first = r[name_col], r[0] if name_col > 0 else ''
            others = [c for k, c in enumerate(r) if c and k not in (0, name_col)]
            if not name or LABEL.match(name) or name.endswith(':') or LABEL.match(first) or first.endswith(':'):
                continue
            if HEADWORD.match(name) or NAME.match(name) or len(first) > 8:
                continue
            if not (others or first):
                continue
            cur[1] += 1
    return out


def check_source(use_source):
    files = sorted(glob.glob(os.path.join(ROOT, 'data', '*', '[0-9]*.json')))
    if not files:
        fail('data/ holds no season files')
        return
    source = find_source() if use_source else None
    if use_source and not source:
        if '--require-source' in sys.argv:
            fail('The old site\'s pages were not found, so data/ could not be compared with them. '
                 'Set CCBM_WEEBLY_ARCHIVE to the weebly_archive folder.')
            return
        skipped.append('SKIPPED: the comparison of data/ with the old site\'s pages. Those pages are in the '
                       'club\'s Google Drive and are not on this machine. The season files were still checked '
                       'against their own counts, and every other check ran.')
    checked = 0
    for f in files:
        with open(f, encoding='utf-8') as fh:
            d = json.load(fh)
        label = '%s %d' % (d['series'], d['year'])
        ids = [t['id'] for t in d['tournaments']]
        if len(ids) != len(set(ids)):
            fail('%s: two tournaments share an id' % label)
        flow_ids = [x['id'] for x in d['flow'] if x['kind'] == 'tournament']
        if sorted(flow_ids) != sorted(ids):
            fail('%s: the page order (flow) and the tournaments list do not hold the same tournaments' % label)
        for t in d['tournaments']:
            c = t['source_rows']
            if c['results'] != len(t['results']):
                fail('%s %s: %d result rows in the file, but its own count says %d' % (label, t['id'], len(t['results']), c['results']))
            if c['title'] + c['header'] + c['results'] + c['other'] + c['blank'] != c['table_rows']:
                fail('%s %s: the rows of the source table are not all accounted for (%s)' % (label, t['id'], c))
        a = d['source']['rows']
        if a['unassigned']:
            fail('%s: %d rows of the source page were not put anywhere' % (label, a['unassigned']))
        if a['table_rows'] != (a['tournament_rows'] + a['standings_rows'] + a['schedule_rows'] + a['summary_table_rows']
                               + a['file_table_rows'] + a['other_table_rows'] + a['blank_outside'] + a['unassigned']):
            fail('%s: the table rows of the source page are not all accounted for (%s)' % (label, a))
        if not source or 'page' not in d['source']:
            continue          # a season added as data later has no old page to compare with
        page = os.path.join(source, d['source']['page'])
        if not os.path.isfile(page):
            fail('%s: source page %s not found' % (label, d['source']['page']))
            continue
        with open(page, 'rb') as fh:
            if hashlib.sha256(fh.read()).hexdigest() != d['source']['sha256']:
                fail('%s: the source page has changed since it was imported' % label)
        src = count_source(page)
        real = sum(len(t) for t in source_tables(page))
        if real != a['table_rows']:
            fail('%s: the source page has %d table rows, the data accounts for %d' % (label, real, a['table_rows']))
        if not d['tournaments'] and not src:
            continue
        checked += 1
        if len(src) != len(d['tournaments']):
            fail('%s: %d tournaments on the source page, %d in data/' % (label, len(src), len(d['tournaments'])))
            continue
        for (title, n), t in zip(src, d['tournaments']):
            if n != len(t['results']):
                fail('%s, %s: %d result rows on the source page, %d in data/' % (label, title or t['id'], n, len(t['results'])))
        n_src, n_data = sum(n for _, n in src), sum(len(t['results']) for t in d['tournaments'])
        notes.append('%-10s %2d tournaments, %4d result rows: source and data agree' % (label, len(src), n_data)
                     if n_src == n_data else '%-10s DIFFERS' % label)
    if source:
        notes.append('%d seasons parsed from tables were compared with their source pages.' % checked)
    else:
        notes.append('%d season files checked against their own row counts.' % len(files))


# ------------------------------------------------------------------ 2 and 3. links

def check_links():
    pages = sorted(glob.glob(os.path.join(DOCS, '*.html')))
    if not pages:
        fail('docs/ holds no pages: run python3 build.py first')
        return
    # Only matters if docs/ is ever committed again and served straight from the branch: GitHub Pages
    # then runs Jekyll unless this file is there, and Jekyll drops files named _something.
    if not os.path.isfile(os.path.join(DOCS, '.nojekyll')):
        fail('docs/.nojekyll is missing: build.py should have written it')
    ids, links = {}, {}
    external = 0
    # every file in docs/, spelled exactly as it is on disk. A Mac finds "Photo.JPG" when asked for
    # "photo.jpg"; GitHub's servers do not, so a link must match the file name letter for letter.
    on_disk = set()
    for base, dirs, files_here in os.walk(DOCS):
        for f in files_here:
            on_disk.add(os.path.relpath(os.path.join(base, f), DOCS).replace(os.sep, '/'))
    for p in pages:
        name = os.path.basename(p)
        with open(p, encoding='utf-8') as f:
            text = f.read()
        ids[name] = set(re.findall(r'\bid="([^"]+)"', text))
        links[name] = []
        if '<script' in text.lower():
            fail('%s: holds a <script>; the site is to have none' % name)
        if 'name="viewport"' not in text:
            fail('%s: has no viewport line, so it will not fit a phone' % name)
        if re.search(r'\{\{[^}]*\}\}|<!--/?rows:', text):
            fail('%s: a template marker was left unfilled' % name)
        # 5. no address that starts at the root of the host, on any tag
        for attr, url in re.findall(r'\b(href|src|srcset|poster|action|data)\s*=\s*["\']([^"\']*)["\']', text, re.I):
            for part in (url.split(',') if attr.lower() == 'srcset' else [url]):
                part = html.unescape(part).strip()
                if part.startswith('/') and not part.startswith('//'):
                    fail('%s: the address %s starts with "/"; it must be relative, or it breaks when the site '
                         'is served under a sub-path' % (name, part))
        for url in re.findall(r'url\(\s*["\']?([^"\')]+)', text, re.I):
            if url.startswith('/') and not url.startswith('//'):
                fail('%s: the address %s in a style starts with "/"; it must be relative' % (name, url))
        for tag, attr, url in re.findall(r'<(a|img|link|source|iframe)\b[^>]*?\b(href|src)="([^"]*)"', text, re.I):
            url = html.unescape(url)
            if url.startswith('/') and not url.startswith('//'):
                continue          # already reported above
            if url.startswith('//'):
                url = 'https:' + url
            if re.match(r'^(mailto:|tel:)', url):
                continue
            if re.match(r'^https?://', url):
                external += 1
                if tag.lower() != 'a' and not re.match(r'^https://fonts\.(googleapis|gstatic)\.com', url):
                    fail('%s: loads %s from another site' % (name, url))
                continue
            if tag.lower() == 'iframe':
                fail('%s: holds a frame' % name)
            path, _, frag = url.partition('#')
            path = path.split('?')[0]
            target = name if path == '' else path
            if path and not os.path.isfile(os.path.join(DOCS, path)):
                fail('%s: link to %s, which does not exist' % (name, path))
                continue
            if path and os.path.normpath(path).replace(os.sep, '/') not in on_disk:
                fail('%s: link to %s, but the file\'s name is spelled with different capital letters; '
                     'that works on a Mac and fails on GitHub' % (name, path))
                continue
            links[name].append((target, frag))
    for name, ls in links.items():
        for target, frag in ls:
            if frag and target.endswith('.html') and frag not in ids.get(target, set()):
                fail('%s: link to %s#%s, but that page has no part with that name' % (name, target, frag))
    # reachable from the home page
    seen, todo = set(), ['index.html']
    while todo:
        n = todo.pop()
        if n in seen or n not in links:
            continue
        seen.add(n)
        todo += [t for t, _ in links[n] if t.endswith('.html')]
    for p in pages:
        if os.path.basename(p) not in seen:
            fail('%s cannot be reached from the home page' % os.path.basename(p))
    from_results = {t for t, _ in links.get('results.html', [])}
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '*', '[0-9]*.json'))):
        series, year = os.path.basename(os.path.dirname(f)), os.path.basename(f)[:-5]
        page = '%s-%s.html' % (series, year)
        if page not in from_results:
            fail('results.html has no link to %s' % page)
    # the stylesheets too
    for css in sorted(glob.glob(os.path.join(DOCS, '**', '*.css'), recursive=True)):
        with open(css, encoding='utf-8') as f:
            for url in re.findall(r'url\(\s*["\']?([^"\')]+)', f.read(), re.I):
                rel = os.path.relpath(css, DOCS)
                if url.startswith('/') and not url.startswith('//'):
                    fail('%s: the address %s starts with "/"; it must be relative' % (rel, url))
                elif not re.match(r'^(https?:)?//|^data:', url) and not os.path.isfile(
                        os.path.join(os.path.dirname(css), url.split('?')[0].split('#')[0])):
                    fail('%s: names %s, which does not exist' % (rel, url))
    notes.append('%d pages in docs/: every link and picture address leads somewhere (%d links go to other sites and were not followed).'
                 % (len(pages), external))
    notes.append('Every address inside the site is relative: none starts with "/".')


# ------------------------------------------------------------------ 4. colours

PAIRS = [  # (words, background, where)
    ('#13202E', '#F5F7FA', 'text on the page'), ('#13202E', '#FFFFFF', 'text on a card'),
    ('#4A5B6C', '#FFFFFF', 'small print on a card'), ('#4A5B6C', '#F5F7FA', 'small print on the page'),
    ('#1565A8', '#FFFFFF', 'link on a card'), ('#1565A8', '#F5F7FA', 'link on the page'),
    ('#FFFFFF', '#0C2340', 'header and footer'), ('#D5DEE8', '#0C2340', 'footer words'),
    ('#B7C6D6', '#0C2340', 'captions on navy'), ('#F5A524', '#0C2340', 'selected menu item'),
    ('#0C2340', '#F5A524', 'amber button'), ('#0C2340', '#FFFFFF', 'navy on white'),
    ('#13202E', '#FFF6E3', 'text on the cream note'), ('#4A5B6C', '#FFF6E3', 'small print on the cream note'),
    ('#7A4B00', '#FFE3A8', 'the "addition" tag'), ('#1565A8', '#FFF6E3', 'link on the cream note'),
]


def lum(hexcol):
    v = [int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    v = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def check_colours():
    worst = 99
    for fg, bg, where in PAIRS:
        a, b = sorted((lum(fg), lum(bg)), reverse=True)
        ratio = (a + 0.05) / (b + 0.05)
        worst = min(worst, ratio)
        if ratio < 4.5:
            fail('contrast of %s on %s (%s) is %.2f to 1; it must be at least 4.5' % (fg, bg, where, ratio))
    used = set()
    for p in glob.glob(os.path.join(DOCS, '*.html')) + glob.glob(os.path.join(DOCS, 'assets', '*.css')):
        with open(p, encoding='utf-8') as f:
            used |= {c.upper() for c in re.findall(r'(?<![\w&])color:\s*(#[0-9A-Fa-f]{6})', f.read())}
    known = {fg for fg, _, _ in PAIRS}
    for c in sorted(used - known):
        fail('a text colour is in use that the contrast check does not know: %s (add it to PAIRS in check.py)' % c)
    notes.append('Lowest contrast among the %d colour pairs in use: %.1f to 1.' % (len(PAIRS), worst))


def main():
    check_source('--no-source' not in sys.argv)
    check_links()
    check_colours()
    for n in notes:
        print(n)
    if '--no-source' in sys.argv:
        print('SKIPPED: the comparison of data/ with the old site\'s pages (--no-source).')
    for line in skipped:
        print(line)
    if errors:
        print('\n' + '!' * 70)
        print('CHECK FAILED: %d problem%s' % (len(errors), '' if len(errors) == 1 else 's'))
        for e in errors:
            print('  - ' + e)
        print('!' * 70)
        sys.exit(1)
    print('\nAll checks passed.')


if __name__ == '__main__':
    main()
