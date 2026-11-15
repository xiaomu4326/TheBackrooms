"""Fandom（MediaWiki）数据源。

接口说明：
    索引：action=query&list=allpages（按 Level / 楼层 前缀分页）
    页面：action=parse&prop=text|categories|revid
    搜索：action=query&list=search
"""

from __future__ import annotations

import html
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

from . import config
from .base import BaseClient, LevelNotFound
from .http_client import FetchError, HttpClient
from .minidom import clean_inline, parse_html
from .models import IndexEntry, LevelInfo
from .parser import build_class, extract_quote, extract_summary, is_hidden, level_code, split_title

_TAG_RE = re.compile(r"<[^>]+>")

# 索引里只保留真正的层级页：Level 0 / Level ZH 38 / Level C-156 / 楼层 1 / Level !
_LEVEL_PAGE_TITLE_RE = re.compile(
    r"^(?:level|楼层|層級)\s*(?:(?:zh|c)\s*[-–—－]?\s*)?[!\-0-9]",
    re.I,
)


def _is_level_page_title(title: str) -> bool:
    return bool(_LEVEL_PAGE_TITLE_RE.match((title or "").strip()))

# 便携信息框里可能承载生存难度的 data-source
CLASS_DATA_SOURCES = {
    "difficulty", "class", "level_class", "levelclass",
    "survival_difficulty", "survivaldifficulty", "生存难度", "难度",
}

DIFFICULTY_WORDS = (
    "安全", "稳定", "穩定", "不稳定", "不穩定", "不安全", "宜居", "死区", "死區",
    "死亡区", "死亡區", "未知", "未解明", "机密", "機密", "环境危害", "環境危害",
    "环境", "環境", "实体", "實體", "非实体", "非實體", "数量", "數量", "资源", "資源",
    "聚居", "威胁", "威脅", "勘探", "危害",
    "safe", "secure", "unsafe", "unsecure", "habitable", "deadzone",
    "unknown", "entit", "environmental", "hostile", "hazard",
)

# 兼容「生存难度等级：」「生存難度評級：」这类带后缀的标签
_LABEL_PATTERN = (
    r"(?:生存难度|生存難度|难度|難度|survival\s+difficulty|difficulty)"
    r"(?:\s*(?:等级|等級|分级|分級|级别|級別|评级|評級))?"
)

# 块级标签：用来把「生存难度」「三条细则」拆成独立行
_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "center", "dd", "div", "dl",
    "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "li", "main", "nav", "ol", "p", "pre",
    "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}

# 细则分隔/前缀：Fandom 中文常用「》」，也有 »、•、·、＞、顿号等
_DETAIL_SPLIT_RE = re.compile(r"\s*[》»«＞>•·・◦▸▹◆◇▪■、；;\u2800]\s*")
_DETAIL_PREFIX_CHARS = "》»«＞>•·・◦▸▹◆◇▪■-—－* \u2800"

_CLASS_PREFIX = r"(?:class|等级|等級|分级|分級)"
_CLASS_TOKEN = (
    r"(?:[0-9]{1,2}\s*[A-Za-z]?|[IVX]{1,4}|unknown|habitable|deadzone|pending|n/?a|amended|omega|"
    r"未知|宜居|死区|死區|等待分级|等待分級|不适用|不適用|修正|终结|終結|終焉)"
)
# 带 Class / 等级 前缀的等级短语；单独的「16」不算，避免把正文数字当等级
_CLASS_PREFIXED_RE = re.compile(rf"^\s*(?:{_CLASS_PREFIX}\s*[:：]?\s*){{1,2}}{_CLASS_TOKEN}\b", re.I)
# 只在「生存难度：」标签后面才接受裸等级
_BARE_CLASS_RE = re.compile(rf"^\s*{_CLASS_TOKEN}\b", re.I)
# 独立的短元素/属性必须明确写 Class / 等级，避免把「Level 97」这种链接标题当等级
_CLASS_WORD_RE = re.compile(r"^\s*(?:class|等级|等級|分级|分級)\b", re.I)


