"""离线测试：用模拟的 MediaWiki 响应验证 Fandom 数据源。

真实 Fandom 在部分网络下无法直连，这里保证解析逻辑本身可靠。
运行：python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import unittest
from urllib.parse import parse_qs, urlparse

from backrooms.fandom import FandomClient, parse_fandom_page, split_display_title
from backrooms.http_client import FetchError
from backrooms.parser import _normalize_class_key

PAGE_HTML = """
<div class="mw-parser-output">
<aside class="portable-infobox pi-background pi-theme-wikia">
  <h2 class="pi-title">Level 0</h2>
  <div class="pi-item pi-data pi-item-spacing" data-source="difficulty">
    <h3 class="pi-data-label pi-secondary-font">生存难度</h3>
    <div class="pi-data-value pi-font">
      Class 1
      <ul>
        <li>安全</li>
        <li>稳定</li>
        <li>极少量实体</li>
      </ul>
    </div>
  </div>
</aside>
<p>Level 0 是后室的第 1 层，主要由黄色的房间、潮湿的地毯和嗡嗡作响的荧光灯组成，是多数流浪者抵达后室的第一站。</p>
<h2><span class="mw-headline" id="描述">描述</span></h2>
<p>Level 0 是一个非线性空间，外观类似零售店的储藏后室，所有房间都呈现统一的黄色墙纸与潮湿地毯，但没有两个房间完全相同。</p>
<p>这里的荧光灯持续闪烁并发出嗡鸣，指南针和 GPS 在层级内无法正常使用，无线电通信也会变得失真。</p>
</div>
"""

PARSE_PAYLOAD = {
    "parse": {
        "title": "Level 0",
        "revid": 123456,
        "text": PAGE_HTML,
        "categories": [
            {"sortkey": "", "category": "楼层"},
            {"sortkey": "", "category": "生存难度1"},
            {"sortkey": "", "category": "翻译搬运"},
        ],
    }
}


class FakeHttp:
    """按 API 参数返回固定响应，记录请求过的地址。"""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def peek_cache(self, key: str, ttl=None):
        return None

    def get_text(self, url: str, force: bool = False, use_cache: bool = True, ttl=None, timeout=None):
        self.urls.append(url)
        params = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        action = params.get("action", "")

        if action == "parse":
            if params.get("page") == "Level 50":
                return json.dumps(
                    {
                        "parse": {
                            "title": "Level 50",
                            "revid": 777,
                            "text": '<div class="mw-parser-output"><p>这一版页面没有渲染出难度文字。</p></div>',
                            "wikitext": "{{Class 2}}\n* 不安全\n* 稳定\n* 少量实体",
                            "categories": [{"category": "楼层"}],
                        }
                    },
                    ensure_ascii=False,
                ), False
            return json.dumps(PARSE_PAYLOAD, ensure_ascii=False), False
        if params.get("generator") == "allpages":
            prefix = params.get("gapprefix", "")
            raw_pages = {
                "Level": [
                    {"title": "Level 0"},
                    {"title": "Level 1"},
                    {"title": "Level !"},
                ],
                "Level ZH": [
                    {"title": "Level ZH 820", "displaytitle": 'Level ZH 820: "书库"'},
                    {"title": "Level ZH 900", "displaytitle": 'Level ZH 900 "无垠"'},
                ],
                "Level C": [],
                "楼层": [{"title": "楼层 1"}, {"title": "楼层写作指南"}],
            }.get(prefix, [])
            pages = [
                {"title": item["title"], "displaytitle": item.get("displaytitle", item["title"])}
                for item in raw_pages
            ]
            return json.dumps({"query": {"pages": pages}}, ensure_ascii=False), False
        if params.get("list") == "allpages":
            prefix = params.get("apprefix", "")
            pages = {
                "Level": [{"title": "Level 0"}, {"title": "Level 1"}, {"title": "Level !"}],
                "Level ZH": [{"title": "Level ZH 820"}, {"title": "Level ZH 900"}],
                "Level C": [],
                "楼层": [{"title": "楼层 1"}, {"title": "楼层写作指南"}],
            }.get(prefix, [])
            return json.dumps({"query": {"allpages": pages}}, ensure_ascii=False), False
        if params.get("list") == "categorymembers":
            return json.dumps({"query": {"categorymembers": []}}, ensure_ascii=False), False
        if params.get("list") == "search":
            return json.dumps({"query": {"search": [{"title": "Level 0"}]}}, ensure_ascii=False), False
        if params.get("prop") == "revisions":
            return json.dumps(
                {"query": {"pages": [{"revisions": [{"timestamp": "2026-05-01T04:30:00Z"}]}]}},
                ensure_ascii=False,
            ), False
        if "titles" in params:
            exists = params["titles"].lower() in ("level 0", "level 1")
            return json.dumps(
                {"query": {"pages": [{"title": params["titles"], "missing": not exists}]}},
                ensure_ascii=False,
            ), False
        raise FetchError("未覆盖的请求", status=404)


class FallbackHttp(FakeHttp):
    """generator 接口失败时，应退回不带名称的 allpages 索引。"""

    def get_text(self, url: str, force: bool = False, use_cache: bool = True, ttl=None, timeout=None):
        if "generator=allpages" in url:
            raise FetchError("模拟 generator 失败")
        return super().get_text(url, force=force, use_cache=use_cache, ttl=ttl, timeout=timeout)

    def peek_cache(self, key: str, ttl=None):
        if "list=allpages" in key:
            return super().get_text(key)[0]
        return None


class FandomOfflineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = FakeHttp()
        self.client = FandomClient(self.http)

    def test_index_falls_back_to_plain_allpages(self) -> None:
        client = FandomClient(FallbackHttp())
        titles = {entry.title for entry in client.list_levels()}
        self.assertIn("Level 0", titles)
        self.assertIn("Level ZH 820", titles)

    def test_index_lists_pages(self) -> None:
        entries = self.client.list_levels()
        titles = {entry.title for entry in entries}
        self.assertIn("Level 0", titles)
        self.assertIn("楼层 1", titles)
        self.assertIn("Level ZH 820 - “书库”", titles)
        self.assertIn("Level ZH 900 - “无垠”", titles)
        self.assertNotIn("楼层写作指南", titles)
        self.assertEqual(len(entries), len(titles), "索引应去重")
        zh_entry = next(entry for entry in entries if entry.slug == "Level ZH 820")
        self.assertEqual(zh_entry.title, "Level ZH 820 - “书库”")

    def test_resolve_numeric_uses_index(self) -> None:
        self.client.list_levels()
        locator, entry = self.client.resolve("0")
        self.assertEqual(locator, "Level 0")
        self.assertIsNotNone(entry)

    def test_resolve_without_index_uses_api(self) -> None:
        locator, entry = self.client.resolve("1")
        self.assertEqual(locator, "Level 1")
        self.assertIsNone(entry)

    def test_fetch_page_parses_fields(self) -> None:
        info = self.client.fetch_level("0")
        self.assertEqual(info.title, "Level 0")
        self.assertEqual(info.label, "Level 0")
        self.assertEqual(info.code, "0")
        self.assertEqual(info.class_key, "1")
        self.assertIn("Class 1", info.class_text)
        self.assertEqual(info.class_items, ["安全", "稳定", "极少量实体"])
        self.assertIn("生存难度1", info.tags)
        self.assertIn("非线性空间", info.summary)
        self.assertEqual(info.revision, "123456")
        self.assertTrue(info.updated_at)
        self.assertIn("/wiki/Level_0", info.url)
        self.assertEqual(info.page_key, "Level 0")

    def test_fetch_page_uses_wikitext_fallback(self) -> None:
        info = self.client.fetch_page("Level 50")
        self.assertEqual(info.title, "Level 50")
        self.assertEqual(info.class_text, "Class 2")
        self.assertEqual(info.class_key, "2")
        self.assertEqual(info.class_items, ["不安全", "稳定", "少量实体"])

    def test_text_only_difficulty(self) -> None:
        html = (
            '<div class="mw-parser-output"><p>生存难度：等级 2</p>'
            "<ul><li>不安全</li><li>稳定</li><li>少量实体</li></ul>"
            "<p>" + "这是一段足够长的层级描述，用于验证摘要提取逻辑是否正常工作。" * 2 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 7", url="https://example.invalid/Level_7")
        self.assertEqual(info.class_text, "等级 2")
        self.assertEqual(info.class_key, "2")
        self.assertEqual(info.class_items, ["不安全", "稳定", "少量实体"])

    def test_environmental_class_keeps_suffix_and_details(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度: Class 1e - 环境危害(ℵ)</div>"
            "<div>》安全</div><div>》已勘探完全</div><div>》极少非实体危害</div>"
            "<p>" + "这是一个环境危害层级的描述段落，用于确保正文不会被误当成难度细则。" * 2 + "</p>"
            "</div>"
        )
        info = parse_fandom_page(html, title="Level ZH 820", url="https://example.invalid/Level_ZH_820")
        self.assertEqual(info.class_text, "Class 1e - 环境危害(ℵ)")
        self.assertEqual(info.class_key, "1e")
        self.assertEqual(info.class_items, ["安全", "已勘探完全", "极少非实体危害"])

    def test_environment_suffix_completed(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度: Class 3e</div>"
            "<p>" + "页面只写了 Class 3e，后缀应由程序补全为「环境危害」。" * 2 + "</p>"
            "</div>"
        )
        info = parse_fandom_page(html, title="Level 12", url="https://example.invalid/Level_12")
        self.assertEqual(info.class_text, "Class 3e - 环境危害")
        self.assertEqual(info.class_key, "3e")

    def test_class_from_categories_keeps_suffix(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<p>" + "页面没有难度组件，只能从分类标签推断等级和污染类型。" * 2 + "</p>"
            "</div>"
        )
        info = parse_fandom_page(
            html,
            title="Level ZH 900",
            url="https://example.invalid/Level_ZH_900",
            categories=["楼层", "生存难度1e", "生存难度1e - 环境危害"],
        )
        self.assertEqual(info.class_text, "等级 1e - 环境危害")
        self.assertEqual(info.class_key, "1e")

    def test_inline_details_after_class(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度: Class 1e - 环境危害 》安全 》已勘探完全 》极少非实体危害</div>"
            "<p>" + "同一行里用「》」分隔等级与细则的写法也应该能拆开。" * 2 + "</p>"
            "</div>"
        )
        info = parse_fandom_page(html, title="Level 21", url="https://example.invalid/Level_21")
        self.assertEqual(info.class_text, "Class 1e - 环境危害")
        self.assertEqual(info.class_key, "1e")
        self.assertEqual(info.class_items, ["安全", "已勘探完全", "极少非实体危害"])

    def test_wikitext_template_fallback(self) -> None:
        html = (
            '<div class="mw-parser-output"><p>'
            + "页面正文只描述环境，没有渲染出任何难度文字。" * 2
            + "</p></div>"
        )
        wikitext = "{{Class 1e}}\n* 安全\n* 已勘探完全\n* 极少非实体危害"
        info = parse_fandom_page(
            html, title="Level 33", url="https://example.invalid/Level_33", wikitext=wikitext
        )
        self.assertEqual(info.class_text, "Class 1e - 环境危害")
        self.assertEqual(info.class_key, "1e")
        self.assertEqual(info.class_items, ["安全", "已勘探完全", "极少非实体危害"])

    def test_wikitext_infobox_params(self) -> None:
        html = '<div class="mw-parser-output"><p>' + "模板参数里才写难度。" * 3 + "</p></div>"
        wikitext = (
            "{{楼层信息\n|difficulty = Class 2\n"
            "|one = 不安全\n|two = 稳定\n|three = 少量实体\n}}"
        )
        info = parse_fandom_page(
            html, title="Level 34", url="https://example.invalid/Level_34", wikitext=wikitext
        )
        self.assertEqual(info.class_text, "Class 2")
        self.assertEqual(info.class_key, "2")
        self.assertEqual(info.class_items, ["不安全", "稳定", "少量实体"])

    def test_html_table_difficulty(self) -> None:
        html = (
            '<div class="mw-parser-output"><table><tr>'
            "<th>生存难度</th><td>Class 4</td><td>安全</td><td>稳定</td><td>极少量实体</td>"
            "</tr></table><p>" + "表格版难度布局。" * 4 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 35", url="https://example.invalid/Level_35")
        self.assertEqual(info.class_text, "Class 4")
        self.assertEqual(info.class_key, "4")
        self.assertEqual(info.class_items, ["安全", "稳定", "极少量实体"])

    def test_attribute_alt_text(self) -> None:
        html = (
            '<div class="mw-parser-output"><div class="sd-icon">'
            '<img alt="Class 3e - 环境危害"></div>'
            "<p>" + "难度只写在图片 alt 属性里。" * 4 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 36", url="https://example.invalid/Level_36")
        self.assertEqual(info.class_text, "Class 3e - 环境危害")
        self.assertEqual(info.class_key, "3e")

    def test_classy_element_shape(self) -> None:
        html = (
            '<div class="mw-parser-output"><div class="sd-box">'
            "<div>生存难度</div><div>Class 5e - 环境危害</div>"
            "<div>不安全</div><div>不稳定</div><div>实体横行</div></div>"
            "<p>" + "class 名带 sd 的容器。" * 4 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 37", url="https://example.invalid/Level_37")
        self.assertEqual(info.class_text, "Class 5e - 环境危害")
        self.assertEqual(info.class_key, "5e")
        self.assertEqual(info.class_items, ["不安全", "不稳定", "实体横行"])

    def test_wikitext_sd_template(self) -> None:
        html = '<div class="mw-parser-output"><p>' + "难度写在生存难度模板里。" * 3 + "</p></div>"
        wikitext = "{{生存难度|Class 1|安全|稳定|极少量实体}}"
        info = parse_fandom_page(
            html, title="Level 38", url="https://example.invalid/Level_38", wikitext=wikitext
        )
        self.assertEqual(info.class_text, "Class 1")
        self.assertEqual(info.class_key, "1")
        self.assertEqual(info.class_items, ["安全", "稳定", "极少量实体"])

    def test_standalone_class_with_image_label(self) -> None:
        html = (
            '<div class="mw-parser-output"><div style="border:1px solid #ccc">'
            '<img alt="生存难度">'
            "<div>Class 3</div><div>不安全</div><div>不稳定</div><div>少量实体</div>"
            "</div><p>" + "内联样式、没有 class 提示的难度框。" * 3 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 39", url="https://example.invalid/Level_39")
        self.assertEqual(info.class_text, "Class 3")
        self.assertEqual(info.class_key, "3")
        self.assertEqual(info.class_items, ["不安全", "不稳定", "少量实体"])

    def test_label_variant_survival_level(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度等级：等级 1</div>"
            "<div>安全</div><div>稳定</div><div>极少量实体</div>"
            "<p>" + "标签写成「生存难度等级」的页面。" * 3 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 40", url="https://example.invalid/Level_40")
        self.assertEqual(info.class_text, "等级 1")
        self.assertEqual(info.class_key, "1")
        self.assertEqual(info.class_items, ["安全", "稳定", "极少量实体"])

    def test_traditional_chinese(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存難度：Class 2</div>"
            "<div>不安全</div><div>穩定</div><div>少量實體</div>"
            "<p>" + "繁體頁面的難度與細則。" * 4 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 41", url="https://example.invalid/Level_41")
        self.assertEqual(info.class_text, "Class 2")
        self.assertEqual(info.class_key, "2")
        self.assertEqual(info.class_items, ["不安全", "穩定", "少量實體"])

    def test_fullwidth_characters(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度：Ｃｌａｓｓ　３</div>"
            "<div>不安全</div><div>不穩定</div><div>少量實體</div>"
            "<p>" + "全角字母与空格的写法。" * 4 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 42", url="https://example.invalid/Level_42")
        self.assertEqual(info.class_text, "Class 3")
        self.assertEqual(info.class_key, "3")
        self.assertEqual(info.class_items, ["不安全", "不穩定", "少量實體"])

    def test_normalize_nested_prefix_and_fullwidth(self) -> None:
        self.assertEqual(_normalize_class_key("等级：Class 1e - 环境"), "1e")
        self.assertEqual(_normalize_class_key("Ｃｌａｓｓ　４"), "4")

    def test_wikitext_env_positional_params(self) -> None:
        html = '<div class="mw-parser-output"><p>' + "位置参数写法。" * 4 + "</p></div>"
        wikitext = "{{Class 1e|环境危害|安全|已勘探完全|极少非实体危害}}"
        info = parse_fandom_page(
            html, title="Level 43", url="https://example.invalid/Level_43", wikitext=wikitext
        )
        self.assertEqual(info.class_text, "Class 1e - 环境危害")
        self.assertEqual(info.class_key, "1e")
        self.assertEqual(info.class_items, ["安全", "已勘探完全", "极少非实体危害"])

    def test_inline_details_separated_by_dunhao(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度：Class 1</div>"
            "<div>安全、稳定、极少量实体</div>"
            "<p>" + "细则用顿号分隔。" * 4 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 45", url="https://example.invalid/Level_45")
        self.assertEqual(info.class_text, "Class 1")
        self.assertEqual(info.class_items, ["安全", "稳定", "极少量实体"])

    def test_display_title_variants(self) -> None:
        self.assertEqual(split_display_title('Level ZH 38: "渴血之旧都"'), ("Level ZH 38", "渴血之旧都"))
        self.assertEqual(split_display_title('Level ZH 37 "无限走廊"'), ("Level ZH 37", "无限走廊"))
        entry = FandomClient._entry_from_page(
            {"title": "Level ZH 1420", "displaytitle": '<span style="display:none;">彬州市</span>'}
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.title, "Level ZH 1420")

    def test_roman_class_and_display_title(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<p>生存难度：</p><p>Class V</p>"
            "<p>》不安全</p><p>》未勘探完全</p><p>》实体侵占</p>"
            "<p>" + "正文段落，不应该被当成难度细则。" * 3 + "</p></div>"
        )
        info = parse_fandom_page(
            html,
            title="Level ZH 38",
            url="https://example.invalid/Level_ZH_38",
            displaytitle='Level ZH 38: "渴血之旧都"',
        )
        self.assertEqual(info.class_text, "Class 5")
        self.assertEqual(info.class_key, "5")
        self.assertEqual(info.class_items, ["不安全", "未勘探完全", "实体侵占"])
        self.assertEqual(info.alias, "渴血之旧都")

    def test_custom_letter_class_and_attribute_noise(self) -> None:
        html = (
            '<div class="mw-parser-output">'
            "<div>生存难度：Class 1d - 梦幻</div>"
            "<div>»\u2800安全</div><div>»\u2800稳定</div><div>»\u2800梦境威胁</div>"
            '<p>入口：<span title="Level 97（页面不存在）">Level 97</span> 的外观陈旧的摩天大楼。'
            + "正文段落不应被当成等级或细则。" * 3
            + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 386", url="https://example.invalid/Level_386")
        self.assertEqual(info.class_text, "Class 1d - 梦幻")
        self.assertEqual(info.class_key, "1d")
        self.assertEqual(info.class_items, ["安全", "稳定", "梦境威胁"])

    def test_bare_number_is_not_a_class(self) -> None:
        html = (
            '<div class="mw-parser-output"><div class="sd-box">'
            "<div>16</div><p>" + "这里只是正文里的一个数字。" * 4 + "</p></div></div>"
        )
        info = parse_fandom_page(html, title="Level 46", url="https://example.invalid/Level_46")
        self.assertEqual(info.class_text, "")
        self.assertEqual(info.class_key, "")

    def test_wikitext_only_page(self) -> None:
        info = parse_fandom_page(
            "",
            title="Level 44",
            url="https://example.invalid/Level_44",
            wikitext="{{Class 0}}",
        )
        self.assertEqual(info.class_text, "Class 0")
        self.assertEqual(info.class_key, "0")

    def test_infobox_environmental_class(self) -> None:
        html = (
            '<div class="mw-parser-output"><aside class="portable-infobox">'
            '<div class="pi-item pi-data" data-source="difficulty">'
            '<h3 class="pi-data-label">生存难度</h3>'
            '<div class="pi-data-value">Class 2e - 环境危害'
            "<ul><li>不安全</li><li>已勘探完全</li><li>少量非实体危害</li></ul>"
            "</div></div></aside>"
            "<p>" + "环境危害层级的描述段落，用于验证信息框解析是否正常工作。" * 2 + "</p></div>"
        )
        info = parse_fandom_page(html, title="Level 9", url="https://example.invalid/Level_9")
        self.assertEqual(info.class_text, "Class 2e - 环境危害")
        self.assertEqual(info.class_key, "2e")
        self.assertEqual(info.class_items, ["不安全", "已勘探完全", "少量非实体危害"])


if __name__ == "__main__":
    unittest.main()
