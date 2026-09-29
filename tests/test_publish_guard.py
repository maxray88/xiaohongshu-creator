#!/usr/bin/env python3
"""发布前红线闸回归测试（core/publish_guard.py）。

背景：02:15 质量门已经检查「标题 ≤18 字」，但它只覆盖**当天 02:15
那一次运行**。02:15 失败、被忽略、或事后单独重跑 03:00/05:00 时，
超长标题会一路走到 `_fill_title()`。而小红书对超长标题是**静默截断** ——
本地文件还是 24 字，06:00 自检照样 PASS，用户看到的却是标题被砍半的笔记。

所以规则在出口前再判一次，不依赖上游是否会跑。
"""
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ / "core"))

from publish_guard import (  # noqa: E402
    CONTENT_MAX,
    CONTENT_MIN,
    TITLE_MAX,
    check_publishable,
    require_publishable,
)

GOOD_TITLE = "今天，试着说不"
GOOD_CONTENT = "正文内容。" * 100          # 500 字，区间内


# ── 正常内容必须放行 ──────────────────────────────────────────────

def test_good_content_passes():
    assert check_publishable(GOOD_TITLE, GOOD_CONTENT) == []
    require_publishable(GOOD_TITLE, GOOD_CONTENT)     # 不抛异常即通过


@pytest.mark.parametrize("n", [CONTENT_MIN, 450, CONTENT_MAX])
def test_content_length_boundaries_pass(n):
    body = "字" * n
    assert check_publishable(GOOD_TITLE, body) == [], \
        f"{n} 字应在 [{CONTENT_MIN}, {CONTENT_MAX}] 内却被拦"


# ── 标题：静默截断是这里要防的坑 ──────────────────────────────────

@pytest.mark.parametrize("n", [TITLE_MAX, 1])
def test_title_length_boundaries_pass(n):
    assert check_publishable("字" * n) == [], f"{n} 字应通过"


@pytest.mark.parametrize("n", [TITLE_MAX + 1, 20, 24, 100])
def test_title_too_long_is_blocked(n):
    """超长标题必须拦 —— 平台会静默截断，本地检查却会放行。"""
    probs = check_publishable("字" * n)
    assert probs, f"{n} 字标题应被拦"
    assert "标题" in probs[0]
    with pytest.raises(ValueError):
        require_publishable("字" * n)


def test_actual_day82_style_overlong_title():
    """真实量级：一个看起来正常的、实际超长 1 字的标题。

    18 字恰好合规（上限 18），19 字必须拦 —— 边界上只差一个字，
    正是最容易在人工复核时看漏的情形。
    """
    assert check_publishable("当你的同事总在下班前给你加活儿的时候") == [], \
        "18 字应在上限内"
    probs = check_publishable("当你的同事又总在下班前给你加活儿的时候")
    assert probs, "19 字标题应被拦（上限 18）"
    assert "19" in probs[0]


def test_empty_title_blocked():
    assert check_publishable("") != []
    assert check_publishable("   ") != []


def test_title_with_hash_blocked():
    assert any("#" in p for p in check_publishable("标题#标签"))


def test_title_ending_with_question_blocked():
    assert any("问号" in p for p in check_publishable("你今天累了吗？"))
    assert any("问号" in p for p in check_publishable("你今天累了吗?"))


def test_title_with_question_inside_is_ok():
    """问号只在结尾才违规，中间出现（虽罕见）不拦。"""
    assert check_publishable("你问我累不累，我说不累") == []


# ── 正文长度 ──────────────────────────────────────────────────────

def test_content_too_short_blocked():
    assert any("少于" in p for p in check_publishable(GOOD_TITLE, "太短了"))


def test_content_too_long_blocked():
    assert any("超出" in p for p in check_publishable(GOOD_TITLE, "字" * (CONTENT_MAX + 1)))


def test_content_optional():
    """不传 content 时只查标题（05:00 视频侧目前只传标题）。"""
    assert check_publishable(GOOD_TITLE) == []


# ── 多项问题要一次全报出来，而不是只报第一个 ────────────────────

def test_all_problems_reported_at_once():
    probs = check_publishable("这个标题超长而且带#号还以问号结尾？", "短")
    assert len(probs) >= 3, f"应一次报出全部问题，实际：{probs}"


# ── 与真实 day82 数据一致（防止守卫误伤合规内容）─────────────────

def test_real_day82_content_passes():
    """day82 的真实标题/正文必须能过闸 —— 守卫不能误伤。"""
    import json
    import os
    d = os.path.expanduser("~/.hermes/data/xhs_treehole/day_20260927_day82/post_data.json")
    if not os.path.isfile(d):
        pytest.skip("day82 数据不在本机")
    pd = json.load(open(d, encoding="utf-8"))
    body = pd.get("content_text", "")
    probs = check_publishable(pd.get("title", ""), body)
    assert probs == [], f"day82 合规内容被守卫误伤：{probs}"
