#!/bin/bash
# 情绪树洞 — HTML 卡片 → JPG 截图渲染
# 在 V2 生成之后运行，确保 04:00 合成时有图片可用
# cron: 每天 02:30（02:00 V2 生成之后）

# No `set -e`: on a failing python/render below, `set -e` would exit this wrapper
# BEFORE the EXIT_CODE capture and the trailing pkill — leaving a stale Chrome
# on port 9222 exactly when a problem occurred. Every exit path is handled
# explicitly (graceful skips + `exit $EXIT_CODE`), so no early abort is needed.

BASE="$HOME/.hermes/data/xhs_treehole"
# 解释器（venv 仍留在项目外，是 32MB 二进制依赖，不进 Git）
VENV="$HOME/.hermes/xhs_skills/venv/bin/activate"
# 项目根目录 —— 推导而非硬编码，换机器/改路径不会指错地方
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$PROJ_ROOT/core/render_xhs_cards.py"

# 共享逻辑（kill_pipeline_chrome / require_python）必须在**开头**引入，
# 否则脚本前半段的内联 python 会用系统 python3、后半段用 venv ——
# 同一脚本里两套解释器，venv 缺失时报错位置会误导排查。
. "$(dirname "$0")/_xhs_common.sh"
if ! require_python; then
  echo "Exit code: 1"
  exit 1
fi

echo "=========================================="
echo "🖼️  情绪树洞 · HTML→JPG 渲染"
echo "=========================================="

# 找最新的 V2 目录
V2_DIR=$(ls -d ${BASE}/day_*_v2 2>/dev/null | sort -r | head -1)
if [ -z "$V2_DIR" ]; then
    echo "❌ No V2 directories found"
    exit 1
fi

echo "V2: $(basename $V2_DIR)"

# 只处理「今天」的 V2。01:00/02:00 生成历史上有 ~13% 的天数失败，
# 这时最新 _v2 会落到昨天——重渲染昨天卡片纯属浪费（assemble 幂等、
# 05:00 发布与 03:00 填表已有同样守卫），未触 Chrome 直接跳过；
# 06:00 watchdog 仍会以「今天没有生成新内容」告警，不会掩盖失败。
TODAY=$(date +%Y%m%d)
if [[ "$(basename "$V2_DIR")" != *"_${TODAY}_"* ]]; then
    echo "skipped: latest V2 is $(basename "$V2_DIR"), not today ${TODAY} - 跳过渲染避免无谓 Chrome"
    exit 0
fi

# 检查 manifest
MANIFEST="$V2_DIR/manifest.json"
if [ ! -f "$MANIFEST" ]; then
    echo "❌ No manifest.json"
    exit 1
fi

# 检查是否已渲染
IMAGES_RENDERED=$(MANIFEST="$MANIFEST" "$XHS_PY" -c "import json,os; print(json.load(open(os.environ['MANIFEST'])).get('images_rendered', False))" 2>/dev/null)
JPG_COUNT=$(ls "$V2_DIR"/images/card_v2_*.jpg 2>/dev/null | wc -l | tr -d ' ')
# images_rendered flag is only trusted when it matches reality (≥6 JPGs present):
# a stale True flag with missing/stale cards would otherwise skip the per-card
# mtime re-render and cascade to a broken 04:00 assemble. Mirrors the watchdog,
# which no longer trusts images_rendered either.
if [ "$IMAGES_RENDERED" = "True" ] && [ "$JPG_COUNT" -ge 6 ]; then
    echo "✅ Images already rendered ($JPG_COUNT JPGs), skipping"
    # 即使跳过渲染，也要保证 manifest.cards[].file 指向 .jpg：
    # 02:00 可能自带 JPG 却留下 .html 引用（day70 事故），04:00 会按 .html
    # 当图片喂给 ffmpeg 而静默失败。翻转是幂等的。
    # 原子写：直接 open(p,'w') 覆盖，cron 中途被杀会留下截断的 JSON，
    # 而 manifest 是 04:00 assemble 唯一的图片来源（day70/day82 事故链的起点）。
    MANIFEST="$MANIFEST" "$XHS_PY" -c "
import json, os
p = os.environ['MANIFEST']
m = json.load(open(p, encoding='utf-8'))
dirty = False
for c in m.get('cards', []):
    f = c.get('file', '')
    if f.endswith('.html'):
        jpg = f[:-5] + '.jpg'
        if os.path.isfile(os.path.join(os.path.dirname(p), 'images', jpg)):
            c['file'] = jpg
            dirty = True
if dirty:
    tmp = f'{p}.tmp.{os.getpid()}'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(m, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)
    print('  ✅ manifest 回填：.html → .jpg（skip 分支）')
"
    exit 0
fi
if [ "$IMAGES_RENDERED" = "True" ] && [ "$JPG_COUNT" -lt 6 ]; then
    echo "⚠️  images_rendered=True 但仅 $JPG_COUNT 张 JPG — 重新渲染缺失卡片"
fi

# Kill any leftover Chrome CDP — 只杀流水线自己拉起的那个，
# 不要连带杀掉用户手动开着调试的 Chrome（宽匹配会）。
# 共享逻辑已在脚本开头引入。
kill_pipeline_chrome
sleep 1

# Headless — CDP screenshots need no GUI window
export XHS_CHROME_HEADLESS=1

# Source venv and run render script
source "$VENV"
"$XHS_PY" "$SCRIPT" "$V2_DIR"
EXIT_CODE=$?

# Cleanup Chrome
kill_pipeline_chrome

echo ""
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
