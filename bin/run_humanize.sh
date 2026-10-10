#!/bin/bash
# 情绪树洞 — 文本去 AI 味（规则版）
# cron: 每天 01:30（01:00 内容生成之后）
# 纯规则处理，不消耗 LLM quota

# No `set -e`: python 失败仍需走到末尾的清理与退出码传递。
# 共享逻辑见 bin/_xhs_common.sh（限定只杀流水线自己拉起的 Chrome）。
. "$(dirname "$0")/_xhs_common.sh"

echo "=========================================="
echo "🧬 情绪树洞 · 文本去 AI 味"
echo "=========================================="

kill_pipeline_chrome

if ! require_python; then
  echo "Exit code: 1"
  exit 1
fi

export XHS_CHROME_HEADLESS=1

run_project_python core/humanize_text.py 2>&1
EXIT_CODE=$?

kill_pipeline_chrome

echo ""
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