_STYLE_BLOCK_RE = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.I | re.S)


def strip_tags(text: str) -> str:
    text = _STYLE_BLOCK_RE.sub("", text or "")
    return clean_inline(html.unescape(_TAG_RE.sub("", text)))


def _safe_alias(alias: str) -> str:
    """过滤掉 displaytitle 里混进的 CSS/动画文本，只保留正常名称。"""
    alias = clean_inline(alias).strip("“”\"「」『』 ")
    if not alias or len(alias) > 30:
        return ""
    if re.search(r"[{}<>]|style|animation|data-|::|\\", alias, re.I):
        return ""
    return alias


_FULLWIDTH_RE = re.compile(r"[\uFF01-\uFF5E\u3000]")


def _nfkc(text: str) -> str:
    """只在含全角字符时做 NFKC，避免把 ℵ 这类符号兼容归一掉。"""
    if text and _FULLWIDTH_RE.search(text):
        return unicodedata.normalize("NFKC", text)
    return text


def _own_text(node) -> str:
    """只取节点自身的文字，跳过其中的列表/表格（那些是难度分项）。"""
    parts: list[str] = []

    def walk(current) -> None:
        for child in current.children:
            if child.tag in ("ul", "ol", "table"):
                continue
            if child.tag == "#text":
                parts.append(child.text)
            else:
                walk(child)

    walk(node)
    return clean_inline("".join(parts))


def text_lines(node) -> list[str]:
    """把节点文本按块级元素拆成行，用于识别「生存难度 / 细则」这类竖排结构。"""
    parts: list[str] = []

    def walk(current) -> None:
        for child in current.children:
            if child.tag == "#text":
                parts.append(child.text)
            elif child.tag in ("script", "style"):
                continue
            elif child.tag == "br":
                parts.append("\n")
            elif child.tag in _BLOCK_TAGS:
                parts.append("\n")
                walk(child)
                parts.append("\n")
            else:
                walk(child)

    walk(node)
    return [line for line in (clean_inline(part) for part in "".join(parts).split("\n")) if line]


def _class_phrase(text: str, allow_bare: bool = False) -> str:
    """从一行文字里截出完整的等级短语，保留「- 环境危害」这类后缀。

    默认要求带 Class / 等级 前缀；只有紧跟「生存难度：」标签时才允许裸数字/裸等级。
    """
    normalized = _nfkc(clean_inline(text))
    match = _CLASS_PREFIXED_RE.match(normalized)
    if not match and allow_bare:
        match = _BARE_CLASS_RE.match(normalized)
    if not match:
        return ""
    phrase = match.group(0)
    suffix = re.match(
        r"^\s*[-–—－]\s*[^\s》>•·・\n]{1,14}",
        normalized[len(phrase):],
    )
    return clean_inline(phrase + (suffix.group(0) if suffix else ""))


def _looks_like_detail(text: str) -> bool:
    text = clean_inline(text)
    if not 1 < len(text) <= 24:
        return False
    low = text.lower()
    return any(word.lower() in low for word in DIFFICULTY_WORDS)


def _plausible_detail(text: str) -> bool:
    """细则应是短句；过滤掉整段正文（wikitext 里也常以 * 开头）。"""
    text = clean_inline(text)
    return bool(text) and len(text) <= 32 and not text.endswith(("。", "！", "？", ".", "!", "?"))


def _split_details(text: str) -> list[str]:
    return [part for part in (clean_inline(p) for p in _DETAIL_SPLIT_RE.split(text)) if part]


