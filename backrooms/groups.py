"""层级分组：普通层级、子层级、C层级、C子层级、ZH层级、ZH子层级、其他页面。"""

from __future__ import annotations

import re

from .models import IndexEntry
from .parser import clean_inline, split_title

GROUP_LABELS = {
    "normal": "普通层级",
    "sub": "子层级",
    "c": "C层级",
    "c_sub": "C子层级",
    "zh": "ZH层级",
    "zh_sub": "ZH子层级",
    "other": "其他页面",
}

# 侧边栏顶层分组（子层级挂在各自上级下面，不再单独成组）
TOP_ORDER = ("normal", "c", "zh", "hidden", "joke", "orphan", "other")
TOP_LABELS = {
    "normal": "普通层级",
    "c": "C层级",
    "zh": "ZH层级",
    "hidden": "隐秘层级",
    "joke": "玩笑层级",
    "orphan": "子层级",
    "other": "其他页面",
}

_ORDER = {
    "wikidot": ("normal", "sub", "c", "c_sub", "other"),
    "fandom": ("normal", "sub", "c", "c_sub", "zh", "zh_sub", "other"),
}

# 默认全部折叠，由用户点击分组标题展开
_DEFAULT_EXPANDED = {
    "normal": False,
    "sub": False,
    "c": False,
    "c_sub": False,
    "zh": False,
    "zh_sub": False,
    "orphan": False,
    "other": False,
}

_ZH_TITLE_RE = re.compile(r"^(?:level|楼层|層級)\s*zh\s*[-–—－]?\s*(-?\d+)(\.\d+)?", re.I)
_ZH_SLUG_RE = re.compile(r"^level[\s_-]*zh", re.I)
_C_TITLE_RE = re.compile(r"^(?:level|antrum)\s*c\s*-\s*(-?\d+)(\.\d+)?", re.I)
_C_SLUG_RE = re.compile(r"^level-c-(\d+)(?:-(\d+))?$", re.I)
_LEVEL_TITLE_RE = re.compile(r"^(?:level|楼层|層級)\s*(-?\d+)(\.\d+)?", re.I)
_NUMBER_RE = re.compile(r"(-?\d+(?:\.\d+)?)")


def group_order(source: str) -> tuple[str, ...]:
    return _ORDER.get(source, _ORDER["wikidot"])


def top_group_order(source: str) -> tuple[str, ...]:
    return TOP_ORDER


def level_parts(entry: IndexEntry, source: str) -> tuple[str, str, bool]:
    """返回 (顶层分组, 上级编号, 是否子层级)。

    例如 Level 0.1 → ("normal", "0", True)；Level 0 → ("normal", "0", False)；
    Level C-1038.1 → ("c", "1038", True)；Level ZH 336.1 → ("zh", "336", True)。
    """
    label, _alias = split_title(entry.title or "")
    label = clean_inline(label)
    slug = (entry.slug or "").strip()
    tags = set(getattr(entry, "tags", ()) or ())

    # 隐秘层级 / 玩笑层级：标签优先，标题兜底
    if "hidden" in tags or re.match(r"^(?:隐秘层级|隱秘層級|隐秘楼层|隱秘樓層)", label):
        return "hidden", label, False
    if (
        "joke" in tags
        or re.match(r"^(?:\(Joke\)|Joke\s*Level|玩笑)", label, re.I)
        or re.search(r"[（(](?:搞笑|Joke)[)）]", label, re.I)
    ):
        return "joke", label, False

    match = _C_TITLE_RE.match(label)
    if match:
        return "c", match.group(1), bool(match.group(2))
    match = _C_SLUG_RE.match(slug)
    if match:
        return "c", match.group(1), bool(match.group(2))

    match = _ZH_TITLE_RE.match(label)
    if match:
        return "zh", match.group(1), bool(match.group(2))
    match = re.match(r"^level[\s_-]*zh[\s_-]*(-?\d+)(?:[.-](\d+))?$", slug, re.I)
    if match:
        return "zh", match.group(1), bool(match.group(2))

    match = _LEVEL_TITLE_RE.match(label)
    if match:
        return "normal", match.group(1), bool(match.group(2))
    match = re.match(r"^level-(-?\d+)(?:-(\d+))?$", slug, re.I)
    if match:
        return "normal", match.group(1), bool(match.group(2))

    if _ZH_SLUG_RE.match(slug):
        return "zh", label, False
    if re.match(r"^(?:level|楼层|層級)\b", label, re.I):
        return "normal", label.lower(), False
    return "other", "", False


def sort_children(entries: list[IndexEntry], top: str) -> list[IndexEntry]:
    prefix = {
        "c": r"level\s*c\s*-?\s*",
        "zh": r"level\s*zh\s*",
    }.get(top, r"(?:level|楼层|層級)\s*")
    return sorted(entries, key=lambda e: _number_key(prefix, e.title))


