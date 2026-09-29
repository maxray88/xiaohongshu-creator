#!/usr/bin/env python3
"""humanize_text 回归测试（2026-09-27 审计发现）。

修掉的两个 HIGH：
- H4 二次运行摧毁原文：content_text_original 每次被已处理文本覆盖
- H5 替换与删除规则互杀：「因此→所以」替换后又被「所以」删除规则吃掉，
  语义连接词凭空消失

附带锁住 Reviewer 点名的误杀：小数（3.14）、序数词（第一次）、
语义连接词（然而/不过/此外）。

运行：python3 -m pytest tests/ -q（项目根目录）
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from humanize_text import humanize_day_dir, humanize_text  # noqa: E402


# ── 语义连接词不得被删除 ────────────────────────────────────────

def test_connective_survives_replacement_and_deletion():
    """「因此」应被替换成口语词，但不能在同一次运行里又被删空。"""
    out = humanize_text("因此，我去了。")
    assert out.strip().endswith("我去了。")
    assert out.strip() != "我去了。", "语义连接词被整句吃掉了"


def test_然而_不过_等连接词保留语义():
    """连接词要么原样保留，要么变成口语等价词 —— 但不能凭空消失。

    旧版这个测试只断言 len(out) >= 3，是注水测试：把「然而」整个删掉
    （mutant：`然而他没说话。` → `他没说话。`，len=5）照样通过。
    这里断言具体的等价词在输出里。
    """
    expectations = {
        "然而他没说话。": ("不过", "但"),
        "不过没关系。": ("不过",),
        "此外还有一件事。": ("还有",),
    }
    for src, alts in expectations.items():
        out = humanize_text(src).strip()
        assert any(a in out for a in alts), \
            f"{src!r} -> {out!r}，连接词消失且无口语等价词"
        # 正文主体必须在（把连接词从原文和输出里都剔掉后应仍有内容）
        assert out.replace("不过", "").replace("还有", "").strip("，,。 ") != "", \
            f"{src!r} -> {out!r} 正文主体被清空"


# ── 最长匹配优先（Reviewer 2026-09-27 抓出）────────────────────

def test_另一方面_not_sliced_into_另():
    """「一方面」是「另一方面」的子串，顺序反了会把后者切成「另」。"""
    out = humanize_text("另一方面又怕。")
    assert not out.startswith("另又"), f"「另一方面」被腰斩成 {out!r}"
    assert "另一方面" not in out or out == "另一方面又怕。"


def test_一方面_still_stripped():
    """真正的一方面还是要删。"""
    out = humanize_text("一方面很在意。")
    assert not out.startswith("一方面")


def test_综上所述_uses_replacement_not_residue():
    """「综上」不该被当序号词删掉（会切出「所述，很好。」残句）。"""
    out = humanize_text("综上所述，很好。")
    assert "所述" not in out.split("，")[0], f"残句: {out!r}"
    assert "所以" in out


# ── 中文顿号编号无空格 ──────────────────────────────────────────

def test_chinese_comma_numbering_without_space():
    out = humanize_text("1、第一条\n2、第二条")
    assert not out.startswith("1、")
    assert "第一条" in out and "第二条" in out


# ── 替换撞词（Reviewer 抓出「还有还有」）────────────────────────

def test_replacement_result_not_reprocessed():
    """「此外」→「还有」撞上原文已有的「还有」曾产生「还有还有」。"""
    out = humanize_text("此外还有。")
    assert "还有还有" not in out, f"重复词未合并: {out!r}"


def test_intentional_redup_survives():
    """真叠词不能被误合并。"""
    for src in ("你看看这个", "一点点小问题"):
        assert humanize_text(src) == src


def test_no_double_replacement_across_all_replacements():
    """全表跑一遍：任何输入不得出现叠词（除已知真叠词）。"""
    from humanize_text import REPLACEMENTS
    for src in REPLACEMENTS:
        out = humanize_text(src + "。")
        import re as _re
        assert not _re.search(r"([\u4e00-\u9fa5]{2,4})\1", out), \
            f"{src!r} -> {out!r} 出现叠词"


# ── 误杀防护 ────────────────────────────────────────────────────

def test_decimal_number_not_truncated():
    """旧正则 `\\d+[\\.、]\\s*` 会把 3.14 变成 14。"""
    out = humanize_text("这个数是3.14，不要改。")
    assert "3.14" in out
    assert "14，" not in out.replace("3.14", "")


def test_ordinal_words_not_truncated():
    """旧正则 `第[一二三…]+` 会把「第一次」变成「次」。"""
    for src in ["这是我第一次尝试。", "第二天就见效了。", "第三次去的时候。"]:
        out = humanize_text(src)
        assert "第一次" in out or src == out, f"{src!r} -> {out!r}"


def test_list_numbering_still_stripped():
    """行首列表序号是要去掉的（那才是「AI 味」）。"""
    out = humanize_text("1. 第一条\n2. 第二条\n3. 第三条")
    assert not out.strip().startswith("1.")
    assert "第一条" in out and "第三条" in out


# ── 幂等性与原文保全 ────────────────────────────────────────────

def _daydir(tmp_path, text):
    (tmp_path / "post_data.json").write_text(
        json.dumps({"content_text": text, "title": "T"}, ensure_ascii=False),
        encoding="utf-8")
    return str(tmp_path)


def test_second_run_does_not_destroy_original(tmp_path):
    """H4：旧实现每次拿 content_text 当原文重跑并覆盖 original。"""
    orig = "因此，我去了。首先，这件事本身并不重要。"
    d = _daydir(tmp_path, orig)

    humanize_day_dir(d)
    first = json.load(open(os.path.join(d, "post_data.json"), encoding="utf-8"))

    humanize_day_dir(d)
    second = json.load(open(os.path.join(d, "post_data.json"), encoding="utf-8"))

    assert second["content_text_original"] == orig, "原文被已处理文本覆盖了"
    assert first["content_text"] == second["content_text"], "二次运行结果变了（不幂等）"


def test_second_run_is_skipped_flagged(tmp_path):
    d = _daydir(tmp_path, "因此，我去了。")
    humanize_day_dir(d)
    r2 = humanize_day_dir(d)
    assert r2.get("skipped_already_humanized") is True


def test_humanize_text_is_idempotent_on_itself():
    src = "因此，我去了。首先，这件事本身并不重要。其次，再看看。"
    once = humanize_text(src)
    assert humanize_text(once) == once


def test_empty_and_none_safe():
    assert humanize_text("") == ""
    assert humanize_text(None) is None
