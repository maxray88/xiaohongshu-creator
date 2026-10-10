#!/usr/bin/env python3
"""Content red-line regression test — standalone, date-independent.

Checks for any day dir:
  - title ≤18, no emoji/#/?
  - hashtags 6-10, contains 情绪树洞 + emotion_tag verbatim, no #
  - content_text 400-900, no emoji, contains ？, first line contains emotion_tag verbatim
  - best_post_time ∈ [20,23]
  - V1 manifest/post_data/V2 manifest same title & series (cross-file identity)

Usage:
  python3 core/content_regression.py           # check latest day
  python3 core/content_regression.py --all     # check all days
  python3 core/content_regression.py --day day_20260827_day50
"""
import argparse, json, os, re, sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from theme_rotation import parse_day_dir
from manifest_title import manifest_title, plain_title, plain_series
from content_checks import has_emoji as _has_emoji
from content_checks import load_json_tolerant
from xhs_config import TITLE_MAX

BASE = Path.home() / ".hermes/data/xhs_treehole"


def _parse_hour(s: str) -> int | None:
    """从 best_post_time 里解析出小时，解析不出返回 None。

    支持：20:00-22:00 / 20:30 / 2026-09-27T20:00+08:00 / 20时 /
    晚上8点 / 8点 / 纯 20。

    「晚上8点」= 20 点而不是 8 点 —— 中文口语的上下午省略很常见，
    按字面解析会得到 8，然后报「不在 20-23h」这种看似合理的错。
    """
    s = s.strip()
    # 中文时段词 → 12 小时制补正
    pm_shift = 0
    if re.search(r"晚上|傍晚|夜里|晚", s):
        pm_shift = 12
    m = re.search(r"(?<!\d)(\d{1,2})\s*(?:[:：]\d{1,2})?\s*(?:时|点|:|：|$)", s)
    if not m:
        return None
    h = int(m.group(1))
    if pm_shift and 1 <= h <= 11:
        h += 12
    return h if 0 <= h <= 23 else None


