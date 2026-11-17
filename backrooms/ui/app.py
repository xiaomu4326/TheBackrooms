"""主窗口。左侧层级索引，右侧档案卡片。"""

from __future__ import annotations

import queue
import random
import threading
import time
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

from .. import config, groups
from ..base import BaseClient
from ..models import IndexEntry, LevelInfo
from ..service import LevelNotFound, create_client
from . import theme as th


@dataclass
class _Row:
    """列表里的一行：分组标题或层级条目。"""

    kind: str                      # "group" | "entry"
    key: str = ""
    entry: IndexEntry | None = None
    depth: int = 0                 # 0=分组标题，1=上级层级，2=子层级
    child_count: int = 0
    expanded: bool = False


class ChipRow(tk.Frame):
    """自动换行的标签块。"""

    def __init__(self, master: tk.Misc, font, bg: str = th.PANEL,
                 chip_bg: str = th.CHIP_BG, chip_fg: str = th.CHIP_FG, **kwargs) -> None:
        super().__init__(master, bg=bg, **kwargs)
        self._font = font
        self._chip_bg = chip_bg
        self._chip_fg = chip_fg
        self._chips: list[tk.Label] = []
        self.bind("<Configure>", lambda _event: self._layout())

    def set_chips(self, texts: list[str]) -> None:
        for chip in self._chips:
            chip.destroy()
        self._chips = []
        for text in texts:
            chip = tk.Label(
                self, text=text, font=self._font, bg=self._chip_bg,
                fg=self._chip_fg, padx=8, pady=2,
            )
            self._chips.append(chip)
        self._layout()

    def _layout(self) -> None:
        if not self._chips:
            self.configure(height=1)
            return
        width = self.winfo_width()
        if width <= 1:
            width = 560
        x = y = 0
        gap, row_h = 6, 0
        height = self._font.metrics("linespace") + 8
        for chip in self._chips:
            chip_w = self._font.measure(chip.cget("text")) + 18
            if x and x + chip_w > width:
                x, y = 0, y + row_h + gap
                row_h = 0
            chip.place(x=x, y=y, width=chip_w, height=height)
            x += chip_w + gap
            row_h = max(row_h, height)
        self.configure(height=y + row_h)


