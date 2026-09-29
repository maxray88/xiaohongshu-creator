#!/usr/bin/env python3
"""V1 manifest 标题读取 —— 单一实现，三个检查器共用。

## 背景

01:00 的 LLM cron 生成 V1 manifest.json 时，标题有两种落法（两种都真实产出过）：

    扁平：  {"title": "今天，试着说不"}
    嵌套：  {"post_data": {"title": "今天，试着说不"}}

2026-09-27 day82 出了分叉：post_data.json 换成新版内容后 V1 manifest 也重写了，
但标题落在嵌套的 post_data 里，而三个检查器都只读顶层 title →
mtitle 为空 → `if mtitle and ptitle and mtitle != ptitle` 整条一致性检查静默跳过。
**恰好在最该报警的时候失声。**

## 为什么是独立模块而不是各写一份

同一段取值逻辑曾复制在三个文件里（core/content_regression.py、
bin/check_xhs_pipeline.py、bin/check_content_quality.py）。补两处漏一处已经发生过
（2026-09-27 审出 MED-2）。三处拷贝 + 手工同步 = 下次再漏。
所以这里给出唯一实现，各处 import。

## 崩溃路径（这里是本次修复的另一半）

`(v1m.get("post_data") or {}).get("title")` 看着对，但 `or {}` 只兜 falsy 值：
post_data 是**非空字符串/列表**时 `.get` 直接 AttributeError。
即便 post_data 是 dict，里面的 title 若非 str，`.strip()` 同样 AttributeError。
两种情况都会让 06:00 自检**崩栈**而不是报出「标题缺失」—— 最坏情况是
连别的检查项都跑不完。LLM 一般不会这么写，但自检必须假设它会。
"""
from __future__ import annotations

from typing import Any, Mapping


def _as_text(v: Any) -> str:
    """只有 str 才算文本；其余（None/数字/列表/dict）一律当空。

    不用 `str(v)` 兜底：把 123 转成 "123" 会让「标题是数字」看起来像
    一个合法的非空标题，从而跳过一致性检查 —— 正是要防的那类假绿。
    """
    return v.strip() if isinstance(v, str) else ""


def manifest_title(v1m: Any) -> str:
    """从 V1 manifest 读标题，兼容扁平与嵌套两种落法。

    嵌套优先还是扁平优先？取**扁平**优先：顶层是更早、更权威的位置，
    嵌套是 2026-09-27 起才出现的。两处都存在时以扁平为准。
    """
    if not isinstance(v1m, Mapping):
        return ""
    flat = _as_text(v1m.get("title"))
    if flat:
        return flat
    nested = v1m.get("post_data")
    if not isinstance(nested, Mapping):
        return ""
    return _as_text(nested.get("title"))


def plain_title(m: Any) -> str:
    """从 post_data / V2 manifest 这类**单层** JSON 读标题。

    与 manifest_title 分开是因为语义不同：这里不做双落法，
    少一层猜测就少一处能出错的地方。
    """
    if not isinstance(m, Mapping):
        return ""
    return _as_text(m.get("title"))


def plain_series(m: Any) -> str:
    """读 series（系列名）。同样只认 str，避免数字系列名造成假绿。"""
    if not isinstance(m, Mapping):
        return ""
    return _as_text(m.get("series"))


if __name__ == "__main__":
    import json
    import sys

    for raw in sys.argv[1:]:
        print(f"{raw!r} -> {manifest_title(json.loads(raw))!r}")
