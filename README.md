# roads-to-philosophy

CLI tool that traces Wikipedia's "first link" chain from any article to Philosophy. Supports **243 languages** — every Wikipedia that has a Philosophy article.

```bash
uv run roads.py https://es.wikipedia.org/wiki/Arte
uv run roads.py -p ko 음악
uv run roads.py https://fr.wikipedia.org/wiki/Musique
```

## Usage

```text
uv run roads.py [options] <wikipedia-url>
uv run roads.py [options] <lang> "<title>" [<target>]

Options:
  -p, --plain            Print without numbers
  --target <article>     Override target article (default: auto-detected
                         from 243-language Philosophy map)

Examples:
  uv run roads.py https://en.wikipedia.org/wiki/Chair
  uv run roads.py -p es "Arte"
  uv run roads.py ko 철학
  uv run roads.py fr Musique
```

### Output modes

**Numbered** (default):
```
1. Chair
2. Seat
...
17. Philosophy
```

**Plain** (`-p`):
```
Chair
Seat
...
Philosophy
```

## How it works

1. Uses the MediaWiki Action API (`action=parse`) to fetch article HTML.
2. Strips infoboxes, navboxes, references, hatnotes, etc.
3. Walks the first `<p>` in the lead section, tracking parenthesis depth, returns the first `/wiki/` link not inside parentheses (skipping `File:`, `Special:`, etc.).
4. Follows that link and repeats until reaching Philosophy, a loop, or 60 hops.
5. 0.6s delay between hops; exponential backoff on 429s.

## Credits

Inspired by [road-to-philosophy.com](https://road-to-philosophy.com/) — the original web-based Wikipedia link chain visualizer by [@kubi](https://github.com/kubi).
