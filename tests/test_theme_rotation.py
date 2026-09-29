#!/usr/bin/env python3
"""主题轮换校验单测（core/theme_rotation.py）。

规则与 06:00 watchdog 历史行为一致：
- V1 不得出现在最近 3 天 V1/V2 主题中
- V2 不得等于当天 V1，不得出现在最近 3 天 V2 主题中

运行：python3 -m pytest tests/ -v（项目根目录）
"""

import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from theme_rotation import (manifest_color_scheme, parse_day_dir,  # noqa: E402
                            recent_schemes, validate_rotation)


def test_clean_rotation_passes():
    assert validate_rotation("A", "B", {"X", "Y"}, {"Z"}) == []


def test_v1_collision_with_history():
    ps = validate_rotation("X", "B", {"X"}, set())
    assert len(ps) == 1 and "V1" in ps[0]


def test_v1_collision_with_v2_history():
    ps = validate_rotation("Z", "B", set(), {"Z"})
    assert len(ps) == 1 and "V1" in ps[0]


def test_v2_equals_today_v1():
    ps = validate_rotation("A", "A", set(), set())
    assert len(ps) == 1 and "V2" in ps[0]


def test_v2_collision_with_v2_history():
    ps = validate_rotation("A", "Z", set(), {"Z"})
    assert len(ps) == 1 and "V2" in ps[0]


def test_unknown_schemes_are_reported_not_silently_passed():
    """M13：manifest 缺失/损坏时主题检查必须报警，不能一片绿灯。"""
    ps = validate_rotation(None, None, set(), set())
    assert len(ps) == 2
    assert any("V1 主题未知" in p for p in ps)
    assert any("V2 主题未知" in p for p in ps)


def test_one_unknown_still_reports_that_side():
    ps = validate_rotation("A", None, set(), set())
    assert len(ps) == 1 and "V2" in ps[0]


def test_empty_string_is_normalized_upstream_not_here():
    """空串的归一化发生在 manifest_color_scheme 层（它返回 None）。

    validate_rotation 只处理 None/str；直接喂 "" 不是真实调用路径，
    但为防御起见也让它落到「未知」分支而不是当成一个主题名。
    """
    ps = validate_rotation("", "B", {""}, set())
    assert ps, "空串不应被当作合法主题名"
    assert any("未知" in p for p in ps)


# ── parse_day_dir（M1：畸形目录名不得参与排序）──────────────────

def test_parse_day_dir_normal():
    assert parse_day_dir("day_20260927_day82") == ("20260927", 82, False)


def test_parse_day_dir_v2():
    assert parse_day_dir("day_20260927_day82_v2") == ("20260927", 82, True)


def test_parse_day_dir_rejects_malformed():
    for bad in ("day_broken", "day_pipeline_test", "zzz", "day_20260927",
                "day_abcdefgh_day1", "day_2026092_day1", "xday_20260927_day1"):
        assert parse_day_dir(bad) is None, f"{bad!r} 不该被解析成日期"


def test_parse_day_dir_keeps_day_num_numeric():
    """day_9 必须能排对 day_10 —— 字符串排序会反过来。"""
    assert parse_day_dir("day_20260927_day9")[1] == 9
    assert parse_day_dir("day_20260927_day10")[1] == 10
    assert parse_day_dir("day_20260927_day10")[1] > parse_day_dir("day_20260927_day9")[1]


# ── manifest_color_scheme（M11：strip）──────────────────────────

def _mk(tmp, name, payload):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False),
                                     encoding="utf-8")
    return str(d)


def test_color_scheme_is_stripped(tmp_path):
    """LLM 写「雾蓝海湾 」带尾空格 → 与历史「雾蓝海湾」比较会不相等。"""
    d = _mk(tmp_path, "day_20260901_day1",
            {"v1_color_scheme": "雾蓝海湾 ", "color_scheme": "暮色琥珀\t"})
    assert manifest_color_scheme(d, want_v2=False) == "雾蓝海湾"
    assert manifest_color_scheme(d, want_v2=True) == "暮色琥珀"


def test_color_scheme_empty_becomes_none(tmp_path):
    d = _mk(tmp_path, "day_20260901_day1", {"v1_color_scheme": "   "})
    assert manifest_color_scheme(d, want_v2=False) is None


def test_color_scheme_non_string_becomes_none(tmp_path):
    d = _mk(tmp_path, "day_20260901_day1", {"color_scheme": 123})
    assert manifest_color_scheme(d, want_v2=True) is None


def test_color_scheme_missing_manifest_is_none(tmp_path):
    d = tmp_path / "day_20260901_day1"
    d.mkdir()
    assert manifest_color_scheme(str(d), want_v2=False) is None


# ── recent_schemes（M12：窗口按日历日而非磁盘存在）──────────────

def _mkday(base, day_off, v1_cs, v2_cs):
    ds = (date.today() - timedelta(days=day_off)).strftime("%Y%m%d")
    d1 = base / f"day_{ds}_day{100 + day_off}"
    d1.mkdir(parents=True)
    (d1 / "manifest.json").write_text(
        json.dumps({"v1_color_scheme": v1_cs, "color_scheme": v1_cs}, ensure_ascii=False),
        encoding="utf-8")
    if v2_cs:
        d2 = base / f"day_{ds}_day{100 + day_off}_v2"
        d2.mkdir(parents=True)
        (d2 / "manifest.json").write_text(
            json.dumps({"color_scheme": v2_cs}, ensure_ascii=False), encoding="utf-8")
    return ds


def test_window_is_calendar_days_not_disk_days(tmp_path):
    """M12 核心回归：中间某天磁盘上没有目录，窗口不能悄悄缩成 2 天。"""
    base = tmp_path
    today = date.today()
    # 只造 day-1 和 day-3，缺 day-2
    _mkday(base, 1, "A1", "B1")
    _mkday(base, 3, "A3", "B3")
    v1, v2 = recent_schemes(str(base), today.strftime("%Y%m%d"), n=3)
    # 两天的数据都应被收进窗口
    assert "A1" in v1 and "A3" in v1
    assert "B1" in v2 and "B3" in v2


def test_window_excludes_days_outside_n(tmp_path):
    base = tmp_path
    _mkday(base, 1, "A1", None)
    _mkday(base, 2, "A2", None)
    _mkday(base, 3, "A3", None)
    _mkday(base, 10, "FAR", "FAR2")   # 远在窗口外
    v1, v2 = recent_schemes(str(base), date.today().strftime("%Y%m%d"), n=3)
    assert "A1" in v1 and "A2" in v1 and "A3" in v1
    assert "FAR" not in v1 and "FAR2" not in v2


def test_malformed_dirs_do_not_enter_window(tmp_path):
    base = tmp_path
    (base / "day_broken").mkdir()
    (base / "day_pipeline_test").mkdir()
    _mkday(base, 1, "A1", None)
    v1, _ = recent_schemes(str(base), date.today().strftime("%Y%m%d"), n=3)
    assert v1 == {"A1"}


def test_recent_schemes_bad_date_returns_empty(tmp_path):
    v1, v2 = recent_schemes(str(tmp_path), "not-a-date", n=3)
    assert v1 == set() and v2 == set()


def test_recent_schemes_missing_dir_returns_empty(tmp_path):
    v1, v2 = recent_schemes(str(tmp_path / "nope"), date.today().strftime("%Y%m%d"))
    assert v1 == set() and v2 == set()