def _parse_difficulty_lines(lines: list[str]) -> tuple[str, list[str]]:
    """从若干行里取「等级短语 + 细则」。"""
    raw = ""
    items: list[str] = []
    for line in lines:
        line = _nfkc(clean_inline(line))
        if not line:
            continue

        head = re.match(
            r"^(?:" + _LABEL_PATTERN + r")\s*[:：]?\s*(.*)$",
            line,
            re.I,
        )
        had_label = bool(head)
        if head:
            line = clean_inline(head.group(1))

        if not raw:
            phrase = _class_phrase(line, allow_bare=had_label)
            if phrase:
                raw = phrase
                rest = clean_inline(line[len(phrase):]).lstrip(" :：")
                if rest:
                    parts = _split_details(rest)
                    if len(parts) > 1:
                        items.extend(part for part in parts if _plausible_detail(part))
                    elif parts and _looks_like_detail(parts[0]):
                        items.append(parts[0])
                continue
        if not raw:
            continue

        stripped = line.lstrip(_DETAIL_PREFIX_CHARS)
        if stripped != line and stripped:
            if _plausible_detail(stripped):
                items.append(clean_inline(stripped))
        elif len(_DETAIL_SPLIT_RE.split(line)) > 1:
            items.extend(
                part for part in _split_details(line)
                if part != line and _plausible_detail(part)
            )
        elif _looks_like_detail(line):
            items.append(line)
        if len(items) >= 4:
            break

    unique: list[str] = []
    for item in items:
        item = item.strip(" .。·")
        if item and item != raw and item not in unique:
            unique.append(item)
    return raw, unique[:3]


def _difficulty_list(content) -> list[str]:
    """兜底：找一组看起来像「安全 / 稳定 / 极少实体」的列表项。"""
    for ul in content.find_all(tag="ul"):
        if is_hidden(ul):
            continue
        items = [clean_inline(li.text_content()).strip(" .。·") for li in ul.find_all(tag="li")]
        items = [item for item in items if item]
        if not 2 <= len(items) <= 6:
            continue
        if sum(1 for item in items if _looks_like_detail(item)) >= 2:
            return items[:3]
    return []


# 可能用来包住生存难度的 class 名
_CLASSY_HINTS = (
    "sd-", "sd_", "sdbox", "difficulty", "survival", "level-class",
    "levelclass", "class-box", "classbox", "danger-level",
)

_TEMPLATE_CLASS_RE = re.compile(
    r"\{\{\s*(?:class|等级|等級|分级|分級|survival\s+difficulty)\s*"
    r"([^}|]{0,40}?)\s*(\|[^{}]*)?\}\}",
    re.I,
)

_TEMPLATE_SD_RE = re.compile(
    r"\{\{\s*(?:生存难度|生存難度|难度|survival\s+difficulty)\s*(\|[^{}]*)?\}\}",
    re.I,
)

_WIKITEXT_LABEL_RE = re.compile(r"^(?:" + _LABEL_PATTERN + r")\s*[:：]?\s*(.*)$", re.I)


def _clean_wiki_item(text: str) -> str:
    """去掉 wikitext 的加粗/链接标记，只留文字。"""
    text = re.sub(r"'{2,}", "", text or "")
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    return clean_inline(text)


def _template_items(params: str, skip_environment: bool = False) -> list[str]:
    """从模板参数里取 one / two / three 三条描述。"""
    if not params:
        return []
    named: dict[str, str] = {}
    for key, value in re.findall(r"\|\s*(one|two|three|1|2|3)\s*=\s*([^|\n}]*)", params, re.I):
        named[key.lower()] = _clean_wiki_item(value)
    ordered = [named[key] for key in ("one", "1", "two", "2", "three", "3") if named.get(key)]
    if ordered:
        return [item for item in ordered if item][:3]
    # 位置参数里偶尔直接写描述；环境分级的第一项通常是「环境危害」标签
    positional = [
        _clean_wiki_item(part)
        for part in params.split("|")[1:]
        if "=" not in part
    ]
    if skip_environment and positional and ("环境" in positional[0] or "環境" in positional[0]):
        positional = positional[1:]
    return [part for part in positional if _looks_like_detail(part)][:3]


def _wikitext_items_after(wikitext: str, offset: int) -> list[str]:
    items: list[str] = []
    tail = wikitext[offset:offset + 1000]
    for line in tail.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith(("*", "》", "»", ">", "•", "·", "・")):
            item = _clean_wiki_item(text.lstrip("*》»>•·・ ").strip())
            if item and _plausible_detail(item):
                items.append(item)
        elif items:
            break
        if len(items) >= 3:
            break
    return items[:3]


