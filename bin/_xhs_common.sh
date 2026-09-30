#!/bin/bash
# 情绪树洞 — 共用 wrapper 前置/后置逻辑
#
# ── 为什么不再用 pkill -f "remote-debugging-port=9222" ──────────────
#
# 原先每个 wrapper 各写一份，有三个问题：
#
# 1. 匹配太宽。`pkill -f` 匹配整条命令行，会连带杀掉**用户手动开着**
#    的 CDP 调试 Chrome（2026-09-27 实测确实有一个在跑）。
# 2. 只匹配到 Renderer 子进程。Chrome 的辅助进程也带同样的命令行，
#    杀子进程主进程未必退出 —— 这个「清理」很可能从来没干净过。
# 3. 在 publish_xhs_video.sh 里它多余且有害：Chrome 启动本就交给
#    chrome_launcher.ensure_chrome()，后者会自愈（profile 被非 CDP
#    Chrome 占用时自己终止持有者并带 CDP 重启）。wrapper 先杀一遍
#    反而抢在自愈逻辑前面。
#
# 下面的实现对齐 chrome_launcher._profile_holders_without_cdp 的做法：
# `ps -ax -o pid=,command=` 逐行解析，只保留**主进程**（排除 Helper），
# 且要求命令行同时含完整的 --user-data-dir 与 --remote-debugging-port。

XHS_CHROME_PORT="${XHS_CHROME_PORT:-9222}"
# 流水线专用 profile —— 必须与 chrome_launcher.get_user_data_dir() 实际
# 使用的路径一致，否则 kill_pipeline_chrome() 匹配不到任何进程（静默失效）。
#
# 2026-09-30 修正：这个值原先写成 XiaohongshuProfiles/default（复数 + /default，
# 5.5G），但真正启动 Chrome 的是 vendor/xhs/chrome_launcher.py，它在没有
# account_manager 时回退到硬编码的 PROFILE_DIR_NAME = "XiaohongshuProfile"
# （**单数、无 /default**，147M）。两者不是同一个目录，于是：
#   · Chrome 照常用 147M 那个（专用小红书 profile，只有 4 个 xiaohongshu 域名）
#   · 本函数的进程匹配永远落空 → 清理形同虚设 → 标签页逐次累积
# 实测 2026-09-30 跑出 10 个 creator.xiaohongshu.com 登录页标签就是这么来的。
#
# 5.5G 那个 XiaohongshuProfiles/default 是多平台混杂 profile（抖音 23 /
# Google 20 / TikTok 20 / YouTube 17 条 cookie），**不是**本流水线该用的。
# 若将来要改用环境变量注入以覆盖公共库硬编码，5 个 cron 直调的 .py 入口
# （check_xhs_login / check_xhs_pipeline / cleanup_xhs_treehole 等）也得
# 同步注入，shim 只做转发不设 env。
XHS_CHROME_PROFILE="${XHS_CHROME_PROFILE:-$HOME/Google/Chrome/XiaohongshuProfile}"

# 下面列出**本流水线自己拉起的** Chrome 主进程；不碰其他 profile。
#
# 注意保证的边界：这里区分的是「profile」不是「谁启动的」。若用户用
# open_xhs_creator.sh 打开的窗口恰好也是这个 profile + 9222，同样会被
# 终止 —— 这是有意的：cron 必须独占该端口，那个 opener 脚本本身也这么做。
# 但**其他 profile 的 Chrome 一定不受影响**（实测 CDP 9224 / NewAccount
# 均零匹配）。
kill_pipeline_chrome() {
  local pids
  pids=$(ps -ax -o pid=,command= 2>/dev/null \
    | awk -v prof="--user-data-dir=$XHS_CHROME_PROFILE" \
          -v cdp="--remote-debugging-port=$XHS_CHROME_PORT" '
        /Google Chrome/ && !/Google Chrome Helper/ \
        && index($0, prof) && index($0, cdp) { print $1 }')
  [ -z "$pids" ] && return 0
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  # 给 Chrome 一点时间写盘并退出，避免下次启动撞上 profile 锁
  local waited=0
  while [ "$waited" -lt 10 ]; do
    pids=$(ps -ax -o pid=,command= 2>/dev/null \
      | awk -v prof="--user-data-dir=$XHS_CHROME_PROFILE" \
            -v cdp="--remote-debugging-port=$XHS_CHROME_PORT" '
          /Google Chrome/ && !/Google Chrome Helper/ \
          && index($0, prof) && index($0, cdp) { print $1 }')
    [ -z "$pids" ] && return 0
    sleep 1
    waited=$((waited + 1))
  done
  # 优雅退出没成功才升级为 SIGKILL —— 仍然只针对本流水线的 Chrome
  # shellcheck disable=SC2086
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null
  return 0
}

# 列出（不杀）流水线 Chrome 的 PID，供排查用
list_pipeline_chrome() {
  ps -ax -o pid=,command= 2>/dev/null \
    | awk -v prof="--user-data-dir=$XHS_CHROME_PROFILE" \
          -v cdp="--remote-debugging-port=$XHS_CHROME_PORT" '
      /Google Chrome/ && !/Google Chrome Helper/ \
      && index($0, prof) && index($0, cdp) { print $1, $2, $3 }'
}

# 校验 venv 解释器存在。原先硬编码路径，venv 缺失时 shell 找不到
# 解释器，错误信息与真实原因无关，排查困难。
XHS_PY="${XHS_PY:-$HOME/.hermes/xhs_skills/venv/bin/python3}"
require_python() {
  if [ ! -x "$XHS_PY" ]; then
    echo "❌ venv 解释器不存在或不可执行: $XHS_PY"
    echo "   → XHS 依赖装在专用 venv 里（edge-tts / playwright），用系统 python 会缺"
    echo "   → 修复: python3 -m venv ~/.hermes/xhs_skills/venv 后安装 requirements.txt"
    return 1
  fi
  return 0
}
