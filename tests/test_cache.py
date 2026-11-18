import json
import tempfile
import unittest
from pathlib import Path

from backrooms import config, groups
from backrooms.base import BaseClient
from backrooms.http_client import HttpClient
from backrooms.models import IndexEntry
from backrooms.service import WikidotClient


class CachePersistenceTest(unittest.TestCase):
    def test_default_ttl_never_expires(self) -> None:
        self.assertEqual(config.CACHE_TTL, -1)
        self.assertEqual(config.INDEX_TTL, -1)

    def test_negative_ttl_reads_old_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = HttpClient(cache_dir=Path(tmp))
            url = "https://example.invalid/old"
            client._write_cache(url, "cached body")
            path = client._cache_path(url)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["ts"] = 0
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            self.assertEqual(client._read_cache(url, -1), "cached body")
            self.assertIsNone(client._read_cache(url, 1))

    def test_wikidot_cached_page_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = WikidotClient(HttpClient(cache_dir=Path(tmp)))
            entry = IndexEntry("level-0", "Level 0")
            self.assertFalse(client.is_page_cached(entry))
            client.http._write_cache(f"{config.BASE_URL}/{entry.slug}", "page")
            self.assertTrue(client.is_page_cached(entry))

    def test_cache_tree_keeps_home_grouping(self) -> None:
        entries = [
            IndexEntry("level-0", "Level 0"),
            IndexEntry("level-0-1", "Level 0.1"),
            IndexEntry("level-c-156", "Level C-156"),
        ]
        tree = groups.cache_tree(entries, "wikidot", BaseClient.sort_entries)
        labels = [group["label"] for group in tree]
        self.assertIn("普通层级", labels)
        self.assertIn("C层级", labels)
        normal = next(group for group in tree if group["key"] == "normal")
        self.assertEqual(normal["sections"][0]["entries"][0]["depth"], 0)
        self.assertEqual(normal["sections"][0]["entries"][1]["depth"], 1)
