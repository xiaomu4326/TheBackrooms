"""分组逻辑的离线测试。"""

from __future__ import annotations

import unittest

from backrooms import groups
from backrooms.models import IndexEntry


def entry(slug: str, title: str, tags: tuple[str, ...] = ()) -> IndexEntry:
    return IndexEntry(slug=slug, title=title, tags=tags)


class WikidotGroupTest(unittest.TestCase):
    def test_normal_levels(self) -> None:
        self.assertEqual(groups.group_key(entry("level-0", "Level 0 - “教学关卡”"), "wikidot"), "normal")
        self.assertEqual(groups.group_key(entry("level-386", "Level 386 - “通天梯”"), "wikidot"), "normal")

    def test_sub_levels(self) -> None:
        self.assertEqual(groups.group_key(entry("level-0-1", "Level 0.1 - “天顶站”"), "wikidot"), "sub")
        self.assertEqual(groups.group_key(entry("level-11-1", "Asset 11.1 - “私有企业”"), "wikidot"), "sub")
        self.assertEqual(groups.group_key(entry("level-386-1", "Level 386.1"), "wikidot"), "sub")

    def test_c_levels(self) -> None:
        self.assertEqual(groups.group_key(entry("level-c-156", "Antrum C-156"), "wikidot"), "c")
        self.assertEqual(groups.group_key(entry("level-c-37", "Level C-37"), "wikidot"), "c")
        self.assertEqual(groups.group_key(entry("level-c-0-1", "Level C-0.1"), "wikidot"), "c_sub")

    def test_other_pages(self) -> None:
        self.assertEqual(groups.group_key(entry("whale-story", "🐋"), "wikidot"), "other")
        self.assertEqual(groups.group_key(entry("level-c-1", "奇怪的页面"), "wikidot"), "c")


class FandomGroupTest(unittest.TestCase):
    def test_normal_and_zh(self) -> None:
        self.assertEqual(groups.group_key(entry("Level 0", "Level 0"), "fandom"), "normal")
        self.assertEqual(groups.group_key(entry("Level ZH 820", "Level ZH 820"), "fandom"), "zh")
        self.assertEqual(groups.group_key(entry("Level ZH-1", "Level ZH-1"), "fandom"), "zh")

    def test_sub_and_zh_sub(self) -> None:
        self.assertEqual(groups.group_key(entry("Level 0.1", "Level 0.1"), "fandom"), "sub")
        self.assertEqual(
            groups.group_key(entry("Level ZH 336.1", "Level ZH 336.1 - “测试”"), "fandom"),
            "zh_sub",
        )

    def test_other(self) -> None:
        self.assertEqual(groups.group_key(entry("Entity 1", "Entity 1"), "fandom"), "other")

    def test_order(self) -> None:
        self.assertEqual(
            groups.group_order("fandom"),
            ("normal", "sub", "c", "c_sub", "zh", "zh_sub", "other"),
        )


class LevelPartsTest(unittest.TestCase):
    def test_normal_and_sub(self) -> None:
        self.assertEqual(groups.level_parts(entry("level-0", "Level 0"), "wikidot"), ("normal", "0", False))
        self.assertEqual(groups.level_parts(entry("level-0-1", "Level 0.1"), "wikidot"), ("normal", "0", True))
        self.assertEqual(groups.level_parts(entry("level-11-1", "Asset 11.1"), "wikidot"), ("normal", "11", True))

    def test_clusters(self) -> None:
        self.assertEqual(groups.level_parts(entry("level-c-1038-1", "Level C-1038.1"), "wikidot"), ("c", "1038", True))
        self.assertEqual(groups.level_parts(entry("Level ZH 336.1", "Level ZH 336.1"), "fandom"), ("zh", "336", True))

    def test_special_levels(self) -> None:
        self.assertEqual(groups.level_parts(entry("level-!", "Level !"), "fandom")[0], "normal")
        self.assertEqual(groups.level_parts(entry("Entity 1", "Entity 1"), "fandom")[0], "other")

    def test_hidden_and_joke(self) -> None:
        self.assertEqual(
            groups.level_parts(entry("whale-story", "🐋", ("hidden",)), "wikidot")[0], "hidden"
        )
        self.assertEqual(
            groups.level_parts(entry("the-night-bus", "隐秘层级 - “夜行巴士”"), "wikidot")[0],
            "hidden",
        )
        self.assertEqual(
            groups.level_parts(entry("joke-level-meg", "(Joke) Level M.E.G."), "wikidot")[0],
            "joke",
        )
        self.assertEqual(
            groups.level_parts(entry("nivel-es-8-broma", "Level ES-8（搞笑）"), "wikidot")[0],
            "joke",
        )

    def test_top_order(self) -> None:
        self.assertEqual(
            groups.top_group_order("fandom"),
            ("normal", "c", "zh", "hidden", "joke", "orphan", "other"),
        )


class SortTest(unittest.TestCase):
    def test_c_levels_sort_by_number(self) -> None:
        entries = [
            entry("level-c-101", "Level C-101"),
            entry("level-c-9", "Level C-9"),
            entry("level-c-37", "Level C-37"),
        ]

        def fallback(items):
            return items

        ordered = [item.title for item in groups.sort_group(entries, "c", fallback)]
        self.assertEqual(ordered, ["Level C-9", "Level C-37", "Level C-101"])

    def test_sub_levels_sort_by_number(self) -> None:
        entries = [
            entry("level-10-1", "Level 10.1"),
            entry("level-0-2", "Level 0.2"),
            entry("level-2-1", "Level 2.1"),
        ]

        def fallback(items):
            return items

        ordered = [item.title for item in groups.sort_group(entries, "sub", fallback)]
        self.assertEqual(ordered, ["Level 0.2", "Level 2.1", "Level 10.1"])

    def test_default_all_collapsed(self) -> None:
        self.assertFalse(any(groups.default_expanded().values()))


if __name__ == "__main__":
    unittest.main()