class BackroomsApp(tk.Tk):
    def __init__(self, client: BaseClient | None = None, source: str = config.DEFAULT_SOURCE) -> None:
        super().__init__()
        self.source_key = source if client is None else client.key
        self.client: BaseClient = client or create_client(self.source_key)
        self.theme = th.Theme(self)
        self.entries: list[IndexEntry] = []
        self.filtered: list[IndexEntry] = []
        self.current: LevelInfo | None = None
        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        self._generation = 0
        self._request_generation = 0
        self._index_ready = False
        self._rows: list[_Row] = []
        self._expanded: dict[str, bool] = groups.default_expanded()
        self._expanded_parents: set[str] = set()
        self._expanded_ranges: set[str] = set()
        self._last_toggle = 0.0
        self._last_toggle_key = ""

        self.title(config.APP_TITLE)
        self.geometry("1140x780")
        self.minsize(980, 640)
        self.configure(bg=th.BG)

        self._window_icon = None
        try:
            icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
            self._window_icon = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, self._window_icon)
        except Exception:
            self._window_icon = None

        self._build_ui()
        self._render_placeholder()
        self.bind("<Control-f>", lambda _e: self.search_entry.focus_set())
        self.bind("<Control-r>", lambda _e: self._refresh_current())
        self.bind("<F1>", lambda _e: self._show_settings())
        self.after(120, self.search_entry.focus_set)
        self._poll()
        self.after(150, self._load_index_async)

    # ------------------------------------------------------------------ 布局
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        body = tk.Frame(self, bg=th.BG)
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 6))
        body.grid_columnconfigure(0, minsize=280, weight=0)
        body.grid_columnconfigure(1, weight=1, minsize=540)
        body.grid_rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_main_panel(body)

        status = tk.Frame(self, bg=th.BG)
        status.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 10))
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(status, textvariable=self.status_var, bg=th.BG, fg=th.MUTED,
                 font=self.theme.font_small, anchor="w").pack(side="left")
        tk.Label(status, text="缓存目录 cache/", bg=th.BG, fg=th.MUTED,
                 font=self.theme.font_small, anchor="e").pack(side="right")

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=th.BG)
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 12))

        text_box = tk.Frame(header, bg=th.BG)
        text_box.pack(side="left")
        tk.Label(text_box, text="后室层级档案", bg=th.BG, fg=th.INK,
                 font=self.theme.font_title, anchor="w").pack(anchor="w")
        self.subtitle_var = tk.StringVar(value=f"数据来源：{config.SOURCE_HOMES[self.source_key]}")
        tk.Label(text_box, textvariable=self.subtitle_var, bg=th.BG, fg=th.MUTED,
                 font=self.theme.font_small, anchor="w").pack(anchor="w", pady=(2, 0))

        right_box = tk.Frame(header, bg=th.BG)
        right_box.pack(side="right")
        self._build_source_switch(right_box)
        hint_row = tk.Frame(right_box, bg=th.BG)
        hint_row.pack(anchor="e", pady=(6, 0))
        tk.Label(hint_row, text="Enter 查询 · 双击列表打开 · Esc 清空", bg=th.BG,
                 fg=th.MUTED, font=self.theme.font_small).pack(side="left")
        about = tk.Label(hint_row, text="设置", bg=th.BG, fg=th.ACCENT_DARK,
                         font=(self.theme.family, 9, "bold"), cursor="hand2")
        about.pack(side="left", padx=(14, 0))
        about.bind("<Button-1>", lambda _event: self._show_settings())

    @staticmethod
    def _format_bytes(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        if size < 1024 ** 3:
            return f"{size / 1024 ** 2:.1f} MB"
        return f"{size / 1024 ** 3:.2f} GB"

    def _cache_stats_text(self) -> str:
        files = [path for path in config.CACHE_DIR.glob("*.json") if path.is_file()]
        size = 0
        for path in files:
            try:
                size += path.stat().st_size
            except OSError:
                pass
        return f"{len(files)} 个缓存文件 · {self._format_bytes(size)}"

    def _clear_cache(self) -> int:
        removed = 0
        for path in config.CACHE_DIR.glob("*"):
            if not path.is_file():
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
        self._generation += 1
        self.client = create_client(self.source_key)
        self.entries = []
        self.filtered = []
        self.current = None
        self._expanded = groups.default_expanded()
        self._expanded_parents = set()
        self._expanded_ranges = set()
        self.listbox.delete(0, "end")
        self._rows = []
        self.count_var.set("0")
        self.query_var.set("")
        self._render_placeholder()
        self._set_status(f"缓存已清理（删除 {removed} 个文件）")
        return removed

    def _show_settings(self) -> None:
        win = tk.Toplevel(self)
        win.title("设置 · 后室层级档案")
        win.configure(bg=th.BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.geometry("420x500")

        card = tk.Frame(win, bg=th.PANEL, highlightthickness=1,
                        highlightbackground=th.LINE)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        inner = tk.Frame(card, bg=th.PANEL, padx=20, pady=18)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="设置", bg=th.PANEL, fg=th.INK,
                 font=(self.theme.family, 18, "bold")).pack(anchor="w")
        tk.Label(inner, text="缓存", bg=th.PANEL, fg=th.ACCENT_DARK,
                 font=(self.theme.family, 11, "bold")).pack(anchor="w", pady=(18, 4))
        tk.Label(
            inner,
            text="缓存永久保留，不会自动过期或删除。只有手动清理，或点击刷新按钮时才更新。",
            bg=th.PANEL, fg=th.MUTED, font=self.theme.font_small,
            wraplength=340, justify="left",
        ).pack(anchor="w")

        stats_var = tk.StringVar(value=self._cache_stats_text())
        tk.Label(inner, textvariable=stats_var, bg=th.PANEL, fg=th.INK,
                 font=(self.theme.family, 11, "bold")).pack(anchor="w", pady=(10, 8))

        actions = tk.Frame(inner, bg=th.PANEL)
        actions.pack(fill="x")
        def clear():
            if not messagebox.askyesno(
                "清理缓存",
                "清理后，下次查询需要重新从站点下载。确定清理吗？",
                parent=win,
            ):
                return
            self._clear_cache()
            stats_var.set(self._cache_stats_text())

        ttk.Button(actions, text="清理缓存", style="Accent.TButton",
                   command=clear).pack(side="left")
        ttk.Button(actions, text="刷新统计", style="Ghost.TButton",
                   command=lambda: stats_var.set(self._cache_stats_text())).pack(
            side="left", padx=(8, 0))

        tk.Frame(inner, bg=th.LINE, height=1).pack(fill="x", pady=(18, 14))
        tk.Label(inner, text="关于", bg=th.PANEL, fg=th.ACCENT_DARK,
                 font=(self.theme.family, 11, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(inner, text="版本、许可证与 GitHub 仓库", bg=th.PANEL,
                 fg=th.MUTED, font=self.theme.font_small).pack(anchor="w")
        ttk.Button(inner, text="打开关于", style="Ghost.TButton",
                   command=lambda: (win.destroy(), self._show_about())).pack(
            anchor="w", pady=(8, 0))

        ttk.Button(inner, text="返回", style="Ghost.TButton",
                   command=win.destroy).pack(side="bottom", anchor="e", pady=(16, 0))
        win.bind("<Escape>", lambda _event: win.destroy())
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _show_about(self) -> None:
        win = tk.Toplevel(self)
        win.title("关于 · 后室层级档案")
        win.configure(bg=th.BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.geometry("390x700")

        card = tk.Frame(win, bg=th.PANEL, highlightthickness=1,
                        highlightbackground=th.LINE)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        inner = tk.Frame(card, bg=th.PANEL, padx=20, pady=18)
        inner.pack(fill="both", expand=True)

        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        try:
            icon = tk.PhotoImage(file=str(icon_path)).subsample(4)
            self._about_icon = icon
            tk.Label(inner, image=icon, bg=th.PANEL).pack()
        except Exception:
            pass

        tk.Label(inner, text="后室层级档案", bg=th.PANEL, fg=th.INK,
                 font=(self.theme.family, 18, "bold")).pack(pady=(10, 0))
        tk.Label(inner, text=f"v{config.APP_VERSION}", bg=th.PANEL, fg=th.MUTED,
                 font=self.theme.font_small).pack(pady=(2, 8))
        tk.Label(
            inner,
            text="把后室中文维基的层级档案收进一个查询器：支持 Wikidot / Fandom、"
                 "层级分组、子层级展开、生存难度与详情页。",
            bg=th.PANEL, fg=th.INK, font=self.theme.font_body,
            wraplength=310, justify="left",
        ).pack(fill="x", pady=(0, 12))

        info = tk.Frame(inner, bg="#F4EDE0", padx=12, pady=10)
        info.pack(fill="x")
        for label, value in (
            ("版本", config.APP_VERSION),
            ("许可证", "代码 MIT · 维基内容 CC BY-SA 3.0"),
            ("数据源", "Wikidot / Fandom"),
        ):
            row = tk.Frame(info, bg="#F4EDE0")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg="#F4EDE0", fg=th.MUTED, width=7,
                     anchor="w", font=self.theme.font_small).pack(side="left")
            tk.Label(row, text=value, bg="#F4EDE0", fg=th.INK, anchor="w",
                     font=self.theme.font_small).pack(side="left", fill="x", expand=True)

        tk.Label(inner, text="GitHub 仓库", bg=th.PANEL, fg=th.MUTED,
                 font=(self.theme.family, 9, "bold")).pack(anchor="w", pady=(14, 2))
        repo = tk.Label(inner, text="https://github.com/xiaomu4326/TheBackrooms",
                        bg=th.PANEL, fg=th.ACCENT_DARK,
                        font=(self.theme.family, 9, "underline"), cursor="hand2")
        repo.pack(anchor="w")
        repo.bind("<Button-1>", lambda _event: webbrowser.open(
            "https://github.com/xiaomu4326/TheBackrooms"))
        tk.Label(
            inner,
            text="维基文本版权归后室中文维基 / Fandom 及作者所有，遵循 CC BY-SA 3.0。",
            bg=th.PANEL, fg=th.MUTED, font=self.theme.font_small,
            wraplength=310, justify="left",
        ).pack(anchor="w", pady=(14, 0))

        ttk.Button(inner, text="返回", style="Ghost.TButton",
                   command=win.destroy).pack(side="bottom", anchor="e", pady=(14, 0))
        win.bind("<Escape>", lambda _event: win.destroy())
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build_source_switch(self, parent: tk.Misc) -> None:
        box = tk.Frame(parent, bg=th.BG)
        box.pack(anchor="e")
        tk.Label(box, text="数据源", bg=th.BG, fg=th.MUTED,
                 font=self.theme.font_small).pack(side="left", padx=(0, 8))
        self._source_tabs: dict[str, tk.Label] = {}
        for key in ("wikidot", "fandom"):
            tab = tk.Label(
                box, text=config.SOURCE_LABELS[key], bg=th.PANEL, fg=th.MUTED,
                font=(self.theme.family, 9, "bold"), padx=14, pady=5,
                highlightthickness=1, highlightbackground=th.LINE, cursor="hand2",
            )
            tab.pack(side="left", padx=(0, 6))
            tab.bind("<Button-1>", lambda _event, k=key: self._switch_source(k))
            self._source_tabs[key] = tab
        self._style_source_tabs()

    def _style_source_tabs(self) -> None:
        for key, tab in self._source_tabs.items():
            active = key == self.source_key
            tab.configure(
                bg=th.ACCENT_SOFT if active else th.PANEL,
                fg=th.ACCENT_DARK if active else th.MUTED,
                highlightbackground=th.ACCENT if active else th.LINE,
            )

    def _switch_source(self, key: str) -> None:
        if key == self.source_key or key not in config.SOURCE_LABELS:
            return
        self.source_key = key
        self.client = create_client(key)
        self._generation += 1
        self._style_source_tabs()
        self.subtitle_var.set(f"数据来源：{config.SOURCE_HOMES[key]}")
        self.hint_var.set(self._search_hint())
        self.entries = []
        self.filtered = []
        self.current = None
        self._index_ready = False
        self._rows = []
        self._expanded = groups.default_expanded()
        self._expanded_parents = set()
        self._expanded_ranges = set()
        self.listbox.delete(0, "end")
        self.count_var.set("加载中…")
        self.query_var.set("")
        self._render_placeholder()
        self._set_busy(False, f"已切换到 {config.SOURCE_LABELS[key]}，正在加载索引…")
        self._load_index_async()

    def _search_hint(self) -> str:
        if self.source_key == "fandom":
            return "可输入 0、0.1、37，或直接搜页面标题（例如 Level 0）"
        return "可输入 0、0.1、C-156、Level 37，或直接搜「教学关卡」这类别称"

    def _build_sidebar(self, parent: tk.Misc) -> None:
        card = tk.Frame(parent, bg=th.PANEL, highlightbackground=th.LINE, highlightthickness=1)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        head = tk.Frame(card, bg=th.PANEL)
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        tk.Label(head, text="层级列表", bg=th.PANEL, fg=th.ACCENT_DARK,
                 font=self.theme.font_section).pack(side="left")
        self.count_var = tk.StringVar(value="加载中…")
        tk.Label(head, textvariable=self.count_var, bg=th.PANEL, fg=th.MUTED,
                 font=self.theme.font_small).pack(side="right")

        self._filter_placeholder = "筛选编号或名称…"
        self._filter_show_placeholder = True
        self.filter_var = tk.StringVar(value=self._filter_placeholder)
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        self.filter_entry = tk.Entry(
            card, textvariable=self.filter_var, bg=th.PANEL, fg=th.MUTED,
            insertbackground=th.INK, relief="flat", highlightthickness=1,
            highlightbackground="#D9D0BC", highlightcolor=th.ACCENT,
            font=self.theme.font_small,
        )
        self.filter_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 0), ipady=6)
        self.filter_entry.bind("<FocusIn>", self._on_filter_focus_in)
        self.filter_entry.bind("<FocusOut>", self._on_filter_focus_out)

        tk.Label(card, text="点击分组标题展开；带 ▸ 的层级可展开子层级", bg=th.PANEL, fg=th.MUTED,
                 font=(self.theme.family, 8)).grid(
            row=2, column=0, sticky="w", padx=17, pady=(4, 2))

        list_wrap = tk.Frame(card, bg=th.PANEL)
        list_wrap.grid(row=3, column=0, sticky="nsew", padx=(10, 8), pady=(2, 10))
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_wrap, activestyle="none", bd=0, highlightthickness=0,
            bg=th.PANEL, fg=th.INK, selectbackground="#E8D8B0",
            selectforeground=th.INK, font=self.theme.font_small,
            selectborderwidth=0, exportselection=False,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.listbox.yview,
                               style="Vertical.TScrollbar")
        scroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind("<ButtonRelease-1>", self._on_list_click)
        self.listbox.bind("<Double-Button-1>", self._on_list_double)
        self.listbox.bind("<Return>", self._on_list_enter)

    def _build_main_panel(self, parent: tk.Misc) -> None:
        card = tk.Frame(parent, bg=th.PANEL, highlightbackground=th.LINE, highlightthickness=1)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        search = tk.Frame(card, bg=th.PANEL)
        search.grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 6))
        search.grid_columnconfigure(0, weight=1)

        self.query_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.query_var, style="Search.TEntry",
                          font=(self.theme.family, 11))
        entry.grid(row=0, column=0, sticky="ew")
        entry.bind("<Return>", lambda _e: self._do_search())
        entry.bind("<Escape>", lambda _e: self.query_var.set(""))
        self.search_entry = entry

        self.search_button = ttk.Button(search, text="查询", style="Accent.TButton",
                                        command=self._do_search)
        self.search_button.grid(row=0, column=1, padx=(10, 0))
        ttk.Button(search, text="随机", style="Ghost.TButton",
                   command=self._random_level).grid(row=0, column=2, padx=(6, 0))

        self.hint_var = tk.StringVar(value=self._search_hint())
        tk.Label(card, textvariable=self.hint_var,
                 bg=th.PANEL, fg=th.MUTED, font=(self.theme.family, 8)).grid(
            row=1, column=0, sticky="w", padx=24, pady=(0, 8))

        self.detail = tk.Frame(card, bg=th.PANEL)
        self.detail.grid(row=2, column=0, sticky="nsew")

    # ------------------------------------------------------------------ 数据
    def _load_index_async(self, force: bool = False) -> None:
        self._set_status(f"正在获取 {self.client.label} 层级索引…")
        generation = self._generation
        threading.Thread(
            target=self._index_worker, args=(force, generation), daemon=True
        ).start()

    def _index_worker(self, force: bool, generation: int) -> None:
        entries = self.client.list_levels(force=force)
        self._queue.put(("index", generation, entries))

    def _start_fetch(self, query: str, force: bool,
                     entry: IndexEntry | None = None) -> None:
        """立即开始新请求；旧请求返回时按编号丢弃，不阻塞切换。"""
        self._request_generation += 1
        request_id = self._request_generation
        self._set_busy(True, f"正在打开「{entry.title}」…" if entry else f"正在查询「{query}」…")
        threading.Thread(
            target=self._fetch_worker,
            args=(query, force, entry, request_id),
            daemon=True,
        ).start()

    def _do_search(self) -> None:
        query = self.query_var.get().strip()
        if not query:
            self._set_status("请输入层级编号")
            return
        if not self._index_ready:
            self._set_status("索引还在加载，请稍候再查询")
            return
        self._start_fetch(query, False)

    def _selected_row(self) -> _Row | None:
        selection = self.listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def _on_list_click(self, event) -> None:
        """单击分组标题或带子层级的上级层级，展开 / 收起。"""
        if self._filter_keyword():
            return
        index = self.listbox.nearest(event.y)
        if not 0 <= index < len(self._rows):
            return
        bbox = self.listbox.bbox(index)
        if bbox is not None and not (bbox[1] <= event.y <= bbox[1] + bbox[3]):
            return
        row = self._rows[index]
        if row.kind == "group":
            target = f"group:{row.key}"
        elif row.kind == "range":
            target = f"range:{row.key}"
        elif row.kind == "entry" and row.child_count:
            target = f"entry:{row.key}"
        else:
            return
        now = time.time()
        if target == self._last_toggle_key and now - self._last_toggle < 0.25:
            return
        self._last_toggle_key = target
        self._last_toggle = now
        if row.kind == "group":
            self._toggle_group(row.key)
        elif row.kind == "range":
            self._toggle_range(row.key)
        else:
            self._toggle_parent(row.key)

    def _on_list_double(self, _event=None) -> None:
        row = self._selected_row()
        if row is None or row.kind != "entry" or row.entry is None:
            return
        self.query_var.set(row.entry.title)
        self._open_entry(row.entry)

    def _on_list_enter(self, _event=None) -> None:
        row = self._selected_row()
        if row is None:
            return
        if row.kind == "group":
            self._toggle_group(row.key)
        elif row.kind == "range":
            self._toggle_range(row.key)
        elif row.entry is not None:
            self.query_var.set(row.entry.title)
            self._open_entry(row.entry)

    def _toggle_group(self, key: str) -> None:
        self._expanded[key] = not self._expanded.get(key, False)
        self._apply_filter()
        for index, row in enumerate(self._rows):
            if row.kind == "group" and row.key == key:
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(index)
                self.listbox.see(index)
                break

    def _toggle_range(self, key: str) -> None:
        if key in self._expanded_ranges:
            self._expanded_ranges.discard(key)
        else:
            self._expanded_ranges.add(key)
        self._apply_filter()
        for index, row in enumerate(self._rows):
            if row.kind == "range" and row.key == key:
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(index)
                self.listbox.see(index)
                break

    def _toggle_parent(self, slug: str) -> None:
        if slug in self._expanded_parents:
            self._expanded_parents.discard(slug)
        else:
            self._expanded_parents.add(slug)
        self._apply_filter()
        self._select_entry_row(slug)

    def _fetch_worker(self, query: str, force: bool,
                      entry: IndexEntry | None = None,
                      request_id: int = 0) -> None:
        client = self.client
        generation = self._generation
        try:
            if entry is not None:
                info = client.fetch_page(entry.slug, query=entry.title, entry=entry)
            else:
                info = client.fetch_level(query, force=force)
        except LevelNotFound as exc:
            self._queue.put(("error", generation, request_id, str(exc)))
        except Exception as exc:  # noqa: BLE001 - 界面需要兜住任何抓取异常
            self._queue.put(("error", generation, request_id, f"查询失败：{exc}"))
        else:
            self._queue.put(("level", generation, request_id, info))

    def _refresh_current(self) -> None:
        if self.current is None:
            return
        query = self.current.title or self.current.url
        self._start_fetch(query, True)

    def _random_level(self) -> None:
        prefixes = ("level", "楼层", "層級")
        pool = [e for e in self.entries if e.title.lower().startswith(prefixes)]
        if not pool:
            self._set_status("索引尚未加载完成")
            return
        entry = random.choice(pool)
        self.query_var.set(self._display_title(entry))
        self._open_entry(entry)

    def _open_entry(self, entry: IndexEntry) -> None:
        self._start_fetch(entry.slug, False, entry)

    # ------------------------------------------------------------------ 队列
    def _poll(self) -> None:
        try:
            while True:
                kind, generation, *rest = self._queue.get_nowait()
                if generation != self._generation:
                    continue  # 数据源已经切换，丢弃旧结果
                if kind == "index":
                    self._on_index(rest[0])
                    continue
                request_id, payload = rest
                if request_id != self._request_generation:
                    continue  # 已切换到更新的页面请求
                if kind == "level":
                    self._on_level(payload)
                elif kind == "error":
                    self._on_error(payload)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _on_index(self, entries: list[IndexEntry]) -> None:
        self.entries = self.client.sort_entries(entries or [])
        self._index_ready = True
        self._apply_filter()
        if self.entries:
            self._set_status(
                f"{self.client.label} 索引就绪，共 {len(self.entries)} 个层级页面"
            )
        else:
            detail = self.client.last_error
            self._set_status(
                f"{self.client.label} 索引获取失败"
                + (f"：{detail}" if detail else "，可手动输入编号或检查网络")
            )

    def _on_level(self, info: LevelInfo) -> None:
        self.current = info
        self._set_busy(False, "已加载" + ("（本地缓存）" if info.cached else "（在线）"))
        try:
            if self.source_key == "fandom" and info.alias:
                self._rename_entry(info)
            self._render_info(info)
        except Exception as exc:  # noqa: BLE001 - 渲染异常不应该让界面白屏
            self._render_error(f"界面渲染出错：{exc}")
            return
        self._highlight_in_list(info)

    def _rename_entry(self, info: LevelInfo) -> None:
        """Fandom 的页面名藏在 DISPLAYTITLE 里，加载后同步到左侧列表。"""
        label = info.label or info.title
        if not label:
            return
        new_title = f"{label} - “{info.alias}”"
        for index, entry in enumerate(self.entries):
            if entry.slug != info.page_key:
                continue
            if entry.title != new_title:
                # IndexEntry 是 frozen dataclass，只能整体替换
                self.entries[index] = IndexEntry(
                    slug=entry.slug, title=new_title, tags=entry.tags
                )
                if not self._filter_keyword():
                    self._apply_filter()
            return

    def _on_error(self, message: str) -> None:
        if self.source_key == "fandom" and any(
            word in message for word in ("网络", "超时", "连接", "JSON", "拦截")
        ):
            message += "\nFandom 在部分地区无法直连，可配置 HTTPS_PROXY 后重启程序。"
        self._set_busy(False, message)
        self._render_error(message)

    # ------------------------------------------------------------------ 列表
    def _on_filter_focus_in(self, _event=None) -> None:
        if self._filter_show_placeholder:
            self._filter_show_placeholder = False
            self.filter_var.set("")
            self.filter_entry.configure(fg=th.INK)

    def _on_filter_focus_out(self, _event=None) -> None:
        if not self.filter_var.get().strip():
            self._filter_show_placeholder = True
            self.filter_var.set(self._filter_placeholder)
            self.filter_entry.configure(fg=th.MUTED)

    def _filter_keyword(self) -> str:
        if self._filter_show_placeholder:
            return ""
        return self.filter_var.get().strip()

    def _apply_filter(self) -> None:
        keyword = self._filter_keyword()
        hits = self.client.search_entries(self.entries, keyword, limit=4000)
        self.filtered = hits
        self.listbox.delete(0, "end")
        self._rows = []
        total = len(self.entries)

        # 筛选时直接平铺结果，避免分组标题干扰
        if keyword:
            for entry in hits:
                self._add_entry_row(entry)
            self.count_var.set(f"找到 {len(hits)} 条" if total else "0")
            return

        families = self._build_families(hits)
        for key in groups.top_group_order(self.source_key):
            family = families.get(key) or {}
            count = self._family_count(key, family)
            if not count:
                continue
            self._add_group_row(key, count)
            if not self._expanded.get(key):
                continue
            if key == "normal":
                for section in family.get("sections", []):
                    range_key = f"{key}:{section['key']}"
                    expanded = range_key in self._expanded_ranges
                    self._add_range_row(range_key, section["label"], section["count"], expanded)
                    if not expanded:
                        continue
                    for item in section["mains"]:
                        parent = item["entry"]
                        children = item["children"]
                        parent_expanded = parent.slug in self._expanded_parents
                        self._add_entry_row(
                            parent, depth=2, child_count=len(children),
                            expanded=parent_expanded,
                        )
                        if parent_expanded:
                            for child in children:
                                self._add_entry_row(child, depth=3)
            elif key in ("c", "zh"):
                canonical = family.get("canonical") or {}
                for parent in family["mains"]:
                    _top, base, _is_sub = groups.level_parts(parent, self.source_key)
                    signature = (key, base)
                    owner = canonical.get(signature)
                    # 同名上级（重写版/归档版）只让一个挂子层级，避免重复
                    children = (
                        family["children"].get(signature, [])
                        if owner is None or owner == parent.slug
                        else []
                    )
                    expanded = parent.slug in self._expanded_parents
                    self._add_entry_row(
                        parent, depth=1, child_count=len(children), expanded=expanded
                    )
                    if expanded:
                        for child in children:
                            self._add_entry_row(child, depth=2)
            else:
                for entry in family["mains"]:
                    self._add_entry_row(entry, depth=1)
        self.count_var.set(f"{total} 条" if total else "0")

    def _build_families(self, entries: list[IndexEntry]) -> dict[str, dict]:
        """把子层级挂到各自的上级层级下；找不到上级的进「子层级」组。"""
        return groups.build_families(entries, self.source_key, self.client.sort_entries)

    @staticmethod
    def _family_count(key: str, family: dict) -> int:
        return groups.family_count(key, family)

    def _add_group_row(self, key: str, count: int) -> None:
        arrow = "▾" if self._expanded.get(key) else "▸"
        label = groups.TOP_LABELS.get(key, key)
        self.listbox.insert("end", f"{arrow} {label}（{count}）")
        index = self.listbox.size() - 1
        self.listbox.itemconfig(
            index,
            foreground=th.ACCENT_DARK,
            background="#F7F1E1",
            selectbackground=th.ACCENT_SOFT,
            selectforeground=th.ACCENT_DARK,
        )
        self._rows.append(_Row("group", key))

    def _add_range_row(self, key: str, label: str, count: int, expanded: bool) -> None:
        arrow = "▾" if expanded else "▸"
        self.listbox.insert("end", f"    {arrow} {label}（{count}）")
        index = self.listbox.size() - 1
        self.listbox.itemconfig(
            index,
            foreground="#6F5B2C",
            background="#FAF4E4",
            selectbackground="#EFE0BC",
            selectforeground="#4E3F1D",
        )
        self._rows.append(_Row("range", key, depth=1, expanded=expanded))

    def _add_entry_row(
        self,
        entry: IndexEntry,
        depth: int = 0,
        child_count: int = 0,
        expanded: bool = False,
    ) -> None:
        prefix = ""
        if child_count:
            prefix = "▾ " if expanded else "▸ "
        text = "    " * depth + prefix + entry.title
        self.listbox.insert("end", text)
        index = self.listbox.size() - 1
        self.listbox.itemconfig(
            index,
            foreground=th.INK,
            background=th.PANEL,
            selectbackground="#E8D8B0",
            selectforeground=th.INK,
        )
        self._rows.append(
            _Row("entry", entry.slug, entry, depth=depth,
                 child_count=child_count, expanded=expanded)
        )

    @staticmethod
    def _display_title(entry: IndexEntry) -> str:
        return entry.title

    def _highlight_in_list(self, info: LevelInfo) -> None:
        key = info.page_key or info.url.rsplit("/", 1)[-1]
        if self._select_entry_row(key):
            return
        if self._filter_keyword():
            return

        probe = IndexEntry(slug=key, title=info.label or info.title or key)
        top, base, is_sub = groups.level_parts(probe, self.source_key)
        if top in self._expanded:
            self._expanded[top] = True
        if top == "normal":
            self._expanded_ranges.add(
                f"normal:{groups.normal_range_key(probe, self.source_key)}"
            )
        if is_sub:
            parent_found = False
            for entry in self.entries:
                entry_top, entry_base, entry_is_sub = groups.level_parts(entry, self.source_key)
                if entry_top == top and entry_base == base and not entry_is_sub:
                    self._expanded_parents.add(entry.slug)
                    parent_found = True
                    break
            if not parent_found:
                self._expanded["orphan"] = True
        self._apply_filter()
        self._select_entry_row(key)

    def _select_entry_row(self, key: str) -> bool:
        for index, row in enumerate(self._rows):
            if row.kind == "entry" and row.entry is not None and row.entry.slug == key:
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(index)
                self.listbox.see(index)
                return True
        return False

    # ------------------------------------------------------------------ 渲染
    def _clear_detail(self) -> None:
        for child in self.detail.winfo_children():
            child.destroy()

    def _render_placeholder(self) -> None:
        self._clear_detail()
        host = tk.Frame(self.detail, bg=th.PANEL)
        host.place(relx=0.5, rely=0.42, anchor="center")
        tk.Label(host, text="输入层级编号开始查询", bg=th.PANEL, fg=th.INK,
                 font=(self.theme.family, 14, "bold")).pack()
        tk.Label(host, text="例如 0、1、0.1、37、C-156；也可以直接点左侧列表",
                 bg=th.PANEL, fg=th.MUTED, font=self.theme.font_small).pack(pady=(6, 12))
        chips = ChipRow(host, self.theme.chip_font, bg=th.PANEL)
        chips.pack(fill="x")
        chips.set_chips(["Level 0", "Level 1", "Level 0.1", "Level 999", "Level C-156"])

    def _render_error(self, message: str) -> None:
        self._clear_detail()
        host = tk.Frame(self.detail, bg=th.PANEL)
        host.place(relx=0.5, rely=0.4, anchor="center")
        tk.Label(host, text="没有拿到数据", bg=th.PANEL, fg=th.DANGER,
                 font=(self.theme.family, 13, "bold")).pack()
        tk.Label(host, text=message, bg=th.PANEL, fg=th.MUTED, justify="center",
                 wraplength=420, font=self.theme.font_small).pack(pady=(6, 0))

    def _render_info(self, info: LevelInfo) -> None:
        self._clear_detail()
        host = self.detail
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(4, weight=1)

        # 标题
        title_row = tk.Frame(host, bg=th.PANEL)
        title_row.grid(row=0, column=0, sticky="ew", padx=22, pady=(14, 0))
        tk.Label(title_row, text=info.label or info.title or info.query, bg=th.PANEL,
                 fg=th.INK, font=self.theme.font_title, anchor="w").pack(side="left")
        if info.alias:
            tk.Label(title_row, text=f"“{info.alias}”", bg=th.PANEL, fg=th.ACCENT_DARK,
                     font=self.theme.font_alias, anchor="w").pack(
                side="left", padx=(10, 0), pady=(7, 0))

        # 元信息
        meta_bits = []
        if info.code:
            meta_bits.append(f"编号 {info.code}")
        if info.revision:
            meta_bits.append(f"页面版本 {info.revision}")
        if info.updated_at:
            meta_bits.append(f"最后编辑 {info.updated_at}")
        meta_bits.append("缓存" if info.cached else "在线抓取")
        tk.Label(host, text=" · ".join(meta_bits), bg=th.PANEL, fg=th.MUTED,
                 font=self.theme.font_small, anchor="w").grid(
            row=1, column=0, sticky="w", padx=24, pady=(4, 0))

        # 生存难度卡片
        self._build_class_card(host, info)

        # 简介
        section = tk.Frame(host, bg=th.PANEL)
        section.grid(row=3, column=0, sticky="ew", padx=22, pady=(16, 2))
        tk.Label(section, text="简介", bg=th.PANEL, fg=th.ACCENT_DARK,
                 font=self.theme.font_section).pack(side="left")
        if info.quote:
            tk.Label(section, text="开篇引文见原文", bg=th.PANEL, fg=th.MUTED,
                     font=(self.theme.family, 8)).pack(side="left", padx=(10, 0), pady=(3, 0))

        text_wrap = tk.Frame(host, bg=th.PANEL)
        text_wrap.grid(row=4, column=0, sticky="nsew", padx=22)
        text_wrap.grid_rowconfigure(0, weight=1)
        text_wrap.grid_columnconfigure(0, weight=1)
        body = tk.Text(
            text_wrap, wrap="word", bd=0, highlightthickness=0, bg=th.PANEL,
            fg="#3B362C", font=self.theme.font_body, padx=0, pady=2,
            spacing1=2, spacing3=7, cursor="arrow", height=6,
        )
        content = info.summary or "该页面没有可提取的正文段落，可点下方按钮查看原文。"
        if info.quote and info.summary:
            content = f"“{info.quote}”\n\n{info.summary}"
        elif info.quote and not info.summary:
            content = f"“{info.quote}”"
        body.insert("1.0", content)
        body.configure(state="disabled")
        body.yview_moveto(0.0)
        body.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=body.yview,
                               style="Vertical.TScrollbar")
        scroll.grid(row=0, column=1, sticky="ns")
        body.configure(yscrollcommand=scroll.set)

        # 标签
        tags_row = tk.Frame(host, bg=th.PANEL)
        tags_row.grid(row=5, column=0, sticky="ew", padx=22, pady=(10, 0))
        tk.Label(tags_row, text="标签", bg=th.PANEL, fg=th.MUTED,
                 font=(self.theme.family, 8)).pack(side="left", anchor="n", pady=(4, 0))
        chips = ChipRow(tags_row, self.theme.chip_font, bg=th.PANEL)
        chips.pack(side="left", fill="x", expand=True, padx=(10, 0))
        chips.set_chips(info.tags[:18] or ["（无标签）"])

        # 操作
        actions = tk.Frame(host, bg=th.PANEL)
        actions.grid(row=6, column=0, sticky="ew", padx=22, pady=(12, 16))
        ttk.Button(actions, text="打开原文页面", style="Accent.TButton",
                   command=lambda: webbrowser.open(info.url)).pack(side="left")
        ttk.Button(actions, text="刷新（忽略缓存）", style="Ghost.TButton",
                   command=self._refresh_current).pack(side="left", padx=(8, 0))
        tk.Label(actions, text=info.url, bg=th.PANEL, fg=th.MUTED,
                 font=(self.theme.family, 8), anchor="e", wraplength=360).pack(
            side="right", fill="x", expand=True)

    def _build_class_card(self, host: tk.Misc, info: LevelInfo) -> None:
        key = (info.class_key or "").strip()
        rgb = config.CLASS_COLORS.get(key) or config.CLASS_COLORS.get(key.lower())
        if rgb is None and info.class_text:
            rgb = config.FALLBACK_CLASS_COLOR
        rgb = rgb or config.FALLBACK_CLASS_COLOR
        fg = th.contrast_text(rgb)
        subtle = th.hex_color(
            th.blend(tuple(int(fg[i:i + 2], 16) for i in (1, 3, 5)), rgb, 0.34)
        )

        card = tk.Frame(host, bg=th.hex_color(rgb))
        card.grid(row=2, column=0, sticky="ew", padx=22, pady=(12, 0))
        card.grid_columnconfigure(1, weight=1)

        left = tk.Frame(card, bg=th.hex_color(rgb))
        left.grid(row=0, column=0, sticky="w", padx=(18, 0), pady=12)
        tk.Label(left, text="生存难度", bg=th.hex_color(rgb), fg=subtle,
                 font=(self.theme.family, 9)).pack(anchor="w")
        tk.Label(left, text=info.class_text or "未标注", bg=th.hex_color(rgb), fg=fg,
                 font=self.theme.font_class).pack(anchor="w")

        right = tk.Frame(card, bg=th.hex_color(rgb))
        right.grid(row=0, column=1, sticky="w", padx=(30, 18), pady=12)
        if info.class_items:
            for item in info.class_items:
                tk.Label(right, text=f"· {item}", bg=th.hex_color(rgb), fg=fg,
                         font=(self.theme.family, 10), anchor="w").pack(anchor="w")
        else:
            tk.Label(right, text="该页面未列出难度分项", bg=th.hex_color(rgb), fg=subtle,
                     font=(self.theme.family, 9), anchor="w").pack(anchor="w")

    # ------------------------------------------------------------------ 状态
    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self._busy = busy
        # 加载中仍允许发起新的查询/切换页面；旧请求的结果会按编号丢弃。
        self.search_button.configure(state="normal")
        if message:
            self._set_status(message)


def run(source: str = config.DEFAULT_SOURCE) -> None:
    app = BackroomsApp(source=source)
    app.mainloop()


if __name__ == "__main__":  # pragma: no cover
    run()