def difficulty_from_wikitext(wikitext: str) -> tuple[str, list[str]]:
    """从 MediaWiki 源码里找生存难度，兜住模板渲染出来的各种奇怪结构。"""
    if not wikitext:
        return "", []

    match = _TEMPLATE_CLASS_RE.search(wikitext)
    if match:
        token = clean_inline(match.group(1))
        if token:
            raw = token if re.match(r"^(?:class|等级|等級|分级)", token, re.I) else f"Class {token}"
            params = match.group(2) or ""
            is_env = bool(re.match(r"^[1-5]\s*[eE]\b", token, re.I))
            items = _template_items(params, skip_environment=is_env) or _wikitext_items_after(
                wikitext, match.end()
            )
            return raw, items[:3]

    # {{生存难度|Class 1|安全|稳定|极少量实体}}
    match = _TEMPLATE_SD_RE.search(wikitext)
    if match:
        params = match.group(1) or ""
        phrase = _class_phrase(clean_inline(params))
        if not phrase:
            inner = re.search(
                r"Class\s*[0-9]{1,2}\s*[eE]?(?:\s*[-–—－]\s*[^\s|}]{1,14})?",
                params,
                re.I,
            )
            phrase = clean_inline(inner.group(0)) if inner else ""
        if phrase:
            parts = [clean_inline(part) for part in params.split("|")[1:]]
            items = [part for part in parts if _looks_like_detail(part)]
            if (
                re.match(r"^class\s*[1-5]e\b", phrase, re.I)
                and items
                and ("环境" in items[0] or "環境" in items[0])
            ):
                items = items[1:]
            return phrase, items[:3]

    match = re.search(
        r"\|\s*(?:difficulty|class|level_class|levelclass|生存难度|难度)\s*=\s*([^\n|}]{1,48})",
        wikitext,
        re.I,
    )
    if match:
        raw = clean_inline(match.group(1))
        items = _template_items(wikitext[max(0, match.start() - 400):match.start() + 900])
        return raw, items[:3]

    for line in (clean_inline(item) for item in wikitext.splitlines()):
        label = _WIKITEXT_LABEL_RE.match(line)
        if not label:
            continue
        phrase = _class_phrase(clean_inline(label.group(1)), allow_bare=True) or _class_phrase(
            line, allow_bare=True
        )
        if phrase:
            return phrase, []
    return "", []


def _has_difficulty_hint(scope) -> bool:
    if re.search(
        r"生存难度|生存難度|难度|難度|survival\s+difficulty|difficulty",
        clean_inline(scope.text_content()),
        re.I,
    ):
        return True
    for node in scope.walk():
        classes = " ".join(node.classes).lower()
        if classes and any(hint in classes for hint in _CLASSY_HINTS):
            return True
        for attribute in ("alt", "title", "data-difficulty", "data-class"):
            if re.search(r"生存难度|difficulty|难度", node.get(attribute), re.I):
                return True
    return False


def _scan_standalone_class(root) -> tuple[str, list[str]]:
    """没有「生存难度」文字标签时：找本身就是 Class N 的短元素，看父级线索。"""
    for node in root.walk():
        if node.tag not in ("div", "p", "span", "td", "th", "li", "center", "b", "strong", "font"):
            continue
        text = clean_inline(node.text_content())
        if not text or len(text) > 28:
            continue
        if not _CLASS_WORD_RE.match(text):
            continue
        phrase = _class_phrase(text)
        if not phrase or len(phrase) < len(text) - 2:
            continue
        scope = node.parent or node
        if not _has_difficulty_hint(scope):
            continue
        raw, items = _parse_difficulty_lines(text_lines(scope))
        if raw:
            return raw, items
    return "", []


