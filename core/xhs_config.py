"""情绪树洞项目常量。

从各模块收敛而来。改这里等于改全项目 —— 调用方 import，不重复定义。
CDP 端口 9222 是本项目唯一正确的调试端口（9224 是其他平台环境）。
"""
from __future__ import annotations

# ─── CDP ───────────────────────────────────────────
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

# ─── URL ───────────────────────────────────────────
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
CREATOR_HOST_FRAGMENT = "creator.xiaohongshu.com"     # 用于 href 子串判断
STATISTICS_URL = "https://creator.xiaohongshu.com/statistics/data-analysis"

# ─── 内容红线阈值 ───────────────────────────────────
# publish_guard.py 是这些规则的唯一定义处（见该文件 docstring：
# 本项目第三次因「同一段红线逻辑复制多处」返工）。
TITLE_MAX = 18          # 小红书标题上限 20，留 2 字余量
CONTENT_MIN = 400
CONTENT_MAX = 900
