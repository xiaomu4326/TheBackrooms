"""Android（Chaquopy）桥接：给 Java 界面提供索引树与层级查询。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from backrooms import config, groups
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


def _entry(entry) -> dict:
    return {
        "slug": entry.slug,
        "title": entry.title,
        "tags": list(entry.tags or ()),
    }


def _class_color(key: str) -> str:
    rgb = config.CLASS_COLORS.get(key or "")
    if not rgb:
        return "#F7E375"
    return "#%02X%02X%02X" % tuple(rgb)


def _payload(info) -> dict:
    return {
        "ok": True,
        "title": info.title,
        "label": info.label,
        "alias": info.alias,
        "code": info.code,
        "page_key": getattr(info, "page_key", ""),
        "class_text": info.class_text,
        "class_key": info.class_key,
        "class_items": info.class_items,
        "class_color": _class_color(info.class_key),
        "tags": info.tags,
        "summary": info.summary,
        "revision": info.revision,
        "updated_at": info.updated_at,
        "url": info.url,
        "cached": info.cached,
    }


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


def _main(parent, children) -> dict:
    return {
        "entry": _entry(parent),
        "children": [_entry(child) for child in children],
    }


def index(source: str, force: bool = False) -> str:
    """返回与桌面端一致的层级树：分组、上级、子层级、计数。"""
    try:
        client = _client(source)
        entries = client.sort_entries(client.list_levels(force=force))
        families = groups.build_families(entries, source, client.sort_entries)
        payload = []
        for key in groups.top_group_order(source):
            family = families.get(key) or {}
            count = groups.family_count(key, family)
            if not count:
                continue
            if key == "normal":
                sections = []
                for section in family.get("sections", []):
                    sections.append(
                        {
                            "key": section["key"],
                            "label": section["label"],
                            "count": section["count"],
                            "mains": [
                                _main(item["entry"], item["children"])
                                for item in section["mains"]
                            ],
                        }
                    )
                payload.append(
                    {
                        "key": key,
                        "label": groups.TOP_LABELS.get(key, key),
                        "count": count,
                        "sections": sections,
                    }
                )
                continue

            mains = []
            if key in ("c", "zh"):
                canonical = family.get("canonical") or {}
                for parent in family["mains"]:
                    top, base, _is_sub = groups.level_parts(parent, source)
                    signature = (top, base)
                    children = (
                        family["children"].get(signature, [])
                        if canonical.get(signature) == parent.slug
                        else []
                    )
                    mains.append(_main(parent, children))
            else:
                for entry in family["mains"]:
                    mains.append({"entry": _entry(entry), "children": []})
            payload.append(
                {
                    "key": key,
                    "label": groups.TOP_LABELS.get(key, key),
                    "count": count,
                    "mains": mains,
                }
            )
        return json.dumps(
            {"ok": True, "total": len(entries), "groups": payload},
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001 - 把错误传回 Android 界面
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def fetch(source: str, query: str, force: bool = False) -> str:
    """按输入查询；先直连页面，失败再走索引解析。"""
    try:
        client = _client(source)
        locator = _direct_locator(source, query)
        info = None
        if locator:
            try:
                info = client.fetch_page(locator, query=query, force=force)
            except LevelNotFound:
                info = None
        if info is None:
            info = client.fetch_level(query, force=force)
        return json.dumps(_payload(info), ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def fetch_slug(source: str, slug: str, title: str = "", force: bool = False) -> str:
    """点击列表条目时直接按 slug 抓取，避免再查索引。"""
    try:
        client = _client(source)
        try:
            info = client.fetch_page(slug, query=title or slug, force=force)
        except LevelNotFound:
            info = client.fetch_level(title or slug, force=force)
        return json.dumps(_payload(info), ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
