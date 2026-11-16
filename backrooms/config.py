"""全局配置：站点地址、缓存策略、生存难度配色。"""

from __future__ import annotations

import pathlib
from urllib.parse import quote

APP_VERSION = "1.0.2"
APP_TITLE = f"后室层级档案 · Backrooms CN 查询器 v{APP_VERSION}"
APP_SUBTITLE = "数据来源：backrooms-wiki-cn.wikidot.com"

# 网络：桌面端默认重试 3 次；移动端可在 mobile.init 里调低
HTTP_RETRIES = 3

BASE_URL = "https://backrooms-wiki-cn.wikidot.com"
LEVEL_INDEX_URL = f"{BASE_URL}/system:page-tags/tag/{quote('层级')}"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)

REQUEST_TIMEOUT = 25
MIN_REQUEST_INTERVAL = 0.7
# 缓存永久保留，只有手动刷新或设置页清理才会更新/删除。
# -1 表示不做时间过期判断，避免大陆网络慢时反复重新抓取。
CACHE_TTL = -1
INDEX_TTL = -1

CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent / "cache"

# 组件 component:level-class / component:sd-class 中定义的等级配色
CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "0": (247, 227, 117),
    "1": (255, 201, 14),
    "2": (245, 156, 0),
    "3": (249, 90, 0),
    "4": (254, 23, 1),
    "5": (175, 6, 6),
    "unknown": (38, 38, 38),
    "未知": (38, 38, 38),
    "habitable": (26, 128, 111),
    "宜居": (26, 128, 111),
    "deadzone": (44, 13, 12),
    "死区": (44, 13, 12),
    "pending": (182, 182, 182),
    "等待分级": (182, 182, 182),
    "n/a": (38, 38, 38),
    "不适用": (38, 38, 38),
    "amended": (185, 135, 212),
    "修正": (185, 135, 212),
    "omega": (25, 46, 255),
    "终结": (25, 46, 255),
    "1e": (129, 178, 154),
    "2e": (96, 152, 130),
    "3e": (62, 122, 106),
    "4e": (36, 94, 86),
    "5e": (16, 66, 64),
    "environmental": (129, 178, 154),
    "其他": (120, 116, 108),
    "other": (120, 116, 108),
}
FALLBACK_CLASS_COLOR = (120, 116, 108)

# 生存难度标签前缀，例如「生存难度1」
CLASS_TAG_PREFIX = "生存难度"

# Wikidot 额外分类：隐秘层级用官方列表页，玩笑层级用标签
WIKIDOT_HIDDEN_LIST_URL = f"{BASE_URL}/enigmatic-levels"
WIKIDOT_EXTRA_TAGS = {
    "joke": "搞笑",
}

# ------------------------------------------------------------------ 数据源
# Fandom 中文后室使用 MediaWiki 的 /zh 语言路径，接口与页面都在同一前缀下。
FANDOM_HOME = "https://backrooms.fandom.com/zh"
FANDOM_API = f"{FANDOM_HOME}/api.php"
FANDOM_WIKI = f"{FANDOM_HOME}/wiki/"
FANDOM_INDEX_PREFIXES = ("Level", "Level ZH", "Level C", "楼层", "層級")
FANDOM_LEVEL_CATEGORY = "Category:楼层"
FANDOM_TIMEOUT = 12

SOURCE_LABELS = {"wikidot": "Wikidot", "fandom": "Fandom"}
SOURCE_HOMES = {
    "wikidot": "backrooms-wiki-cn.wikidot.com",
    "fandom": "backrooms.fandom.com/zh",
}
DEFAULT_SOURCE = "wikidot"
