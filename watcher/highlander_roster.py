#!/usr/bin/env python3
"""Expand the Highlander Watch entity roster from Wikidata.

This keeps the manually curated roster authoritative while discovering additional
cast/crew linked to the franchise roots. It intentionally adds only people with
recognized production roles and never removes existing profiles.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data" / "highlander_entities.json"
SPARQL = "https://query.wikidata.org/sparql"
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")
    return value or "highlander_person"


def run_query(root_ids: list[str]) -> list[dict[str, str]]:
    roots = " ".join(f"wd:{qid}" for qid in root_ids)
    props = " ".join(f"wdt:{pid}" for pid in ROLE_PROPERTIES)
    query = f"""
SELECT DISTINCT ?work ?workLabel ?person ?personLabel ?prop WHERE {{
  VALUES ?root {{ {roots} }}
  VALUES ?prop {{ {props} }}
  {{ BIND(?root AS ?work) }}
  UNION {{ ?work (wdt:P179|wdt:P361)+ ?root. }}
  UNION {{ ?work wdt:P1434 wd:Q1032900. }}
  ?work ?prop ?person.
  ?person wdt:P31 wd:Q5.
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language \"en\". }}
}}
"""
    url = SPARQL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": "Watchtower Highlander roster/2.0"})
    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.loads(res.read().decode("utf-8"))
    out: list[dict[str, str]] = []
    for row in data.get("results", {}).get("bindings", []):
        prop_url = row.get("prop", {}).get("value", "")
        out.append({
            "work": row.get("workLabel", {}).get("value", "Highlander"),
            "person": row.get("personLabel", {}).get("value", ""),
            "person_url": row.get("person", {}).get("value", ""),
            "property": prop_url.rsplit("/", 1)[-1],
        })
    return out


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
            "aliases": [name],
            "search_queries": [f'\"{name}\"'],
            "include_any": ["Highlander", *sorted(info["roles"])],
            "exclude_any": [],
            "roles": sorted(info["roles"]),
            "franchise_titles": sorted(info["works"]),
            "wikidata_url": info["wikidata_url"],
            "discovered_by": "Wikidata roster expansion",
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
    roots = [r["wikidata_id"] for r in roster.get("roster_expansion", {}).get("roots", [])]
    rows = run_query(roots)
    roster, added = merge(rows, roster)
    print(f"Wikidata credits returned: {len(rows)}; new roster entities: {added}")
    if not args.dry_run:
        save_json(ROSTER, roster)


if __name__ == "__main__":
    main()
