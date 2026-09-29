#!/usr/bin/env python3
"""06:00 自检的误报降级逻辑回归测试。

背景（2026-09-27）：用户反复投诉「06:00 误报」。实测根因是
check_xhs_pipeline.py 只看 cron 的 last_status，而该字段记录的是
「最后一次运行」的结果 —— 02:15 质量门当时因 V2 未建成而 exit 1，
人工重跑修好后 last_status 仍停在 'error'，06:00 于是继续报，
但当场跑一遍质量门是 exit 0。

修复原则：对「产物可验证」的步骤，产物是权威，last_status 只作参考；
无产物可验的步骤（登录探针、清理）仍以 last_status 为准。

运行：python3 -m pytest tests/ -q（项目根目录）
"""

import importlib.util
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_spec = importlib.util.spec_from_file_location(
    "check_xhs_pipeline", os.path.join(ROOT, "bin", "check_xhs_pipeline.py"))
ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ck)


# ── _ran_today 三态 ─────────────────────────────────────────────

def test_ran_today_true_for_today_iso():
    assert ck._ran_today("2026-09-27T02:15:45.448911+08:00", "2026-09-27") is True


def test_ran_today_false_for_yesterday():
    assert ck._ran_today("2026-09-26T23:00:00+08:00", "2026-09-27") is False


def test_ran_today_accepts_space_separator():
    assert ck._ran_today("2026-09-27 02:15:45", "2026-09-27") is True


def test_ran_today_accepts_compact_date():
    assert ck._ran_today("20260927", "2026-09-27") is True


def test_ran_today_empty_is_false_not_none():
    """字段缺失 = 确实没跑（False），不是格式问题（None）。"""
    assert ck._ran_today("", "2026-09-27") is False
    assert ck._ran_today(None, "2026-09-27") is False


def test_ran_today_garbage_is_none_so_it_is_reported_separately():
    """格式漂移必须与「没跑」区分开，否则排查方向被引偏（旧实现是 startswith）。"""
    assert ck._ran_today("garbage", "2026-09-27") is None
    assert ck._ran_today("2026/09/27 10:00", "2026-09-27") is None


# ── _artifact_ok 产物判定 ────────────────────────────────────────

def _mkv2(tmp, slots, njpg_each=1):
    imgs = os.path.join(tmp, "images")
    os.makedirs(imgs, exist_ok=True)
    for i, sl in enumerate(slots, 1):
        for _ in range(njpg_each):
            open(os.path.join(imgs, f"card_v2_{i}_{sl}.jpg"), "w").close()
    return tmp


ALL_SLOTS = ["cover", "scene", "insight", "method", "gentle", "cta"]


def test_render_artifacts_ok_with_all_six_slots(tmp_path):
    v2 = _mkv2(str(tmp_path), ALL_SLOTS)
    assert ck._artifact_ok("render_xhs_cards.sh", str(tmp_path), v2) is True


def test_render_artifacts_false_when_images_dir_missing(tmp_path):
    v2 = str(tmp_path / "nope")
    assert ck._artifact_ok("render_xhs_cards.sh", str(tmp_path), v2) is False


def test_render_artifacts_false_with_only_three_slots(tmp_path):
    """只数总数会放过「6 张重复」；必须按卡位判定。"""
    v2 = _mkv2(str(tmp_path), ALL_SLOTS[:3], njpg_each=2)  # 6 个文件但只覆盖 3 卡位
    assert ck._artifact_ok("render_xhs_cards.sh", str(tmp_path), v2) is False


def test_render_artifacts_accepts_alternate_card_naming(tmp_path):
    """01:00 曾产出 card_01_cover.html 风格，glob 必须两种都吃。"""
    imgs = tmp_path / "images"
    imgs.mkdir()
    for i, sl in enumerate(ALL_SLOTS, 1):
        (imgs / f"card_{i:02d}_{sl}.jpg").write_text("x")
    assert ck._artifact_ok("render_xhs_cards.sh", str(tmp_path), str(tmp_path)) is True


def test_video_artifacts_require_real_file(tmp_path):
    v2 = str(tmp_path)
    assert ck._artifact_ok("assemble_xhs_treehole.sh", str(tmp_path), v2) is False
    (tmp_path / "video").mkdir()
    assert ck._artifact_ok("assemble_xhs_treehole.sh", str(tmp_path), v2) is False
    (tmp_path / "video" / "video_note.mp4").write_text("x")
    assert ck._artifact_ok("assemble_xhs_treehole.sh", str(tmp_path), v2) is True


def test_unverifiable_steps_never_get_downgraded(tmp_path):
    """没有本地可验产物的步骤，必须仍以 last_status 为准。

    特别包含 publish：它的产物是云端草稿，本地验不了。
    Reviewer 2026-09-27 抓出过一个洞 —— 曾把 mp4 当作 publish 的判据，
    而 mp4 是 assemble 造的，publish 失败时照样在盘上，于是 publish 的
    error 永远被降成 note，检查被架空。这里锁死该行为。
    """
    for script in ("check_xhs_login.py", "cleanup_xhs_treehole.py",
                   "publish_xhs_video.sh"):
        assert ck._artifact_ok(script, str(tmp_path), str(tmp_path)) is False, \
            f"{script} 没有本地可验产物，不该享受 last_status 降级"


def test_publish_never_borrowed_assemble_artifact(tmp_path):
    """mp4 存在不得让 publish 被判定为可信。"""
    (tmp_path / "video").mkdir()
    (tmp_path / "video" / "video_note.mp4").write_text("x")
    assert ck._artifact_ok("assemble_xhs_treehole.sh", str(tmp_path), str(tmp_path)) is True
    assert ck._artifact_ok("publish_xhs_video.sh", str(tmp_path), str(tmp_path)) is False


def test_bare_date_without_time_is_accepted():
    """LOW：裸日期 YYYY-MM-DD 不该被判成「格式无法解析」。"""
    assert ck._ran_today("2026-09-27", "2026-09-27") is True
    assert ck._ran_today("2026-09-26", "2026-09-27") is False


def test_unknown_script_is_false(tmp_path):
    assert ck._artifact_ok("some_future_step.py", str(tmp_path), str(tmp_path)) is False
