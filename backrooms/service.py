"""Wikidot 数据源与数据源工厂。"""

from __future__ import annotations

import re
from urllib.parse import quote

from . import config
from .base import BaseClient, LevelNotFound
from .http_client import FetchError, HttpClient
from .models import IndexEntry, LevelInfo
from .parser import parse_level_page, parse_page_link_slugs, parse_tag_index, split_title

__all__ = ["WikidotClient", "create_client", "LevelNotFound", "BaseClient"]


class WikidotClient(BaseClient):
    """后室中文维基（Wikidot）。"""

    key = "wikidot"
    label = "Wikidot"
    home_url = config.BASE_URL

    # ---------------------------------------------------------------- 索引
    def list_levels(self, force: bool = False) -> list[IndexEntry]:
        """获取全部层级页面（来自「层级」标签索引，失败时返回空列表）。"""
        with self._lock:
            if self._index is not None and not force:
                return self._index
        try:
            html, _ = self.http.get_text(
                config.LEVEL_INDEX_URL,
                force=force,
                ttl=config.INDEX_TTL,
            )
            entries = parse_tag_index(html)
        except FetchError:
            entries = []

        # 额外分类：玩笑层级用标签，隐秘层级用官方列表页（避免「隐秘系列」把实体也带进来）
        extra_tags: dict[str, set[str]] = {}
        for group, tag in config.WIKIDOT_EXTRA_TAGS.items():
            url = f"{config.BASE_URL}/system:page-tags/tag/{quote(tag)}"
            try:
                tag_html, _ = self.http.get_text(url, force=force, ttl=config.INDEX_TTL)
            except FetchError:
                continue
            slugs = {item.slug for item in parse_tag_index(tag_html)}
            if slugs:
                extra_tags[group] = slugs
        try:
            hidden_html, _ = self.http.get_text(
                config.WIKIDOT_HIDDEN_LIST_URL,
                force=force,
                ttl=config.INDEX_TTL,
            )
            hidden_slugs = parse_page_link_slugs(hidden_html)
        except FetchError:
            hidden_slugs = set()
        if hidden_slugs:
            extra_tags["hidden"] = hidden_slugs
        if extra_tags:
            entries = [
                IndexEntry(
                    slug=entry.slug,
                    title=entry.title,
                    tags=tuple(
                        group for group, slugs in extra_tags.items() if entry.slug in slugs
                    ),
                )
                for entry in entries
            ]

        self._remember_index(entries)
        return entries

    # ---------------------------------------------------------------- 解析
    def _locator_guesses(self, text: str) -> list[str]:
        base = text.strip().strip("/")
        base = re.sub(r"\s+", "-", base).lower()
        base = re.sub(r"^level-?", "level-", base)
        if re.fullmatch(r"-?\d+(?:\.\d+)?", base):
            base = "level-" + base
        if not base.startswith(("level", "old:", "exclamation")):
            base = "level-" + base.lstrip("-")
        guesses = [base, base.replace(".", "-")]
        return [g for i, g in enumerate(guesses) if g and g not in guesses[:i]]

    # ---------------------------------------------------------------- 抓取
    def fetch_page(
        self,
        locator: str,
        query: str = "",
        force: bool = False,
        entry: IndexEntry | None = None,
    ) -> LevelInfo:
        slug = locator
        url = f"{config.BASE_URL}/{slug}"
        tried: list[str] = []
        html = ""
        cached = False

        for candidate in [slug] + self._locator_guesses(slug):
            if candidate in tried:
                continue
            tried.append(candidate)
            try:
                html, cached = self.http.get_text(
                    f"{config.BASE_URL}/{candidate}",
                    force=force,
                )
                url = f"{config.BASE_URL}/{candidate}"
                break
            except FetchError as exc:
                if exc.status == 404:
                    continue
                raise

        if not html:
            raise LevelNotFound(f"站点上找不到「{query or slug}」对应的层级页面")

        info = parse_level_page(html, url, query=query or slug)
        info.cached = cached
        if not info.title:
            raise LevelNotFound(f"「{query or slug}」不是一个层级页面")
        if entry is not None and not info.alias:
            _, alias = split_title(entry.title)
            info.alias = alias
        return info


def create_client(source: str = config.DEFAULT_SOURCE, http: HttpClient | None = None) -> BaseClient:
    """按数据源标识创建客户端。"""
    if source == "fandom":
        from .fandom import FandomClient

        return FandomClient(http)
    return WikidotClient(http)
