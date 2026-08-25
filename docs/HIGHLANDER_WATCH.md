# Highlander Watch

Highlander Watch is an entity-centered intelligence module inside Watchtower. It follows the same model as Creator Watch: the roster is primary; feeds/search are discovery tools.

## What it tracks

- Highlander franchise/reboot news
- Cast, creators, directors, writers, producers, composers, cinematographers, editors, and voice actors connected to Highlander
- Health/death events
- Convention and public appearances
- Interviews and podcasts
- New projects and casting
- Awards and legal events
- Production/release changes

## Noise policy

Collection is broad. Attention is selective.

A newly discovered item is canonicalized once even if it matches several people. The event stores all matched entities, chooses the strongest match as primary, and only marks an item as a notification candidate when its score/event type warrants attention.

No qualifying change means no user-facing alert.

## Roster

`data/highlander_entities.json` contains manually curated profiles plus the roster-expansion policy. Manual profiles are never removed by automatic discovery.

`watcher/highlander_roster.py` expands the roster from Wikidata using Highlander film-series, television-series, universe, and related-work relationships. Discovered people are added at normal priority and can later be promoted with custom rules.

## Output

- `data/highlander-events.json`: canonical discovered events
- `data/highlander-seen.json`: global event dedupe keys
- `data/highlander-state.json`: per-entity health and metrics
- `data/highlander-run-log.json`: recent poll history
- `outbox/second-brain/00-Inbox/Highlander Watch/`: qualifying research notes

Events include the Personal OS fields `entity`, `event_type`, `source_date`, `urgency`, `impact`, `actionability`, and `novelty`, plus matched entities, evidence, relevance score, and notification candidacy.

## Run locally

```bash
python watcher/highlander_watcher.py --dry-run --entity-limit 3
python watcher/highlander_watcher.py --once
python watcher/highlander_roster.py --dry-run
python watcher/highlander_roster.py
```

## Automation

`.github/workflows/highlander-watch.yml` polls twice daily. On Sundays it also refreshes the roster before committing state/output updates.

## Design rule

One canonical event, many matched entities. Broad watch, selective attention. Save research without automatically creating work.
