#!/bin/bash
# 情绪树洞 — 试水评论晨间播种（cron 零参数入口）
# feed_id/xsec_token 不在此文件中，来自本地 engagement_job.json（chmod 600，operator 创建）。

# No `set -e`: python 失败仍需走到末尾的退出码传递。
# 共享逻辑见 bin/_xhs_common.sh。
. "$(dirname "$0")/_xhs_common.sh"

echo "=========================================="
echo "🌱 情绪树洞 · 试水评论播种（晨间）"
echo "=========================================="

# NOTE: 有意不调 kill_pipeline_chrome。查过 _xhs_common.sh：它只按
# --user-data-dir=$XHS_CHROME_PROFILE + --remote-debugging-port=$XHS_CHROME_PORT
# （默认 9222）匹配流水线 Chrome；本 seeder 只连测试号 CDP 9229，
# 且经 publisher connect/disconnect 管理自己的 tab 生命周期。
# 在此调用 kill 既打不到 9229（无用），也无需清理。

if ! require_python; then
  echo "Exit code: 1"
  exit 1
fi

run_project_python bin/seed_test_comments.py --pool "$HOME/.hermes/data/xhs_treehole/engagement_pool.json" --live --max-comments 1 2>&1
EXIT_CODE=$?

echo ""
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
