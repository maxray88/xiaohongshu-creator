#!/bin/bash
# 情绪树洞 — 视频笔记 → 小红书草稿 (CDP 版)
# 替代旧的 Playwright 版本
# cron: 每天 05:00（视频合成之后）

# No `set -e`: on a failing python below, `set -e` would exit this wrapper
# BEFORE the EXIT_CODE capture and the trailing pkill — leaving a stale Chrome
# on port 9222 exactly when a problem occurred. Exit status is still propagated
# via the explicit `exit $EXIT_CODE` at the bottom.

# 本脚本**不再**执行 `pkill -f "remote-debugging-port=9222"`。
#
# 原因（2026-09-27 审计）：
# 1. 它是多余且有害的。Chrome 启动交给 xhs_video_draft.py ->
#    XiaohongshuPublisher.connect() -> ensure_chrome()，后者本就会自愈：
#    非 CDP Chrome 占着 profile 时它自己杀掉持有者并带 CDP 重启一次。
#    wrapper 先杀一遍反而抢在自愈逻辑前面，且用的是宽匹配 ——
#    `pkill -f` 匹配整条命令行，会连带杀掉**用户手动开着**的 CDP
#    调试 Chrome（2026-09-27 实测确实有一个在跑）。
# 2. 它匹配到的其实是 Chrome 的 Renderer 子进程，杀子进程未必让
#    主进程退出 —— 所以这个「清理」很可能从来没干净过。
#
# 现在只保留兜底：脚本结束后确保不留下本流水线拉起的 Chrome。
# 共享逻辑见 bin/_xhs_common.sh。
. "$(dirname "$0")/_xhs_common.sh"

echo "=========================================="
echo "📹 情绪树洞 · 视频 → 小红书草稿 (CDP)"
echo "=========================================="

# Headless — the CDP upload/draft-save flow needs no GUI window
export XHS_CHROME_HEADLESS=1

if ! require_python; then
  echo "Exit code: 1"
  exit 1
fi

# Run the video draft script — no need to cd, xhs_video_draft.py uses absolute imports
"$XHS_PY" "$HOME/02_Cronjobs_Projects/01_XHS_Daily_Post/core/xhs_video_draft.py" 2>&1
EXIT_CODE=$?

# Cleanup（仅本流水线的 Chrome）
sleep 1
kill_pipeline_chrome

echo ""
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
