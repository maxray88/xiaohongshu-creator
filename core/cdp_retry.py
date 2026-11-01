#!/usr/bin/env python3
"""CDP 调用重试（3× backoff）。

tracker 的翻页循环是定制的（点击 → 轮询表格变化 → 确认翻页），语义不可
泛化，故不受本 helper 约束；本 helper 覆盖无状态单次调用（如截图）。
"""
import time
from collections.abc import Callable
from typing import Any


def run_with_retries(fn: Callable[[], Any], attempts: int = 3,
                     backoff: float = 2.0, label: str = "CDP 调用") -> Any:
    """执行 fn()，失败则 backoff 秒后重试，最多 attempts 次。

    最後一次失败则原样抛出最后一个异常（调用方决定是降级还是 loud fail）。
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — 重试helper必须兜底所有调用方异常
            last = e
            if i < attempts:
                print(f"  ⚠ {label} 失败（第 {i}/{attempts} 次):"
                      f"{type(e).__name__}: {e}，{backoff}s 后重试…")
                time.sleep(backoff)
    raise last