def _difficulty_from_html(root, content) -> tuple[str, list[str]]:
    # 1) 便携信息框
    for node in root.walk():
        source = (node.get("data-source") or "").strip().lower()
        if not source or source not in CLASS_DATA_SOURCES:
            continue
        value = node.find(cls="pi-data-value") or node
        raw, items = _parse_difficulty_lines(text_lines(value))
        if not raw:
            raw = _own_text(value)
        if not items:
            items = [clean_inline(li.text_content()).strip(" .。·") for li in value.find_all(tag="li")]
            items = [item for item in items if item]
        if raw or items:
            return raw, items[:3]

    # 2) class 名带 sd / difficulty / survival 提示的元素
    for node in root.walk():
        classes = " ".join(node.classes).lower()
        if not classes or not any(hint in classes for hint in _CLASSY_HINTS):
            continue
        raw, items = _parse_difficulty_lines(text_lines(node))
        if raw:
            return raw, items

    # 3) 表格行：<th>生存难度</th><td>Class 1</td>
    for row in root.find_all(tag="tr"):
        if not re.search(
            r"生存难度|生存難度|难度|難度|survival\s+difficulty|difficulty",
            clean_inline(row.text_content()),
            re.I,
        ):
            continue
        raw, items = _parse_difficulty_lines(text_lines(row))
        if raw:
            return raw, items

    # 4) 正文行「生存难度：…」
    lines = text_lines(content)
    for index, line in enumerate(lines):
        if re.match(
            r"^(?:" + _LABEL_PATTERN + r")(?=\s|[:：]|$|Class|等级|等級|[0-9])",
            line,
            re.I,
        ):
            raw, items = _parse_difficulty_lines(lines[index:index + 9])
            if raw:
                return raw, items

    # 5) 属性：图标 alt / title / data-*
    for node in root.walk():
        for attribute in ("data-difficulty", "data-class", "alt", "title"):
            value = clean_inline(node.get(attribute))
            if not value or len(value) > 48:
                continue
            # 链接的 title 往往是「Level 97」，不能当等级
            if attribute in ("alt", "title") and not _CLASS_WORD_RE.match(value):
                continue
            phrase = _class_phrase(
                value,
                allow_bare=attribute in ("data-difficulty", "data-class"),
            )
            if phrase:
                return phrase, []

    # 6) 没有文字标签时，靠「短元素 + 父级线索」识别
    raw, items = _scan_standalone_class(root)
    if raw:
        return raw, items

    # 7) 全文兜底
    match = re.search(
        r"\bClass\s*[0-9]{1,2}\s*[A-Za-z]?(?:\s*[-–—－]\s*[^\s》>]{1,14})?",
        _nfkc(content.text_content()),
        re.I,
    )
    if match:
        return clean_inline(match.group(0)), _difficulty_list(content)
    return "", _difficulty_list(content)


def extract_difficulty(root, content, wikitext: str = "") -> tuple[str, list[str]]:
    """Fandom 页面取生存难度：HTML 结构 → 正文 → 属性 → wikitext 模板源码。"""
    raw, items = _difficulty_from_html(root, content)
    wiki_raw, wiki_items = difficulty_from_wikitext(wikitext)
    if not raw:
        raw = wiki_raw
    if not items:
        items = wiki_items
    return raw, items[:3]


_ROMAN_CLASS_RE = re.compile(r"^class\s+[ivx]{1,4}\b", re.I)


def _normalize_roman_class(text: str, key: str) -> str:
    """Class V 这类罗马数字统一显示成 Class 5，避免误读。"""
    if key.isdigit() and _ROMAN_CLASS_RE.match(text or ""):
        return f"Class {key}"
    return text


def _complete_environment_suffix(text: str, key: str) -> str:
    """1e～5e 若页面只写了 Class 1e（后缀由模板/CSS 补），这里补上中文后缀。"""
    if not re.fullmatch(r"[1-5]e", key or ""):
        return text
    if "环境" in text or "環境" in text or "environmental" in text.lower():
        return text
    return f"{text} - 环境危害"


