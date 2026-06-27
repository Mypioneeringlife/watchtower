# Watchtower Runbook

## 1. Test the app locally

Open `index.html` in a browser, or serve the folder locally:

```bash
python -m http.server 8080
```

Then visit `http://localhost:8080`.

## 2. Test the watcher with sample data

```bash
python watcher/watchtower.py --dry-run --sample watcher/tests/sample_feed.xml
```

Expected behavior:

- The Highlander reboot sample should match.
- The Toyota Highlander sample should be rejected by exclusion terms.
- The USDA food safety sample should match.

## 3. Enable real sources

Edit `data/sources.json`:

```json
"url": "https://example.com/feed.xml",
"enabled": true
```

Start with one or two trusted feeds. Do not enable a bunch of random sources at once.

## 4. Run once manually

```bash
python watcher/watchtower.py --once
```

## 5. Review output

Check:

- `data/signals.json`
- `data/seen.json`
- `outbox/second-brain/`

## 6. GitHub Actions

The workflow runs at 5:07 a.m. and 5:07 p.m. Pacific time equivalent during standard UTC conversion. Adjust the cron if daylight saving precision matters.