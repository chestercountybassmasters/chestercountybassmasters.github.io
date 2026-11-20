"""Work the club records out from data/ and compare them with the lists on the old site.

Used by build.py. Nothing here changes a record: it reports differences, and the
records page shows the site's lists with any missing bags marked as additions.

How a bag is counted
  - Club tournaments only (the Opens are team bags and are not in the club lists).
  - One bag for each angler in each tournament day. A two-day Classic row holds a
    weight for each day; each day is its own bag on its own water and date.
  - The weight is the total after penalties where the table has a "Total Weight"
    column, otherwise the weight shown.
  - Only seasons whose results are tables can be checked. Results that are pictures
    are not read.
"""
import datetime
import re

WATER_LONG = {'North East': 'North East River', 'Nanticoke': 'Nanticoke River', 'Conowingo': 'Conowingo',
              'Marshyhope': 'Marshyhope River', 'Sassafras': 'Sassafras River', 'Potomac': 'Potomac River',
              'Gunpowder': 'Gunpowder River', 'Wicomico': 'Wicomico River', 'Choptank': 'Choptank River'}


def num(s):
    s = (s or '').strip().rstrip('*').replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None


def us_date(iso):
    y, m, d = iso.split('-')
    return '%d/%d/%s' % (int(m), int(d), y)


def iso_date(us):
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', us.strip())
    if not m:
        return None
    return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat()


def last_name(name):
    name = re.sub(r'\(.*?\)', ' ', name).replace('*', ' ')
    parts = [p for p in re.split(r'[\s.]+', name.strip()) if p]
    return parts[-1].lower() if parts else ''


def same_person(a, b):
    """Loose match: the tables sometimes write PAUL S. or a first name only."""
    a2 = re.sub(r'\(.*?\)', ' ', a).replace('*', ' ').lower().split()
    b2 = re.sub(r'\(.*?\)', ' ', b).replace('*', ' ').lower().split()
    if not a2 or not b2:
        return False
    if a2 == b2:
        return True
    if a2[0][:3] != b2[0][:3] and not (a2[0] in ('woo', 'jim', 'james', 'jimmy') and b2[0] in ('woo', 'jim', 'james', 'jimmy')):
        return False
    la, lb = a2[-1].rstrip('.'), b2[-1].rstrip('.')
    if len(a2) == 1 or len(b2) == 1:
        return True
    return la == lb or la.startswith(lb) or lb.startswith(la)


def collect(seasons):
    """Every bag and every big fish in the club seasons that were parsed from tables."""
    bags, fish, table_days, fish_days, odd = [], [], set(), set(), []
    for (series, year), d in sorted(seasons.items()):
        if series != 'club':
            continue
        for t in d['tournaments']:
            roles = [c['role'] for c in t['columns']]
            if t.get('two_day'):
                days = [('d1_weight', 'd1_big_fish', 0), ('d2_weight', 'd2_big_fish', 1)]
            else:
                days = [('total_weight' if 'total_weight' in roles else 'weight', 'big_fish', 0)]
            for wkey, fkey, k in days:
                if k >= len(t['dates']) or k >= len(t['waters']) or not t['waters'][k]:
                    continue
                date, water = t['dates'][k], t['waters'][k]
                table_days.add(date)
                if fkey in roles:
                    fish_days.add(date)
                for r in t['results']:
                    base = {'name': r['name'], 'date': date, 'water': water, 'year': year,
                            'tournament': t['id'], 'guest': bool(r.get('guest'))}
                    w = num(r.get(wkey))
                    if w:
                        bags.append(dict(base, weight=w, as_written=r.get(wkey)))
                    f = num(r.get(fkey))
                    before = max([x for x in (w, num(r.get('weight'))) if x] or [0])
                    if f and before and f > before + 0.005:
                        # a "big fish" heavier than the whole bag: a slip in the table, not a record
                        odd.append(dict(base, weight=f, as_written=r.get(fkey), bag=r.get(wkey)))
                    elif f:
                        fish.append(dict(base, weight=f, as_written=r.get(fkey)))
    return bags, fish, table_days, fish_days, odd


