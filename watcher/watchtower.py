#!/usr/bin/env python3
"""Watchtower RSS/Atom watcher.

This is a focused watcher, not a broad crawler. It reads configured RSS/Atom
sources, scores matching items against topic rules, prevents duplicates, writes
Markdown notes into the second-brain outbox, and records a run log so the phone
app can show whether the watcher is actually working.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTBOX = ROOT / "outbox" / "second-brain"
SEEN = DATA / "seen.json"
SIGNALS = DATA / "signals.json"
RUN_LOG = DATA / "run-log.json"


def utc_now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_text(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        req = urllib.request.Request(url, headers={"User-Agent": "Watchtower personal RSS watcher/1.5"})
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.read().decode("utf-8", errors="replace")
    return (ROOT / url).read_text(encoding="utf-8")


def clean(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_feed(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        items.append({
            "title": clean(item.findtext("title")),
            "url": clean(item.findtext("link")),
            "summary": clean(item.findtext("description")),
            "published": clean(item.findtext("pubDate")),
        })
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        link = ""
        link_el = entry.find("atom:link", ns)
        if link_el is not None:
            link = link_el.attrib.get("href", "")
        items.append({
            "title": clean(entry.findtext("atom:title", default="", namespaces=ns)),
            "url": clean(link),
            "summary": clean(entry.findtext("atom:summary", default="", namespaces=ns)),
            "published": clean(entry.findtext("atom:updated", default="", namespaces=ns)),
        })
    return items


def contains_any(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [term for term in terms if term.lower() in low]


def score_item(item: dict[str, str], topic: dict[str, Any], source: dict[str, Any]) -> tuple[int, list[str]]:
    text = f"{item.get('title','')} {item.get('summary','')} {item.get('url','')}"
    required = contains_any(text, topic.get("required_any", []))
    include = contains_any(text, topic.get("include_any", []))
    excluded = contains_any(text, topic.get("exclude", []))
    why: list[str] = []
    score = 0
    if required:
        score += 50 + min(20, 8 * len(required))
        why.append("required: " + ", ".join(required[:4]))
    if include:
        score += min(20, 5 * len(include))
        why.append("context: " + ", ".join(include[:4]))
    if source.get("reliability") == "official":
        score += 12
        why.append("official source")
    elif source.get("reliability") == "trusted":
        score += 8
        why.append("trusted source")
    if excluded:
        score -= 100
        why.append("excluded: " + ", ".join(excluded[:4]))
    return max(0, min(100, score)), why


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "signal"


def signal_id(url: str, title: str) -> str:
    return hashlib.sha256((url or title).encode("utf-8")).hexdigest()[:16]


def write_note(signal: dict[str, Any]) -> Path:
    today = dt.date.today().isoformat()
    folder = OUTBOX / signal["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{today}-{slugify(signal['title'])[:72]}.md"
    body = f"""---
title: "{signal['title'].replace('"', "'")}"
type: "Web Watch"
status: "Inbox"
topic: "{signal['topic']}"
source: "{signal['source']}"
url: "{signal['url']}"
captured: "{today}"
priority: "{signal['priority']}"
relevance_score: {signal['score']}
tags:
  - web-watch
  - {slugify(signal['topic'])}
---

# {signal['title']}

## Summary

{signal.get('summary') or 'Captured by Watchtower. Review before promoting this into permanent research.'}

## Why this matched

"""
    for reason in signal.get("why", []):
        body += f"- {reason}\n"
    body += f"""
## Possible use

Research lead, content idea, or second-brain reference note.

## Link

{signal['url']}

## Processing log

