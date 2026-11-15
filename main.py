"""程序入口。

用法：
    python main.py              启动图形界面
    python main.py 0            命令行查看 Level 0
    python main.py --cli 0.1    同上
"""

from __future__ import annotations

import argparse
import sys

from backrooms import config
from backrooms.models import LevelInfo
from backrooms.service import LevelNotFound, create_client


def print_info(info: LevelInfo) -> None:
    """命令行输出一份层级档案。"""
    lines: list[str] = []
    lines.append("=" * 52)
    lines.append(info.display_name)
    if info.title and info.title != info.display_name:
        lines.append(f"页面标题：{info.title}")
    if info.class_text:
        lines.append(f"生存难度：{info.class_text}")
    for item in info.class_items:
        lines.append(f"  · {item}")
    if info.tags:
        lines.append("标签：" + " / ".join(info.tags))
    if info.revision or info.updated_at:
        lines.append(
            "版本："
            + " ".join(
                part for part in (
                    f"第 {info.revision} 版" if info.revision else "",
                    f"最后编辑 {info.updated_at}" if info.updated_at else "",
                ) if part
            )
        )
    if info.summary:
        lines.append("-" * 52)
        lines.append(info.summary)
    lines.append("-" * 52)
    lines.append(info.url)
    lines.append("=" * 52)
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="后室中文维基层级查询器")
    parser.add_argument("query", nargs="?", help="层级编号，例如 0 / 0.1 / C-156")
    parser.add_argument(
        "--source",
        choices=("wikidot", "fandom"),
        default=config.DEFAULT_SOURCE,
        help="数据源：wikidot（默认）或 fandom",
    )
    parser.add_argument("--cli", action="store_true", help="仅输出命令行结果")
    parser.add_argument("--refresh", action="store_true", help="忽略本地缓存")
    args = parser.parse_args(argv)

    if not args.query:
        from backrooms.ui import run

        run(source=args.source)
        return 0

    client = create_client(args.source)
    client.list_levels()  # 先建立索引，便于解析别称
    try:
        info = client.fetch_level(args.query, force=args.refresh)
    except LevelNotFound as exc:
        print(f"未找到：{exc}")
        print(f"可在 {config.SOURCE_HOMES[args.source]} 手动确认页面名称。")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"抓取失败：{exc}")
        return 2

    print_info(info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
