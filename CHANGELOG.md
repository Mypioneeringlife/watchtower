# Changelog

## v1.5.0

- Added watcher run logging to `watcher/watchtower.py`.
- Added `data/run-log.json` for persistent run history.
- Added a Run Log screen in the phone app.
- Added run metrics for items checked, new signals, notes written, and source errors.
- Added per-source run status, item counts, match counts, note counts, and error display.
- Updated the GitHub Actions workflow so run logs are committed with watcher output.
- Added `assets/js/runlog.js` and updated the service worker cache.

## v1.4.0

- Added the Source Manager screen.
- Added source metrics for enabled, disabled, official, and placeholder sources.
- Added filters for All, Enabled, Disabled, Need URL, Official, Trusted, and Test.
- Added dynamic source cards from `data/sources.json`.
- Added topic labels, reliability labels, and URL readiness warnings for each source.
- Added a copy-ready source snippet for adding new RSS feeds safely.
- Updated the service worker cache for the v1.4 app shell.

## v1.3.0

- Made the Signal Inbox interactive.
- Added loading from `data/signals.json`, with sample cards used only when the file is empty.
- Added filters for All, Alerts, New, Saved, Reviewed, and Ignored.
- Added local review status storage on the phone.
- Added signal buttons for Open, Note, Save, Reviewed, and Ignore.
- Added copy-ready Markdown generation from a selected signal.

## v1.2.0

- Rebuilt the phone UI so Watchtower feels like an actual mobile app instead of a rough document page.
- Added a dark blue and silver visual system matching the approved icon direction.
- Added a dashboard hero, metric cards, system status cards, sample priority signals, and a bottom navigation bar.
- Added separate screens for Dashboard, Signals, Topics, Sources, Tools, and Settings.
- Added external CSS and JavaScript files under `assets/`.
- Updated the service worker cache so the new UI assets load correctly.

## v1.1.1

- Created repository build for `Mypioneeringlife/watchtower`.
- Added mobile-first PWA dashboard.
- Added SVG app icon so the logo can populate reliably from GitHub Pages and local browser views.
- Added starter topic watchlists.
- Added source configuration with disabled placeholders.
- Added Python RSS/Atom watcher.
- Added relevance scoring, duplicate tracking, and Markdown note output.
- Added scheduled GitHub Actions workflow.
- Added docs, runbook, roadmap, and note template.
