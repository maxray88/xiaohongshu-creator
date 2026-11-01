"""原子写 JSON。

直接覆盖写若在中途被 cron 杀掉，目标文件会变成截断的半截 JSON ——
而 manifest.json / post_data.json / published_content.json
分别是 02:15/04:00/06:00 的共同输入，损坏即连锁失败。
"""
from __future__ import annotations

import json
import os


def atomic_write_json(path: str, data: dict | list) -> None:
    """tmp + fsync + rename 原子写。"""
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
