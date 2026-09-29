#!/usr/bin/env python3
"""content_regression 的反例测试。

2026-09-27 审计发现：
- 标题一致性用 `and` 短路，任一为空就整条检查跳过 —— 而标题缺失
  正是最该报警的情况
- emoji 只查 So，漏掉带肤色修饰的 Sk
- best_post_time 用固定切片 bpt[11:13]，格式一变就切出错位数字
- _latest_day 只查 startswith("day_")，畸形名 day_broken 切出 'broke'
- --all 在数据目录不存在时抛 FileNotFoundError
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import content_regression as cr


def _mk_day(base: Path, name="day_20260927_day82", **pd_over):
    v1 = base / name
    v2 = base / (name + "_v2")
    (v1 / "images").mkdir(parents=True, exist_ok=True)
    v2.mkdir(parents=True, exist_ok=True)

    pd = {
        "title": "你不是不够好",
        "hashtags": ["情绪树洞", "反PUA", "a", "b", "c", "d", "e"],
        "emotion_tag": "反PUA",
        "content_text": "反PUA\n" + "我去了，那些事就算了。" * 45 + "为什么？",
        "best_post_time": "20:00-22:00",
        "series": "情绪树洞",
    }
    pd.update(pd_over)
    (v1 / "post_data.json").write_text(json.dumps(pd, ensure_ascii=False), encoding="utf-8")
    (v1 / "manifest.json").write_text(
        json.dumps({"title": pd["title"], "series": "情绪树洞"}, ensure_ascii=False),
        encoding="utf-8")
    (v2 / "manifest.json").write_text(
        json.dumps({"title": pd["title"], "series": "情绪树洞"}, ensure_ascii=False),
        encoding="utf-8")
    return name


def test_clean_day_passes(tmp_path):
    name = _mk_day(tmp_path)
    probs = cr.check_day(name, base=tmp_path)
    assert probs == [], probs


# ── 标题一致性：不能因任一方为空而跳过 ──────────────────────────

def test_missing_title_is_flagged_not_skipped(tmp_path):
    """V1 manifest 缺 title，post_data 有 —— 旧逻辑直接跳过一致性检查。"""
    name = _mk_day(tmp_path)
    (tmp_path / name / "manifest.json").write_text(
        json.dumps({"series": "情绪树洞"}, ensure_ascii=False), encoding="utf-8")
    probs = cr.check_day(name, base=tmp_path)
    assert any("标题缺失不一致" in p for p in probs), \
        f"一方标题为空被静默跳过: {probs}"


def test_v2_title_missing_is_flagged(tmp_path):
    name = _mk_day(tmp_path)
    (tmp_path / (name + "_v2") / "manifest.json").write_text(
        json.dumps({"series": "情绪树洞"}, ensure_ascii=False), encoding="utf-8")
    probs = cr.check_day(name, base=tmp_path)
    assert any("标题缺失不一致" in p for p in probs), f"V2 标题为空被跳过: {probs}"


def test_mismatch_reports_both_values(tmp_path):
    name = _mk_day(tmp_path)
    (tmp_path / (name + "_v2") / "manifest.json").write_text(
        json.dumps({"title": "完全不同的标题", "series": "情绪树洞"}, ensure_ascii=False),
        encoding="utf-8")
    probs = cr.check_day(name, base=tmp_path)
    mism = [p for p in probs if "mismatch" in p]
    assert mism, probs
    assert "你不是不够好" in mism[0] and "完全不同的标题" in mism[0], \
        f"报错应含双方实际值: {mism[0]}"


# ── emoji 肤色修饰 ─────────────────────────────────────────────

def test_emoji_with_skin_tone_modifier_caught(tmp_path):
    """👍🏽 = So + Sk，只查 So 会漏。"""
    name = _mk_day(tmp_path, title="今天不想上班👍🏽")
    probs = cr.check_day(name, base=tmp_path)
    assert any("emoji" in p for p in probs), f"带肤色的 emoji 漏检: {probs}"


def test_plain_emoji_still_caught(tmp_path):
    name = _mk_day(tmp_path, title="今天不想上班👍")
    probs = cr.check_day(name, base=tmp_path)
    assert any("emoji" in p for p in probs), probs


# ── best_post_time 解析 ────────────────────────────────────────

def test_best_post_time_formats(tmp_path):
    ok_formats = ["20:00-22:00", "20:30", "晚上8点", "21时", "20", "2026-09-27T20:00+08:00"]
    for f in ok_formats:
        name = _mk_day(tmp_path, best_post_time=f)
        probs = [p for p in cr.check_day(name, base=tmp_path) if "best_post_time" in p]
        assert probs == [], f"{f!r} 被误判: {probs}"


def test_best_post_time_out_of_range_caught(tmp_path):
    name = _mk_day(tmp_path, best_post_time="15:00")
    probs = cr.check_day(name, base=tmp_path)
    assert any("best_post_time" in p and "20-23" in p for p in probs), \
        f"15:00 应被判出范围: {probs}"


def test_best_post_time_garbage_flagged(tmp_path):
    name = _mk_day(tmp_path, best_post_time="随便什么时候")
    probs = cr.check_day(name, base=tmp_path)
    assert any("format bad" in p for p in probs), f"垃圾值应报格式错: {probs}"


# ── 目录名校验 ────────────────────────────────────────────────

def test_malformed_dir_ignored(tmp_path):
    _mk_day(tmp_path)
    (tmp_path / "day_broken").mkdir()
    days = cr._day_dirs(tmp_path)
    assert "day_broken" not in days, f"畸形目录混入: {days}"
    assert cr._latest_day(tmp_path) == "day_20260927_day82"


def test_v2_dir_excluded_from_day_list(tmp_path):
    _mk_day(tmp_path)
    assert all(not d.endswith("_v2") for d in cr._day_dirs(tmp_path))


def test_missing_base_dir_is_empty_not_crash(tmp_path):
    missing = tmp_path / "nope"
    assert cr._day_dirs(missing) == []
    assert cr._latest_day(missing) is None


# ── CLI ───────────────────────────────────────────────────────

def test_all_flag_on_missing_dir_exits_cleanly():
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.argv=['x','--all']; "
         "import content_regression as c; c.BASE=__import__('pathlib').Path('/nonexistent-xyz'); "
         "sys.exit(c.main())"],
        capture_output=True, text=True,
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
    assert r.returncode == 1, f"应 exit 1，实际 {r.returncode}\n{r.stderr}"
    assert "Traceback" not in r.stderr, f"不应抛栈:\n{r.stderr}"
