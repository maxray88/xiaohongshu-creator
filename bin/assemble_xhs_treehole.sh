#!/bin/bash
# 情绪树洞视频合成 — 由 cron job 触发 (04:00)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:$PATH"
set -e
source "$(dirname "${BASH_SOURCE[0]}")/_xhs_common.sh"
require_python || exit 1
cd "$HOME/.hermes/data/xhs_treehole" || exit 1
run_project_python core/_cron_assemble.py
