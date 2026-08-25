# Highlander Watch

Highlander Watch is an entity-centered intelligence module inside Watchtower. It follows the Creator Watch model: the roster is primary; search/feed sources are discovery tools.

## What it tracks

- Highlander franchise and reboot news
- Cast, creators, directors, writers, producers, composers, cinematographers, editors, and voice actors connected to Highlander
- Health and death events
- Convention and public appearances
- Interviews and podcasts
- New projects and casting
- Awards and legal events
- Production and release changes

## Creator-Watcher behavior

Collection is broad. Attention is selective.

A discovered article is canonicalized once even if it mentions several Highlander people. The event keeps all matched entities, chooses the strongest match as primary, and only becomes a notification candidate when its freshness, event type, and relevance score warrant attention.

A new entity is never allowed to dump its historical search backlog into the alert stream. Its first successful poll establishes a silent baseline. Only later discoveries can become new events.

Historical items are still useful for research, but old rediscoveries do not masquerade as breaking news.

## Roster tiers

`data/highlander_entities.json` contains manually curated profiles plus the roster-expansion policy.

- **Core**: franchise, lead cast, important creators, reboot principals, and other high-priority people. Checked four times daily.
- **Extended**: automatically discovered cast and crew plus lower-priority profiles. Checked once daily.

Manual profiles are never removed by automatic discovery.

`watcher/highlander_roster.py` expands the roster from Wikidata relationships for the Highlander film series, television series, universe, and related works. Automatically discovered people enter at extended priority and baseline silently on their first poll.

Wikidata is a broad discovery source, not a guarantee that every uncredited or poorly documented crew member in franchise history is present. More complete production-credit sources can be added later without changing the watcher architecture.

## Freshness and noise rules

Default thresholds:

- Inbox candidate: 52
- Save/research note: 72
- Alert candidate: 88
- Alert freshness window: 30 days
- Research-note freshness window: 60 days

Health/death events for high-priority Highlander people receive special handling, but still must be new relative to the established baseline.

## Output

- `data/highlander-events.json`: canonical discovered events
- `data/highlander-seen.json`: global event dedupe keys
- `data/highlander-state.json`: per-entity health, initialization state, and metrics
- `data/highlander-run-log.json`: recent poll history
- `outbox/second-brain/00-Inbox/Highlander Watch/`: qualifying research notes

Events include the Personal OS fields `entity`, `event_type`, `source_date`, `urgency`, `impact`, `actionability`, and `novelty`, plus matched entities, evidence, relevance score, and notification candidacy.

## Run locally

```bash
python -m unittest watcher.tests.test_highlander_watch
python watcher/highlander_watcher.py --dry-run --entity-limit 3
python watcher/highlander_watcher.py --once --scope core
python watcher/highlander_watcher.py --once --scope all
python watcher/highlander_roster.py --dry-run
python watcher/highlander_roster.py
```

## Automation

`.github/workflows/highlander-watch.yml` runs core polling four times daily and the full roster once daily. The automatic roster expansion refreshes weekly on the Sunday full-roster run. A manual workflow run refreshes the roster and then scans all enabled entities.

## Design rule

One canonical event, many matched entities. Broad watch, selective attention. Save research without automatically creating work.