- [ ] Reviewed
- [ ] Promoted to permanent note
- [ ] Used in content
- [ ] Discarded
"""
    path.write_text(body, encoding="utf-8")
    return path


def append_run_log(entry: dict[str, Any]) -> None:
    existing = load_json(RUN_LOG, {"version": "1.5.0", "runs": []})
    runs = existing.get("runs", [])
    runs.insert(0, entry)
    save_json(RUN_LOG, {"version": "1.5.0", "runs": runs[:30]})


def run(sample: str | None = None, dry_run: bool = False) -> int:
    started_at = utc_now()
    watchlists = load_json(DATA / "watchlists.json", {"topics": []})
    sources = load_json(DATA / "sources.json", {"sources": []})
    topic_map = {t["id"]: t for t in watchlists.get("topics", [])}
    seen = set(load_json(SEEN, []))
    signals = load_json(SIGNALS, [])
    new_count = 0
    notes_written = 0
    checked_items = 0
    duplicates = 0
    below_threshold = 0
    source_results: list[dict[str, Any]] = []

    configured_sources = sources.get("sources", [])
    active_sources = configured_sources
    if sample:
        active_sources = [{"id": "sample", "name": "Sample Feed", "url": sample, "topics": list(topic_map), "reliability": "test", "enabled": True}]

    for source in active_sources:
        if not source.get("enabled") and not sample:
            continue
        source_result = {
            "id": source.get("id"),
            "name": source.get("name"),
            "status": "ok",
            "items_checked": 0,
            "matches": 0,
            "notes_written": 0,
            "error": None,
        }
        try:
            items = parse_feed(fetch_text(source["url"]))
            source_result["items_checked"] = len(items)
            checked_items += len(items)
        except Exception as exc:
            source_result["status"] = "error"
            source_result["error"] = str(exc)
            source_results.append(source_result)
            print(f"source failed: {source.get('name')}: {exc}", file=sys.stderr)
            continue
        for item in items:
            sid = signal_id(item.get("url", ""), item.get("title", ""))
            if sid in seen:
                duplicates += 1
                continue
            matched_any_topic = False
            for topic_id in source.get("topics", []):
                topic = topic_map.get(topic_id)
                if not topic:
                    continue
                score, why = score_item(item, topic, source)
                thresholds = topic.get("thresholds", {"inbox": 50, "save": 70, "alert": 90})
                if score < thresholds.get("inbox", 50):
                    continue
                matched_any_topic = True
                signal = {
                    "id": sid,
                    "title": item.get("title") or "Untitled signal",
                    "url": item.get("url") or "",
                    "summary": item.get("summary") or "",
                    "published": item.get("published") or "",
                    "captured": utc_now(),
                    "topic": topic.get("name"),
                    "folder": topic.get("folder"),
                    "priority": topic.get("priority"),
                    "source": source.get("name"),
                    "score": score,
                    "why": why,
                    "status": "new",
                }
                signals.append(signal)
                seen.add(sid)
                new_count += 1
                source_result["matches"] += 1
                if score >= thresholds.get("save", 70) and not dry_run:
                    write_note(signal)
                    notes_written += 1
                    source_result["notes_written"] += 1
            if not matched_any_topic:
                below_threshold += 1
        source_results.append(source_result)

    finished_at = utc_now()
    errors = sum(1 for result in source_results if result.get("status") == "error")
    run_entry = {
        "started_at": started_at,
        "finished_at": finished_at,
        "mode": "sample" if sample else "once",
        "dry_run": dry_run,
        "configured_sources": len(configured_sources),
        "enabled_sources": len([s for s in configured_sources if s.get("enabled")]) if not sample else 1,
        "sources_checked": len(source_results),
        "source_errors": errors,
        "items_checked": checked_items,
        "duplicates_skipped": duplicates,
        "below_threshold": below_threshold,
        "new_signals": new_count,
        "notes_written": notes_written,
        "sources": source_results,
    }

    if not dry_run:
        save_json(SIGNALS, signals[-250:])
        save_json(SEEN, sorted(seen))
        save_json(DATA / "watcher-meta.json", {
            "last_run": finished_at,
            "version": "1.5.0",
            "last_summary": {
                "new_signals": new_count,
                "items_checked": checked_items,
                "source_errors": errors,
                "notes_written": notes_written,
            },
        })
        append_run_log(run_entry)
    else:
        print(json.dumps(run_entry, indent=2))
    print(f"new signals: {new_count}")
    return new_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once against enabled sources")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output files")
    parser.add_argument("--sample", help="Run against a sample XML feed path")
    args = parser.parse_args()
    run(sample=args.sample, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
