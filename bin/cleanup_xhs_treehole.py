#!/usr/bin/env python3
"""
情绪树洞素材清理脚本
删除 ~/.hermes/data/xhs_treehole 中超过 7 天的 day_* 目录。
使用目录名中的日期（day_YYYYMMDD）判断，不依赖 mtime。

退出码：0 = 清理完成（含「什么都没删」）；1 = 有删除失败。
这一点很重要 —— 06:00 自检把「清理旧素材：ok」当成可信信号，
而旧实现即使 rmtree 全部失败也 exit 0，等于报假 ok。
"""
import os, shutil, sys
from pathlib import Path
from datetime import datetime, timedelta

TARGET = os.path.expanduser("~/.hermes/data/xhs_treehole")
NOW = datetime.now()
# cutoff 取「7 天前的当天零点」，不是 NOW-7d。
# NOW-7d 带着当前时分秒：05:30 跑时，7 天前零点比 cutoff 老 5.5 小时，
# 于是「正好 7 天」的目录会被删 —— 名义保留 7 天，实际只留 6.77 天。
CUTOFF_DATE = (NOW - timedelta(days=7)).date()

today_str = NOW.strftime("%Y%m%d")
yesterday_str = (NOW - timedelta(days=1)).strftime("%Y%m%d")

KEPT = 0
DELETED = 0
ERRORS = 0

print(f"Cleanup: {TARGET}")
print(f"Cutoff: {CUTOFF_DATE} (delete dirs strictly older than this date)")
print(f"Protected: {today_str}, {yesterday_str}")
print()

if not os.path.isdir(TARGET):
    print(f"Directory not found: {TARGET}")
    print("Nothing to clean.")
    sys.exit(0)


def _rmtree(path: Path) -> None:
    """删一个目录，连带它的 _v2 兄弟目录。

    旧实现把 V1 与 _v2 当两个独立条目分别处理：V1 删成功、_v2 因权限
    失败时会留孤儿 day_XXX_v2/。而 theme_rotation.recent_schemes 是按
    目录枚举的，孤儿 _v2 会被算进「最近 3 天」窗口，污染主题轮换判定。
    成对处理杜绝这种残留。
    """
    global DELETED, ERRORS
    sibling = path.parent / (path.name + "_v2")
    for target in ([path] if not sibling.exists() else [path, sibling]):
        try:
            if target.exists():
                shutil.rmtree(str(target))
                print(f"  DELETED:           {target.name}")
                DELETED += 1
        except Exception as e:
            print(f"  ERROR: {target.name}: {e}")
            ERRORS += 1


for entry in sorted(Path(TARGET).iterdir()):
    if not entry.is_dir() or not entry.name.startswith("day_"):
        continue
    if entry.name == "pipeline_test":
        continue
    if entry.name.endswith("_v2"):
        # 随 V1 成对删除，不在这里独立判定（否则会重复计数/重复删）
        continue

    parts = entry.name.split("_")
    if len(parts) < 2:
        continue
    dir_date_str = parts[1]

    if dir_date_str in (today_str, yesterday_str):
        print(f"  KEEP (recent):    {entry.name}")
        KEPT += 1
        continue

    try:
        dir_date = datetime.strptime(dir_date_str, "%Y%m%d").date()
    except ValueError:
        print(f"  KEEP (bad date):  {entry.name}")
        KEPT += 1
        continue

    if dir_date < CUTOFF_DATE:
        age = (NOW.date() - dir_date).days
        _rmtree(entry)
        if not entry.exists():
            print(f"  (was {age}d old)")
    else:
        age = (NOW.date() - dir_date).days
        print(f"  KEEP ({age}d):     {entry.name}")
        KEPT += 1

# 孤儿 _v2 扫尾：V1 已被删除（人工清理/历史事故）而 _v2 残留。
# 它不随 V1 成对删除，所以必须单独扫 —— 而孤儿恰好会污染
# theme_rotation.recent_schemes 的「最近 3 天」窗口，正是成对删除想避免的事。
orphans = []
for entry in sorted(Path(TARGET).iterdir()):
    if not entry.is_dir() or not entry.name.startswith("day_"):
        continue
    if not entry.name.endswith("_v2"):
        continue
    v1_sibling = Path(TARGET) / entry.name[:-3]
    if v1_sibling.exists():
        continue  # 有 V1 兄弟，正常路径会成对处理
    parts = entry.name.split("_")
    if len(parts) < 2:
        continue
    try:
        dir_date = datetime.strptime(parts[1], "%Y%m%d").date()
    except ValueError:
        continue
    if dir_date < CUTOFF_DATE:
        age = (NOW.date() - dir_date).days
        _rmtree(entry)  # 孤儿自己没有 _v2 兄弟，_rmtree 只会删它自己
        if not entry.exists():
            orphans.append(entry.name)
            print(f"  (orphan, was {age}d old)")
if orphans:
    print(f"  ⚠️ 清理了 {len(orphans)} 个孤儿 _v2 目录：{orphans}")

# Sweep leftover V2 generator scripts written to the data-dir top level
# (the V2 prompt used to put generate_day{N}_v2.py there; the day_* purge
# above never reached them). They are regenerable scratch run at 02:00 gen
# time, so deleting at 05:30 is always safe.
for entry in Path(TARGET).glob("generate_day*.py"):
    try:
        entry.unlink()
        print(f"  DELETED (gen script):  {entry.name}")
        DELETED += 1
    except Exception as e:
        print(f"  ERROR: {entry.name}: {e}")
        ERRORS += 1

# Sweep root-level cruft that the day_* purge can't reach and nothing active
# references: a dead day-stub (current_day.txt, no writers since migration),
# the pyc cache of scripts that once lived here (canonical copies now live in
# the project tree), and macOS Finder artifacts. The empty legacy video/ dir
# is a leftover inbox — real videos go into day_..._v2/video/ now. All are
# safe to delete at 05:30; deleting keeps the root list the watchdog lists
# every morning readable.
for name in ("current_day.txt", "__pycache__", ".DS_Store"):
    target = Path(TARGET) / name
    try:
        if target.is_dir():
            shutil.rmtree(str(target))
            print(f"  DELETED (cruft):  {name}")
            DELETED += 1
        elif target.exists():
            target.unlink()
            print(f"  DELETED (cruft):  {name}")
            DELETED += 1
    except Exception as e:
        print(f"  ERROR: {name}: {e}")
        ERRORS += 1

empty_video_dir = Path(TARGET) / "video"
if empty_video_dir.is_dir() and not any(empty_video_dir.iterdir()):
    try:
        empty_video_dir.rmdir()
        print("  DELETED (empty dir):  video")
        DELETED += 1
    except Exception as e:
        print(f"  ERROR: video: {e}")
        ERRORS += 1

print(f"\nSummary: {DELETED} deleted, {KEPT} kept, {ERRORS} errors")
# 有删除失败必须非零退出：06:00 自检把本脚本的 ok 当可信信号，
# exit 0 会让「磁盘在涨、脚本报成功」长期无人察觉。
sys.exit(1 if ERRORS else 0)
