#!/bin/bash
# 情绪树洞 — 图文笔记 → 小红书草稿 (CDP 版)
# cron: 每天 03:00（V1 生成之后）
# 纯脚本任务，不消耗 LLM quota（避开 weekly 429）

# No `set -e`: same rationale as publish_xhs_video.sh — failing python must
# still reach the trailing cleanup + exit-code propagation.
# 共享逻辑见 bin/_xhs_common.sh（限定只杀流水线自己拉起的 Chrome）。
. "$(dirname "$0")/_xhs_common.sh"

echo "=========================================="
echo "🖼️  情绪树洞 · 图文 → 小红书草稿 (CDP)"
echo "=========================================="

kill_pipeline_chrome

if ! require_python; then
  echo "Exit code: 1"
  exit 1
fi

export XHS_CHROME_HEADLESS=1

"$XHS_PY" "$HOME/02_Cronjobs_Projects/01_XHS_Daily_Post/core/xhs_image_draft.py" 2>&1
EXIT_CODE=$?

kill_pipeline_chrome

echo ""
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
