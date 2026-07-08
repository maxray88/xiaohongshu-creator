# Xiaohongshu Daily Cron Workflow

Daily 14:00 auto-generate content + covers + save draft.

**Python path**: `PYTHON=python3  # Python 3.11 required`
**Output dir**: `/tmp/xhs_daily`

## ⚠️ Critical: Valid `--style` values only

`xhs_content_generator.py` only accepts:
```
auto | funny | emotional | inspirational | savage | warm
```

**`realism` is NOT valid** — script exits with error. Always use `emotional` for 副业/赚钱/职场 content.

## Four Pillar Rotation

1. 小白副业实操
2. AI工具赚钱
3. 省钱攒钱
4. 普通人逆袭

## 30-Day Topic Calendar

| Day | Topic |
|-----|-------|
| Day2 | 打工人必备5个AI赚钱工具，最后一个太猛了 |
| Day3 | 从月花8000到存5000，我做了这3件事 |
| Day4 | 副业实操Day1：PPT代做全流程，从接单到交付 |
| Day5 | 用ChatGPT写文案，一小时50元实操全过程 |
| Day6 | 下班3小时时间管理法：主业副业两不误 |
| Day7 | 副业Day4：犯了个错误，今天差点被骗 |
| Day8 | 用Notion管理副业项目，效率提升300% |
| Day9 | 外卖优惠券攻略：每月省下500+的5个方法 |
| Day10 | 100天攒10万挑战Day7复盘：进度40%，遇到瓶颈 |
| Day11 | 简历优化副业：从0到月入2000的全过程 |
| Day12 | 普通人如何用AI工具每年多赚3万 |
| Day13 | 消费降级后，我的生活反而更好了 |
| Day14 | 从月薪5000到副业过万：我的真实时间线 |
| Day15 | 闲鱼卖货Day1：如何找到高利润产品 |

## Execution Steps (Day N Example)

```bash
TOPIC="用ChatGPT写文案，一小时50元实操全过程"
DAY_DIR="/tmp/xhs_daily/day5"

# Step 1: Generate content (agent LLM call required)
PYTHON=python3  # Python 3.11 required
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \
    --topic "$TOPIC" \
    --style emotional \
    --emoji "💰" \
    --output "$DAY_DIR"

# Step 2: Agent generates post_data.json from /tmp/xhs_content_prompt.txt
# (script cannot call LLM — must be done by agent)

# Step 3: Generate covers (S6 hand-drawn style)
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py \
    --query "desk setup laptop notebook minimal warm lighting" \
    --title "ChatGPT副业" \
    --subtitle "一小时50元实操全过程" \
    --emoji "💰" \
    --key-points "文案代写" "某宝接单" "AI辅助写作" "当天结算" \
    --kp-emojis "📝" "🛒" "🤖" "✨" \
    --cta "下班试试？" --cta-emoji "🌙" \
    --output "$DAY_DIR/covers"

# Step 4: Save as draft (via Python API, NOT CLI — CLI has content length limits)
# See scripts/xhs_publish_draft.py for usage

# Step 5: Notify via Feishu
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/cron_notify.py \
    "✅ Day5 已保存草稿: $TOPIC"
```

## Draft Save — Known Timeout Issue

**Problem**: `xhs_publish.py` via Python API may timeout on the "存草稿" button click (`TimeoutError: Locator.scroll_into_view_if_needed`). The form is filled correctly — this is a UI/selector issue only.

**Workaround**: XHS auto-saves as draft when you navigate away. If explicit save times out:
1. Navigate to creator home: `page.goto("https://creator.xiaohongshu.com")`
2. Check 草稿箱 — content usually appears there

**Always verify**: Check 草稿箱 after each cron run.

## Content Length Limit via CLI

**Problem**: Content >~200 chars with emojis in CLI args triggers security scan timeout.

**Fix**: Use Python API for content passing:
```python
with open("$DAY_DIR/content.txt") as f:
    content = f.read()
# Pass via JSON file, not shell expansion
```

## Session Validity Check (Before Cron Run)

```bash
# Check Chrome CDP is running
lsof -i :9222 | head -3

# Check cookies exist
ls -la ~/.xiaohongshu-creator/cookies.json

# Check published_topics (if empty but previous runs existed = session invalid)
tail -3 ~/.xiaohongshu-creator/published_topics.txt
```

If session invalid: run `xhs_login.py --manual` before cron.

## Feishu Notification

Uses `scripts/cron_notify.py` which wraps Feishu IM API:
- Token acquired automatically
- Sends to `FEISHU_HOME_CHANNEL` (chat_id)
- msg_type: text with structured message

Requires env vars: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_HOME_CHANNEL`