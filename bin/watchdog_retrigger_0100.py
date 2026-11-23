#!/usr/bin/env python3
"""01:00 生成重触发看门狗。

配合 hermes no_agent cron 使用，01:20 运行：
  - 当天 V1 内容目录存在 → 无 stdout、exit 0 → 静默（不投递）
  - 当天 V1 缺失 → 重触发 250be2028330，输出中文通知、exit 0/1
"""

import glob
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from xhs_config import DATA_BASE

BASE = DATA_BASE
HERMES = "/Users/maochundong/.local/bin/hermes"
JOB_ID = "250be2028330"
TIMEOUT = 1500


def find_today_v1(base, today):
    """返回当天第一个非 _v2 的 day_<today>_day* 目录，无则 None。"""
    for entry in sorted(glob.glob(os.path.join(base, "day_%s_day*" % today))):
        if entry.endswith("_v2"):
            continue
        if os.path.isdir(entry):
            return entry
    return None


def _real_runner(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def main(base=BASE, today=None, runner=None):
    today = today or datetime.now().strftime("%Y%m%d")
    if find_today_v1(base, today):
        return 0
    runner = runner or _real_runner
    rc, out = runner([HERMES, "cron", "run", JOB_ID])
    print("⚠️ 01:00 生成缺失（%s），已重触发 %s" % (today, JOB_ID))
    if out:
        print(out)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
