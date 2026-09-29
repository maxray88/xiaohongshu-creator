#!/bin/bash
# 情绪树洞视频合成 — 由 cron job 触发 (04:00)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:$PATH"
PROJ="$HOME/02_Cronjobs_Projects/01_XHS_Daily_Post"
cd "$HOME/.hermes/data/xhs_treehole" || exit 1; python3 "$PROJ/core/_cron_assemble.py"