def build_families(entries: list[IndexEntry], source: str, sorter) -> dict[str, dict]:
    """把子层级挂到上级层级下；桌面端和 Android 端共用同一套树结构。"""
    families: dict[str, dict] = {
        key: {"mains": [], "children": {}}
        for key in top_group_order(source)
    }
    main_index: dict[tuple[str, str], IndexEntry] = {}
    pending: list[tuple[str, str, IndexEntry]] = []

    for entry in entries:
        top, base, is_sub = level_parts(entry, source)
        if top == "other":
            families["other"]["mains"].append(entry)
            continue
        if is_sub:
            pending.append((top, base, entry))
            continue
        families[top]["mains"].append(entry)
        main_index.setdefault((top, base), entry)

    for top, base, entry in pending:
        if (top, base) in main_index:
            families[top]["children"].setdefault((top, base), []).append(entry)
        else:
            families["orphan"]["mains"].append(entry)

    for top in ("normal", "c", "zh"):
        family = families[top]
        family["canonical"] = {
            signature: parent.slug
            for signature, parent in main_index.items()
            if signature[0] == top
        }
        family["mains"] = sort_group(family["mains"], top, sorter)
        for signature, children in family["children"].items():
            family["children"][signature] = sort_children(children, top)

    families["orphan"]["mains"] = sort_children(families["orphan"]["mains"], "normal")
    for top in ("hidden", "joke", "other"):
        families[top]["mains"] = sorter(families[top]["mains"])
    return families


def family_count(key: str, family: dict) -> int:
    if not family:
        return 0
    if key in ("normal", "c", "zh"):
        return len(family["mains"]) + sum(
            len(children) for children in family["children"].values()
        )
    return len(family["mains"])


def default_expanded() -> dict[str, bool]:
    return dict(_DEFAULT_EXPANDED)


def group_key(entry: IndexEntry, source: str) -> str:
    """判断条目属于哪个分组；标题优先，slug 兜底。"""
    label, _alias = split_title(entry.title or "")
    label = clean_inline(label)
    slug = (entry.slug or "").strip()

    # C 层群：Level C-156 / Level C-0.1 / Antrum C-156
    match = _C_TITLE_RE.match(label)
    if match:
        return "c_sub" if match.group(2) else "c"
    match = _C_SLUG_RE.match(slug)
    if match:
        return "c_sub" if match.group(2) else "c"

    # ZH 层群：Level ZH 38 / Level ZH 336.1
    match = _ZH_TITLE_RE.match(label)
    if match:
        return "zh_sub" if match.group(2) else "zh"

    # 普通层级与普通子层级：Level 386 / Level 0.1 / 楼层 1.1
    match = _LEVEL_TITLE_RE.match(label)
    if match:
        return "sub" if match.group(2) else "normal"

    # 标题不规范时（例如 Asset 11.1）用 slug 的层级编号判断
    if slug.startswith("level-c-"):
        return "c_sub" if "-" in slug[len("level-c-"):] else "c"
    if slug.startswith("level-"):
        tail = slug[len("level-"):]
        if re.fullmatch(r"\d+(?:-\d+)*", tail):
            return "sub" if "-" in tail else "normal"

    if _ZH_SLUG_RE.match(slug):
        return "zh"
    # Level !、Level -4 这类非数字层级仍归入普通层级
    if re.match(r"^(?:level|楼层|層級)\b", label, re.I):
        return "normal"
    return "other"


def _number_key(prefix: str, title: str):
    match = re.search(prefix + r"(-?\d+(?:\.\d+)?)", title or "", re.I)
    if not match:
        match = _NUMBER_RE.search(title or "")
    if match:
        try:
            return (0, float(match.group(1)), title)
        except ValueError:
            pass
    return (1, float("inf"), title)


def sort_group(entries: list[IndexEntry], key: str, fallback) -> list[IndexEntry]:
    """分组内排序：层级编号按数值排，其余沿用全局排序。"""
    if key == "c":
        return sorted(entries, key=lambda e: _number_key(r"level\s*c\s*-?\s*", e.title))
    if key == "c_sub":
        return sorted(entries, key=lambda e: _number_key(r"level\s*c\s*-?\s*", e.title))
    if key == "zh":
        return sorted(entries, key=lambda e: _number_key(r"level\s*zh\s*", e.title))
    if key == "zh_sub":
        return sorted(entries, key=lambda e: _number_key(r"level\s*zh\s*", e.title))
    if key == "sub":
        return sorted(entries, key=lambda e: _number_key(r"(?:level|楼层|層級)\s*", e.title))
    return fallback(entries)