def site_lists(site):
    """The lists on the old records page, as dicts."""
    out = {'champions': {}, 'bags': None, 'bass': None, 'rider': None, 'waters': {}}
    for lst in site['lists']:
        title = lst['title']
        rows = lst['rows']
        if title in ('Angler of the Year', 'Club Classic Winners', 'Rookie of the Year', 'Rider of the Year'):
            out['champions'][title] = {int(r[0]): r[1] for r in rows if r[0].isdigit()}
            continue
        m = re.match(r'^Top Bags on (.+)$', title)
        entries = []
        for r in rows:
            if m:
                name, w, date = r[0], r[1], r[2]
                water = m.group(1)
            else:
                name, w, water, date = r[0], r[1], r[2], r[3]
            entries.append({'name': name, 'weight': float(w), 'as_written': w, 'water': water,
                            'date': iso_date(date), 'date_text': date})
        if m:
            out['waters'][m.group(1)] = entries
        elif title == 'Top Bags':
            out['bags'] = entries
        elif title == 'Top Bass':
            out['bass'] = entries
        elif title == 'Top Rider Bags':
            out['rider'] = entries
    return out


def compare(title, site, found, table_days, table_years, check_missing=True):
    """Compare one list on the site with what the tables hold."""
    res = {'title': title, 'site': site, 'missing': [], 'not_found': [], 'name_differs': [],
           'not_checked': [], 'confirmed': 0, 'ties': []}
    matched = set()
    for s in site:
        year = int(s['date'][:4]) if s['date'] else None
        if s['date'] not in table_days:
            why = 'results for that date are not a table in the data'
            if year in table_years:
                why = 'that season is parsed from tables, but no table holds this for that date'
            res['not_checked'].append(dict(s, why=why))
            continue
        hit = [i for i, c in enumerate(found) if c['date'] == s['date'] and abs(c['weight'] - s['weight']) < 0.005
               and c['water'] == s['water']]
        if not hit:
            near = [c for c in found if c['date'] == s['date'] and same_person(c['name'], s['name'])]
            res['not_found'].append(dict(s, near=near[:2]))
            continue
        names = [n.strip() for n in s['name'].split(' - ')]   # "A - B" on the list is a tie
        good = [i for i in hit if any(same_person(found[i]['name'], n) for n in names)]
        if good and len(good) >= len(names):
            matched.update(good)
            res['confirmed'] += 1
        elif good:
            matched.add(good[0])
            res['confirmed'] += 1
        else:
            matched.add(hit[0])
            res['name_differs'].append(dict(s, table_name=found[hit[0]]['name']))
    if check_missing and site:
        floor = min(s['weight'] for s in site) if len(site) >= 10 else 0.0
        extra = [c for i, c in enumerate(found) if i not in matched and c['weight'] > floor + 0.005]
        extra.sort(key=lambda c: (-c['weight'], c['date']))
        pool = [s['weight'] for s in site]
        for c in extra:
            rank = 1 + sum(1 for w in pool if w > c['weight'] + 0.005)
            if rank <= 10:
                res['missing'].append(dict(c, rank=rank))
                pool.append(c['weight'])
        res['ties'] = [c for i, c in enumerate(found) if i not in matched and abs(c['weight'] - floor) <= 0.005
                       and len(site) >= 10]
        # which of the site's entries an addition would push out of the first ten
        if res['missing']:
            merged = sorted([(s['weight'], 0, s) for s in site] + [(c['weight'], 1, c) for c in res['missing']],
                            key=lambda x: -x[0])
            res['pushed_out'] = [x[2] for x in merged[10:] if x[1] == 0]
        else:
            res['pushed_out'] = []
    return res


