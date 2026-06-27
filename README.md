# Watchtower

A phone-first personal web watcher that tracks chosen topics, filters useful signals, sends priority alerts, and saves Markdown notes into a second brain.

## What this repo contains

- A mobile-first PWA dashboard in `index.html`
- A Watchtower app icon in `assets/icons/watchtower.svg`
- Editable watchlists in `data/watchlists.json`
- Source configuration in `data/sources.json`
- A Python RSS/Atom watcher engine in `watcher/watchtower.py`
- A scheduled GitHub Actions workflow in `.github/workflows/watchtower.yml`
- Markdown note output under `outbox/second-brain/`
- Setup and operating notes in `docs/`

## Current version

`v1.1.1` repository build.

## Local test

```bash
python watcher/watchtower.py --dry-run --sample watcher/tests/sample_feed.xml
```

## Run against enabled real sources

```bash
python watcher/watchtower.py --once
```

Real RSS source URLs are disabled placeholders until you choose the exact sources to monitor.