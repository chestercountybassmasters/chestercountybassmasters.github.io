#!/usr/bin/env python3
"""Turn the six design pages of 20 November 2026 into the templates in templates/.

This was run once, to start the site from the design. The templates are now the
thing to edit; running this again would overwrite any hand edits made to them
since, so it refuses unless --force is given.

    python3 -I tools/convert_design.py --force

What it does to each design page:
  - keeps only the part between the header and the footer (those are in base.html);
  - swaps each /_blob/... picture address for a {{photo:slot}} marker;
  - points every link at a real page;
  - wraps the parts that the build fills from data/ and content/ in
    <!--rows:name--> ... <!--/rows:name--> comments (the rows left inside are the
    design's own, and the build uses them as the pattern for the rows it writes);
  - swaps the words that live in content/ for {{markers}}.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'templates')

PAGES = {'Main': 'home', 'Results': 'results', 'Opens': 'opens', 'Club': 'club',
         'Records': 'records', 'Schedule': 'schedule'}

SLOTS = {
    'home': ['home-top', 'home-opens-1', 'home-opens-2', 'home-opens-3',
             'home-club-1', 'home-club-2', 'home-club-3'],
    'opens': ['opens-top', 'opens-strip-1', 'opens-strip-2', 'opens-strip-3'],
    'club': ['club-top', 'club-members-1', 'club-members-2', 'club-members-3'],
}

# link text -> where it goes (checked before the page-to-page map below)
BY_TEXT = {
    'Full result': '{{latest_tournament_url}}',
    'Full standings': '{{club_season_url}}#standings',
    'Open results': '{{opens_season_url}}',
    '2026 Open results': '{{opens_season_url}}',
    'Tournament rules (PDF)': 'files/club-tournament-rules.pdf',
    'Club tournament rules (PDF)': 'files/club-tournament-rules.pdf',
    'Maryland Bass Nation tournaments': 'https://mdbassnation.com/tournaments/',
    'Member gallery': 'gallery.html',
    'Upper Bay tournament directors': 'upper-bay-tournament-directors.html',
    'Upper Bay tournament directors: meetings and notes': 'upper-bay-tournament-directors.html',
    'Bass fishing links': 'links.html',
    'Old club pictures': 'http://www.chestercountybassmasters.com/coppermine/index.php',
    'kept here': 'http://www.chestercountybassmasters.com/coppermine/index.php',
    'Maryland B.A.S.S. Nation': 'http://www.mdbass.com/',
    'Every angler, tournament by tournament': '{{club_season_url}}#standings',
    'All teams': '{{opens_season_url}}#standings',
    'Maryland DNR tournament requirements (PDF)': 'files/maryland-dnr-tournament-requirements-2026.pdf',
    'Mail-in entry form (PDF)': 'files/ccbm-open-entry-form-mail-in.pdf',
    'Earlier, back to 2004': 'results.html#seasons',
    'Earlier, back to 2013': 'results.html#seasons',
    '2004 to 2012': 'results.html#seasons',
    'Join us': 'club.html#join',
    'Mission and officers': 'club.html',
    'Where we meet': 'club.html#join',
}
BY_PAGE = {'Main.dc.html': 'index.html', 'Results.dc.html': 'results.html', 'Opens.dc.html': 'opens.html',
           'Club.dc.html': 'club.html', 'Records.dc.html': 'records.html', 'Schedule.dc.html': 'schedule.html'}


def find_design():
    env = os.environ.get('CCBM_DESIGN_PAGES')
    if env:
        return env
    hits = sorted(glob.glob(os.path.expanduser(
        '~/Library/CloudStorage/GoogleDrive-*/My Drive/CCBM/website/design_2026-11-20/pages')))
    hits = [h for h in hits if os.path.isfile(os.path.join(h, 'Main.dc.html'))]
    return hits[0] if hits else None


def links(html):
    def fix(m):
        href, rest, text = m.group(1), m.group(2), m.group(3)
        plain = re.sub(r'<[^>]+>', '', text).strip()
        if plain in BY_TEXT:
            href = BY_TEXT[plain]
        elif href in BY_PAGE:
            href = BY_PAGE[href]
        return '<a href="%s"%s>%s</a>' % (href, rest, text)
    return re.sub(r'<a href="([^"]*)"([^>]*)>(.*?)</a>', fix, html, flags=re.S)


def mark_tbody(html, n, name):
    """Wrap the rows of the n-th <tbody> (counting from 1) in rows markers."""
    k = [0]

    def fix(m):
        k[0] += 1
        if k[0] != n:
            return m.group(0)
        return '<tbody>\n<!--rows:%s-->%s<!--/rows:%s-->\n</tbody>' % (name, m.group(1), name)
    out = re.sub(r'<tbody>(.*?)</tbody>', fix, html, flags=re.S)
    assert k[0] >= n, 'no tbody %d for %s' % (n, name)
    return out


def mark_run(html, pattern, name):
    """Wrap the first run of text matching pattern in rows markers."""
    m = re.search(pattern, html, flags=re.S)
    assert m, 'pattern for %s not found' % name
    return html[:m.start()] + '<!--rows:%s-->\n%s\n<!--/rows:%s-->' % (name, m.group(0).strip('\n'), name) + html[m.end():]


def swap(html, old, new, count=1):
    assert html.count(old) >= count, 'text not found (%d of %d): %r' % (html.count(old), count, old[:70])
    return html.replace(old, new) if count == 0 else html.replace(old, new, count)


def photos(html, name):
    slots = list(SLOTS.get(name, []))

    def fix(m):
        assert slots, 'more pictures than slots on ' + name
        return '{{photo:%s}}' % slots.pop(0)
    html = re.sub(r'src="/_blob/[0-9a-f]+" alt="[^"]*"', fix, html)
    assert not slots, 'slots left over on %s: %s' % (name, slots)
    assert '/_blob/' not in html
    return html


A_RUN = r'(?:<a [^>]*>[^<]*</a>\s*)+'


def convert(name, html):
    a = html.index('</header>') + len('</header>')
    b = html.index('<footer')
    body = html[a:b].strip('\n')
    body = photos(body, name)
    body = links(body)
    if name == 'home':
        body = swap(body, '>[Caption: which tournament, and who]<', '>{{caption:home-top}}<')
        body = swap(body, '>Club Classic</h3>', '>{{latest.name}}</h3>')
        body = swap(body, '>November 7 and 8 · Nanticoke River and North East River</p>', '>{{latest.when_where}}</p>')
        body = mark_tbody(body, 1, 'latest_top5')
        body = swap(body, '>20 anglers, 114 fish, 218.14 pounds. Big fish: Steve Manista, 3.62.</p>', '>{{latest.summary}}</p>')
        body = mark_tbody(body, 2, 'aoy_top7')
        body = swap(body, '>Rider of the Year: Sean Clark.</p>', '>Rider of the Year: {{champ.rider}}.</p>')
        body = mark_tbody(body, 3, 'opens_top5')
        body = swap(body, '>[2027 dates and ramps: to be posted when the club sets them]</p>', '>{{schedule.next}}</p>')
        body = swap(body, '>Usually the third Thursday of each month at Garnet Valley Pizza. We are',
                    '>{{meeting.sentence}} We are')
        body = swap(body, '>[Captions: which Open, and who]</p>', '>{{caption:home-opens}}</p>')
        body = swap(body, '<strong>2027 dates:</strong> [to be posted]', '<strong>{{schedule.opens_next_year}} dates:</strong> {{schedule.opens_next_short}}')
        body = swap(body, '>The club at the Nanticoke, April 2023. [Other captions to come]</p>', '>{{caption:home-club}}</p>')
        for label, key in (('Angler of the Year', 'aoy'), ('Classic winner', 'classic'),
                           ('Rider of the Year', 'rider'), ('Open champions', 'opens')):
            body, n = re.subn(r'(>)2026 %s(</span><span [^>]*>)[^<]*(</span>)' % re.escape(label),
                              r'\g<1>{{champ.year}} %s\g<2>{{champ.%s}}\g<3>' % (label, key), body)
            assert n == 1, label
        body = mark_run(body, r'(?<=Club results by season:</p>\n)<div [^>]*>\n' + A_RUN + r'</div>', 'home_seasons')
        body = mark_run(body, r'(?:<li [^>]*>[^<]*</li>\s*)+(?=</ul>\s*</section>\s*$)', 'sponsors')
    elif name == 'results':
        body = mark_run(body, r'(?<=>Season</span>\n)' + A_RUN, 'club_picker')
        body = swap(body, '>2026 club tournaments</h2>', '>{{season.year}} club tournaments</h2>')
        body = mark_tbody(body, 1, 'season_index')
        body = swap(body, '>Club Classic, November 7 and 8, 2026</h2>', '>{{featured.title}}</h2>')
        body = mark_tbody(body, 2, 'featured_rows')
        body = swap(body, '>114 fish for 218.14 pounds. Day 1 lunker: Greg Arrowood, 3.15. Day 2 lunker: Steve Manista, 3.62.</p>',
                    '>{{featured.summary}}</p>')
        body = mark_tbody(body, 3, 'aoy_top7')
        body = swap(body, '>2026 honors</h2>', '>{{season.year}} honors</h2>')
        body = swap(body, '<a href="#classic"', '<a href="#classic"', 1)
    elif name == 'opens':
        body = swap(body, '>[Caption: which Open, and who]<', '>{{caption:opens-top}}<')
        body = swap(body, '>[2027 dates: to be posted when the club sets them]</p>', '>{{schedule.opens_next}}</p>')
        body = swap(body, '>2027 Opens</h2>', '>{{schedule.opens_next_year}} Opens</h2>')
        body = mark_run(body, r'(?<=>Season</span>\n)' + A_RUN, 'opens_picker')
        body = swap(body, '>The 2026 Opens</h2>', '>The {{opens.year}} Opens</h2>')
        body = mark_tbody(body, 2, 'opens_top10')
        body = mark_run(body, r'(?:<li [^>]*><a [^>]*>[^<]*</a><span [^>]*>[^<\[]*</span><span [^>]*>[^<]*</span></li>\s*)+', 'opens_each')
        # the cash Open has no result yet: words only, no link
        body, n = re.subn(r'<a href="[^"]*"( style="[^"]*")>(November 14, cash Open)</a>', r'<strong>\2</strong>', body)
        assert n == 1
    elif name == 'club':
        body = swap(body, '>The club at the Nanticoke, April 2023.</figcaption>', '>{{caption:club-top}}</figcaption>')
        body = swap(body, '<strong>When:</strong> usually the third Thursday of each month', '<strong>When:</strong> {{meeting.when}}')
        body = swap(body, '<strong>Where:</strong> Garnet Valley Pizza, 1104 Naamans Creek Road, Garnet Valley, PA 19060. '
                    'About five minutes south of Wegmans, just off Route 202.', '<strong>Where:</strong> {{meeting.where}}')
        body = swap(body, '>[Next meeting date]</p>', '>{{meeting.next}}</p>')
        body = mark_run(body, r'(?:<div [^>]*><dt [^>]*>[^<]*</dt><dd [^>]*>[^<]*</dd></div>\s*)+(?=</dl>)', 'officers')
        body = swap(body, '>[Captions to come.] More photos', '>{{caption:club-members}} More photos')
    elif name == 'records':
        body = mark_tbody(body, 1, 'champions')
        body = mark_tbody(body, 2, 'top_bags')
        body = mark_tbody(body, 3, 'top_bass')
        body = mark_tbody(body, 4, 'top_rider_bags')
        body = mark_tbody(body, 5, 'best_by_water')
    elif name == 'schedule':
        body = swap(body, '>[2027 dates and ramps: to be posted when the club sets them]</p>', '>{{schedule.next}}</p>')
        body = swap(body, '>2027 club tournaments</h2>', '>{{schedule.next_year}} club tournaments</h2>')
        body = swap(body, '>2026 club tournaments</h2>', '>{{schedule.year}} club tournaments</h2>')
        body = mark_tbody(body, 1, 'schedule_rows')
        body = swap(body, '>Usually the third Thursday of each month at Garnet Valley Pizza. The draw',
                    '>{{meeting.sentence}} The draw')
        # no map exists on the old site: say so in brackets, do not link nowhere
        body, n = re.subn(r'<a href="#top"( style="[^"]*")>Map of the ramps we use</a>',
                          r'<span\1>[Map of the ramps we use: to come]</span>', body)
        assert n == 1
    assert 'dc.html' not in body, name
    left = re.findall(r'href="#top"', body)
    assert not left or name == 'home', (name, len(left))
    return body + '\n'


def main():
    if '--force' not in sys.argv and os.path.isfile(os.path.join(OUT, 'home.html')):
        sys.exit('templates/ already exists. This would overwrite hand edits; pass --force to do it anyway.')
    design = find_design()
    if not design:
        sys.exit('Design pages not found. Set CCBM_DESIGN_PAGES to the folder that holds Main.dc.html.')
    os.makedirs(OUT, exist_ok=True)
    for src, name in PAGES.items():
        with open(os.path.join(design, src + '.dc.html'), encoding='utf-8') as f:
            html = f.read()
        title = re.search(r'<title>(.*?)</title>', html).group(1)
        body = convert(name, html)
        with open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8') as f:
            f.write('<!-- title: %s -->\n' % title)
            f.write(body)
        print('wrote templates/%s.html  (%d markers, %d rows blocks)' % (
            name, len(re.findall(r'\{\{[^}]+\}\}', body)), len(re.findall(r'<!--rows:', body))))


if __name__ == '__main__':
    main()
