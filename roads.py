#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import json
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_HOPS = 60

_HERE = Path(__file__).parent
PHILOSOPHY_ARTICLES = json.loads((_HERE / 'philosophy-languages.json').read_text())

SKIP_TAGS = frozenset({'table', 'sup', 'style', 'script'})

SKIP_CLASS_KEYWORDS = frozenset({
    'infobox', 'sidebar', 'navbox', 'mw-empty-elt',
    'reference', 'reflist', 'IPA', 'nowrap',
    'hatnote', 'dablink', 'shortdescription',
    'metadata', 'noprint', 'sisterproject',
})


def parse_input(raw):
    raw = raw.strip()
    m = re.match(r'^(?:https?://)?([a-z]{2,3})\.wikipedia\.org/', raw)
    if m:
        lang = m.group(1)
        title_m = re.search(r'/wiki/(.+?)(?:#.*)?$', raw)
        if title_m:
            return lang, urllib.parse.unquote(title_m.group(1)).replace('_', ' ')
    return None, raw.replace('_', ' ')


class FirstLinkFinder(HTMLParser):
    def __init__(self, current_title):
        super().__init__()
        self.current_title = current_title
        self.found = None
        self._paren_depth = 0
        self._in_lead = True
        self._skip_depth = 0
        self._in_p = False
        self._skip_remainder = False

    def handle_starttag(self, tag, attrs):
        if self._skip_remainder or self.found:
            return

        # inside a skipped element — count nesting to know when we're out
        if self._skip_depth:
            self._skip_depth += 1
            return

        if not self._in_lead:
            return

        if tag == 'h2':
            self._in_lead = False
            return

        if tag in SKIP_TAGS:
            self._skip_depth = 1
            return

        d = dict(attrs)
        cls = d.get('class', '')
        if any(kw in cls for kw in SKIP_CLASS_KEYWORDS):
            self._skip_depth = 1
            return

        if tag == 'p':
            self._in_p = True
            self._paren_depth = 0
            return

        if tag in ('div', 'span', 'ul', 'ol', 'li', 'dl', 'dd', 'dt',
                   'i', 'b', 'em', 'strong', 'small', 'br'):
            return

        if tag == 'a' and self._in_p and self._paren_depth == 0:
            href = d.get('href', '')
            if href.startswith('/wiki/') and not re.search(
                r'/(File|Special|Help|Wikipedia|Talk|Category|Portal|'
                r'Wiktionary|Template|Template_talk):', href
            ):
                t = urllib.parse.unquote(
                    href.replace('/wiki/', '').replace('_', ' ')
                )
                if t and t != self.current_title and not t.startswith('#'):
                    self.found = t
                    self._skip_remainder = True

    def handle_endtag(self, tag):
        if self._skip_depth:
            self._skip_depth -= 1
            return

        if tag == 'p' and self._in_p:
            self._in_p = False
            self._paren_depth = 0

    def handle_data(self, data):
        if self._skip_depth or self._skip_remainder or self.found:
            return
        if not self._in_lead or not self._in_p:
            return
        for ch in data:
            if ch == '(':
                self._paren_depth += 1
            elif ch == ')':
                self._paren_depth = max(0, self._paren_depth - 1)


def fetch_first_link(title, lang):
    params = urllib.parse.urlencode({
        'action': 'parse',
        'page': title.replace(' ', '_'),
        'prop': 'text',
        'format': 'json',
        'origin': '*',
        'redirects': '1',
    })
    url = f'https://{lang}.wikipedia.org/w/api.php?{params}'
    ua = 'roads-to-philosophy-cli/1.0 (https://github.com/Arecsu/roads-to-philosophy)'
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': ua})
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode('utf-8'))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                wait = int(e.headers.get('Retry-After', 5 * (2 ** attempt)))
                print(f'  (rate limited, retrying in {wait}s...)', file=sys.stderr)
                time.sleep(wait)
            else:
                raise
    if 'error' in data:
        raise RuntimeError(
            data['error'].get('info', f'API error for "{title}"')
        )
    resolved = data['parse']['title']
    html = data['parse']['text']['*']
    finder = FirstLinkFinder(resolved)
    finder.feed(html)
    return finder.found, resolved


def run(title, lang, target=None):
    if not target:
        target = PHILOSOPHY_ARTICLES.get(lang)
        if not target:
            raise RuntimeError(
                f'No Philosophy article known for "{lang}". '
                f'Provide a target via --target or as a third argument.'
            )
    chain = []
    seen = set()
    cur = title
    for _ in range(MAX_HOPS):
        if cur in seen:
            chain.append(cur)
            return chain, 'loop'
        seen.add(cur)
        chain.append(cur)
        if cur == target:
            return chain, 'reached φ'

        nxt, resolved = fetch_first_link(cur, lang)

        time.sleep(0.6)

        if resolved != cur:
            seen.discard(cur)
            seen.add(resolved)
            chain[-1] = resolved
            cur = resolved
            if cur == target:
                return chain, 'reached φ'

        if not nxt:
            return chain, f'error: no valid link in "{cur}"'
        cur = nxt

    return chain, 'loop (max hops)'


def main():
    args = sys.argv[1:]
    plain = False
    target = None

    stripped = []
    i = 0
    while i < len(args):
        if args[i] in ('-p', '--plain'):
            plain = True
        elif args[i] == '--target' and i + 1 < len(args):
            target = args[i + 1]
            i += 1
        else:
            stripped.append(args[i])
        i += 1
    args = stripped

    if not args:
        print('Usage:')
        print('  uv run roads.py [options] <wikipedia-url>')
        print('  uv run roads.py [options] <lang> "<title>" [<target>]')
        print()
        print('Options:')
        print('  -p, --plain            Print without numbers')
        print('  --target <article>     Override target article (default: auto-detected')
        print('                         from 243-language Philosophy map)')
        print()
        print('Examples:')
        print('  uv run roads.py https://es.wikipedia.org/wiki/Arte')
        print('  uv run roads.py -p es Arte')
        print('  uv run roads.py ko 철학')
        print('  uv run roads.py https://fr.wikipedia.org/wiki/Musique')
        print('  uv run roads.py fr Musique --target Philosophie')
        sys.exit(1)

    if len(args) == 1:
        lang, title = parse_input(args[0])
        if not lang:
            print(
                f'Could not detect language from "{args[0]}".',
                file=sys.stderr,
            )
            print('Use: uv run roads.py <lang> "<title>"', file=sys.stderr)
            sys.exit(1)
    elif len(args) == 2:
        lang, title = args[0], args[1].replace('_', ' ')
    else:
        lang, title, target = args[0], args[1].replace('_', ' '), args[2]

    chain, status = run(title, lang, target)
    print()
    if plain:
        for node in chain:
            print(node)
    else:
        for i, node in enumerate(chain, 1):
            print(f'{i}. {node}')
    print(f'\n({status})')


if __name__ == '__main__':
    main()
