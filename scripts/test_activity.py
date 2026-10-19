import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import activity


class ActivityTests(unittest.TestCase):
    def event(self, date="2026-10-19T10:00:00Z", **changes):
        return dict(public=True, type="PushEvent", actor={"login": "ss-sevesh"},
                    repo={"name": "ss-sevesh/localvoice"}, payload={}, created_at=date, **changes)

    def test_filter_and_order(self):
        recent = self.event()
        old = self.event("2026-10-18T10:00:00Z")
        hidden = dict(recent, public=False)
        bot = dict(recent, actor={"login": "github-actions[bot]"})
        output = dict(recent, repo={"name": "ss-sevesh/ss-sevesh"}, payload={"ref": "refs/heads/output"})
        star = dict(recent, type="WatchEvent")
        invalid = dict(recent, repo={"name": '<script>&"'})
        self.assertEqual(activity.select_events([old, hidden, bot, output, star, invalid, recent]), [recent, old])

    def test_calendar_levels_and_dates(self):
        days = [dict(date=f"2026-10-{18+i}", contributionCount=i, contributionLevel=level)
                for i, level in enumerate(activity.LEVELS)]
        doc = activity.calendar_svg(dict(totalContributions=10, weeks=[dict(contributionDays=days)]), "now & later")
        root = ET.fromstring(doc)
        self.assertIn("now &amp; later", doc)
        self.assertTrue(all(color in doc for color in activity.COLORS))
        self.assertEqual(len(root.findall('.//{*}rect/{*}title')), 5)
        self.assertIn('y="98"', doc)

    def test_empty_unicode_and_xml(self):
        doc, links = activity.activity_svg([], "हिंदी & <test>")
        ET.fromstring(doc)
        self.assertIn("No recent", links)
        self.assertIn("&lt;test&gt;", doc)

    def test_failed_fetch_does_not_write(self):
        with patch.object(activity, "api", side_effect=RuntimeError("unavailable")), patch.object(Path, "write_text") as write:
            with self.assertRaises(RuntimeError):
                activity.generate()
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
