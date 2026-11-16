import json
import tempfile
import unittest
from pathlib import Path

from backrooms import config
from backrooms.http_client import HttpClient


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
