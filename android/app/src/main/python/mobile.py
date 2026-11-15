"""Android（Chaquopy）桥接：给 Java 界面提供层级查询。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from backrooms import config
from backrooms.base import LevelNotFound
from backrooms.service import create_client

_clients: dict[str, object] = {}


def init(cache_dir: str, proxy: str = "") -> None:
    """设置 Android 私有缓存目录、网络参数与可选代理。"""
    try:
        config.CACHE_DIR = Path(cache_dir) / "backrooms-cache"
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    config.REQUEST_TIMEOUT = 10
    config.HTTP_RETRIES = 1
    if proxy:
        os.environ["http_proxy"] = proxy
        os.environ["https_proxy"] = proxy
    else:
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
    _clients.clear()


def _client(source: str):
    if source not in _clients:
        _clients[source] = create_client(source)
    return _clients[source]


def _direct_locator(source: str, query: str) -> str:
    """数字/编号查询直接猜页面地址，避免首查加载整份索引。"""
    text = re.sub(r"(?i)^level\s*", "", query.strip()).strip()
    if not text:
        return ""
    if source == "wikidot":
        slug = "level-" + text.lower().replace(" ", "-").replace(".", "-")
        return re.sub(r"-+", "-", slug)
    if source == "fandom":
        return "Level " + text
    return ""


def fetch(source: str, query: str) -> str:
    """查询层级并返回 JSON 字符串；异常也转成 JSON，界面不会崩。"""
    try:
        client = _client(source)
        locator = _direct_locator(source, query)
        try:
            info = client.fetch_page(locator, query=query) if locator else None
        except LevelNotFound:
            info = None
        if info is None:
            info = client.fetch_level(query)
        return json.dumps(
            {
                "ok": True,
                "title": info.title,
                "label": info.label,
                "alias": info.alias,
                "class_text": info.class_text,
                "class_key": info.class_key,
                "class_items": info.class_items,
                "tags": info.tags,
                "summary": info.summary,
                "url": info.url,
                "cached": info.cached,
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001 - 需要把错误传回 Android 界面
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