def check_day(day_name: str, base: Path = BASE) -> list[str]:
    problems: list[str] = []
    v1 = base / day_name
    v2 = base / (day_name + "_v2")
    pd_path = v1 / "post_data.json"
    if not pd_path.is_file():
        return [f"[{day_name}] post_data.json missing"]
    try:
        pd = json.loads(pd_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"[{day_name}] post_data.json parse error: {e}"]
    title = (pd.get("title") or "").strip()
    if not title:
        problems.append(f"[{day_name}] title missing")
    elif len(title) > TITLE_MAX:
        problems.append(f"[{day_name}] title {len(title)} chars (>{TITLE_MAX}): {title[:24]}")
    if title and (_has_emoji(title) or "#" in title or title.endswith(("?", "？"))):
        problems.append(f"[{day_name}] title has emoji/# or ends with ?")
    tags = pd.get("hashtags") or []
    if not (6 <= len(tags) <= 10):
        problems.append(f"[{day_name}] hashtags {len(tags)} not 6-10")
    etag = (pd.get("emotion_tag") or "").strip()
    if etag and not any(etag in t for t in tags):
        problems.append(f"[{day_name}] hashtags missing emotion_tag '{etag}'")
    if any("#" in t for t in tags):
        problems.append(f"[{day_name}] hashtag contains #")
    if not any("情绪树洞" in t for t in tags):
        problems.append(f"[{day_name}] hashtags missing 情绪树洞")
    body = (pd.get("content_text") or "").strip()
    if not body:
        problems.append(f"[{day_name}] content_text missing")
    elif not (400 <= len(body) <= 900):
        problems.append(f"[{day_name}] content_text {len(body)} not 400-900")
    if body and _has_emoji(body):
        problems.append(f"[{day_name}] content_text has emoji")
    if body and "？" not in body:
        problems.append(f"[{day_name}] content_text no ？")
    first_line = body.splitlines()[0].strip() if body else ""
    if etag and first_line and etag not in first_line:
        problems.append(f"[{day_name}] first line missing emotion_tag '{etag}'")
    bpt = (pd.get("best_post_time") or "").strip()
    if bpt:
        # 正则解析，别用固定切片 bpt[11:13] —— 01:00 改格式
        # （"20:30"、"晚上8点"、纯 "20"）都会静默切成错位数字，
        # 然后报出一个看似合理的「不在 20-23h」。
        h = _parse_hour(bpt)
        if h is None:
            problems.append(f"[{day_name}] best_post_time format bad: {bpt}")
        elif not (20 <= h <= 23):
            problems.append(f"[{day_name}] best_post_time {bpt} not 20-23h")
    # cross-file identity
    def _load(p: Path) -> dict:
        def _on_err(path, e):
            problems.append(f"[{day_name}] {Path(path).name} parse error: {e}")
        return load_json_tolerant(str(p), default={}, on_error=_on_err)
    v1m = _load(v1 / "manifest.json")
    v2m = _load(v2 / "manifest.json")
    # V1 manifest 的 title 有两种落法（扁平 / 嵌套 post_data.title），
    # 且嵌套里的 title 可能不是 str —— 统一交给 manifest_title 处理，
    # 崩溃路径与落法兼容都只有一份实现。
    mtitle = manifest_title(v1m)
    ptitle = plain_title(pd)
    pseries = plain_series(pd)
    v2title = plain_title(v2m)
    v2series = plain_series(v2m)
    # 一致性检查不能靠 `and` 短路：
    # 旧写法 `if mtitle and ptitle and mtitle != ptitle` 在任何一方为空时
    # 直接跳过 —— 而标题缺失本身正是最该报警的情况，且此时「一致」无从谈起。
    if mtitle and ptitle and mtitle != ptitle:
        problems.append(f"[{day_name}] V1 manifest vs post_data title mismatch: "
                        f"{mtitle!r} != {ptitle!r}")
    elif bool(mtitle) != bool(ptitle):
        problems.append(f"[{day_name}] 标题缺失不一致：V1 manifest={mtitle!r} "
                        f"post_data={ptitle!r}（一方为空，无法校验一致性）")
    if v2.is_dir():
        if ptitle and v2title and ptitle != v2title:
            problems.append(f"[{day_name}] V1 vs V2 title mismatch: "
                            f"{ptitle!r} != {v2title!r}")
        elif bool(ptitle) != bool(v2title):
            problems.append(f"[{day_name}] 标题缺失不一致：post_data={ptitle!r} "
                            f"V2 manifest={v2title!r}")
    if pseries and v2series and pseries != v2series:
        problems.append(f"[{day_name}] V1 vs V2 series mismatch: "
                        f"{pseries!r} != {v2series!r}")
    return problems

def _day_dirs(base: Path) -> list[str]:
    """列出规范的 V1 day 目录（day_YYYYMMDD_dayN）。

    严格校验目录名：只查 startswith("day_") 会让 day_broken 混进来，
    而 max(key=d[4:12]) 会切出 'broke' 这种错位字符串。
    """
    try:
        names = os.listdir(base)
    except FileNotFoundError:
        return []
    return sorted(
        (d for d in names
         if d.startswith("day_") and not d.endswith("_v2")
         and (base / d).is_dir() and parse_day_dir(d)),
        key=lambda d: (parse_day_dir(d)[0], parse_day_dir(d)[1]),
    )


def _latest_day(base: Path = BASE) -> str | None:
    days = _day_dirs(base)
    return days[-1] if days else None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="check all days")
    ap.add_argument("--day", type=str, default=None, help="specific day_YYYYMMDD_dayN")
    args = ap.parse_args()
    if args.day:
        targets = [args.day]
    elif args.all:
        targets = _day_dirs(BASE)
        if not targets:
            print(f"no day dirs under {BASE}")
            return 1
    else:
        latest = _latest_day()
        if not latest:
            print("no day dirs")
            return 1
        targets = [latest]
    all_probs: list[str] = []
    for t in targets:
        probs = check_day(t)
        if probs:
            for p in probs:
                print(f"❌ {p}")
            all_probs.extend(probs)
        else:
            print(f"✅ {t} — red lines + identity PASS")
    if all_probs:
        print(f"\n{len(all_probs)} issue(s) across {len(targets)} day(s)")
        return 1
    print(f"\nAll {len(targets)} day(s) PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
