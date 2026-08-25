#!/usr/bin/env python3
"""Expand the Highlander Watch entity roster from Wikidata.

The curated roster remains authoritative. Automatic discovery uses Wikidata's
normal entity API instead of the SPARQL service, follows Highlander work/season/
episode relationships where they are explicitly represented, and merges named
human cast/crew into the extended watch tier.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data" / "highlander_entities.json"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

ROLE_PROPERTIES = {
    "P161": "cast member",
    "P57": "director",
    "P58": "screenwriter",
    "P162": "producer",
    "P86": "composer",
    "P344": "director of photography",
    "P1040": "film editor",
    "P725": "voice actor",
    "P170": "creator",
}

# Stable franchise/work roots. Additional titles below are resolved dynamically.
BASE_WORK_IDS = {
    "Q1990805",   # Highlander franchise
    "Q16864738",  # Highlander film series
    "Q156539",    # Highlander (1986)
    "Q771408",    # Highlander II
    "Q994209",    # Highlander III
    "Q1617964",   # Highlander: Endgame
    "Q2029663",   # Highlander: The Source
    "Q1520493",   # Highlander: The Series
    "Q1613495",   # Highlander: The Search for Vengeance
}
SEARCH_WORK_TITLES = [
    "Highlander: The Raven",
    "Highlander: The Animated Series",
]
PART_PROPERTY = "P527"  # has part(s)
HUMAN_QID = "Q5"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")
    return value or "highlander_person"


def chunks(values: Iterable[str], size: int = 40) -> Iterable[list[str]]:
    chunk: list[str] = []
    for value in values:
        chunk.append(value)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def api_get(params: dict[str, str], timeout: int = 20) -> dict[str, Any]:
    query = dict(params)
    query.setdefault("format", "json")
    query.setdefault("formatversion", "2")
    url = WIKIDATA_API + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Watchtower Highlander roster/2.1.1"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def entity_label(entity: dict[str, Any], fallback: str) -> str:
    labels = entity.get("labels", {})
    label = labels.get("en", {}) if isinstance(labels, dict) else {}
    return label.get("value") or fallback


def claim_entity_ids(entity: dict[str, Any], property_id: str) -> list[str]:
    out: list[str] = []
    for claim in entity.get("claims", {}).get(property_id, []):
        mainsnak = claim.get("mainsnak", {})
        value = mainsnak.get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            out.append(value["id"])
    return out


def fetch_entities(ids: Iterable[str], *, props: str = "claims|labels") -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    unique = sorted(set(ids))
    for batch in chunks(unique):
        payload = api_get({
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": props,
            "languages": "en",
        })
        for qid, entity in payload.get("entities", {}).items():
            if not entity.get("missing"):
                result[qid] = entity
    return result


def resolve_title(title: str) -> str | None:
    payload = api_get({
        "action": "wbsearchentities",
        "search": title,
        "language": "en",
        "type": "item",
        "limit": "8",
    })
    candidates = payload.get("search", [])
    exact = [c for c in candidates if c.get("label", "").casefold() == title.casefold()]
    chosen = exact[0] if exact else (candidates[0] if candidates else None)
    return chosen.get("id") if chosen else None


def discover_work_entities(max_depth: int = 2) -> dict[str, dict[str, Any]]:
    work_ids = set(BASE_WORK_IDS)
    for title in SEARCH_WORK_TITLES:
        try:
            resolved = resolve_title(title)
        except Exception:
            resolved = None
        if resolved:
            work_ids.add(resolved)

    discovered: dict[str, dict[str, Any]] = {}
    frontier = set(work_ids)
    for _depth in range(max_depth + 1):
        if not frontier:
            break
        fetched = fetch_entities(frontier)
        discovered.update(fetched)
        next_frontier: set[str] = set()
        for entity in fetched.values():
            next_frontier.update(claim_entity_ids(entity, PART_PROPERTY))
        next_frontier -= set(discovered)
        frontier = next_frontier
    return discovered


def is_human(entity: dict[str, Any]) -> bool:
    return HUMAN_QID in claim_entity_ids(entity, "P31")


def rows_from_works(works: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    credits: list[tuple[str, str, str]] = []
    people: set[str] = set()
    for work_id, entity in works.items():
        for property_id in ROLE_PROPERTIES:
            for person_id in claim_entity_ids(entity, property_id):
                credits.append((work_id, property_id, person_id))
                people.add(person_id)

    person_entities = fetch_entities(people) if people else {}
    rows: list[dict[str, str]] = []
    for work_id, property_id, person_id in credits:
        person = person_entities.get(person_id)
        if not person or not is_human(person):
            continue
        work = works.get(work_id, {})
        rows.append({
            "work": entity_label(work, work_id),
            "person": entity_label(person, person_id),
            "person_url": f"https://www.wikidata.org/entity/{person_id}",
            "property": property_id,
        })
    return rows


def discover_rows() -> tuple[list[dict[str, str]], int]:
    works = discover_work_entities(max_depth=2)
    return rows_from_works(works), len(works)


def merge(rows: list[dict[str, str]], roster: dict[str, Any]) -> tuple[dict[str, Any], int]:
    entities = roster.setdefault("entities", [])
    by_name = {e.get("name", "").casefold(): e for e in entities}
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row.get("person", "").strip()
        if not name:
            continue
        g = grouped.setdefault(name, {"roles": set(), "works": set(), "wikidata_url": row.get("person_url", "")})
        g["roles"].add(ROLE_PROPERTIES.get(row.get("property", ""), row.get("property", "production credit")))
        g["works"].add(row.get("work", "Highlander"))

    added = 0
    for name, info in sorted(grouped.items()):
        existing = by_name.get(name.casefold())
        if existing:
            existing["roles"] = sorted(set(existing.get("roles", [])) | set(info["roles"]))
            existing["franchise_titles"] = sorted(set(existing.get("franchise_titles", [])) | set(info["works"]))
            existing.setdefault("wikidata_url", info["wikidata_url"])
            continue
        base_id = slugify(name)
        candidate = base_id
        used = {e.get("id") for e in entities}
        n = 2
        while candidate in used:
            candidate = f"{base_id}_{n}"
            n += 1
        entities.append({
            "id": candidate,
            "name": name,
            "kind": "person",
            "priority": 60,
            "poll_tier": "extended",
            "aliases": [name],
            "search_queries": [f'\"{name}\"'],
            "include_any": ["Highlander", *sorted(info["roles"])],
            "exclude_any": [],
            "roles": sorted(info["roles"]),
            "franchise_titles": sorted(info["works"]),
            "wikidata_url": info["wikidata_url"],
            "discovered_by": "Wikidata entity API roster expansion",
            "enabled": True,
        })
        by_name[name.casefold()] = entities[-1]
        added += 1
    entities.sort(key=lambda e: (-int(e.get("priority", 50)), e.get("name", "").casefold()))
    return roster, added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    roster = load_json(ROSTER)
    rows, works = discover_rows()
    roster, added = merge(rows, roster)
    print(f"Wikidata works inspected: {works}; credit rows: {len(rows)}; new roster entities: {added}")
    if not args.dry_run:
        save_json(ROSTER, roster)


if __name__ == "__main__":
    main()
