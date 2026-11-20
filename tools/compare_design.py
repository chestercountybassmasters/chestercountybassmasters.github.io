#!/usr/bin/env python3
"""Compare the words on the six built front pages with the words on the design pages.

    python3 -I tools/compare_design.py

Prints every line of words that is on one and not on the other. Differences are
expected where the build adds a section the design did not have; the rest should
be empty. Needs the design pages (in the club's Drive, or CCBM_DESIGN_PAGES).
"""
import difflib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import convert_design  # noqa: E402

PAIRS = {'Main': 'index', 'Results': 'results', 'Opens': 'opens', 'Club': 'club', 'Records': 'records',
         'Schedule': 'schedule'}


def words(html):
    html = re.sub(r'<(script|style)\b.*?</\1>', '', html, flags=re.S)
    html = re.sub(r'<(br|/p|/h\d|/li|/tr|/div|/article|/section|/dt|/dd|/td|/th|/a|/span|/strong|/figcaption)\b[^>]*>', '\n', html)
    text = re.sub(r'<[^>]+>', '', html)
    import html as h
    lines = [' '.join(h.unescape(x).split()) for x in text.split('\n')]
    return [x for x in lines if x]


def main():
    design = convert_design.find_design()
    if not design:
        sys.exit('design pages not found')
    total = 0
    for src, out in PAIRS.items():
        a = open(os.path.join(design, src + '.dc.html'), encoding='utf-8').read()
        a = a[a.index('</header>'):a.index('<footer')]
        b = open(os.path.join(os.path.dirname(HERE), 'docs', out + '.html'), encoding='utf-8').read()
        b = b[b.index('<main'):b.index('</main>')]
        diff = [l for l in difflib.unified_diff(words(a), words(b), 'design', 'built', lineterm='', n=0)
                if not l.startswith(('---', '+++', '@@'))]
        print('== %s: %d lines differ' % (out, len(diff)))
        for l in diff:
            print('   ' + l)
        total += len(diff)
    print('\n%d lines differ in all.' % total)


if __name__ == '__main__':
    main()
