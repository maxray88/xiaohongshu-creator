#!/usr/bin/env python3
"""主题轮换校验（V1/V2 配色与最近 3 天不重复）。

从 bin/check_xhs_pipeline.py 提取的纯函数，便于复用与单测：
- 06:00 watchdog（事后合规门）
- 02:15 内容质量门（事前拦截，渲染/发布之前告警）

判定规则（与 watchdog 历史行为完全一致）：
- V1 主题不得出现在最近 3 天的 V1 或 V2 主题集合中
- V2 主题不得等于当天 V1，且不得出现在最近 3 天的 V2 主题集合中

注意：不硬编码 10 主题池名单——池子由 01:00/02:00 的 LLM prompt 维护，
此处只校验「与历史不重复」这一条规则，避免两处名单分叉。
"""

import json
import os
import re

# 目录名规范：day_YYYYMMDD_dayN（V2 另有 day_YYYYMMDD_dayN_v2）
DAY_DIR_RE = re.compile(r"^day_(\d{8})_day(\d+)(_v2)?$")


def parse_day_dir(name: str):
    """从目录名解析 (date_c, day_num, is_v2)；不符合规范返回 None。

    旧实现直接切 d[4:12]，畸形名（day_broken / 临时目录 / day_pipeline_test）
    会切出垃圾字符串参与排序：'broke' 的 ASCII 值大于任何数字，会
    打败所有正常日期被当成 latest_day。
    """
    m = DAY_DIR_RE.match(name or "")
    if not m:
        return None
    return m.group(1), int(m.group(2)), bool(m.group(3))


def manifest_color_scheme(day_dir, want_v2: bool):
    """读取某天 manifest 的主题名。want_v2 取 V2 主题，否则取 V1 主题。

    返回值一律 strip 并把空串归一为 None：LLM 写「雾蓝海湾 」带尾空格时，
    与历史的「雾蓝海湾」比较不相等 → 重复主题静默漏检。
    """
    m = os.path.join(day_dir, "manifest.json")
    if not os.path.isfile(m):
        return None
    try:
        j = json.load(open(m, encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(j, dict):
        return None
    v = j.get("color_scheme") if want_v2 else (
        j.get("v1_color_scheme") or j.get("color_scheme"))
    if not isinstance(v, str):
        return None
    v = v.strip()
    return v or None


def recent_schemes(base_dir, today_date, n=3):
    """最近 n 个历史日期（< today_date）的 V1/V2 主题集合。

    返回 (v1_set, v2_set)。today_date 为紧凑 YYYYMMDD。

    窗口按「日历日」生成而非「磁盘上存在的日期」：旧实现只枚举
    存在的目录，某天缺失（05:30 清理边界 / 当天生成失败）时窗口会
    悄悄缩成 2 天，重复主题静默通过。
    """
    from datetime import date, timedelta

    try:
        y, m, d = int(today_date[:4]), int(today_date[4:6]), int(today_date[6:8])
        today = date(y, m, d)
    except (ValueError, TypeError):
        return set(), set()

    # 日历日窗口（含今天在内的前 n+1 天去掉今天 → 前 n 天）
    want_dates = [(today - timedelta(days=k)).strftime("%Y%m%d")
                  for k in range(n, 0, -1)]

    try:
        names = [d for d in os.listdir(base_dir)
                 if d.startswith("day_") and os.path.isdir(os.path.join(base_dir, d))]
    except Exception:
        return set(), set()

    # date_c -> 该日期下的 (v1_dirs, v2_dirs)
    by_date = {}
    for name in names:
        parsed = parse_day_dir(name)
        if not parsed:
            continue
        date_c, _day_num, is_v2 = parsed
        by_date.setdefault(date_c, ([], []))[1 if is_v2 else 0].append(name)

    last_v1, last_v2 = set(), set()
    for date_c in want_dates:  # 只看窗口内，窗口外的不影响
        v1_dirs, v2_dirs = by_date.get(date_c, ([], []))
        for name in v1_dirs:
            cs = manifest_color_scheme(os.path.join(base_dir, name), want_v2=False)
            if cs:
                last_v1.add(cs)
        for name in v2_dirs:
            cs = manifest_color_scheme(os.path.join(base_dir, name), want_v2=True)
            if cs:
                last_v2.add(cs)
    return last_v1, last_v2


def validate_rotation(v1_cs, v2_cs, last_v1, last_v2):
    """校验当天 V1/V2 主题轮换，返回问题列表（为空即通过）。"""
    problems = []
    if not v1_cs:
        # 空串与 None 同义：主题「未知」，多半是 manifest 缺失/损坏
        # 或 LLM 写了空值。旧实现对 None 静默通过，主题检查一片绿灯，
        # 而那正是最需要警告的状态。
        problems.append("[合规] V1 主题未知（V1 manifest 缺失/损坏/为空），无法校验轮换")
    elif v1_cs in (set(last_v1) | set(last_v2)):
        problems.append(f"[合规] V1 主题「{v1_cs}」与最近 3 天重复")
    if not v2_cs:
        problems.append("[合规] V2 主题未知（V2 manifest 缺失/损坏/为空），无法校验轮换")
    elif v2_cs == v1_cs or v2_cs in set(last_v2):
        problems.append(f"[合规] V2 主题「{v2_cs}」与 V1 或最近 3 天 V2 重复")
    return problems


def main_cli(today_date: str) -> int:
    """确定性主题查询（供 01:00 prompt 调用，消除 LLM 误读 manifest 这一类事故）。

    用法：python3 theme_rotation.py 20260922
    输出最近 3 天的 V1/V2 主题集合。day77 事故：LLM 称 day76=苔藓/莓果，
    实际磁盘 day76_v2=晨雾薄荷，致 V1 误选玫瑰暮云撞 day74_v2。
    """
    base = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")
    last_v1, last_v2 = recent_schemes(base, today_date, n=3)
    print(f"最近3天V1: {sorted(last_v1)}")
    print(f"最近3天V2: {sorted(last_v2)}")
    print(f"禁用主题（V1 不可选）: {sorted(set(last_v1) | set(last_v2))}")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("用法：python3 theme_rotation.py YYYYMMDD")
        sys.exit(2)
    sys.exit(main_cli(sys.argv[1]))
