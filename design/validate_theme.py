#!/usr/bin/env python3
"""Validate new theme does not repeat within last 3 days — used by Open Design selection and 06:00 check.

本文件曾自带一份主题轮换实现，与 core/theme_rotation.py 分叉：
- 这里按日历日集合排序取最后 3 天，那里按前 3 个日历日 —— 边界不同
- 这里用 n[4:12] 切日期，畸形目录名会切出错位字符串
- 这里用 sorted()[-3:]（字典序），那里用日期数值序
两处判定不一致时，「01:00 选主题时认为不重复、06:00 自检时认为重复」，
或者反过来 —— 都是难以排查的问题。

现在统一委托给 core/theme_rotation.recent_schemes()，本文件只负责
CLI 参数解析和 JSON 输出。
"""
import json
import sys
import time
from pathlib import Path

PROJ = Path.home() / "02_Cronjobs_Projects/01_XHS_Daily_Post"
sys.path.insert(0, str(PROJ / "core"))

from theme_rotation import recent_schemes  # noqa: E402

BASE = Path.home() / ".hermes/data/xhs_treehole"
TOKENS = PROJ / "design/design_tokens.json"


def _valid_themes():
    if not TOKENS.is_file():
        return set()
    try:
        return set(json.loads(TOKENS.read_text(encoding="utf-8")).get("themes", {}).keys())
    except Exception:
        return set()


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv[1:]
    if len(args) < 1:
        print("Usage: validate_theme.py <new_theme> [--json]")
        sys.exit(2)
    new_theme = args[0]

    if not BASE.is_dir():
        payload = {"ok": True, "theme": new_theme, "recent": [],
                   "skipped": "BASE not found"}
        if as_json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print("BASE not found, skipping history check")
        sys.exit(0)

    valid = _valid_themes()
    today = time.strftime("%Y%m%d")
    v1_recent, v2_recent = recent_schemes(str(BASE), today)
    # 判定用两窗并集：01:00 选的是 V1 主题，但 V1 与 V2 主题共享
    # 同一套配色池，任一近期用过都算重复。
    pool = set(v1_recent) | set(v2_recent)
    ok = new_theme not in pool

    if valid and new_theme not in valid:
        note = f"'{new_theme}' not in theme library, allowed if not repeating"
    else:
        note = ""

    if as_json:
        print(json.dumps({
            "ok": ok,
            "theme": new_theme,
            "today": today,
            "recent_v1": sorted(v1_recent),
            "recent_v2": sorted(v2_recent),
            "note": note,
        }, ensure_ascii=False))
    else:
        if note:
            print(f"⚠ {note}")
        if ok:
            print(f"✅ Theme '{new_theme}' OK — recent: "
                  f"{sorted(pool) or 'none'}")
        else:
            print(f"❌ Theme '{new_theme}' repeats within last 3 days: "
                  f"{sorted(pool)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
