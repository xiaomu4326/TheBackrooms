"""后室中文维基页面解析。

负责两件事：
1. 从层级页面 HTML 里取出名称、生存难度、标签、摘要、版本信息；
2. 从来「层级」标签索引页里取出 slug ↔ 标题的对应表。
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from urllib.parse import unquote

from .config import CLASS_TAG_PREFIX
from .minidom import Node, clean_inline, parse_html, squash
from .models import IndexEntry, LevelInfo

# 生存难度组件的各类分项文字前缀
_TOP_TEXT = "top-text"
_BOTTOM_TEXT = "bottom-text"
_BOTTOM_BOX = "bottom-box"

_CLASS_PREFIX_RE = re.compile(r"^(?:等级|等級|分级|分級|class|level)\s*[:：]?\s*", re.I)
_PLACEHOLDER_RE = re.compile(r"^\{\$.*\}$")
_TRAILING_PUNCT = " .。·"

_CLASS_KEY_ALIASES = {
    "終焉": "omega",
    "终焉": "omega",
    "終結": "omega",
    "其他": "其他",
    "其它": "其他",
    "未知": "未知",
    "宜居": "宜居",
    "死区": "死区",
    "死區": "死区",
    "等待分级": "等待分级",
    "等待分級": "等待分级",
    "不适用": "不适用",
    "不適用": "不适用",
    "修正": "修正",
    "运变": "amended",
    "運變": "amended",
}

# component:level-class 的 CSS 在作者没传 |one= |two= |three= 时，
# 用 .default::after 按等级注入的固定文案（浏览器里看到的就是这些）。
CLASS_DEFAULT_ITEMS: dict[str, tuple[str, str, str]] = {
    "0": ("安全", "稳定", "实体绝迹"),
    "1": ("安全", "稳定", "极少量实体"),
    "2": ("不安全", "稳定", "少量实体"),
    "3": ("不安全", "不稳定", "少量实体"),
    "4": ("不安全", "不稳定", "中量实体"),
    "5": ("不安全", "不稳定", "实体横行"),
    "unknown": ("性质未解明", "信息未知", "未探明实体"),
    "未知": ("性质未解明", "信息未知", "未探明实体"),
    "habitable": ("安全", "长期聚居地", "无有害实体"),
    "宜居": ("安全", "长期聚居地", "无有害实体"),
    "deadzone": ("环境危害", "极度不宜居", "潜在异常实体"),
    "死区": ("环境危害", "极度不宜居", "潜在异常实体"),
    "pending": ("安全性未知", "不稳定", "未探明实体存在"),
    "等待分级": ("安全性未知", "不稳定", "未探明实体存在"),
    "n/a": ("不存在", "缺失物质", "不适合生命存在"),
    "不适用": ("不存在", "缺失物质", "不适合生命存在"),
    "amended": ("不安全且不稳定", "未知实体数量", "文件被篡改"),
    "修正": ("不安全且不稳定", "未知实体数量", "文件被篡改"),
    "omega": ("隐藏的档案", "机密性质", "受保护的实体"),
    "终结": ("隐藏的档案", "机密性质", "受保护的实体"),
}


def _first_visible(node: Node, pred) -> Node | None:
    for child in node.walk():
        if child is node:
            continue
        if pred(child) and not is_hidden(child):
            return child
    return None


def is_hidden(node: Node) -> bool:
    """节点是否位于 display:none / 著作信息折叠区里。"""
    current: Node | None = node
    while current is not None:
        style = (current.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            return True
        if "creditrate" in current.classes or "credit" in current.classes:
            return True
        current = current.parent
    return False


def _inside(node: Node, tags: set[str], classes: set[str]) -> bool:
    for parent in node.ancestors():
        if parent.tag in tags or parent.classes & classes:
            return True
    return False


def _visible(node: Node) -> bool:
    return not is_hidden(node)


def _page_title(root: Node, html: str) -> str:
    node = root.find(id="page-title")
    title = clean_inline(node.text_content()) if node else ""
    if title:
        return title
    match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if not match:
        return ""
    raw = clean_inline(re.sub(r"<[^>]+>", "", match.group(1)))
    return re.sub(r"\s*-\s*The Backrooms.*$", "", raw, flags=re.I).strip()


def split_title(title: str) -> tuple[str, str]:
    """把「Level 0 - “教学关卡”」拆成标签与别称。"""
    text = title.strip()
    # 分隔符两侧必须有空格，避免把「Antrum C-156」这种编号拆开
    match = re.match(
        r"^(?P<label>[^\-–—]+?)\s+[\-–—]\s+[“\"「『]?(?P<alias>.+?)[”\"」』]?\s*$",
        text,
    )
    if not match:
        return text, ""
    label = clean_inline(match.group("label"))
    alias = clean_inline(match.group("alias")).strip("“”\"「」『』 ")
    return label, alias


def level_code(label: str, slug: str = "") -> str:
    match = re.match(r"^(?:level|层级|樓層|楼层)\s*(.+)$", label, re.I)
    if match:
        code = match.group(1).strip()
        code = re.sub(r"[（(].*?[)）]\s*$", "", code).strip()
        return code
    match = re.search(r"([0-9]+(?:\.[0-9]+)?[A-Za-z]?)\s*$", label)
    if match:
        return match.group(1)
    match = re.search(r"(?:level|ground|asset|antrum)\W*([0-9][0-9.\-A-Za-z]*)", slug, re.I)
    return match.group(1) if match else ""


def _class_from_tags(tags: list[str]) -> str:
    """标签里取最具体的一条，例如「生存难度1e - 环境危害」优于「生存难度1e」。"""
    values: list[str] = []
    for tag in tags:
        for prefix in (CLASS_TAG_PREFIX, "生存難度"):
            if not tag.startswith(prefix):
                continue
            value = tag[len(prefix):].strip()
            if value:
                values.append(value)
            break
    if not values:
        return ""
    return max(values, key=len)


def _nfkc(text: str) -> str:
    """只在含全角字符时做 NFKC，避免符号被兼容归一。"""
    if text and re.search(r"[\uFF01-\uFF5E\u3000]", text):
        return unicodedata.normalize("NFKC", text)
    return text


def _normalize_class_key(raw: str) -> str:
    """把「Class 1e - 环境危害」「等级 終焉」「1e」统一成配色用的 key。"""
    text = _nfkc(clean_inline(raw))
    text = re.sub(
        r"^(?:生存难度|生存難度|survival\s+difficulty|difficulty)"
        r"(?:\s*(?:等级|等級|分级|分級|级别|級別|评级|評級))?\s*[:：]?\s*",
        "",
        text,
        flags=re.I,
    )
    # 允许「等级：Class 1」这种叠了两层前缀的写法
    for _ in range(2):
        stripped = _CLASS_PREFIX_RE.sub("", text).strip(_TRAILING_PUNCT)
        if stripped == text:
            break
        text = stripped
    if not text:
        return ""

    # 数字等级，可带字母后缀（1e 环境分级、1d 自定义分级等）
    match = re.match(r"([0-9]{1,2}\s*[A-Za-z]?)\b", text)
    if match:
        return match.group(1).replace(" ", "").lower()

    # 罗马数字：Fandom 的 Class V / Class III
    match = re.match(r"([IVX]{1,4})\b", text, re.I)
    if match:
        roman = match.group(1).upper()
        roman_map = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5"}
        if roman in roman_map:
            return roman_map[roman]

    # 英文分级词
    match = re.match(r"([A-Za-z]+(?:\s*/\s*[A-Za-z]+)?)", text)
    if match:
        word = re.sub(r"\s+", "", match.group(1)).lower()
        if word in (
            "unknown", "habitable", "deadzone", "pending", "n/a",
            "amended", "omega", "environmental",
        ):
            return word

    # 中文分级词：取最长匹配，避免「等待分级」被截断
    for alias in sorted(_CLASS_KEY_ALIASES, key=len, reverse=True):
        if text.startswith(alias):
            return _CLASS_KEY_ALIASES[alias]
    return text


def _ancestor_with_prefix(node: Node, prefix: str) -> Node | None:
    for parent in node.ancestors():
        if any(c.startswith(prefix) for c in parent.classes):
            return parent
    return None


def _in_bottom_box(node: Node) -> bool:
    current = node.parent
    while current is not None:
        if any(c.startswith(_BOTTOM_BOX) for c in current.classes):
            return True
        current = current.parent
    return False


def _class_key_from_scope(scope: Node) -> str:
    """从组件的 class-1 / class-unknown 这类 class 名反推等级。"""
    for node in scope.walk():
        for name in node.classes:
            if not name.startswith("class-"):
                continue
            candidate = name[len("class-"):].strip()
            if not candidate or "{" in candidate:
                continue
            key = _normalize_class_key(candidate)
            if key:
                return key
    return ""


def _class_items(scope: Node, class_key: str = "") -> list[str]:
    """取「三条难度描述」。

    组件里未填写的 {$one} 这类占位符不会出现在网页上：CSS 会把占位 span 隐藏，
    再由 .default::after 按等级注入固定文案，所以这里用同一张表补回来。
    """
    defaults = CLASS_DEFAULT_ITEMS.get(class_key, ())
    items: list[str] = []
    for ul in scope.find_all(tag="ul"):
        if is_hidden(ul) or not _in_bottom_box(ul):
            continue
        for position, li in enumerate(ul.find_all(tag="li")):
            text = clean_inline(li.text_content()).strip(_TRAILING_PUNCT)
            if not text or _PLACEHOLDER_RE.match(text) or text.startswith("{$"):
                if position < len(defaults):
                    items.append(defaults[position])
                continue
            items.append(text)
            if len(items) >= 3:
                break
        if items:
            break
    return items[:3]


def extract_survival(root: Node, content: Node) -> tuple[str, list[str]]:
    """返回 (生存难度原文, 三条描述)。"""
    nodes = list(content.walk())

    # 1) 标准组件：先找 .sd-container，再看其中的 bottom-text / bottom-box
    for container in content.find_all(cls="sd-container"):
        if not _visible(container):
            continue
        bottom = _first_visible(container, lambda n: any(c.startswith(_BOTTOM_TEXT) for c in n.classes))
        if bottom is None:
            continue
        raw = clean_inline(bottom.text_content())
        if raw:
            key = _normalize_class_key(raw) or _class_key_from_scope(container)
            return raw, _class_items(container, key)

    # 2) 自定义版式：任意「生存难度：」块（如 level-999 的 top-box-a）
    for index, node in enumerate(nodes):
        if not any(c.startswith(_TOP_TEXT) for c in node.classes):
            continue
        if not _visible(node):
            continue
        header = clean_inline(node.text_content())
        if not header.startswith("生存难度"):
            continue
        raw = ""
        block = node.parent
        if block is not None:
            bottom = _first_visible(block, lambda n: any(c.startswith(_BOTTOM_TEXT) for c in n.classes))
            if bottom is not None and bottom is not node:
                raw = clean_inline(bottom.text_content())
        if not raw:
            match = re.match(r"^生存难度\s*[:：]?\s*(.+)$", header)
            raw = clean_inline(match.group(1)) if match else ""
        if not raw:
            for follow in nodes[index + 1: index + 12]:
                text = clean_inline(follow.text_content())
                if text.startswith(("等级", "等級", "Class")):
                    raw = text
                    break
        if raw:
            top_box = _ancestor_with_prefix(node, "top-box") or (block or content)
            scope = top_box.parent or content
            key = _normalize_class_key(raw) or _class_key_from_scope(scope)
            return raw, _class_items(scope, key)

    # 3) 纯文本兜底：「生存难度：Class 3」
    text = squash(content.text_content())
    match = re.search(r"生存难度\s*[:：]\s*([^\n]{1,30})", text)
    if match:
        return clean_inline(match.group(1)), []
    return "", []


def _tags(root: Node) -> list[str]:
    box = root.find(id="page-tags") or root.find(cls="page-tags")
    if box is None:
        return []
    tags: list[str] = []
    for link in box.find_all(tag="a"):
        text = clean_inline(link.text_content())
        if text and text not in tags:
            tags.append(text)
    return tags


def extract_summary(content: Node, limit: int = 3) -> str:
    """正文摘要：优先取「描述 / 简介 / 概述」小节，否则取开头段落。"""
    skip_tags = {"table", "code", "sup", "iframe", "blockquote"}
    skip_classes = {"code", "creditRate", "credit", "footnotes-footer", "licensebox", "scp-image-caption", "blockquote"}
    nodes = list(content.walk())

    def collect(start: int, stop_at_heading: bool) -> list[str]:
        collected: list[str] = []
        for node in nodes[start:]:
            if stop_at_heading and node.tag in ("h1", "h2"):
                break
            if node.tag != "p" or is_hidden(node):
                continue
            if _inside(node, skip_tags, skip_classes):
                continue
            text = clean_inline(node.text_content())
            if len(text) < 60:
                continue
            if text.startswith(("生存难度", "页面版本", "除非特别注明", "Footnote")):
                continue
            collected.append(text)
            if len(collected) >= limit:
                break
        return collected

    for index, node in enumerate(nodes):
        if node.tag not in ("h1", "h2", "h3") or is_hidden(node):
            continue
        heading = clean_inline(node.text_content())
        if len(heading) <= 24 and any(
            word in heading for word in ("描述", "简介", "概述", "概要", "概览", "说明")
        ):
            paragraphs = collect(index + 1, stop_at_heading=True)
            if paragraphs:
                return "\n\n".join(paragraphs)[:1200]

    joined = "\n\n".join(collect(0, stop_at_heading=False))
    return joined[:1200]


def extract_quote(content: Node) -> str:
    for node in content.find_all(tag="blockquote"):
        if is_hidden(node):
            continue
        text = clean_inline(node.text_content())
        if 12 <= len(text) <= 400:
            return text
    return ""


def _revision(root: Node) -> tuple[str, str]:
    box = root.find(id="page-info")
    if box is None:
        return "", ""
    text = clean_inline(box.text_content())
    match = re.search(r"页面版本\s*[:：]\s*(\d+)", text)
    revision = match.group(1) if match else ""
    updated = ""
    for node in box.walk():
        for name in node.classes:
            if name.startswith("time_") and name[5:].isdigit():
                try:
                    updated = datetime.fromtimestamp(int(name[5:])).strftime("%Y-%m-%d %H:%M")
                except (OverflowError, OSError, ValueError):
                    updated = ""
                break
        if updated:
            break
    return revision, updated


def parse_level_page(html: str, url: str, query: str = "") -> LevelInfo:
    root = parse_html(html)
    content = root.find(id="page-content")
    if content is None:
        return LevelInfo(query=query, url=url, fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    title = _page_title(root, html)
    label, alias = split_title(title)
    tags = _tags(root)
    raw_class, items = extract_survival(root, content)
    class_text, class_key = build_class(raw_class, items, tags, content)
    revision, updated = _revision(root)

    return LevelInfo(
        query=query,
        title=title,
        label=label,
        code=level_code(label, url.rsplit("/", 1)[-1]),
        alias=alias,
        class_text=class_text,
        class_key=class_key,
        class_items=items,
        tags=tags,
        summary=extract_summary(content),
        quote=extract_quote(content),
        revision=revision,
        updated_at=updated,
        url=url,
        page_key=unquote(url.rsplit("/", 1)[-1]),
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def build_class(
    raw_class: str,
    items: list[str],
    tags: list[str],
    content: Node | None = None,
) -> tuple[str, str]:
    """把组件原文整理成展示文本与归一化等级。"""
    raw = clean_inline(raw_class)
    key = _normalize_class_key(raw)
    if not key:
        tag_class = _class_from_tags(tags)
        if tag_class:
            key = _normalize_class_key(tag_class)
            if not raw:
                raw = tag_class  # 保留「1e - 环境危害」这类后缀
    if not raw and key:
        raw = key
    if raw and not raw.lower().startswith(("等级", "等級", "class", "分级")):
        raw = f"等级 {raw}"
    return raw, key


def parse_page_link_slugs(html: str) -> set[str]:
    """取页面正文里的站内链接 slug，例如「隐秘层级列表」中的人工分类名单。"""
    root = parse_html(html)
    content = root.find(id="page-content") or root
    slugs: set[str] = set()
    for link in content.find_all(tag="a"):
        href = (link.get("href") or "").strip()
        if not href.startswith("/"):
            continue
        slug = href.split("#", 1)[0].strip("/")
        if slug and not slug.startswith(("system:", "forum:", "search")):
            slugs.add(slug)
    return slugs


def parse_tag_index(html: str) -> list[IndexEntry]:
    """解析「层级」标签页，拿到全部层级页面的 slug 与标题。"""
    root = parse_html(html)
    scope = root.find(id="tagged-pages-list") or root.find(cls="pages-list") or root
    entries: list[IndexEntry] = []
    seen: set[str] = set()
    for item in scope.find_all(cls="pages-list-item"):
        link = item.find(tag="a")
        if link is None:
            continue
        href = link.get("href").strip()
        if not href.startswith("/"):
            continue
        slug = href.split("#", 1)[0].strip("/")
        if not slug or slug in seen:
            continue
        title = clean_inline(link.text_content())
        if not title:
            continue
        seen.add(slug)
        entries.append(IndexEntry(slug=slug, title=title))
    return entries


def normalize_title(text: str) -> str:
    """标题归一化，便于模糊匹配：去空格、去引号、转小写。"""
    text = clean_inline(text).lower()
    text = re.sub(r"[“”\"'「」『』]", "", text)
    return text.replace(" ", "")
