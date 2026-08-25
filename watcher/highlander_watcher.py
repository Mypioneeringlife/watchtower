#!/usr/bin/env python3
"""Entity-centered Highlander intelligence watcher.

Modelled after Creator Watch: the roster is primary, sources are discovery tools.
It broadly collects new activity about Highlander people/franchise entities,
deduplicates it, classifies events, scores usefulness, records per-entity health,
and only marks high-value items as notification candidates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTBOX = ROOT / "outbox" / "second-brain" / "00-Inbox" / "Highlander Watch"
ENTITIES_FILE = DATA / "highlander_entities.json"
EVENTS_FILE = DATA / "highlander-events.json"
SEEN_FILE = DATA / "highlander-seen.json"
STATE_FILE = DATA / "highlander-state.json"
RUN_LOG_FILE = DATA / "highlander-run-log.json"

EVENT_RULES: list[tuple[str, list[str], int]] = [
    ("death", ["died", "dies", "dead", "death", "obituary", "passed away", "passes away"], 34),
    ("health", ["collapsed", "hospital", "health", "illness", "injury", "surgery", "diagnosed", "medical"], 30),
    ("highlander_production", ["highlander", "reboot", "remake", "filming", "production", "casting", "release date"], 28),
    ("appearance", ["convention", "comic con", "comic-con", "steel city con", "panel", "appearance", "appearing"], 22),
    ("interview", ["interview", "podcast", "q&a", "q & a", "talks about", "reflects on"], 16),
    ("new_project", ["cast in", "joins cast", "new film", "new series", "announced", "starring", "directing"], 14),
    ("award", ["award", "honored", "honoured", "nomination", "nominated", "wins", "lifetime achievement"], 12),
    ("legal", ["lawsuit", "sues", "sued", "court", "arrest", "charged"], 18),
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Watchtower Highlander intelligence watcher/2.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


def google_news_url(query: str) -> str:
    params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return f"https://news.google.com/rss/search?{params}"


def parse_feed(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        source_el = item.find("source")
        items.append({
            "title": clean(item.findtext("title")),
            "url": clean(item.findtext("link")),
            "summary": clean(item.findtext("description")),
            "published": clean(item.findtext("pubDate")),
            "source": clean(source_el.text if source_el is not None else ""),
        })
    return items


def contains_any(text: str, terms: list[str]) -> list[str]:
    low = text.casefold()
    return [term for term in terms if term.casefold() in low]


def entity_matches(item: dict[str, str], entity: dict[str, Any]) -> bool:
    text = f"{item.get('title','')} {item.get('summary','')}".casefold()
    aliases = [entity.get("name", ""), *entity.get("aliases", [])]
    return any(alias and alias.casefold() in text for alias in aliases)


def classify_event(text: str) -> tuple[str, int, list[str]]:
    low = text.casefold()
    best_type = "other"
    best_bonus = 0
    hits: list[str] = []
    for event_type, terms, bonus in EVENT_RULES:
        matched = [term for term in terms if term.casefold() in low]
        if matched and bonus > best_bonus:
            best_type = event_type
            best_bonus = bonus
            hits = matched[:4]
    return best_type, best_bonus, hits


def score_item(item: dict[str, str], entity: dict[str, Any]) -> tuple[int, str, list[str]]:
    text = f"{item.get('title','')} {item.get('summary','')} {item.get('source','')}"
    event_type, event_bonus, event_hits = classify_event(text)
    score = 42
    why: list[str] = [f"matched entity: {entity['name']}"]

    if "highlander" in text.casefold():
        score += 24
        why.append("explicit Highlander reference")

    include_hits = contains_any(text, entity.get("include_any", []))
    if include_hits:
        score += min(18, 4 * len(include_hits))
        why.append("context: " + ", ".join(include_hits[:4]))

    exclude_hits = contains_any(text, entity.get("exclude_any", []))
    if exclude_hits:
        score -= 100
        why.append("excluded: " + ", ".join(exclude_hits[:4]))

    if event_bonus:
        score += event_bonus
        why.append(f"event: {event_type} ({', '.join(event_hits)})")

    priority = int(entity.get("priority", 50))
    score += max(0, min(10, (priority - 50) // 5))
    return max(0, min(100, score)), event_type, why


def event_id(item: dict[str, str]) -> str:
    """Canonical item identity, independent of how many roster entities match it."""
    stable = f"{item.get('url','')}|{item.get('title','')}"
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]


def thresholds(config: dict[str, Any]) -> tuple[int, int, int]:
    d = config.get("defaults", {})
    return int(d.get("inbox_threshold", 52)), int(d.get("save_threshold", 68)), int(d.get("alert_threshold", 82))


def urgency_for(score: int, event_type: str, alert_threshold: int) -> str:
    if event_type in {"death", "health"} and score >= alert_threshold:
        return "immediate"
    if score >= alert_threshold:
        return "high"
    if score >= 68:
        return "normal"
    return "low"


def impact_for(event_type: str) -> str:
    if event_type in {"death", "health", "highlander_production"}:
        return "high"
    if event_type in {"appearance", "interview", "new_project", "legal"}:
        return "medium"
    return "low"


def actionability_for(event_type: str) -> str:
    if event_type in {"highlander_production", "appearance", "interview", "health", "death"}:
        return "review for Corrupted Chronicle coverage"
    return "archive unless useful"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-") or "signal"


def write_note(event: dict[str, Any]) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    date = dt.date.today().isoformat()
    path = OUTBOX / f"{date}-{slugify(event['entity'])}-{slugify(event['event_type'])}-{event['id'][:8]}.md"
    why = "\n".join(f"- {x}" for x in event.get("evidence", [])) or "- Entity roster match"
    body = f'''---
title: "{event['title'].replace('"', "'")}"
type: "Highlander Watch"
status: "Inbox"
entity: "{event['entity'].replace('"', "'")}"
event_type: "{event['event_type']}"
source: "{event.get('source','').replace('"', "'")}"
source_url: "{event.get('source_url','')}"
source_date: "{event.get('source_date','')}"
relevance_score: {event['score']}
route: "Corrupted Chronicle research"
notify_candidate: {str(bool(event.get('notify_candidate'))).lower()}
tags:
  - highlander-watch
  - corrupted-chronicle
---

# {event['title']}

## What changed

{event.get('summary') or 'A new Highlander-related signal was discovered.'}

## Why it surfaced

{why}

## Recommended handling

{event['actionability']}.

## Source

{event.get('source_url','')}
'''
    path.write_text(body, encoding="utf-8")
    return path


def update_entity_state(state: dict[str, Any], entity: dict[str, Any], *, checked: int = 0,
                        new_events: int = 0, qualifying: int = 0, error: str | None = None) -> None:
    entities = state.setdefault("entities", {})
    e = entities.setdefault(entity["id"], {
        "name": entity["name"], "unique_events": 0, "qualifying_events": 0,
        "error_count": 0, "last_successful_poll": None, "last_qualifying_event": None,
    })
    e["name"] = entity["name"]
    e["items_checked_last_poll"] = checked
    if error:
        e["error_count"] = int(e.get("error_count", 0)) + 1
        e["last_error"] = error
    else:
        e["last_successful_poll"] = utc_now()
        e["last_error"] = None
    e["unique_events"] = int(e.get("unique_events", 0)) + new_events
    e["qualifying_events"] = int(e.get("qualifying_events", 0)) + qualifying
    if qualifying:
        e["last_qualifying_event"] = utc_now()


def run(*, dry_run: bool = False, entity_limit: int | None = None) -> int:
    started = utc_now()
    config = load_json(ENTITIES_FILE, {"defaults": {}, "entities": []})
    inbox_threshold, save_threshold, alert_threshold = thresholds(config)
    entities = [e for e in config.get("entities", []) if e.get("enabled", True)]
    if entity_limit:
        entities = entities[:entity_limit]

    seen = set(load_json(SEEN_FILE, []))
    events = load_json(EVENTS_FILE, [])
    state = load_json(STATE_FILE, {"version": "2.0.0", "entities": {}})
    totals = {"items_checked": 0, "unique_items_discovered": 0, "new_events": 0,
              "qualifying_events": 0, "notification_candidates": 0,
              "notes_written": 0, "errors": 0}

    discovered: dict[str, dict[str, str]] = {}
    entity_stats: dict[str, dict[str, Any]] = {
        e["id"]: {"checked": 0, "new": 0, "qualifying": 0, "errors": []} for e in entities
    }
    for entity in entities:
        stats = entity_stats[entity["id"]]
        queries = entity.get("search_queries") or [f'"{entity["name"]}" Highlander']
        for query in queries:
            try:
                items = parse_feed(fetch_text(google_news_url(query)))
            except Exception as exc:
                stats["errors"].append(f"{query}: {exc}")
                totals["errors"] += 1
                continue
            stats["checked"] += len(items)
            totals["items_checked"] += len(items)
            for item in items:
                discovered.setdefault(event_id(item), item)

    totals["unique_items_discovered"] = len(discovered)

    for eid, item in discovered.items():
        if eid in seen:
            continue
        matches: list[tuple[dict[str, Any], int, str, list[str]]] = []
        for entity in entities:
            if not entity_matches(item, entity):
                continue
            score, event_type, why = score_item(item, entity)
            if score >= inbox_threshold:
                matches.append((entity, score, event_type, why))
        if not matches:
            continue

        matches.sort(key=lambda x: (x[1], int(x[0].get("priority", 50))), reverse=True)
        primary, score, event_type, primary_why = matches[0]
        seen.add(eid)
        totals["new_events"] += 1
        qualifying = score >= save_threshold
        if qualifying:
            totals["qualifying_events"] += 1
        notify_candidate = score >= alert_threshold or (
            event_type in {"death", "health"} and score >= save_threshold
        )
        if notify_candidate:
            totals["notification_candidates"] += 1

        matched_entities = []
        evidence = list(primary_why)
        for entity, entity_score, entity_event_type, _why in matches:
            stats = entity_stats[entity["id"]]
            stats["new"] += 1
            if entity_score >= save_threshold:
                stats["qualifying"] += 1
            matched_entities.append({
                "id": entity["id"],
                "name": entity["name"],
                "kind": entity.get("kind", "unknown"),
                "roles": entity.get("roles", []),
                "franchise_titles": entity.get("franchise_titles", []),
                "score": entity_score,
                "event_type": entity_event_type,
            })
            if entity["id"] != primary["id"]:
                evidence.append(f"also matched: {entity['name']} ({entity_score})")

        event = {
            "id": eid,
            "entity_id": primary["id"],
            "entity": primary["name"],
            "entity_kind": primary.get("kind", "unknown"),
            "entities": matched_entities,
            "roles": primary.get("roles", []),
            "franchise_titles": primary.get("franchise_titles", []),
            "event_type": event_type,
            "source_date": item.get("published", ""),
            "captured": utc_now(),
            "urgency": urgency_for(score, event_type, alert_threshold),
            "impact": impact_for(event_type),
            "actionability": actionability_for(event_type),
            "novelty": "new",
            "source_url": item.get("url", ""),
            "source": item.get("source", "Google News"),
            "title": item.get("title", "Untitled signal"),
            "summary": item.get("summary", ""),
            "evidence": evidence,
            "score": score,
            "route": config.get("defaults", {}).get("route", "Corrupted Chronicle research"),
            "notify_candidate": notify_candidate,
            "status": "new",
        }
        events.append(event)
        if qualifying and not dry_run:
            write_note(event)
            totals["notes_written"] += 1

    for entity in entities:
        stats = entity_stats[entity["id"]]
        update_entity_state(
            state, entity, checked=stats["checked"], new_events=stats["new"],
            qualifying=stats["qualifying"],
            error="; ".join(stats["errors"]) if stats["errors"] else None,
        )

    finished = utc_now()
    run_entry = {
        "started_at": started,
        "finished_at": finished,
        "mode": "dry-run" if dry_run else "once",
        "entities_checked": len(entities),
        **totals,
    }
    if dry_run:
        print(json.dumps(run_entry, indent=2))
    else:
        save_json(EVENTS_FILE, events[-1000:])
        save_json(SEEN_FILE, sorted(seen))
        state["version"] = "2.0.0"
        state["last_run"] = finished
        state["last_summary"] = totals
        save_json(STATE_FILE, state)
        run_log = load_json(RUN_LOG_FILE, {"version": "2.0.0", "runs": []})
        runs = run_log.get("runs", [])
        runs.insert(0, run_entry)
        save_json(RUN_LOG_FILE, {"version": "2.0.0", "runs": runs[:60]})
    print(f"Highlander Watch: {totals['new_events']} new events, {totals['notification_candidates']} notification candidates")
    return totals["new_events"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run the Highlander entity roster once")
    parser.add_argument("--dry-run", action="store_true", help="Do not write state, events, or notes")
    parser.add_argument("--entity-limit", type=int, help="Only poll the first N enabled entities")
    args = parser.parse_args()
    run(dry_run=args.dry_run, entity_limit=args.entity_limit)


if __name__ == "__main__":
    main()