def split_display_title(text: str) -> tuple[str, str]:
    """解析 DISPLAYTITLE：Level ZH 38: "渴血之旧都" 或 Level ZH 37 "无限走廊"。"""
    text = clean_inline(text)
    match = re.match(
        r"^(?P<label>[^:：]{2,40}?)\s*[:：]\s*[“\"「『]?(?P<alias>.+?)[”\"」』]?$",
        text,
    )
    if match:
        label = clean_inline(match.group("label"))
        alias = clean_inline(match.group("alias")).strip("“”\"「」『』 ")
        return label, alias
    match = re.match(
        r"^(?P<label>.+?)\s+[“\"「『](?P<alias>.+?)[”\"」』]\s*$",
        text,
    )
    if match:
        label = clean_inline(match.group("label"))
        alias = clean_inline(match.group("alias")).strip("“”\"「」『』 ")
        return label, alias
    return split_title(text)


def parse_fandom_page(
    html: str,
    *,
    title: str,
    url: str,
    query: str = "",
    categories: list[str] | None = None,
    revision: str = "",
    updated: str = "",
    cached: bool = False,
    wikitext: str = "",
    displaytitle: str = "",
) -> LevelInfo:
    root = parse_html(html)
    content = (
        root.find(cls="mw-parser-output")
        or root.find(id="mw-content-text")
        or root
    )
    display = strip_tags(title)
    label = split_title(display)[0]
    full_title = strip_tags(displaytitle) or display
    _display_label, alias = split_display_title(full_title)
    alias = _safe_alias(alias)
    if not alias:
        for node in content.find_all(tag=("h1", "h2", "h3")):
            heading = strip_tags(node.text_content())
            if not heading or len(heading) > 80:
                continue
            heading_label, heading_alias = split_display_title(heading)
            if heading_alias and heading_label == label:
                alias = _safe_alias(heading_alias)
                break
    tags = [strip_tags(item) for item in (categories or []) if strip_tags(item)]
    raw_class, items = extract_difficulty(root, content, wikitext)
    class_text, class_key = build_class(raw_class, items, tags, content)
    class_text = _normalize_roman_class(class_text, class_key)
    class_text = _complete_environment_suffix(class_text, class_key)

    return LevelInfo(
        query=query,
        title=display,
        label=label,
        code=level_code(label, label),
        alias=alias,
        class_text=class_text,
        class_key=class_key,
        class_items=items,
        tags=tags,
        summary=extract_summary(content),
        quote=extract_quote(content),
        revision=str(revision or ""),
        updated_at=updated,
        url=url,
        page_key=display,
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        cached=cached,
    )


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        moment = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return value
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


