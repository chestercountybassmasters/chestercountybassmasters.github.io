"""Read the content area of a page from the Weebly archive into a flat list of blocks.

Standard library only. A block is one of:
  {'kind': 'heading', 'text': ...}
  {'kind': 'text', 'text': ..., 'links': [(href, text), ...]}
  {'kind': 'image', 'src': ..., 'alt': ..., 'href': link the picture sits in, or '',
   'title': the words Weebly showed when the mouse was over the picture, or ''}
  {'kind': 'iframe', 'src': ...}
  {'kind': 'table', 'rows': [[cell, ...], ...], 'spans': [(row, col, rowspan, colspan), ...]}
      a real table (not a Weebly column layout). Merged cells are spread out so that
      every row has its cells in the right columns: the text sits in the first cell
      of the merged block and the rest are ''. 'spans' lists the merged blocks.
Weebly lays columns out with <table class="wsite-multicol-table">; those are
walked through, not reported, so the blocks inside them come out in reading order.
"""
from html.parser import HTMLParser

VOID = {'br', 'img', 'hr', 'input', 'meta', 'link', 'area', 'col', 'embed', 'source', 'wbr'}
BLOCK = {'div', 'p', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
         'section', 'form'}
HEAD = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


def _span(v):
    try:
        return max(1, min(60, int(v)))
    except (TypeError, ValueError):
        return 1


def _spread(t):
    """Lay one row's cells out in their true columns, allowing for merged cells."""
    out, col, pend = [], 0, t['pending']

    def skip():
        nonlocal col
        while pend.get(col, 0) > 0:
            out.append('')
            pend[col] -= 1
            col += 1
    for text, cs, rs in t['row']:
        skip()
        if cs > 1 or rs > 1:
            t['spans'].append((len(t['rows']), col, rs, cs))
        for k in range(cs):
            out.append(text if k == 0 else '')
            if rs > 1:
                pend[col] = rs - 1
            col += 1
    skip()
    return out


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.inside = False     # inside div#wsite-content
        self.depth = 0
        self.skip = 0           # inside script/style
        self.buf = []
        self.links = []
        self.link = None        # [href, text] of the open <a>
        self.heading = False
        self.tables = []        # stack of open real tables
        self.layout = []        # stack: True for a real table, False for a layout table

    # -- text handling
    def _flush(self):
        raw = ''.join(self.buf)
        for junk in ('\u200b', '\ufeff'):
            raw = raw.replace(junk, '')
        raw = raw.replace('\xa0', ' ')
        lines = [' '.join(x.split()) for x in raw.split('\n')]
        lines = [x for x in lines if x]
        text = ' '.join(lines)
        self.buf = []
        links, self.links = self.links, []
        if self.tables:
            t = self.tables[-1]
            if t['cell'] is not None and text:
                t['cell'].append('\n'.join(lines))   # line breaks inside a cell are kept
            return
        if text:
            kind = 'heading' if self.heading else 'text'
            b = {'kind': kind, 'text': text, 'lines': lines}
            if links:
                b['links'] = links
            self.blocks.append(b)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.inside:
            if a.get('id') == 'wsite-content':
                self.inside = True
                self.depth = 0
            return
        if tag in ('script', 'style'):
            self.skip += 1
            return
        if tag == 'br':
            self.buf.append('\n')
            return
        if tag == 'img':
            if self.tables:
                return
            self._flush()
            self.blocks.append({'kind': 'image', 'src': a.get('src', ''), 'alt': a.get('alt', ''),
                                'href': self.link[0] if self.link else '',
                                'title': ' '.join((self.link[2] if self.link else '').split())})
            return
        if tag in VOID:
            return
        self.depth += 1
        if tag == 'table':
            self._flush()
            real = 'wsite-multicol-table' not in a.get('class', '')
            self.layout.append(real)
            if real:
                self.tables.append({'rows': [], 'row': None, 'cell': None, 'span': (1, 1),
                                    'pending': {}, 'spans': []})
        elif tag == 'tr':
            if self.layout and self.layout[-1] and self.tables:
                self.tables[-1]['row'] = []
        elif tag in ('td', 'th'):
            if self.layout and self.layout[-1] and self.tables:
                self._flush()
                self.tables[-1]['cell'] = []
                self.tables[-1]['span'] = (_span(a.get('colspan')), _span(a.get('rowspan')))
            else:
                self._flush()
        elif tag == 'iframe':
            self._flush()
            self.blocks.append({'kind': 'iframe', 'src': a.get('src', '')})
        elif tag == 'a':
            self.link = [a.get('href', ''), '', a.get('title', '')]
        elif tag in BLOCK:
            self._flush()
            if tag in HEAD:
                self.heading = True

    def handle_endtag(self, tag):
        if not self.inside:
            return
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
            return
        if tag in VOID:
            return
        if tag == 'a':
            if self.link and self.link[0] and not self.tables:
                self.links.append((self.link[0], ' '.join(self.link[1].split())))
            self.link = None
        elif tag in ('td', 'th'):
            if self.layout and self.layout[-1] and self.tables:
                self._flush()
                t = self.tables[-1]
                if t['row'] is not None and t['cell'] is not None:
                    t['row'].append((' '.join(t['cell']),) + t['span'])
                t['cell'] = None
            else:
                self._flush()
        elif tag == 'tr':
            if self.layout and self.layout[-1] and self.tables:
                t = self.tables[-1]
                if t['row'] is not None:
                    t['rows'].append(_spread(t))
                t['row'] = None
        elif tag == 'table':
            self._flush()
            real = self.layout.pop() if self.layout else False
            if real and self.tables:
                t = self.tables.pop()
                if self.tables:      # a real table inside a real table: keep it as text of the cell
                    cell = self.tables[-1]['cell']
                    if cell is not None:
                        cell.append(' '.join(' '.join(r) for r in t['rows']))
                else:
                    self.blocks.append({'kind': 'table', 'rows': t['rows'], 'spans': t['spans']})
        elif tag in BLOCK:
            self._flush()
            if tag in HEAD:
                self.heading = False
        self.depth -= 1
        if self.depth < 0:
            self._flush()
            self.inside = False

    def handle_data(self, data):
        if self.inside and not self.skip:
            self.buf.append(data)
            if self.link is not None:
                self.link[1] += data


def read_blocks(path):
    """Blocks of the page's content area, in reading order."""
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()
    r = _Reader()
    r.feed(html)
    r.close()
    return r.blocks


def count_source_rows(path):
    """Independent count for check.py: number of <tr> in the content area that sit in a
    real (non-layout) table, counted with a regular expression scan, not the reader above."""
    import re
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()
    i = html.find('id="wsite-content"')
    j = html.find('id="footer', i)
    body = html[i:j if j > 0 else len(html)]
    stack, n = [], 0
    for m in re.finditer(r'<(/?)(table|tr)\b([^>]*)>', body, re.I):
        close, tag, rest = m.group(1), m.group(2).lower(), m.group(3)
        if tag == 'table':
            if close:
                if stack:
                    stack.pop()
            else:
                stack.append('wsite-multicol-table' not in rest)
        elif not close and stack and stack[-1]:
            n += 1
    return n
