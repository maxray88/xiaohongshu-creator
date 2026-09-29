#!/usr/bin/env python3
"""V1 manifest 标题双落法回归测试。

2026-09-27 事故：01:00 重新生成 day82 时，V1 manifest.json 改用**嵌套**
结构 `{"post_data": {"title": ...}}`，而 content_regression.py 与
check_xhs_pipeline.py 都只读顶层 `title` → 两者都判成「V1 manifest 无标题」。

后果比「误报」更糟：一致性检查的写法是
`if mtitle and ptitle and mtitle != ptitle`，mtitle 为空时**整条检查静默跳过** ——
恰好在最该报警（V1 与 V2 标题分叉）的时候不报警。

修法：两处都读。本测试锁定这个兼容行为。
"""
import json
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ / "core"))
sys.path.insert(0, str(PROJ / "bin"))

import content_regression  # noqa: E402
import manifest_title as MT  # noqa: E402

# 取值逻辑现在只有一份实现：core/manifest_title.py。
# 三个检查器都 import 它，所以测它就等于测三处 —— 而且
# 「三处有没有分叉」不再是靠人记，而是 import 关系保证的：
# 谁不 import 就用不了这段逻辑。
#
# 上一版测试用 regex 从生产文件里抽语句再 exec，那确实是「测真代码」，
# 但把测试和源码文本绑死了：重构一下就 collection error。
# 抽成模块后这个脆弱性消失了，同时约束更强（编译期保证）。
_read_title = MT.manifest_title


def test_three_checkers_import_the_shared_module():
    """三个检查器必须都来自同一个模块，不允许再各自拷贝一份。"""
    import check_content_quality
    import check_xhs_pipeline

    for mod in (content_regression, check_xhs_pipeline, check_content_quality):
        assert hasattr(mod, "manifest_title"), f"{mod.__name__} 没有 import manifest_title"
        # 必须是同一个函数对象，不是同名副本
        assert mod.manifest_title is MT.manifest_title, \
            f"{mod.__name__} 的 manifest_title 是副本，不是共享实现"


def _mk_day(tmp_path, v1_manifest, post_data, v2_manifest=None):
    """搭一个最小 day 目录；只放检查器真正读到的字段。"""
    name = "day_20260927_day82"
    v1 = tmp_path / name
    v1.mkdir(parents=True)
    (v1 / "manifest.json").write_text(json.dumps(v1_manifest, ensure_ascii=False), encoding="utf-8")
    (v1 / "post_data.json").write_text(json.dumps(post_data, ensure_ascii=False), encoding="utf-8")
    if v2_manifest is not None:
        v2 = tmp_path / (name + "_v2")
        v2.mkdir(parents=True)
        (v2 / "manifest.json").write_text(json.dumps(v2_manifest, ensure_ascii=False), encoding="utf-8")
    return name


def _pd(title, tag="反PUA"):
    return {
        "title": title, "series": "情绪树洞", "emotion_tag": tag,
        "content_text": "正文内容。" * 200,          # 400+ 字
        "hashtags": ["情绪树洞", "a", "b", "c", "d", "e", "f", "g"],
        "best_post_time": "22:00",
    }


# ── 取值层：两种落法都要读出同一个标题 ────────────────────────────

def test_flat_manifest_title_read():
    """旧版扁平结构仍要读得出标题。"""
    assert _read_title({"title": "你不是不够好"}) == "你不是不够好"


def test_nested_manifest_title_read():
    """新版嵌套结构 —— 这正是 2026-09-27 漏掉的那种。"""
    assert _read_title({"post_data": {"title": "今天，试着说不"}}) == "今天，试着说不"


def test_flat_wins_when_both_present():
    """两处都有时取扁平值（顶层是更早、更权威的位置）。"""
    assert _read_title({"title": "A", "post_data": {"title": "B"}}) == "A"


def test_empty_manifest_yields_empty_not_crash():
    """两者都缺 → 空串，由上层报「标题缺失」，而不是抛异常。"""
    assert _read_title({}) == ""
    assert _read_title({"post_data": None}) == ""


# ── 崩溃路径：post_data 是非 dict ────────────────────────────────
#
# `(v1m.get("post_data") or {}).get("title")` 看起来对，但 `or {}` 只兜住
# **falsy** 值。post_data 若是非空字符串/列表（LLM 写坏、或人手编辑过），
# `.get` 直接 AttributeError —— 06:00 自检崩栈，而不是报出「标题缺失」。
# 这类输入不会天天出现，但一旦出现就是「自检自己挂了」，最坏情况是
# 连别的检查项都跑不完。

@pytest.mark.parametrize("bad", [
    "abc",                    # 字符串
    [1, 2],                   # 列表
    ["title"],                # 含正确键名的列表（最阴的一种：看着像对了）
    123,                      # 数字
    True,                     # bool
    {"a": 1} and ["x"],       # 混合
])
def test_non_dict_post_data_does_not_crash(bad):
    """非 dict 的 post_data 必须回落到空串，不能抛异常。"""
    d = {"day_num": 82, "post_data": bad}
    try:
        got = _read_title(d)
    except AttributeError as e:
        pytest.fail(f"post_data={bad!r} 导致 AttributeError: {e}")
    assert got == ""


def test_falsy_non_dict_post_data_also_safe():
    """falsy 的非 dict 走 `or {}` 兜底，同样必须安全。"""
    for bad in ([], "", 0, False, set()):
        try:
            assert _read_title({"post_data": bad}) == ""
        except AttributeError as e:
            pytest.fail(f"post_data={bad!r} 导致 AttributeError: {e}")


