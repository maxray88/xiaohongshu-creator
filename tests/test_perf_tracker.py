#!/usr/bin/env python3
"""xhs_performance_tracker 的分页与去重回归测试。

H7/H8（2026-09-27 审计）：
- H7 total_pages 解析失败静默截断为 1 页 → 抓 10 篇当 70 篇存档
- H8 翻页 click 结果被丢弃，失败静默跳页；且无去重，翻页没生效
  会把同一页重复 extend，周报数字悄悄虚高

不需要真实 Chrome：全部用假 publisher 驱动 fetch_all_note_data。
运行：python3 -m pytest tests/ -q（项目根目录）
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import xhs_performance_tracker as T  # noqa: E402


def _row(title, views="100", likes="10", saves="5", comments="1"):
    return {"title_time": f"{title}发布于2026-09-20 10:00",
            "exposures": "1000", "views": views, "cover_click_rate": "5%",
            "likes": likes, "comments": comments, "saves": saves,
            "follows": "0", "shares": "0", "avg_watch_time": "3s"}


class FakePub:
    """按脚本演进的假 publisher。

    pages: list of list-of-rows，每页的行
    click_works: 翻页按钮是否真的切页
    table_missing_on: 这些页码上表格返回 None
    """

    def __init__(self, body_text, pages, click_works=True, table_missing_on=()):
        self.body_text = body_text
        self.pages = pages
        self.click_works = click_works
        self.table_missing_on = set(table_missing_on)
        self.cur = 0            # 当前页索引（0-based）
        self.navigated = []
        self.reads = 0

    def _navigate(self, url):
        self.navigated.append(url)

    def _evaluate(self, js):
        if "document.body.innerText" in js:
            return self.body_text
        if "d-pagination-page" in js:  # 翻页点击
            if not self.click_works:
                return True   # 点「成功」了但页面不动 —— 最阴的那种
            import re
            m = re.search(r"var target = '(\d+)'", js)
            if m:
                # JS 里是 1-based 页码，转成 0-based 索引
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(self.pages):
                    self.cur = idx
                    return True
            return False
        # 读表格
        self.reads += 1
        if (self.cur + 1) in self.table_missing_on:
            return None
        if self.cur < len(self.pages):
            return self.pages[self.cur]
        return []


# ── H7：分页解析 ────────────────────────────────────────────────

def test_pagination_parses_chinese_comma():
    """实测踩过：中文逗号 U+FF0C 让 `\\D*?` 之外的写法失配。"""
    pub = FakePub("共 62 条，7 页", [[_row("a")]])
    notes, pages = T._read_pagination(pub)
    assert notes == 62 and pages == 7


def test_pagination_handles_plain_space():
    pub = FakePub("共 70 条 8 页", [[_row("a")]])
    assert T._read_pagination(pub) == (70, 8)


def test_pagination_raises_instead_of_defaulting_to_one_page():
    """H7 核心回归：读不到分页必须抛错，不能默认 1 页。"""
    pub = FakePub("页面加载中...", [[_row("a")]])
    try:
        T._read_pagination(pub)
    except RuntimeError as e:
        assert "分页" in str(e) or "解析" in str(e)
    else:
        raise AssertionError("分页解析失败时必须抛错（旧实现静默当 1 页）")


def test_pagination_raises_on_login_page():
    pub = FakePub("请登录后查看数据", [[_row("a")]])
    try:
        T._read_pagination(pub)
    except RuntimeError:
        pass
    else:
        raise AssertionError("登录页必须抛错")


def test_pagination_with_notes_but_no_pages():
    """有条数无页数：能算出页数，但要能对上条数。"""
    pub = FakePub("共 25 条", [[_row("a")]])
    notes, pages = T._read_pagination(pub)
    assert notes == 25 and pages == 3


# ── 抓取主流程 ──────────────────────────────────────────────────

def test_single_page_fetch(monkeypatch):
    monkeypatch.setattr(T.time, "sleep", lambda *a: None)
    pub = FakePub("共 2 条 1 页", [[_row("a"), _row("b")]])
    rows = T.fetch_all_note_data(pub)
    assert len(rows) == 2


def test_multi_page_fetch(monkeypatch):
    monkeypatch.setattr(T.time, "sleep", lambda *a: None)
    # 每页内容必须不同：翻页确认靠的是「首行 title_time 变了」
    pages = [[_row(f"p{p}t{i}", views=str(p * 100 + i)) for i in range(10)]
             for p in range(3)]
    pub = FakePub("共 30 条 3 页", pages)
    rows = T.fetch_all_note_data(pub)
    assert len(rows) == 30, f"应抓到 30 行，实际 {len(rows)}"
    assert len({r["title_time"] for r in rows}) == 30


def test_pagination_not_moving_raises(monkeypatch):
    """H8 核心回归：翻页点了但页面没动，必须报错而不是重复累加。"""
    monkeypatch.setattr(T.time, "sleep", lambda *a: None)
    pages = [[_row("t1", views="1")], [_row("t2", views="2")]]
    pub = FakePub("共 2 条 2 页", pages, click_works=False)
    try:
        T.fetch_all_note_data(pub)
    except RuntimeError as e:
        assert "翻到第 2 页失败" in str(e)
    else:
        raise AssertionError("翻页失败必须抛错（旧实现会静默重复同一页）")


def test_missing_table_raises(monkeypatch):
    monkeypatch.setattr(T.time, "sleep", lambda *a: None)
    pub = FakePub("共 1 条 1 页", [[_row("a")]], table_missing_on=[1])
    try:
        T.fetch_all_note_data(pub)
    except RuntimeError as e:
        assert "表格" in str(e)
    else:
        raise AssertionError("表格缺失必须抛错")


def test_duplicate_page_is_detected(monkeypatch):
    """若实现里有去重+重复检测，同一页被读两次应该被识别。"""
    monkeypatch.setattr(T.time, "sleep", lambda *a: None)
    # 两页内容完全相同（模拟翻页无效但 click 返回 True 的极端情况）
    same = [_row("same", views="1")]
    pub = FakePub("共 2 条 2 页", [same, same], click_works=False)
    try:
        rows = T.fetch_all_note_data(pub)
    except RuntimeError:
        pass  # 期望路径：翻页未生效被识别
    else:
        # 若实现选择容忍，则必须去重后行数不翻倍
        assert len(rows) == 1, f"重复页导致行数翻倍: {len(rows)}"


# ── 辅助：parse_number ──────────────────────────────────────────

def test_parse_number_handles_dash_and_commas():
    assert T.parse_number("-") == 0
    assert T.parse_number("") == 0
    assert T.parse_number(None) == 0
    assert T.parse_number("1,234") == 1234
    assert T.parse_number("1，234") == 1234
    assert T.parse_number("12.9") == 12
