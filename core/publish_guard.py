#!/usr/bin/env python3
"""发布前的最后一道红线闸 —— 03:00 图文 / 05:00 视频共用。

## 为什么在发布脚本里再校验一次

02:15 的内容质量门已经检查「标题 ≤18 字」。但它只覆盖**当天 02:15
那一次运行**：02:15 失败、被忽略、或事后人工单独重跑 03:00/05:00 时，
超长标题会一路走到 `_fill_title()`。而小红书平台对超长标题是
**静默截断** —— 本地文件还是 24 字，06:00 自检照样 PASS，
用户看到的却是一条标题被砍半的笔记，且没有任何报错。

这类「平台静默截断 + 本地检查假绿」的组合是内容号最贵的 bug：
它不会失败，只会安静地持续产出错误内容。

所以规则是：**任何要写进小红书页面的内容，出口前自己再确认一次**，
不依赖上游是否会跑。

## 为什么是共享模块而不是各自写

这是本项目第三次因为「同一段红线逻辑复制多处、补两处漏一处」而返工
（2026-09-27 的 V1 manifest 标题双落法，MED-2）。规则定义只有一份，
调用方 import，不重复判断。
"""
from __future__ import annotations

TITLE_MAX = 18          # 小红书标题上限 20，留 2 字余量
CONTENT_MIN = 400
CONTENT_MAX = 900


def check_publishable(title: str, content: str = "") -> list[str]:
    """返回阻塞发布的问题列表；空列表 = 可以发。"""
    problems: list[str] = []

    if not title or not title.strip():
        problems.append("标题为空")
    else:
        t = title.strip()
        if len(t) > TITLE_MAX:
            problems.append(
                f"标题 {len(t)} 字，超出 {TITLE_MAX} 字上限：{t[:24]}"
                f"（平台会静默截断，本地检查却会放行）"
            )
        if any(ch in t for ch in "#"):
            problems.append("标题含「#」")
        if t.endswith(("?", "？")):
            problems.append("标题以问号结尾")

    if content:
        n = len(content)
        if n < CONTENT_MIN:
            problems.append(f"正文仅 {n} 字，少于 {CONTENT_MIN} 字下限")
        elif n > CONTENT_MAX:
            problems.append(f"正文 {n} 字，超出 {CONTENT_MAX} 字上限")

    return problems


def require_publishable(title: str, content: str = "") -> None:
    """不满足红线就抛错，让 cron 以非零退出码告警，而不是发出去。"""
    problems = check_publishable(title, content)
    if not problems:
        return
    detail = "\n".join(f"   - {p}" for p in problems)
    raise ValueError(
        f"❌ 内容红线未通过，已阻止存草稿（{len(problems)} 项）:\n{detail}\n"
        f"   → 02:15 质量门本应拦住；到这里说明它没跑或已失效。\n"
        f"   → 修 post_data.json 后重跑，或手动重跑 02:15。"
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <title> [content]")
        raise SystemExit(2)
    probs = check_publishable(sys.argv[1],
                              sys.argv[2] if len(sys.argv) > 2 else "")
    if probs:
        for p in probs:
            print(f"❌ {p}")
        raise SystemExit(1)
    print("✅ 通过")
