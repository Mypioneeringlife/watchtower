# Watcher Engine

`watcher/watchtower.py` is the scheduled RSS/Atom watcher for Watchtower.

## Test with the included sample feed

```bash
python watcher/watchtower.py --dry-run --sample watcher/tests/sample_feed.xml
```

## Run once against enabled real sources

```bash
python watcher/watchtower.py --once
```

## How it works

1. Loads topic rules from `data/watchlists.json`.
2. Loads source rules from `data/sources.json`.
3. Reads enabled RSS/Atom feeds.
4. Scores each item against topic keywords and exclusions.
5. Writes strong matches to `outbox/second-brain/` as Markdown notes.
6. Tracks seen items in `data/seen.json`.
7. Writes recent signals to `data/signals.json`.

This is designed as a focused watcher, not a broad crawler.