class FandomClient(BaseClient):
    """后室中文 Fandom（MediaWiki）。"""

    key = "fandom"
    label = "Fandom"
    home_url = config.FANDOM_HOME

    def __init__(self, http: HttpClient | None = None) -> None:
        super().__init__(http)
        self._offline_until = 0.0

    # ---------------------------------------------------------------- API
    def _api(self, params: dict, force: bool = False, ttl: int | None = None) -> tuple[dict, bool]:
        query = {**params, "format": "json", "formatversion": "2", "utf8": "1"}
        url = f"{config.FANDOM_API}?{urlencode(query)}"
        cache_ttl = config.CACHE_TTL if ttl is None else ttl

        if time.time() < self._offline_until and not force:
            # 已熔断时仍然优先用缓存，避免离线状态下连看过的页面都打不开
            cached_text = self.http.peek_cache(url, cache_ttl)
            if cached_text is None:
                raise FetchError(self.last_error or "Fandom 暂时无法连接")
            text, cached = cached_text, True
        else:
            try:
                text, cached = self.http.get_text(
                    url,
                    force=force,
                    ttl=cache_ttl,
                    timeout=config.FANDOM_TIMEOUT,
                )
            except FetchError as exc:
                # 只有网络层/被拦截才熔断；HTTP 400 之类的接口错误仍可回退旧索引
                message = str(exc)
                if exc.status is None and not message.startswith("HTTP "):
                    self._offline_until = time.time() + 45
                self.last_error = message
                raise
        try:
            data = json.loads(text)
        except ValueError:
            self._offline_until = time.time() + 45
            self.last_error = "Fandom 返回内容不是 JSON，可能被网络拦截或需要人机验证"
            raise FetchError(self.last_error) from None
        if "error" in data:
            info = data["error"].get("info") or data["error"].get("code") or "未知错误"
            self.last_error = f"Fandom API：{info}"
            raise FetchError(self.last_error)
        return data, cached

    # ---------------------------------------------------------------- 索引
    def list_levels(self, force: bool = False) -> list[IndexEntry]:
        with self._lock:
            if self._index is not None and not force:
                return self._index

        entries: list[IndexEntry] = []
        errors: list[str] = []
        for prefix in config.FANDOM_INDEX_PREFIXES:
            got: list[IndexEntry] = []
            try:
                got = self._allpages(prefix, force)
            except FetchError as exc:
                errors.append(str(exc))
                try:
                    got = self._allpages_plain(prefix, force)
                except FetchError as fallback_exc:
                    errors.append(str(fallback_exc))
            entries.extend(got)
            if time.time() < self._offline_until and not got:
                break
        if not entries:
            try:
                entries.extend(self._category_members(force))
            except FetchError as exc:
                errors.append(str(exc))

        unique: dict[str, IndexEntry] = {}
        for entry in entries:
            if not _is_level_page_title(entry.slug):
                continue
            existing = unique.get(entry.slug)
            if existing is None:
                unique[entry.slug] = entry
            elif existing.title == existing.slug and entry.title != entry.slug:
                # 兜底索引没有名称时，用带 displaytitle 的条目覆盖
                unique[entry.slug] = entry
        entries = list(unique.values())
        if not entries and errors:
            self.last_error = errors[0]
        self._remember_index(entries)
        return entries

    def _allpages(self, prefix: str, force: bool) -> list[IndexEntry]:
        """带 DISPLAYTITLE 的索引：一次 500 条，侧边栏可直接显示层级名。"""
        out: list[IndexEntry] = []
        cont: dict = {}
        for _ in range(10):
            params = {
                "action": "query",
                "generator": "allpages",
                "gapnamespace": "0",
                "gapprefix": prefix,
                "gaplimit": "500",
                "prop": "info",
                "inprop": "displaytitle",
            }
            params.update(cont)
            data, _cached = self._api(params, force, ttl=config.INDEX_TTL)
            pages = (data.get("query") or {}).get("pages") or []
            if isinstance(pages, dict):
                pages = list(pages.values())
            for page in pages:
                entry = self._entry_from_page(page)
                if entry is not None:
                    out.append(entry)
            cont = data.get("continue") or {}
            if not cont:
                break
        return out

    @staticmethod
    def _entry_from_page(page: dict) -> IndexEntry | None:
        raw_title = (page.get("title") or "").strip()
        if not raw_title:
            return None
        display = strip_tags(page.get("displaytitle") or "")
        _label, alias = split_display_title(display or raw_title)
        alias = _safe_alias(alias)
        # 用页面真实标题做前缀，避免重写版/子页面显示成完全相同的名字
        title = f"{raw_title} - “{alias}”" if alias else raw_title
        return IndexEntry(slug=raw_title, title=title)

    def _allpages_plain(self, prefix: str, force: bool) -> list[IndexEntry]:
        """旧接口兜底：不带名称，但缓存命中时离线也能用。"""
        out: list[IndexEntry] = []
        cont: dict = {}
        for _ in range(10):
            params = {
                "action": "query",
                "list": "allpages",
                "apnamespace": "0",
                "apprefix": prefix,
                "aplimit": "500",
            }
            params.update(cont)
            data, _cached = self._api(params, force, ttl=config.INDEX_TTL)
            for page in (data.get("query") or {}).get("allpages") or []:
                title = (page.get("title") or "").strip()
                if title:
                    out.append(IndexEntry(slug=title, title=title))
            cont = data.get("continue") or {}
            if not cont:
                break
        return out

    def _category_members(self, force: bool) -> list[IndexEntry]:
        out: list[IndexEntry] = []
        cont: dict = {}
        for _ in range(5):
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": config.FANDOM_LEVEL_CATEGORY,
                "cmnamespace": "0",
                "cmlimit": "500",
            }
            params.update(cont)
            data, _cached = self._api(params, force, ttl=config.INDEX_TTL)
            for page in (data.get("query") or {}).get("categorymembers") or []:
                title = (page.get("title") or "").strip()
                if title:
                    out.append(IndexEntry(slug=title, title=title))
            cont = data.get("continue") or {}
            if not cont:
                break
        return out

    # ---------------------------------------------------------------- 解析
    def resolve(self, query: str) -> tuple[str, IndexEntry | None]:
        text = (query or "").strip()
        if not text:
            raise LevelNotFound("请输入层级编号，例如 0、1、0.1 或 C-156")

        entries = self.cached_index()
        if entries:
            entry = self._match(entries, text)
            if entry is not None:
                return entry.slug, entry

        title = self._lookup_title(text)
        if title:
            return title, None
        if time.time() < self._offline_until and self.last_error:
            raise FetchError(self.last_error)
        raise LevelNotFound(f"Fandom 上找不到「{text}」对应的页面")

    def _lookup_title(self, text: str) -> str:
        candidates = [text]
        if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
            candidates.append(f"Level {text}")
        for candidate in candidates:
            title = self._exact_title(candidate)
            if title:
                return title
        return self._search_title(text)

    def _exact_title(self, title: str) -> str:
        try:
            data, _cached = self._api(
                {"action": "query", "titles": title, "redirects": "1", "prop": "info"}
            )
        except FetchError:
            return ""
        for page in (data.get("query") or {}).get("pages") or []:
            if page.get("missing"):
                continue
            return (page.get("title") or "").strip()
        return ""

    def _search_title(self, text: str) -> str:
        try:
            data, _cached = self._api(
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": text,
                    "srlimit": "1",
                    "srnamespace": "0",
                }
            )
        except FetchError:
            return ""
        hits = (data.get("query") or {}).get("search") or []
        if hits:
            return (hits[0].get("title") or "").strip()
        return ""

    # ---------------------------------------------------------------- 抓取
    def fetch_page(
        self,
        locator: str,
        query: str = "",
        force: bool = False,
        entry: IndexEntry | None = None,
    ) -> LevelInfo:
        data, cached = self._api(
            {
                "action": "parse",
                "page": locator,
                "prop": "text|wikitext|displaytitle|categories|revid",
                "redirects": "1",
                "disableeditsection": "1",
            },
            force,
        )
        parsed = data.get("parse") or {}
        html = parsed.get("text")
        if isinstance(html, dict):
            html = html.get("*")
        wikitext = parsed.get("wikitext")
        if isinstance(wikitext, dict):
            wikitext = wikitext.get("*")
        wikitext = wikitext or ""
        if not html and not wikitext:
            raise LevelNotFound(f"Fandom 上找不到「{query or locator}」对应的页面")

        title = strip_tags(parsed.get("title") or locator) or locator
        categories = []
        for item in parsed.get("categories") or []:
            name = item.get("category") or item.get("*") or ""
            if name:
                categories.append(strip_tags(name))

        info = parse_fandom_page(
            html or "",
            title=title,
            url=config.FANDOM_WIKI + quote(title.replace(" ", "_")),
            query=query or locator,
            categories=categories,
            revision=str(parsed.get("revid") or ""),
            updated=self._updated_at(title, force),
            cached=cached,
            wikitext=wikitext,
            displaytitle=parsed.get("displaytitle") or "",
        )
        if entry is not None and not info.alias:
            _, alias = split_title(entry.title)
            info.alias = alias
        return info

    def _updated_at(self, title: str, force: bool) -> str:
        try:
            data, _cached = self._api(
                {
                    "action": "query",
                    "prop": "revisions",
                    "rvprop": "timestamp",
                    "rvlimit": "1",
                    "titles": title,
                    "redirects": "1",
                },
                force,
            )
        except FetchError:
            return ""
        pages = (data.get("query") or {}).get("pages") or []
        for page in pages:
            revisions = page.get("revisions") or []
            if revisions:
                return _format_timestamp(revisions[0].get("timestamp") or "")
        return ""
