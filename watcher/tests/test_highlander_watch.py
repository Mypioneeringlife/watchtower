import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import watcher.highlander_watcher as hw
from watcher.highlander_watcher import entity_matches, event_id, parse_feed, score_item
from watcher.highlander_roster import merge


class HighlanderWatchTests(unittest.TestCase):
    def setUp(self):
        self.lambert = {
            "id": "christopher_lambert",
            "name": "Christopher Lambert",
            "kind": "person",
            "priority": 100,
            "poll_tier": "core",
            "aliases": ["Christopher Lambert", "Christophe Lambert"],
            "include_any": ["Highlander", "Connor MacLeod", "convention"],
            "exclude_any": [],
            "roles": ["actor", "Connor MacLeod"],
            "franchise_titles": ["Highlander"],
        }

    def test_feed_parsing_and_health_scoring(self):
        xml = """<rss><channel><item>
        <title>Christopher Lambert collapses after Highlander convention panel</title>
        <link>https://example.com/story</link>
        <description>The Highlander actor received medical attention.</description>
        <pubDate>Tue, 25 Aug 2026 12:00:00 GMT</pubDate>
        <source>Example News</source>
        </item></channel></rss>"""
        item = parse_feed(xml)[0]
        self.assertTrue(entity_matches(item, self.lambert))
        score, event_type, why = score_item(item, self.lambert)
        self.assertEqual(event_type, "health")
        self.assertGreaterEqual(score, 82)
        self.assertTrue(any("Highlander" in reason for reason in why))

    def test_event_identity_is_global_not_entity_specific(self):
        item = {"title": "One article", "url": "https://example.com/a"}
        self.assertEqual(event_id(item), event_id(dict(item)))

    def test_roster_merge_preserves_curated_profile_and_extends_new_people(self):
        roster = {"entities": [dict(self.lambert)]}
        rows = [
            {
                "work": "Highlander",
                "person": "Christopher Lambert",
                "person_url": "https://www.wikidata.org/entity/Q1",
                "property": "P161",
            },
            {
                "work": "Highlander: The Series",
                "person": "New Highlander Person",
                "person_url": "https://www.wikidata.org/entity/Q2",
                "property": "P58",
            },
        ]
        merged, added = merge(rows, roster)
        self.assertEqual(added, 1)
        lambert = next(e for e in merged["entities"] if e["name"] == "Christopher Lambert")
        self.assertEqual(lambert["priority"], 100)
        new_person = next(e for e in merged["entities"] if e["name"] == "New Highlander Person")
        self.assertIn("screenwriter", new_person["roles"])
        self.assertEqual(new_person["priority"], 60)
        self.assertEqual(new_person["poll_tier"], "extended")

    def test_first_poll_baselines_and_prunes_old_bootstrap_output(self):
        xml = """<rss><channel><item>
        <title>Christopher Lambert discusses Highlander in new interview</title>
        <link>https://example.com/lambert-interview</link>
        <description>Christopher Lambert reflects on Highlander and Connor MacLeod.</description>
        <pubDate>Tue, 25 Aug 2026 12:00:00 GMT</pubDate>
        <source>Example News</source>
        </item></channel></rss>"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            outbox = root / "outbox"
            data.mkdir()
            outbox.mkdir()
            entities_file = data / "entities.json"
            events_file = data / "events.json"
            seen_file = data / "seen.json"
            state_file = data / "state.json"
            run_log_file = data / "run-log.json"
            entities_file.write_text(json.dumps({
                "version": "2.1.0",
                "defaults": {
                    "route": "Corrupted Chronicle research",
                    "inbox_threshold": 52,
                    "save_threshold": 72,
                    "alert_threshold": 88,
                    "max_alert_age_days": 30,
                    "max_save_age_days": 60,
                    "bootstrap_generation": 2,
                    "core_priority_minimum": 80
                },
                "entities": [self.lambert]
            }), encoding="utf-8")
            events_file.write_text("[]", encoding="utf-8")
            seen_file.write_text("[]", encoding="utf-8")
            state_file.write_text(json.dumps({"bootstrap_generation": 0, "entities": {}}), encoding="utf-8")
            run_log_file.write_text(json.dumps({"version": "2.0.0", "runs": [{"old": True}]}), encoding="utf-8")
            bad_note = outbox / "bad-old-note.md"
            bad_note.write_text("bootstrap noise", encoding="utf-8")

            with patch.multiple(
                hw,
                ENTITIES_FILE=entities_file,
                EVENTS_FILE=events_file,
                SEEN_FILE=seen_file,
                STATE_FILE=state_file,
                RUN_LOG_FILE=run_log_file,
                OUTBOX=outbox,
            ), patch.object(hw, "fetch_text", return_value=xml):
                count = hw.run(scope="core")

            self.assertEqual(count, 0)
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(state["bootstrap_generation"], 2)
            self.assertEqual(state["last_summary"]["baseline_items"], 1)
            self.assertEqual(state["last_summary"]["notification_candidates"], 0)
            self.assertTrue(state["entities"]["christopher_lambert"]["initialized"])
            self.assertFalse(bad_note.exists())
            self.assertEqual(json.loads(events_file.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
