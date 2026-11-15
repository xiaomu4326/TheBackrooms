"""界面配色与 ttk 主题。整体走浅色纸感 + 后室黄作为强调色。"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG = "#F4F1E8"          # 窗口底色
PANEL = "#FFFFFF"       # 卡片
PANEL_SOFT = "#FBF8F1"  # 次级卡片
INK = "#211E1A"         # 主文字
MUTED = "#857D6F"       # 次要文字
LINE = "#E4DED0"        # 分隔线
ACCENT = "#C6952D"      # 强调色（后室黄）
ACCENT_DARK = "#8C6714"
ACCENT_SOFT = "#F1E4C2"
CHIP_BG = "#F2EEE2"
CHIP_FG = "#5D5648"
DANGER = "#B04A32"

FONT_FAMILY = "Microsoft YaHei UI"
FONT_FALLBACK = ("Microsoft YaHei", "微软雅黑", "Segoe UI", "Arial")


def pick_font_family(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    if FONT_FAMILY in available:
        return FONT_FAMILY
    for name in FONT_FALLBACK:
        if name in available:
            return name
    return "TkDefaultFont"


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_text(rgb: tuple[int, int, int]) -> str:
    return "#141210" if luminance(rgb) > 0.62 else "#FFFFFF"


def hex_color(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def blend(rgb: tuple[int, int, int], other: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return tuple(round(a + (b - a) * ratio) for a, b in zip(rgb, other))  # type: ignore[return-value]


class Theme:
    """统一管理字体与 ttk 样式。"""

    def __init__(self, root: tk.Tk) -> None:
        self.family = pick_font_family(root)
        self.font_body = (self.family, 10)
        self.font_small = (self.family, 9)
        self.font_section = (self.family, 10, "bold")
        self.font_title = (self.family, 21, "bold")
        self.font_alias = (self.family, 14)
        self.font_class = (self.family, 19, "bold")
        self.chip_font = tkfont.Font(root=root, family=self.family, size=9)
        self._style = ttk.Style(root)
        self._style.theme_use("clam")
        self._configure(root)

    def _configure(self, root: tk.Tk) -> None:
        style = self._style
        style.configure(".", background=BG, foreground=INK, font=self.font_body)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("Soft.TFrame", background=PANEL_SOFT)

        style.configure("TLabel", background=BG, foreground=INK, font=self.font_body)
        style.configure("Card.TLabel", background=PANEL, foreground=INK)
        style.configure("Title.TLabel", background=BG, foreground=INK, font=self.font_title)
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=self.font_small)
        style.configure("CardSub.TLabel", background=PANEL, foreground=MUTED, font=self.font_small)
        style.configure("Section.TLabel", background=PANEL, foreground=ACCENT_DARK, font=self.font_section)
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)

        style.configure(
            "Search.TEntry",
            fieldbackground=PANEL,
            foreground=INK,
            bordercolor="#D9D0BC",
            lightcolor=PANEL,
            darkcolor=PANEL,
            insertcolor=INK,
            padding=(12, 9),
        )
        style.map(
            "Search.TEntry",
            bordercolor=[("focus", ACCENT)],
            lightcolor=[("focus", PANEL)],
            darkcolor=[("focus", PANEL)],
        )

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#2A2109",
            borderwidth=0,
            focusthickness=0,
            padding=(16, 8),
            font=(self.family, 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", ACCENT_DARK), ("active", "#D9A63A")],
            foreground=[("pressed", "#FFFFFF")],
        )
        style.configure(
            "Ghost.TButton",
            background=PANEL,
            foreground=MUTED,
            borderwidth=0,
            padding=(12, 7),
            font=(self.family, 9),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", PANEL_SOFT)],
            foreground=[("active", ACCENT_DARK)],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=LINE,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            width=10,
        )
        style.map("Vertical.TScrollbar", background=[("active", "#CFC7B4")])
        root.option_add("*Font", self.font_body)
