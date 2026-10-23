# -*- coding: utf-8 -*-
"""Podcast search and RSS parsing tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.podcast import (  # noqa: E402
    parse_duration, parse_feed, parse_podcast_search,
)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Test Podcast</title>
    <itunes:image href="https://example.com/cover.jpg"/>
    <item>
      <title>Episode One</title>
      <pubDate>Fri, 18 Oct 2024 10:00:00 GMT</pubDate>
      <itunes:duration>01:02:03</itunes:duration>
      <enclosure url="https://example.com/one.mp3" type="audio/mpeg"/>
    </item>
    <item>
      <title>Episode Two</title>
      <itunes:duration>90</itunes:duration>
      <enclosure url="https://example.com/two.mp3" type="audio/mpeg"/>
    </item>
    <item>
      <title>No audio</title>
    </item>
  </channel>
</rss>
"""


class PodcastTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(parse_duration("01:02:03"), 3723)
        self.assertEqual(parse_duration("90"), 90)
        self.assertEqual(parse_duration("bad"), 0)

    def test_search_parser(self):
        podcasts = parse_podcast_search([
            {"collectionName": "One", "feedUrl": "https://example.com/feed.xml",
             "artistName": "Host", "primaryGenreName": "Tech", "trackCount": 12},
            {"collectionName": "Duplicate", "feedUrl": "https://example.com/feed.xml"},
            {"collectionName": "Bad", "feedUrl": "file:///tmp/feed.xml"},
        ])
        self.assertEqual(len(podcasts), 1)
        self.assertEqual(podcasts[0].name, "One")
        self.assertEqual(podcasts[0].episode_count, 12)

    def test_feed_parser(self):
        name, episodes = parse_feed(RSS)
        self.assertEqual(name, "Test Podcast")
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].title, "Episode One")
        self.assertEqual(episodes[0].duration, 3723)
        self.assertEqual(episodes[0].published, "2024-10-18")
        self.assertTrue(episodes[0].url.endswith("one.mp3"))
        self.assertEqual(episodes[1].duration, 90)


if __name__ == "__main__":
    unittest.main(verbosity=2)
