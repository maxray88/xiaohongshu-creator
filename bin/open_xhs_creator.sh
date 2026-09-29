#!/bin/bash
# 小红书创作平台 — 带 CDP 端口(9222) 的有头 Chrome 快捷启动
# 用途：登录/排查时的人工窗口；同时可被 cdp_publish 的 ensure_chrome() 直接复用
#       （同 profile + 9222 → connect() 会采纳这个实例，无需再起一个）。
# 默认打开「发布笔记」页（该路由能可靠确认登录态，home 路由会误跳 /login）。
# 可用第一个参数覆盖 URL。
# 行为：若 9222 已有 Chrome（通常是 cron 留下的 headless），先收掉再以有头模式
#       重启——保证用户始终得到可见窗口；随后把 URL 交给该实例开新标签页。
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL="${1:-https://creator.xiaohongshu.com/publish/publish?source=official}"
VENV_PY="$HOME/.hermes/xhs_skills/venv/bin/python3"   # 依赖仍在项目外

# CDP 模块走项目内 vendor/xhs/（2026-09-27 vendored）
"$VENV_PY" - "$PROJ_ROOT" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/vendor/xhs")
from chrome_launcher import is_port_open, kill_chrome, launch_chrome, CDP_PORT

if is_port_open(CDP_PORT):
    print("[shortcut] 9222 已有 Chrome —— 以有头模式重启，保证可见窗口")
    kill_chrome(CDP_PORT)
launch_chrome(port=CDP_PORT, headless=False)
PY
sleep 1

# 导航：以同样的 profile/端口再调一次 Chrome 二进制并把 URL 作为参数。实例已在
# 运行时，Chrome 会通过单例握手把 URL 转发给已有进程并开新标签页，不会开第二个窗口。
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Google/Chrome/XiaohongshuProfiles/default" \
  "$URL" &

sleep 2
echo "✅ 已启动有头 Chrome（port 9222，XHS profile）→ $URL"