def run(seasons, site):
    bags, fish, table_days, fish_days, odd = collect(seasons)
    lists = site_lists(site)
    table_years = sorted({y for (s, y), d in seasons.items() if s == 'club' and d['tournaments']})
    out = {'table_years': table_years, 'bags_counted': len(bags), 'fish_counted': len(fish), 'lists': [],
           'waters_without_list': [], 'champions': []}
    out['lists'].append(dict(compare('Top Bags', lists['bags'], bags, table_days, table_years), key='bags'))
    for water, entries in lists['waters'].items():
        sub = [b for b in bags if b['water'] == water]
        for e in entries:
            e['water'] = water
        out['lists'].append(dict(compare('Top Bags on ' + water, entries, sub, table_days, table_years),
                                 key='water:' + water))
    out['lists'].append(dict(compare('Top Bass', lists['bass'], fish, fish_days, table_years), key='bass'))
    out['odd'] = odd
    out['lists'].append(dict(compare('Top Rider Bags', lists['rider'], bags, table_days, table_years,
                                     check_missing=False), key='rider'))
    listed = set(lists['waters'])
    for water in sorted({b['water'] for b in bags} - listed):
        top = sorted([b for b in bags if b['water'] == water], key=lambda b: -b['weight'])[:10]
        out['waters_without_list'].append({'water': water, 'top': top})
    # champions: what the tables can confirm
    champs = lists['champions']
    for year in table_years:
        d = seasons[('club', year)]
        classic = [t for t in d['tournaments'] if t.get('two_day')]
        listed_winner = champs.get('Club Classic Winners', {}).get(year)
        if classic and classic[-1]['results']:
            got = classic[-1]['results'][0]['name']
            out['champions'].append({'year': year, 'what': 'Classic winner', 'site': listed_winner, 'tables': got,
                                     'agree': bool(listed_winner) and same_person(got, listed_winner)})
        else:
            out['champions'].append({'year': year, 'what': 'Classic winner', 'site': listed_winner, 'tables': None,
                                     'agree': None})
        aoy = [s for s in d['standings'] if re.search(r'(?i)aoy', ' '.join(s['title_lines']))]
        listed_aoy = champs.get('Angler of the Year', {}).get(year)
        if aoy and aoy[0]['rows']:
            st = aoy[0]
            ci = 0
            for i, c in enumerate(st['columns']):
                if re.match(r'(?i)^(participant|angler)$', c):
                    ci = i
            got = st['rows'][0][ci].lstrip('*').rstrip('*')
            out['champions'].append({'year': year, 'what': 'Angler of the Year', 'site': listed_aoy, 'tables': got,
                                     'agree': bool(listed_aoy) and same_person(got, listed_aoy)})
        else:
            out['champions'].append({'year': year, 'what': 'Angler of the Year', 'site': listed_aoy, 'tables': None,
                                     'agree': None})
    out['site'] = lists
    out['changes'] = site.get('source', {}).get('changes', [])
    return out


def fmt(w):
    return '%.2f' % w


