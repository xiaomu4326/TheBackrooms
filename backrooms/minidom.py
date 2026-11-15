"""极简 HTML → 节点树解析器（仅用标准库）。

只做本项目需要的事情：把标签树建起来，支持按 tag / class / id 查找节点，
并抽取纯文本。Wikidot 输出的是 XHTML，标签基本闭合，所以逻辑可以保持简单。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Callable, Iterator

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# 取文本时默认跳过的标签与 class（后者用于略去繁体重复内容）
SKIP_TAGS = {"script", "style"}
SKIP_CLASSES = {"lang-tr"}

_WS_RE = re.compile(r"[ \t\r\f\v\u00a0]+")


class Node:
    """一个 HTML 节点。文本节点用 tag='#text' 表示。"""

    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag: str, attrs: dict[str, str] | None = None, text: str = ""):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list[Node] = []
        self.parent: Node | None = None
        self.text = text

    # ---------- 基本属性 ----------
    @property
    def classes(self) -> set[str]:
        raw = self.attrs.get("class") or ""
        return {c for c in raw.split() if c}

    def get(self, name: str, default: str = "") -> str:
        return self.attrs.get(name, default) or default

    def append(self, child: "Node") -> None:
        child.parent = self
        self.children.append(child)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        sample = squash(self.text_content())[:40]
        return f"<{self.tag} class={self.get('class')!r} id={self.get('id')!r}> {sample!r}"

    # ---------- 遍历与查询 ----------
    def walk(self) -> Iterator["Node"]:
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def ancestors(self) -> Iterator["Node"]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def find_all(
        self,
        tag: str | tuple[str, ...] | None = None,
        cls: str | None = None,
        id: str | None = None,
        pred: Callable[["Node"], bool] | None = None,
    ) -> list["Node"]:
        tags = (tag,) if isinstance(tag, str) else tag
        result: list[Node] = []
        for node in self.walk():
            if node is self:
                continue
            if tags is not None and node.tag not in tags:
                continue
            if cls is not None and cls not in node.classes:
                continue
            if id is not None and node.get("id") != id:
                continue
            if pred is not None and not pred(node):
                continue
            result.append(node)
        return result

    def find(
        self,
        tag: str | tuple[str, ...] | None = None,
        cls: str | None = None,
        id: str | None = None,
        pred: Callable[["Node"], bool] | None = None,
    ) -> "Node | None":
        found = self.find_all(tag=tag, cls=cls, id=id, pred=pred)
        return found[0] if found else None

    def find_all_prefix(self, prefix: str) -> list["Node"]:
        """按 class 前缀查找，例如 'bottom-text' 同时命中 bottom-text / bottom-text-a。"""
        return [
            n for n in self.walk()
            if n is not self and any(c.startswith(prefix) for c in n.classes)
        ]

    # ---------- 文本 ----------
    def text_content(
        self,
        skip_tags: set[str] | None = None,
        skip_classes: set[str] | None = None,
        br: str = "\n",
    ) -> str:
        skip_tags = SKIP_TAGS if skip_tags is None else skip_tags
        skip_classes = SKIP_CLASSES if skip_classes is None else skip_classes
        out: list[str] = []

        def rec(node: Node) -> None:
            for child in node.children:
                if child.tag == "#text":
                    out.append(child.text)
                    continue
                if child.tag in skip_tags:
                    continue
                if skip_classes and child.classes & skip_classes:
                    continue
                if child.tag == "br":
                    out.append(br)
                    continue
                rec(child)

        rec(self)
        return "".join(out)


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack: list[Node] = [self.root]

    def handle_starttag(self, tag: str, attrs) -> None:
        node = Node(tag, {k: (v or "") for k, v in attrs})
        self.stack[-1].append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs) -> None:
        node = Node(tag, {k: (v or "") for k, v in attrs})
        self.stack[-1].append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].append(Node("#text", text=data))


def parse_html(html: str) -> Node:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def squash(text: str) -> str:
    """压缩空白：行内空格合并，空行去掉。"""
    if not text:
        return ""
    text = _WS_RE.sub(" ", text)
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def clean_inline(text: str) -> str:
    """单行文本：所有空白压成单个空格。"""
    return " ".join((text or "").split())
