#!/usr/bin/env python3
"""cleanup_xhs_treehole 回归测试。

修掉的两个问题（M8/M9，2026-09-27 审计）：
- M8：全程 exit 0，即使 rmtree 全部失败 → 06:00 的「清理：ok」是假 ok
- M9：CUTOFF = NOW - 7d 带时分秒，05:30 跑时「正好 7 天」的目录
  比 cutoff 老 5.5 小时会被误删，名义保留 7 天实际只留 6.77 天
- 附带：V1 与 _v2 成对删除，避免孤儿 _v2 污染 theme_rotation 的主题窗口

全部在 tempfile 沙盒里跑，不碰真实数据目录。
运行：python3 -m pytest tests/ -q（项目根目录）
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRIPT = os.path.join(ROOT, "bin", "cleanup_xhs_treehole.py")


def _run_in(target_dir, runner_dir=None):
    """把脚本复制到沙盒并把 TARGET 指向沙盒，跑它。

    runner 必须落在已存在的目录里（测试「目标目录不存在」时尤其重要），
    所以默认放在 target_dir 的父目录。
    """
    src = open(SCRIPT, encoding="utf-8").read()
    needle = "TARGET = DATA_BASE"
    assert needle in src, "脚本里找不到 TARGET 定义，测试需同步"
    src = src.replace(needle, f"TARGET = {target_dir!r}")
    # 沙盒拷贝没有 core/ 可 import：TARGET 已被上面替换为沙盒字面量，
    # 该 import 在拷贝里已无用，去掉（仅改拷贝，不改仓库源文件）。
    src = src.replace("from xhs_config import DATA_BASE", "")
    base = runner_dir or os.path.dirname(os.path.abspath(target_dir.rstrip("/")))
    os.makedirs(base, exist_ok=True)
    runner = os.path.join(base, "_cleanup_under_test.py")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(src)
    return subprocess.run([sys.executable, runner], capture_output=True, text=True)


def _mk_day(base, day_off, with_v2=True, day_num=None):
    ds = (datetime.now() - timedelta(days=day_off)).strftime("%Y%m%d")
    n = day_num if day_num is not None else day_off
    name = f"day_{ds}_day{n}"
    p = os.path.join(base, name)
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "marker"), "w") as f:
        f.write("x")
    if with_v2:
        p2 = p + "_v2"
        os.makedirs(p2, exist_ok=True)
        with open(os.path.join(p2, "marker"), "w") as f:
            f.write("y")
    return name


def test_exactly_seven_days_old_is_kept(tmp_path):
    """M9 核心回归：正好 7 天的目录必须保留。"""
    d = str(tmp_path)
    keep7 = _mk_day(d, 7)
    old8 = _mk_day(d, 8)
    r = _run_in(d)
    after = set(os.listdir(d))
    assert keep7 in after, f"正好 7 天被误删了（cutoff 带了时分秒）\n{r.stdout}"
    assert old8 not in after, "8 天的目录应被删除"


def test_today_and_yesterday_always_kept(tmp_path):
    d = str(tmp_path)
    t = _mk_day(d, 0)
    y = _mk_day(d, 1)
    r = _run_in(d)
    after = set(os.listdir(d))
    assert t in after and y in after, "今天/昨天必须无条件保留"
    assert r.returncode == 0


def test_v2_sibling_deleted_together(tmp_path):
    """V1 删了必须连 _v2 一起删，否则孤儿 _v2 污染主题轮换窗口。"""
    d = str(tmp_path)
    old = _mk_day(d, 10)
    r = _run_in(d)
    after = set(os.listdir(d))
    assert old not in after
    assert old + "_v2" not in after, "留了孤儿 _v2 目录"
    assert r.returncode == 0


def test_exit_nonzero_on_delete_failure(tmp_path):
    """M8 核心回归：删除失败必须非零退出，否则 06:00 报假 ok。"""
    d = str(tmp_path)
    _mk_day(d, 10)
    # 用一个 wrapper 注入 rmtree 失败
    src = open(SCRIPT, encoding="utf-8").read()
    needle = "TARGET = DATA_BASE"
    assert needle in src, "脚本里找不到 TARGET 定义，测试需同步"
    src = src.replace(needle, f"TARGET = {d!r}")
    src = src.replace("from xhs_config import DATA_BASE", "")
    src = src.replace(
        "import os, shutil, sys",
        "import os, shutil, sys\n"
        "def _boom(*a, **k):\n"
        "    raise PermissionError('模拟权限不足')\n"
        "shutil.rmtree = _boom",
    )
    runner = os.path.join(d, "_cleanup_fail.py")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(src)
    r = subprocess.run([sys.executable, runner], capture_output=True, text=True)
    assert r.returncode == 1, f"删除失败却 exit {r.returncode}，06:00 会报假 ok"
    assert "errors" in r.stdout


def test_malformed_dir_name_is_kept(tmp_path):
    d = str(tmp_path)
    os.makedirs(os.path.join(d, "day_notadate"), exist_ok=True)
    r = _run_in(d)
    assert "day_notadate" in os.listdir(d)
    assert r.returncode == 0


def test_orphan_v2_swept(tmp_path):
    """V1 已删、只剩 _v2 的孤儿目录必须被清掉。

    它不随 V1 成对删除，而孤儿恰好会污染 theme_rotation 的主题窗口 ——
    正是成对删除想避免的事，所以必须单独扫。
    """
    d = str(tmp_path)
    old = (datetime.now() - timedelta(days=20)).strftime("%Y%m%d")
    orphan = f"day_{old}_day7_v2"
    os.makedirs(os.path.join(d, orphan), exist_ok=True)
    r = _run_in(d)
    assert orphan not in os.listdir(d), "孤儿 _v2 永久残留"
    assert r.returncode == 0


def test_orphan_v2_recent_is_kept(tmp_path):
    d = str(tmp_path)
    recent = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    orphan = f"day_{recent}_day7_v2"
    os.makedirs(os.path.join(d, orphan), exist_ok=True)
    r = _run_in(d)
    assert orphan in os.listdir(d), "近期的孤儿不该被删"
    assert r.returncode == 0


def test_orphan_with_v1_sibling_not_double_counted(tmp_path):
    """有 V1 兄弟的 _v2 由成对路径处理，不该被孤儿扫重复计数。

    用「独立成行的出现次数」计数 —— 直接 count 子串会误判，
    因为 day_X_day10 是 day_X_day10_v2 的前缀。
    """
    d = str(tmp_path)
    name = _mk_day(d, 10)
    r = _run_in(d)
    lines = [ln.strip() for ln in r.stdout.splitlines()]
    deleted = [ln for ln in lines if ln.startswith("DELETED")]
    # V1 与 _v2 各删一次，正好两行
    assert len(deleted) == 2, f"应恰好删除 2 个目录，实际 {deleted}"
    assert sum(1 for ln in deleted if ln.endswith(name)) == 1
    assert sum(1 for ln in deleted if ln.endswith(name + "_v2")) == 1
    assert r.returncode == 0
    assert "孤儿" not in r.stdout, "有 V1 兄弟却走了孤儿扫路径"


def test_missing_target_dir_is_clean_exit(tmp_path):
    d = os.path.join(str(tmp_path), "does_not_exist")
    r = _run_in(d)
    assert r.returncode == 0