# ── 崩溃路径之二：title 本身不是 str ─────────────────────────────
#
# isinstance 只判了 post_data 是 dict，没判 dict 里的 title 是 str。
# {"post_data": {"title": ["x"]}} → ["x"].strip() → AttributeError。
# 扁平 {"title": 123} 同样崩（旧代码遗留）。
#
# 为什么不 str(v) 兜底而要当空：把 123 转成 "123" 会让「标题是个数字」
# 看起来像合法非空标题，从而跳过一致性检查 —— 正是这里要防的假绿。

@pytest.mark.parametrize("bad_title", [
    ["x"], ["title"], {"a": 1}, 123, 0, True, 3.14, ("t",),
])
def test_non_str_title_does_not_crash(bad_title):
    """title 不是 str 时必须当空，不能崩在 .strip() 上。"""
    for payload in ({"title": bad_title},
                    {"post_data": {"title": bad_title}},
                    {"post_data": bad_title}):
        try:
            got = _read_title(payload)
        except (AttributeError, TypeError) as e:
            pytest.fail(f"{payload!r} 导致 {type(e).__name__}: {e}")
        assert got == "", f"{payload!r} 应回落为空串，实际 {got!r}"


def test_str_title_is_stripped():
    """正常字符串仍要 strip，不因为加了守卫而放松。"""
    assert _read_title({"title": "  标题  "}) == "标题"
    assert _read_title({"post_data": {"title": "  嵌套标题  "}}) == "嵌套标题"


def test_check_day_survives_non_dict_post_data(tmp_path):
    """端到端：整个 check_day 在这种畸形输入下不得崩。"""
    name = _mk_day(
        tmp_path,
        v1_manifest={"day_num": 82, "post_data": "这不是 dict"},
        post_data=_pd("正常标题"),
        v2_manifest={"title": "另一个标题", "series": "情绪树洞", "emotion_tag": "反PUA"},
    )
    try:
        problems = content_regression.check_day(name, base=tmp_path)
    except AttributeError as e:
        pytest.fail(f"check_day 崩栈: {e}")
    # 崩溃换成了正确行为：报出「V1 manifest 无标题」类问题
    assert any("标题" in p or "title" in p for p in problems), \
        f"应报出标题类问题，实际：{problems}"


# ── 行为层：嵌套结构不能导致一致性检查静默跳过 ────────────────────

def test_nested_manifest_mismatch_is_reported(tmp_path):
    """嵌套 manifest 的标题与 post_data 分叉 → 必须报 manifest-vs-post_data mismatch。

    fixture 刻意让 **只有 manifest 与 post_data 分叉**，post_data 与 V2 一致：

        manifest(嵌套)="V1 标题"   post_data="另一个标题"   V2="另一个标题"

    上一版这里三处都不同（manifest X / post_data X / V2 Y），于是
    post_data-vs-V2 那个 mismatch 在**新旧逻辑下都会报**，测试照样通过 ——
    断言被另一条检查掩盖了，等于没测。
    本版只留唯一分叉点：旧逻辑 mtitle='' 短路跳过 → 0 个标题问题；
    新逻辑读出「V1 标题」→ 报 mismatch。精确失败。
    """
    name = _mk_day(
        tmp_path,
        v1_manifest={"day_num": 82, "post_data": {"title": "V1 标题"}},
        post_data=_pd("另一个标题"),
        v2_manifest={"title": "另一个标题", "series": "情绪树洞", "emotion_tag": "反PUA"},
    )
    problems = content_regression.check_day(name, base=tmp_path)
    joined = " ".join(problems)
    # 精确断言：必须是 manifest-vs-post_data 这一条，且标题两侧都在
    assert "V1 标题" in joined, f"未报出 manifest 标题：{problems}"
    assert "另一个标题" in joined, f"未报出 post_data 标题：{problems}"
    # 且不能靠 post_data-vs-V2 那条蒙混过关 —— 本 fixture 里两者一致
    assert "V1 vs V2" not in joined, \
        f"fixture 应当只有 manifest-vs-post_data 分叉，却报出了 V1-vs-V2：{problems}"


def test_nested_manifest_consistent_is_clean(tmp_path):
    """嵌套结构 + 三处一致 → 不应产生标题类问题。"""
    name = _mk_day(
        tmp_path,
        v1_manifest={"day_num": 82, "post_data": {"title": "同一个标题"}},
        post_data=_pd("同一个标题"),
        v2_manifest={"title": "同一个标题", "series": "情绪树洞", "emotion_tag": "反PUA"},
    )
    problems = content_regression.check_day(name, base=tmp_path)
    title_problems = [p for p in problems if "title" in p or "标题" in p]
    assert not title_problems, f"三处一致却报标题问题：{title_problems}"


def test_still_detects_missing_title_everywhere(tmp_path):
    """真的全都没标题时，仍必须报缺失（兼容不能把报警也一起关掉）。"""
    name = _mk_day(
        tmp_path,
        v1_manifest={"day_num": 82},
        post_data=_pd(""),                       # post_data 也无标题
        v2_manifest={"title": "V2 有标题", "series": "情绪树洞", "emotion_tag": "反PUA"},
    )
    problems = content_regression.check_day(name, base=tmp_path)
    assert any("标题" in p for p in problems), f"全缺标题却没报警：{problems}"
