"""数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class LevelInfo:
    """一个层级页面的结构化信息。"""

    query: str = ""             # 用户输入的原始内容
    title: str = ""             # 页面标题原文，如 Level 0 - “教学关卡”
    label: str = ""             # 层级标签，如 Level 0
    code: str = ""              # 层级编号，如 0 / 0.1 / C-156
    alias: str = ""             # 别称，如 教学关卡
    class_text: str = ""        # 生存难度原文，如 等级 1
    class_key: str = ""         # 归一化等级，如 1 / unknown / 终结
    class_items: list[str] = field(default_factory=list)  # 难度三条描述
    tags: list[str] = field(default_factory=list)
    summary: str = ""           # 正文摘要
    quote: str = ""             # 开篇引文
    revision: str = ""          # 页面版本，如 87
    updated_at: str = ""        # 最后编辑时间
    url: str = ""
    page_key: str = ""          # 站点内的定位符：Wikidot 是 slug，Fandom 是页面标题
    fetched_at: str = ""
    cached: bool = False

    @property
    def display_name(self) -> str:
        if self.alias:
            return f"{self.label} · “{self.alias}”"
        return self.label or self.title or self.query

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LevelInfo":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True)
class IndexEntry:
    """层级索引里的一条记录。"""

    slug: str
    title: str
    tags: tuple[str, ...] = ()  # 额外分类标记，如 hidden / joke

    def to_dict(self) -> dict:
        return {"slug": self.slug, "title": self.title, "tags": list(self.tags)}

    @classmethod
    def from_dict(cls, data: dict) -> "IndexEntry":
        return cls(
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            tags=tuple(data.get("tags") or ()),
        )
