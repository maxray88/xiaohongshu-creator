#!/usr/bin/env python3
"""draft 脚本共用的保存验证 + 目录筛选回归测试。

对应 2026-09-27 第二轮 Reviewer（deleg_73ec4f3a）的两条反馈：
- MED-C：「已保存」文案零实证，方向 fail-safe 但应覆盖多种形态
- MED-D：tracker 写失败 exit 1 会诱发重跑 → 草稿箱出现重复草稿
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import xhs_video_draft as vd


# ── 保存指示判定 ──────────────────────────────────────────────

def test_bare_draft_never_counts_as_saved():
    """侧边栏永远有「草稿箱」标签 —— 拿它当证据等于恒真。"""
    assert vd.save_confirmed_in("草稿箱  3") is False
    assert vd.save_confirmed_in("草稿  发布笔记  数据中心") is False


def test_known_markers_recognised():
    for s in ("已保存", "保存成功", "已存草稿", "草稿已保存",
              "自动保存于 15:23", "已自动保存", "存为草稿"):
        assert vd.save_confirmed_in(s) is True, f"{s!r} 未被识别"


def test_empty_snippet_is_false():
    assert vd.save_confirmed_in("") is False
    assert vd.save_confirmed_in(None) is False


# ── 目录筛选（畸形名不得胜出）─────────────────────────────────

def test_malformed_v2_dir_never_selected(tmp_path, monkeypatch):
    """day_broken_v2 因 ASCII 'b' > 数字，字符串排序会胜出。"""
    base = str(tmp_path)
    os.makedirs(os.path.join(base, "day_broken_v2"), exist_ok=True)
    os.makedirs(os.path.join(base, "day_20260927_day82_v2"), exist_ok=True)
    monkeypatch.setattr(vd, "BASE", base)
    assert vd.find_latest_v2_dir(wait_seconds=0, attempts=1) == "day_20260927_day82_v2"


def test_day10_sorts_after_day9(tmp_path, monkeypatch):
    """字符串排序会把 day9 排在 day10 前（'9' > '1'）。"""
    base = str(tmp_path)
    os.makedirs(os.path.join(base, "day_20260927_day9_v2"), exist_ok=True)
    os.makedirs(os.path.join(base, "day_20260927_day10_v2"), exist_ok=True)
    monkeypatch.setattr(vd, "BASE", base)
    assert vd.find_latest_v2_dir(wait_seconds=0, attempts=1) == "day_20260927_day10_v2"


def test_real_day_wins_over_higher_but_older(tmp_path, monkeypatch):
    """日期优先于 dayN：day9 的次日在 day10 之前。"""
    base = str(tmp_path)
    os.makedirs(os.path.join(base, "day_20260926_day99_v2"), exist_ok=True)
    os.makedirs(os.path.join(base, "day_20260927_day1_v2"), exist_ok=True)
    monkeypatch.setattr(vd, "BASE", base)
    assert vd.find_latest_v2_dir(wait_seconds=0, attempts=1) == "day_20260927_day1_v2"


# ── 两文件共享同一份 marker（防止日后分叉）───────────────────

def test_image_script_shares_save_markers():
    import xhs_image_draft as im
    assert im.save_confirmed_in is vd.save_confirmed_in, \
        "两侧各写一份 marker，迟早分叉"


# ── tracker 失败不得诱发重跑（MED-D）─────────────────────────

def test_tracker_failure_keeps_exit_zero_and_warns_not_rerun():
    """草稿已存进云端；tracker 失败若 exit 1 → cron 报错 → 重跑 → 重复草稿。"""
    import inspect
    src = inspect.getsource(vd.main)
    tracker_block = src[src.index("published_content.json"):]
    assert "sys.exit(1)" not in tracker_block, \
        "tracker 失败仍 exit 1，会诱发重跑造成重复草稿"
    assert "ACTION-REQUIRED" in tracker_block, \
        "必须显式提示「请勿重跑」"
    assert "勿重跑" in tracker_block, "必须写明重跑后果"


def test_draft_shared_module_exists():
    """draft_shared 模块存在且包含所有共享函数。"""
    import draft_shared
    assert hasattr(draft_shared, 'SAVE_MARKERS')
    assert hasattr(draft_shared, 'save_confirmed_in')
    assert hasattr(draft_shared, 'get_draft_count')
    assert hasattr(draft_shared, 'find_latest_dir')
    assert hasattr(draft_shared, 'navigate_publish_page')


def test_video_draft_imports_from_draft_shared():
    """video draft 从 draft_shared 导入共享函数。"""
    import inspect
    import xhs_video_draft as vd
    src = inspect.getsource(vd)
    assert 'from draft_shared import' in src
    assert 'SAVE_MARKERS' in src  # 仍通过 draft_shared 可用


def test_image_draft_imports_from_draft_shared():
    """image draft 从 draft_shared 导入共享函数。"""
    import inspect
    import xhs_image_draft as im
    src = inspect.getsource(im)
    assert 'from draft_shared import' in src


def test_find_latest_dir_v2_wrapper():
    """find_latest_v2_dir 是 find_latest_dir(is_v2=True) 的 thin wrapper。"""
    import inspect
    import xhs_video_draft as vd
    src = inspect.getsource(vd.find_latest_v2_dir)
    assert 'find_latest_dir(is_v2=True' in src


def test_find_latest_dir_v1_wrapper():
    """find_latest_v1_dir 是 find_latest_dir(is_v2=False) 的 thin wrapper。"""
    import inspect
    import xhs_image_draft as im
    src = inspect.getsource(im.find_latest_v1_dir)
    assert 'find_latest_dir(is_v2=False' in src
