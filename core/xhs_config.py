"""情绪树洞项目常量。

从各模块收敛而来。改这里等于改全项目 —— 调用方 import，不重复定义。
CDP 端口 9222 是本项目唯一正确的调试端口（9224 是其他平台环境）。
"""
from __future__ import annotations

import os

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
QUALITY_SCORE_THRESHOLD = 7.0   # 5 维 LLM 评分通过线（与设计稿 COMMENT_THRESHOLD_SCORE 同值）


# ─── 数据目录 ──────────────────────────────────────
# 全项目唯一的 treehole 根目录。各模块不再各自 expanduser，
# 只 `from xhs_config import ... as BASE`（变量名保持 BASE/TARGET 不变，
# 测试 monkeypatch 的就是这些模块属性）。
DATA_BASE = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")

# ─── ComfyUI ───────────────────────────────────────
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188

# ─── Engagement（评论区运营节拍，分钟；like/save 等待为秒） ─────────
ENGAGEMENT_DELAYS = {
    "creator_prompt_min": 0, "creator_prompt_max": 5,
    "commenter_a_min": 10, "commenter_a_max": 20,
    "creator_reply_min": 15, "creator_reply_max": 30,
    "commenter_b_min": 30, "commenter_b_max": 50,
    "commenter_c_min": 60, "commenter_c_max": 90,
}
LIKE_SAVE_WAIT_MIN_SEC = 60
LIKE_SAVE_WAIT_MAX_SEC = 180
REPLY_MAX_PER_THREAD = 2
REPLY_DELAY_MIN_MIN = 15
REPLY_DELAY_MAX_MIN = 60
HOSTILE_STOP_HOURS = 48

# ─── 内容日历 ──────────────────────────────────────────
CALENDAR_MIN_POSTS = 10
CALENDAR_MAX_POSTS = 14
CALENDAR_AUTO_APPROVE_HOURS = 2


# ─── Cookie 会话 ─────────────────────────────────────────
COOKIE_EXPIRY_WARNING_HOURS = 6
