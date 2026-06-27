# Watchtower Docs

Watchtower has two parts:

1. **Phone app / PWA**: the dashboard, installed from GitHub Pages or opened from the repo.
2. **Watcher engine**: the scheduled Python script that checks RSS/Atom sources and writes second-brain notes.

## Recommended workflow

- Keep source URLs disabled until you confirm them.
- Enable one or two sources at a time.
- Test with the sample feed first.
- Let high-priority topics alert you.
- Let lower-priority topics go into digest/review mode.

## Second-brain rule

Automated notes should go into `00-Inbox/Web Watch` first. Do not let automated intake write directly into permanent notes without review.