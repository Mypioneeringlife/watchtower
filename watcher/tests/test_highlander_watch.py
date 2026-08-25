import unittest

from watcher.highlander_watcher import (
    entity_matches,
    event_id,
    parse_feed,
    score_item,
)
from watcher.highlander_roster import merge


class HighlanderWatchTests(unittest.TestCase):
    def setUp(self):
        self.lambert = {
            "id": "christopher_lambert",
            "name": "Christopher Lambert",
            "kind": "person",
            "priority": 100,
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
        first = event_id(item)
        second = event_id(dict(item))
        self.assertEqual(first, second)

    def test_roster_merge_preserves_curated_profile(self):
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


if __name__ == "__main__":
    unittest.main()
