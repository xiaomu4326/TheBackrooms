"""数据源公共基类：索引匹配、搜索、排序等与站点无关的逻辑。"""

from __future__ import annotations

import re
import threading
from datetime import datetime

from .http_client import HttpClient
from .models import IndexEntry, LevelInfo
from .parser import normalize_title, split_title


class LevelNotFound(Exception):
    """没有找到对应的层级页面。"""


def canonical_slugs(keys: set[str]) -> set[str]:
    """由查询词推出「官方页面」可能使用的 slug，例如 0 → level-0。"""
    out: set[str] = set()
    for key in keys:
        slug = re.sub(r"[“”\"'「」『』\s]+", "", key)
        slug = re.sub(r"^level(?=\d)", "level-", slug)
        out.add(slug)
        if not slug.startswith("level"):
            out.add("level-" + slug)
    return out


class BaseClient:
    """把 HTTP、解析、索引串起来，供界面层调用。子类负责具体站点。"""

    key = "base"
    label = "Base"

    def __init__(self, http: HttpClient | None = None) -> None:
        self.http = http or HttpClient()
        self._index: list[IndexEntry] | None = None
        self._index_time = 0.0
        self._lock = threading.Lock()
        self.last_error = ""

    # ---------------------------------------------------------------- 索引
    def list_levels(self, force: bool = False) -> list[IndexEntry]:  # pragma: no cover
        raise NotImplementedError

    def cached_index(self) -> list[IndexEntry]:
        with self._lock:
            return list(self._index or [])

    def _remember_index(self, entries: list[IndexEntry]) -> None:
        if not entries:
            return
        with self._lock:
            self._index = entries
            self._index_time = datetime.now().timestamp()

    # ---------------------------------------------------------------- 解析
    def resolve(self, query: str) -> tuple[str, IndexEntry | None]:
        """把输入解析成站点内的定位符（Wikidot 是 slug，Fandom 是标题）。"""
        text = (query or "").strip()
        if not text:
            raise LevelNotFound("请输入层级编号，例如 0、1、0.1 或 C-156")

        entries = self.cached_index()
        if entries:
            entry = self._match(entries, text)
            if entry is not None:
                return entry.slug, entry

        candidates = self._locator_guesses(text)
        if not candidates:
            raise LevelNotFound(f"无法解析「{text}」")
        return candidates[0], None

    def _locator_guesses(self, text: str) -> list[str]:
        return [text]

    @staticmethod
    def _match(entries: list[IndexEntry], text: str) -> IndexEntry | None:
        key = normalize_title(text)
        keys = {key}
        if re.fullmatch(r"-?\d+(?:\.\d+)?", key):
            keys.add("level" + key)
        canonical = canonical_slugs(keys)

        best: tuple[int, int, int] | None = None
        best_entry: IndexEntry | None = None
        for entry in entries:
            label, alias = split_title(entry.title)
            base = normalize_title(label)
            alias_key = normalize_title(alias)
            if base in keys or alias_key in keys:
                score = 0
            elif any(base.startswith(k) for k in keys):
                score = 1
            elif any(k and k in base for k in keys):
                score = 2
            else:
                continue
            slug = entry.slug.lower()
            if slug in canonical:
                preference = 0
            elif ":" not in slug:
                preference = 1
            else:
                preference = 2
            rank = (score, preference, len(entry.title))
            if best is None or rank < best:
                best = rank
                best_entry = entry
        return best_entry

    # ---------------------------------------------------------------- 抓取
    def fetch_level(self, query: str, force: bool = False) -> LevelInfo:
        locator, entry = self.resolve(query)
        return self.fetch_page(locator, query=query, force=force, entry=entry)

    def fetch_page(
        self,
        locator: str,
        query: str = "",
        force: bool = False,
        entry: IndexEntry | None = None,
    ) -> LevelInfo:  # pragma: no cover
        raise NotImplementedError

    # ---------------------------------------------------------------- 其他
    @staticmethod
    def search_entries(entries: list[IndexEntry], keyword: str, limit: int = 200) -> list[IndexEntry]:
        keyword = normalize_title(keyword)
        if not keyword:
            return entries[:limit]
        hits = [e for e in entries if keyword in normalize_title(e.title) or keyword in e.slug.lower()]
        return hits[:limit]

    @staticmethod
    def sort_entries(entries: list[IndexEntry]) -> list[IndexEntry]:
        """Level 开头的正式层级排在前面，其余按标题排序。"""

        def sort_key(entry: IndexEntry):
            label, _ = split_title(entry.title)
            plain_number = re.fullmatch(r"(?i)level\s*(\d+(?:\.\d+)?)", label.strip())
            if plain_number:
                return (0, float(plain_number.group(1)), entry.title)
            return (1, 0.0, entry.title)

        return sorted(entries, key=sort_key)