def write_report(path, res, today):
    L = []
    add = L.append
    add('# Records check')
    add('')
    add('Written by `build.py` on %s. It compares the lists on the old site\'s records page' % today)
    add('(`top-bags-lunkers-aoys-etc.html`, copied 2026-11-20) with the results held in `data/`.')
    add('Nothing here changes a record. The records page shows the club\'s lists as they are, and marks')
    add('anything below under "Missing" as an addition found by this check, for Steve to confirm.')
    add('')
    add('## What was checked')
    add('')
    add('- Club seasons parsed from tables: %s. %d bags and %d big-fish weights were counted.' % (
        ', '.join(str(y) for y in res['table_years']), res['bags_counted'], res['fish_counted']))
    add('- One bag for each angler for each tournament day. A two-day Classic gives two bags, each on its own water and date.')
    add('- The weight is the total after penalties where the table has a total column.')
    add('- Not checked: every season whose results are pictures (2004 to 2019), the 2020 Classic (its result is three pictures),')
    add('  and whether a bag was a rider\'s (the tables do not say who rode).')
    add('- "Top Bass" is checked against the big-fish column of the tables. The 2020 tables have no such column, and an')
    add('  angler\'s big fish is in the table only if it was weighed, so that check is weaker than the bag check.')
    add('')
    if res.get('changes'):
        add('## Changes made to the club\'s lists since the copy')
        add('')
        add('Made by hand in `data/records_site.json`, each at the Tournament Director\'s word. The lists below are')
        add('compared as they now stand.')
        add('')
        for c in res['changes']:
            add('- %s, %s: added %s in place %d; %s dropped off the end. %s' % (
                c['date'], c['list'], ', '.join(c['added']), c['place'], ', '.join(c['dropped_off_the_end']), c['why']))
        add('')
    add('## Summary')
    add('')
    add('| List | On the site | Confirmed in tables | Missing from the list | Differences | Not checkable |')
    add('|---|---|---|---|---|---|')
    for l in res['lists']:
        add('| %s | %d | %d | %s | %d | %d |' % (l['title'], len(l['site']), l['confirmed'],
            len(l['missing']) if l['key'] != 'rider' else 'not checked', len(l['not_found']) + len(l['name_differs']),
            len(l['not_checked'])))
    add('')
    n_missing = sum(len(l['missing']) for l in res['lists'])
    add('**%d missing %s found in all.**' % (n_missing, 'entry' if n_missing == 1 else 'entries'))
    add('')
    for l in res['lists']:
        add('## %s' % l['title'])
        add('')
        if l['missing']:
            add('**Missing from the list (in the tables, heavy enough for the first ten):**')
            add('')
            for c in l['missing']:
                add('- %s, %s lb, %s, %s — would be number %d. Source: `data/club/%d.json`, tournament `%s`.%s' % (
                    c['name'], fmt(c['weight']), c['water'], us_date(c['date']), c['rank'], c['year'], c['tournament'],
                    ' Marked as a guest in the table.' if c['guest'] else ''))
            if l.get('pushed_out'):
                add('')
                add('  With these added, the list would run past ten. Now on the list, would fall out of the first ten: %s.' % '; '.join(
                    '%s %s (%s)' % (s['name'], s['as_written'], s['date_text']) for s in l['pushed_out']))
            add('')
        elif l['key'] == 'rider':
            add('Missing rider bags cannot be found from the tables: they do not say who was a rider.')
            add('')
        else:
            add('No missing entry found in the table seasons.')
            add('')
        if l['not_found']:
            add('**On the site\'s list, but the tables do not show that weight on that date and water:**')
            add('')
            for s in l['not_found']:
                near = '; '.join('the table has %s with %s on %s' % (n['name'], n['as_written'], n['water']) for n in s['near'])
                add('- %s, %s lb, %s, %s. %s' % (s['name'], s['as_written'], s['water'], s['date_text'],
                                                 (near[0].upper() + near[1:] + '.') if near else 'No row for that angler on that date.'))
            add('')
        if l['name_differs']:
            add('**Same weight, date and water, but the name is written differently:**')
            add('')
            for s in l['name_differs']:
                add('- %s lb on %s: the list says %s, the table says %s.' % (s['as_written'], s['date_text'], s['name'], s['table_name']))
            add('')
        if l.get('ties'):
            add('**Ties with the tenth entry, not on the list:** ' + '; '.join(
                '%s %s (%s, %s)' % (c['name'], fmt(c['weight']), c['water'], us_date(c['date'])) for c in l['ties']))
            add('')
        add('Confirmed in the tables: %d of %d.' % (l['confirmed'], len(l['site'])))
        if l['not_checked']:
            add('Not checkable (%d): %s.' % (len(l['not_checked']), '; '.join(
                '%s %s on %s' % (s['name'], s['as_written'], s['date_text']) for s in l['not_checked'])))
        add('')
    if res.get('odd'):
        add('## Slips in the tables')
        add('')
        add('A "big fish" heavier than the angler\'s whole bag. Left out of the Top Bass check; shown on the season page as the table has it.')
        add('')
        for c in res['odd']:
            add('- %s, %s: big fish written as %s, bag %s. `data/club/%d.json`, tournament `%s`.' % (
                c['name'], us_date(c['date']), c['as_written'], c['bag'], c['year'], c['tournament']))
        add('')
    if res['waters_without_list']:
        add('## Waters with no list on the site')
        add('')
        add('The tables hold club tournaments on these waters, and the old records page has no list for them.')
        add('The heaviest bags in the table seasons, for information:')
        add('')
        for w in res['waters_without_list']:
            add('- **%s:** %s' % (w['water'], '; '.join('%s %s (%s)' % (b['name'], fmt(b['weight']), us_date(b['date'])) for b in w['top'][:5])))
        add('')
    add('## Champions')
    add('')
    add('What the tables can confirm of the champions lists (a first row of a standings table, a first row of a Classic).')
    add('')
    add('| Year | Title | The site\'s list | The tables | Agree |')
    add('|---|---|---|---|---|')
    for c in res['champions']:
        add('| %d | %s | %s | %s | %s |' % (c['year'], c['what'], c['site'] or '–', c['tables'] or 'no table',
                                           {True: 'yes', False: '**no**', None: 'not checkable'}[c['agree']]))
    add('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
