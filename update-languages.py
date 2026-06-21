#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import json
import urllib.request

url = 'https://en.wikipedia.org/w/api.php?action=query&prop=langlinks&titles=Philosophy&lllimit=500&format=json&origin=*'
req = urllib.request.Request(url, headers={'User-Agent': 'roads-to-philosophy-cli/1.0'})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
pages = data['query']['pages']
langlinks = next(iter(pages.values())).get('langlinks', [])
mapping = {ll['lang']: ll['*'] for ll in langlinks}
mapping['en'] = 'Philosophy'
with open('philosophy-languages.json', 'w') as f:
    json.dump(mapping, f, indent=2, ensure_ascii=False)
print(f'Updated philosophy-languages.json ({len(mapping)} languages)')
