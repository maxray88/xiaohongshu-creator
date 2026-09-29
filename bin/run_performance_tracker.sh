#!/bin/bash
# 情绪树洞 — 小红书表现追踪器
# cron: 每天 06:30（06:00 watchdog 之后）
# 从创作者中心拉取已发布笔记的表现数据，计算 save-to-like ratio

# No `set -e`: python 失败仍需走到末尾的清理与退出码传递。
# 共享逻辑见 bin/_xhs_common.sh（限定只杀流水线自己拉起的 Chrome）。
. "$(dirname "$0")/_xhs_common.sh"

echo "=========================================="
echo "📊 情绪树洞 · 小红书表现追踪"
echo "=========================================="

kill_pipeline_chrome

if ! require_python; then
  echo "Exit code: 1"
  exit 1
fi

export XHS_CHROME_HEADLESS=1

"$XHS_PY" "$HOME/02_Cronjobs_Projects/01_XHS_Daily_Post/core/xhs_performance_tracker.py" 2>&1
EXIT_CODE=$?

kill_pipeline_chrome

echo ""
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
