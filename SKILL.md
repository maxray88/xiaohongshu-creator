---
name: xiaohongshu-creator
description: |
  Automate Xiaohongshu (小红书) creator platform: login, publish, analytics,
  hashtag research, comment management, and engagement automation.
  Use this skill when the user wants to publish, market, or grow their Xiaohongshu account.
metadata:
  hermes:
    tags: [xiaohongshu, creator, publish, marketing, analytics, playwright, automation, social-media]
    category: social-media
    related_skills: [xiaohongshu-content-gen]
---

# Xiaohongshu Creator Automation & Marketing

Automate login, publishing, analytics, hashtag research, and engagement on the Xiaohongshu creator platform using Playwright.

## Architecture

```
~/.hermes/skills/xiaohongshu-creator/
├── SKILL.md                              # This file - main workflow
├── scripts/
│   ├── xhs_auto_publish.py               # 🚀 Orchestrator: content → images → publish (FULL PIPELINE)
│   ├── xhs_content_generator.py          # Viral content generator (titles + body + hashtags + cover designs)
│   ├── xhs_image_pipeline.py             # All-in-one: search → download → cover render
│   ├── xhs_publish.py                    # Publish: CDP → fill form → _onPublish() (v10, merged)
│   ├── xhs_login.py                      # Login: open Chrome, save cookies
│   ├── xhs_analytics.py                  # Analytics: account & post metrics
│   ├── xhs_hashtags.py                   # Hashtag research & trending topics
│   ├── xhs_comments.py                   # Comment management (list/reply/post via CDP)
│   ├── xhs_engage.py                     # Engagement automation (auto-engage like+comment via CDP)
│   └── render_covers.py                  # Cover image renderer (Playwright + HTML, standalone)
├── templates/
│   └── xhs_content_prompt_template.md  # LLM prompt template for content generation (editable)
├── references/
│   ├── xiaohongshu-content-gen.md        # Content generation guide & viral formula
│   ├── xiaohongshu-marketing.md          # Marketing strategy guide
│   ├── playwright-environment.md          # Technical reference
│   ├── xiaohongshu-publish-page-deep-dive.md  # Publish page DOM deep reference
│   ├── best-practices.md                  # Best practices & pitfalls
│   ├── cdp-mode-with-patchright.md       # CDP + Patchright setup
│   ├── image-acquisition-and-composition.md  # Image acquisition guide
│   ├── openverse-search-findings.md         # Openverse search limitations for anime characters
│   ├── xiaohongshu-mcp-server-setup.md   # MCP server setup
│   ├── session-learnings-2026-05-15.md   # Session learnings (2026-05-15)
│   ├── session-learnings-2026-05-16.md   # Session learnings (2026-05-16)
│   ├── session-learnings-2026-05-17.md   # Session learnings (2026-05-17) — `_onPublish()` breakthrough
│   ├── session-learnings-2026-05-18.md   # Session learnings (2026-05-18) — emoji rendering, base64 bg, content pipeline
│   ├── session-learnings-2026-05-18-p2.md # Session learnings (2026-05-18 P2) — analytics column order, prompt escaping
│   ├── session-learnings-2026-05-19.md   # Session learnings (2026-05-19) — CDP comment posting, auto-engage like+comment
│   ├── session-learnings-2026-05-20.md   # Session learnings (2026-05-20) — cover font sizes, key points on cover, navigation fixes
│   ├── session-learnings-2026-05-21.md   # Session learnings (2026-05-21) — Emoji 2x, theme images, draft mode, multi-image upload
│   ├── session-learnings-2026-05-22.md   # Session learnings (2026-05-22) — S6 hand-drawn style, keyword highlighting, 14-day auto-publish
│   ├── session-learnings-2026-05-23.md   # Session learnings (2026-05-23) — session invalidation deep dive
│   ├── session-learnings-2026-05-24.md   # Session learnings (2026-05-24) — weekly review cron, empty analytics diagnostics
│   ├── session-learnings-2026-05-25.md   # Session learnings (2026-05-25) — cron session validation, title truncation, draft save failure
│   ├── feishu-channel-notification.md     # Feishu IM channel messaging for publish reports
│   ├── github-workflow.md                # GitHub upload workflow
│   ├── cover-style-s6-optimized.md       # Approved warm paper texture style with keyword highlighting
│   ├── custom-cover-styling-technique.md # Advanced custom cover rendering (break default template limits)
│   └── treehole-strategy.md              # Current strategy: 泛心理与情绪树洞

**Anti-Detection Approach (do NOT rewrite from scratch):**
When adding anti-detection to Xiaohongshu scripts:
1. **Keep the existing proven logic** — original scripts have correct patterns (home-first navigation, tab detection, JS nativeSetter filling, `_onPublish()` trigger). These took many sessions to stabilize.
2. **Inject anti-detection at key points only**: replace `page.click()` with Bezier mouse movement + human-like press, replace direct `page.type()` with per-character random delay, add random delays between critical steps, use `browser.contexts[0]` instead of `new_context()`.
3. **Do NOT**: create new browser_controller abstractions that launch fresh Chrome, override User-Agent, use `add_init_script()`, or replace the entire script structure.
4. **Do NOT use Python's HTTP stack for navigation** when in sandboxed environments — Chrome's network differs. Use `page.evaluate("window.location.href = '...'")` for CDP-connected pages instead of `page.goto()` from Python.
```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
```

**Data directory**: `~/.xiaohongshu-creator/` (cookies, session state)

## Quality Gate: Self-Review Before Sharing

**Always self-review outputs before sending to the user.** This is a hard requirement:
1. **Cover images**: Open/preview covers visually before sending via Feishu. Check: font sizes readable, emoji rendering correctly, layout centered, overall aesthetic quality.
2. **Content**: Read through generated titles and body text. Check: title ≤20 chars, body has proper hook/story/value/CTA structure, hashtags relevant.
3. **Code/scripts**: Verify syntax with `py_compile` before declaring done.
4. **Screenshots**: When publishing, review screenshots at each step to catch issues early.

**Feishu image delivery — RELIABLE method**: The `MEDIA:/path` approach via `send_message` does NOT reliably deliver images. Use this workflow instead:
1. Upload image via Feishu image API (`POST /open-apis/im/v1/images`) with `image_type=message` → get `image_key`
2. Send image message via Feishu message API (`POST /open-apis/im/v1/messages?receive_id_type=chat_id`) with `msg_type=image` and `content=json.dumps({"image_key": image_key})`
3. Use `execute_code` (Python urllib) for both steps — see avatar generation workflow for full code pattern.

**Feishu text + link delivery**: Use `send_message` with `action=send` and `target=feishu` for text messages with clickable links. This works reliably.

**Feishu channel notifications (publish reports)**: For automated cron publish jobs, send structured reports to a Feishu channel using the IM API directly. See `references/feishu-channel-notification.md` for the full Python pattern. Key: use `receive_id_type=chat_id` and `msg_type=text` with `json.dumps({"text": message})`.

## Prerequisites

Playwright and Chromium should already be installed in the Hermes venv. If not:

```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON -m pip install playwright
$PYTHON -m playwright install chromium
```

> ⚠️ **Important**: Always use the venv Python path above, NOT system python3.

## Workflow

### 🚀 Quick Start: One-Command Auto-Publish

The fastest way to publish — just provide a topic:

```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_auto_publish.py \
    --topic "蜡笔小新妈妈美伢的辛酸史" \
    --style "emotional" \
    --emoji "😭"
```

This single command runs the full pipeline:
1. **Content Generation** — 5 viral titles, full body, 10 hashtags, 3 cover designs
2. **Image Search + Cover Rendering** — Bing search → Playwright HTML covers
3. **Auto-Publish** — CDP → fill form → `_onPublish()` → done!

**Options:**
- `--style`: auto | funny | emotional | inspirational | savage | warm
- `--emoji`: Primary emoji (e.g., 😭 🌸 🔥 ❤️)
- `--dry-run`: Generate content + covers, skip publishing
- `--from-json`: Use existing `post_data.json` (skip content generation)
- `--output`: Output directory (default: `/tmp/xhs_auto_post`)

---

### Step 1: Login (First Time / Session Expired)

```bash
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_login.py --manual
```

> 💡 Use `--manual` flag for the most reliable login flow. Complete SMS login in the Chrome window, then press Enter in the terminal.

### Step 2: Generate Content

See `references/xiaohongshu-content-gen.md` for the full content generation guide.

**🚀 All-in-One Content + Cover Generation (Recommended):**

The `xhs_content_generator.py` script generates everything from a single topic:
- 5 viral title options (≤20 Chinese chars, ranked by viral potential)
- Full body content (hook → story → value list → emotional close → CTA)
- 10 optimized hashtags (broad + niche + trending + emotional)
- 3 cover image designs with search queries
- Auto-invokes `xhs_image_pipeline.py` to generate cover images

```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \
    --topic "蜡笔小新妈妈美伢的辛酸史" \
    --style "emotional" \
    --emoji "😭" \
    --output /tmp/xhs_post
```

**⚠️ IMPORTANT — LLM Architecture**: `xhs_content_generator.py` does NOT call the LLM itself. It outputs a prompt for the agent to process:
1. Run the script → it outputs `__AGENT_PROCESS__` signal + saves prompt to `/tmp/xhs_content_prompt.txt`
2. The **agent** (Hermes) must read the prompt, generate JSON content via its built-in LLM
3. Agent writes JSON to `{output_dir}/content/post_data.json`
4. Re-run with `--from-json` to continue the pipeline

**Options:**
- `--style`: auto | funny | emotional | inspirational | savage | warm
- `--emoji`: Primary emoji for the post (e.g., 😭 🌸 🔥 ❤️)
- `--no-images`: Skip cover image generation (content only)
- `--from-json`: Load content from existing JSON file (to regenerate covers)
- `--agent-prompt`: Output only the LLM prompt for inline agent processing

**Output files in `--output` directory:**
- `content.txt` — Title + body + CTA + hashtags (ready to publish)
- `post_data.json` — Structured data (titles, body, hashtags, cover designs)
- `post_preview.txt` — Formatted preview of the complete post
- `cover_best.jpg` — Best cover image (if image generation enabled)
- `cover_*/` — Individual cover variant directories

Key principles:
- **Title**: ≤20 chars, emotional hooks, numbers, or questions
- **Body**: Hook → Story → Value → Close → Hashtags
- **Hashtags**: 5-10 mix of broad + niche + trending
- **Tone**: Warm, conversational, authentic

**Content file workflow**: Write content to a temp file first (`/tmp/xhs_content_<topic>.txt`), then load with `CONTENT=$(cat /tmp/xhs_content_<topic>.txt)` and pass `--content "$CONTENT"` to the publish script. This avoids JS string escaping issues with special characters.

**Cover image**: Use the all-in-one pipeline script (recommended):

```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py \
    --query "Crayon Shinchan Misae mom" \
    --title "美伢的5个真相" \
    --emoji "😭" \
    --subtitle "看完妈妈们都哭了" \
    --cta "你家娃也这样吗？" \
    --key-points "葱油拌面·香到邻居" "番茄鸡蛋面·酸甜开胃" "麻酱拌面·灵魂拌一拌" \
    --kp-emojis "🧅" "🍅" "🥜" \
    --output /tmp/xhs_covers
```

This single command searches Bing, downloads images, and renders 3 cover variants with themed emoji circles and 88px key point text.

**Alternative — step by step**:
1. Search & download: Use `xhs_image_pipeline.py --query "..." --output /tmp/xhs_covers` (saves to `_images/` subdir)
2. Render covers: Use `render_covers.py --bg /path/to/image.jpg --title "..." --output /tmp/cover.jpg`
3. Pick the best cover and publish with `xhs_publish.py`

See `references/image-acquisition-and-composition.md` for the full workflow.

**⚠️ Pillow emoji limitation**: `ImageFont.truetype("Apple Color Emoji.ttc", size)` throws `OSError: invalid pixel size`. Pillow cannot render color emoji fonts. Use Playwright HTML rendering or emoji CDN PNGs instead.

**Font choices for covers** (user-approved minimums — never go smaller):
- **Title**: Comic Sans MS Bold **≥130px** with accent-color stroke + glow shadow (user explicitly requested larger, more eye-catching titles)
- **Subtitle**: Arial Rounded Bold **≥68px** with glow shadow
- **Key points**: **≥88px** (2x from 44px) with accent-color stroke + 3-layer glow shadow for maximum contrast against any background
- **Key point circles**: **128px** diameter — supports **theme images** (circle-cropped), **Emoji** (88px font), or **numbers** (56px font) as fallback
- **CTA text**: **≥54px** with glow shadow
- **CTA button**: **≥42px** with gradient background + glow shadow
- **Emoji**: Rendered natively by browser **≥110px** — perfect color
- **Accent bars**: **22px** top and bottom edges
- **Reliable in sandbox**: `STHeiti Medium.ttc`, `Comic Sans MS Bold.ttf`, `Arial Rounded Bold.ttf`
- **Avoid**: `PingFang.ttc` — may fail with `OSError` in sandbox
- **⚠️ User explicitly rejected fonts below these sizes as "too small" — always use these minimums.**

**Cover key points feature**: The cover template supports displaying key points from the body text with **three circle modes** (priority order):
1. **Theme images** (recommended): Pass `--kp-image-queries` with a Bing search query for each key point. Images are circle-cropped (128px, `object-fit: cover`, white border + shadow).
2. **Emoji circles**: Pass `--kp-emojis` for themed emoji (88px font, no background/border/shadow).
3. **Number fallback**: If neither image nor emoji provided, shows gradient circle with number.

```bash
# Full example with theme images + emoji fallback:
$PYTHON xhs_image_pipeline.py \
  --query "space galaxy universe aesthetic" \
  --title "5个冷知识" --emoji "🧠" \
  --subtitle "知道3个算你厉害" \
  --cta "你知道几个？" \
  --key-points "章鱼有三颗心脏" "蜂蜜永远不会变质" "香蕉是浆果草莓不是" "一生走路绕地球4圈" "章鱼的血是蓝色的" \
  --kp-image-queries "octopus underwater" "honey jar golden" "banana strawberry fruits" "earth globe space" "blue octopus blood" \
  --kp-emojis "🐯" "🍯" "🍌" "🌍" "💙" \
  --output /tmp/xhs_covers
```

- Max 5 key points per cover
- Theme images downloaded to `_kp_images/` subdir, converted to base64 for HTML embedding
- See `references/session-learnings-2026-05-20.md` for full CSS details.

**Current cover design**: S6 Warm Hand-Drawn Style with keyword highlighting. For full specifications, see 'Cover Design Style Guide (2026-05-21)' below.

**Note**: The pipeline can embed per-key-point theme images using `--kp-image-queries`, but these are small circular thumbnails (128px), not separate full covers.

### Step 3: Research Hashtags

```bash
# Get trending hashtags with competition analysis
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_hashtags.py \
  --category 全部 --limit 20 --analyze
```

### Step 4: Publish (or Save as Draft)

```bash
# Publish immediately
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \
  --title "标题" \
  --content "正文内容 #标签" \
  --images /path/to/image1.jpg /path/to/image2.jpg

# Save as draft only (default safe mode — no --publish flag)
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \
  --title "标题" \
  --content "正文内容" \
  --images /path/to/image1.jpg

# Actually publish (must explicitly pass --publish)
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \
  --title "标题" \
  --content "正文内容 #标签" \
  --images /path/to/image1.jpg /path/to/image2.jpg \
  --publish
```

The publish script (v10) will:
1. **Resolve CDP WebSocket URL** — from file or manual `/json/version` endpoint
2. **Clear SPA state** — navigate via home page first to avoid stale Vue state
3. **Double-navigate to publish URL** — goto `PUBLISH_URL` twice to force SPA re-render (fixes stale success page from previous publish)
4. **Use `domcontentloaded` not `commit`** — `wait_until="commit"` times out on XHS; `domcontentloaded` is more reliable. Wrap in try/except to handle timeouts gracefully.
5. **Detect & switch to image tab** — Bezier-curve human-like click on "上传图文" tab
6. **Upload images** — via file input with `wait_for(state="attached")` before setting files (triggers form to render). Supports **multiple images** (cover + key point images). Upload wait time scales dynamically: `20s + 5s × image_count`. Batch upload failure auto-falls back to one-by-one.
7. **Fill title** — JS nativeSetter (primary) → keyboard typing (fallback)
8. **Fill content** — JS execCommand insertText (primary) → keyboard typing (fallback)
9. **Hide overlays** — removes `.get-cover-suggest`, tippy, popup blockers
10. **Draft by default** — script saves as draft unless `--publish` flag is explicitly passed
11. **Publish via `_onPublish()`** — fully automatic, bypasses `event.isTrusted`
12. **Verify result** — checks URL + page text for 发布成功/审核/草稿
13. **Screenshots at every step** — saved to `/tmp/xhs_screenshots/`

> ✅ **Fully Automatic Publishing** (since 2026-05-17): The `xhs-publish-btn` Custom Element's `_onPublish()` method is called directly via JS, bypassing `event.isTrusted`. No manual click required.

> ⚠️ **CRITICAL**: Do NOT click the sidebar "发布笔记" button (class `publish-video`, at viewport ~x=80, y=90). That's a NAVIGATION button that goes to the publish page. The actual publish button is `xhs-publish-btn` inside the form. Use `_onPublish()` to trigger it.

> 📝 **Note**: Old publish scripts (`xhs_publish_v8.py`, `xhs_publish_cdp_sync.py`) have been removed. `xhs_publish.py` v10 is the single authoritative publish script.

> ⚠️ **Long content via CLI**: Content >~200 chars or with many emojis in CLI args triggers security scan timeout. Use Python API instead: `asyncio.run(publish(image_paths, title, content, cdp))` for draft, or add `publish_mode=True` to actually publish.

### Step 5: Track Performance

### Auto-Publish Scheduling (14-day cycle)

For continuous daily publishing without manual intervention, set up a cron job that runs a daily publish script. See `references/batch-generation-workflow.md` for the complete setup.

Key points:
- The system supports up to 14 days of content (2 weeks) by organizing content in `~/treehole/week1/` and `week2/` subfolders.
- A `current_day.txt` pointer tracks which day to publish next.
- The cron script (`daily_publish.sh`) computes the week folder and day-in-week, then calls the appropriate `publish_day.py`.
- After each successful publish, the day pointer increments (cycling 1-14).
- **To start**: ensure Week 1 and Week 2 drafts exist, set `current_day.txt` to the next unpublished day, and enable the cron job.
- **To extend** to more weeks: add `week3` folder with `publish_day.py` and modify the cron script's max day.

### ⚠️ CRITICAL: Session Validation Before Cron Publish
**Always validate session before attempting publish in cron jobs.**

XHS `galaxy_creator_session_id` can be revoked server-side even with locally valid cookies. When this happens:
- `creator.xiaohongshu.com` redirects to `/login` with `redirectReason=401`
- `xhs_login.py --manual` will timeout (requires user to scan QR/enter SMS — impossible in cron)
- Form may show "Publish button: disabled" even when filled

**Pre-flight validation** (add to cron script before publish step):
```bash
# Quick session check
$PYTHON -c "
import asyncio
from playwright.async_api import async_playwright

async def check():
    browser = await async_playwright().chromium.connect_over_cdp('ws://127.0.0.1:9222/devtools/browser/...')
    page = browser.contexts[0].pages[-1]
    await page.goto('https://creator.xiaohongshu.com/', wait_until='domcontentloaded', timeout=15000)
    if 'login' in page.url:
        print('SESSION_INVALID')
    else:
        print('SESSION_OK')

asyncio.run(check())
"
```

If `SESSION_INVALID`: 
1. **Try cookie injection recovery** (before giving up): Connect via CDP, inject cookies from `~/.xiaohongshu-creator/cookies.json` with `context.add_cookies()`, then re-navigate. This works when cookies haven't expired but the session was server-side invalidated. See `references/session-learnings-2026-05-26.md`.
2. If cookie injection fails or cookies are expired: send Feishu alert, skip publish, do NOT call `xhs_login.py --manual`.

See `references/session-learnings-2026-05-25.md` for full failure analysis.

This automation allows hands-free daily publishing for a fortnight, ideal for consistent content output.

### Cron Job Notification
After each daily publish, send a notification to your Feishu home channel reporting the result. Use the helper script `scripts/cron_notify.py` which wraps the Feishu IM API.

**Prerequisites**:
- `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_HOME_CHANNEL` set in `~/.hermes/.env`
- See `references/feishu-channel-notification.md` for full API details and troubleshooting.

**Usage example** in your cron script (`daily_publish.sh`):
```bash
# ... after successful publish
MESSAGE="✅ Day ${current_day} published: ${title}\nNext (Day ${next_day}): ${next_title}"
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/cron_notify.py "$MESSAGE"
```
The script sends via Feishu `im/v1/messages` using `receive_id_type=chat_id`. It handles token acquisition and prints a confirmation with message ID on success.

### Analytics Dashboard

Fetch account overview and post performance data:

```bash
# Full dashboard (account + notes)
$PYTHON xhs_analytics.py

# Just account metrics
$PYTHON xhs_analytics.py --section dashboard

# Just note list with stats
$PYTHON xhs_analytics.py --section notes

# JSON output for processing
$PYTHON xhs_analytics.py --output json
```

**Metrics tracked:**
- Account: followers, following, likes/collects, account ID
- Dashboard: exposure, views, CTR, likes, comments, saves, shares, net new followers
- Per-note: title, date, exposure, likes, comments, saves, shares

> ⚠️ **Analytics column order**: The note list page columns are: **曝光, 评论, 点赞, 收藏, 分享** (NOT 点赞 before 评论). If likes/comments data looks swapped, check `parse_note_data()` in xhs_analytics.py. See `references/session-learnings-2026-05-18-p2.md`.

**⚠️ Empty analytics diagnostics**: When `xhs_analytics.py` returns `{"notes": []}` or `{"dashboard": {}}`:
1. **Check `~/.xiaohongshu-creator/published_topics.txt`** — if entries exist there but analytics shows no data, session is likely server-side invalidated
2. **Cross-validate with Chrome CDP** — if Chrome is running, `playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")` can verify live session by navigating to creator.xiaohongshu.com and checking for login redirect
3. **Cookie age matters** — cookies file dated >7 days ago is likely stale even if session cookies are present; `acw_tc` refresh alone cannot fix `galaxy_creator_session_id` invalidation
4. **Empty + no cookies file** = fresh account / no posts published yet (not a session issue)

### Hashtag Research

Discover trending topics and analyze competition:

```bash
# All categories
$PYTHON xhs_hashtags.py --category 全部 --limit 20 --analyze

# Specific category
$PYTHON xhs_hashtags.py --category 美食 --limit 10 --analyze

# JSON output
$PYTHON xhs_hashtags.py --output json
```

**Categories**: 全部, 美食, 美妆, 时尚, 出行, 知识, 兴趣爱好

**Analysis includes:**
- Competition level (🔴极高 / 🟠高 / 🟡中等 / 🟢低)
- Engagement index (views per participant)
- Strategic advice for each hashtag
- Example top posts

### Comment Management

Monitor, manage, and post comments:

```bash
# List all notes with comment counts (creator platform)
$PYTHON xhs_comments.py --action list

# Filter by note title
$PYTHON xhs_comments.py --action list --note-title "蜡笔小新"

# Batch reply (lists notes with comments)
$PYTHON xhs_comments.py --action batch-reply --message "感谢支持！💕"

# Post a comment on www.xiaohongshu.com via CDP (by note URL)
$PYTHON xhs_comments.py --action post --note-url "https://www.xiaohongshu.com/explore/xxx" --message "太棒了！"

# Post a comment on www.xiaohongshu.com via CDP (by profile + note index)
$PYTHON xhs_comments.py --action post --profile "https://www.xiaohongshu.com/user/profile/<id>" --note-index 0 --message "太棒了！"
```

**Actions:**
- `list` — List all notes with comment counts (creator platform)
- `reply` — Reply to a specific comment (creator platform)
- `batch-reply` — Reply to all unread comments with the same message (creator platform)
- `mark-read` — Mark all comments as read (creator platform)
- `post` — Post a new comment on `www.xiaohongshu.com` via CDP (logged-in Chrome)

**Key pitfalls for `post` action:**
- **Direct `/explore/<id>` URLs return 404** (error_code=300031). Must navigate via profile page click.
- **Comment input has `not-active` overlay** — use `force=True` or JS `el.click()` to bypass.
- **Send button**: `button.btn.submit` or `button:has-text("发送")`.
- **Verify**: Check page text for comment content after sending.

> ✅ **Confirmed working** (2026-05-19): Successfully posted first comment on "小新的幸福生活太治愈了🌸" via CDP.

### Engagement Automation

Automate liking and commenting on hot posts to grow your account:

```bash
# Auto-engage: search keyword → like + comment on hot posts (via CDP)
$PYTHON xhs_engage.py --action auto-engage --keyword "蜡笔小新" --likes 3 --comments 2

# With niche-specific comment templates
$PYTHON xhs_engage.py --action auto-engage --keyword "蜡笔小新" --likes 3 --comments 2 --niche anime

# Like a specific post (via CDP)
$PYTHON xhs_engage.py --action like --note-url "https://www.xiaohongshu.com/explore/xxx"

# Comment on a specific post (via CDP)
$PYTHON xhs_engage.py --action comment --note-url "https://www.xiaohongshu.com/explore/xxx" --message "太棒了！"

# Browse trending topics (creator platform, text-based parsing)
$PYTHON xhs_engage.py --action browse --category 知识 --limit 15

# View engagement history
$PYTHON xhs_engage.py --action history
```

**How auto-engage works:**
1. Searches `www.xiaohongshu.com` for the keyword
2. Extracts visible note card positions using `offsetWidth`/`offsetHeight` (NOT `getBoundingClientRect()` which returns `nan`)
3. Clicks each note card via `page.mouse.click(cx, cy)` at card center (NOT `page.goto()` which returns 404)
4. Waits for `.like-wrapper` and `#content-textarea` via `wait_for_selector()` before interacting
5. Likes the post (`.like-wrapper` selector)
6. Types and sends a comment (`#content-textarea` + `button.btn.submit`)
7. Goes back to search results, repeats

**Niche comment templates** (`--niche`):
- `default` — Generic positive comments
- `anime` — Anime/fandom specific
- `food`, `beauty`, `fashion`, `travel` — Domain-specific

> ⚠️ **Rate Limits**: Max 10 likes/hour, 5 comments/hour. Enforced automatically via `~/.xiaohongshu-creator/engagement_history.json`.

> ⚠️ **Use responsibly**: Excessive automation may trigger bot detection. Random delays (3-8s) between actions help avoid detection.

> ⚠️ **`--action browse` limitation**: Returns empty results because the creator platform inspiration page is a SPA. Use `xhs_hashtags.py` for trending topic research instead.

**Key technical details:**
- Note cards: `<section class="note-item">` — use `offsetWidth`/`offsetHeight` for dimensions (**NOT** `getBoundingClientRect()` which returns `nan`)
- Navigation: `page.mouse.click(cx, cy)` at card center — **NOT** `page.goto()` (returns 404 for direct `/explore/` URLs)
- Like button: `.like-wrapper` — always `wait_for_selector('.like-wrapper', timeout=10000)` before clicking
- Comment input: `#content-textarea` — always `wait_for_selector('#content-textarea', timeout=10000)` before `force=True` click
- Send button: `button.btn.submit`
- Python Playwright: `page.evaluate("expr", arg)` does NOT support `arguments[0]` syntax — use the second parameter
- `page.go_back()` to return to search results after engaging with a note
- **Always use `wait_for_selector()`** before interacting with note page elements — SPA navigation means the page may not be fully loaded even after URL changes

## GitHub Repository

The skill is maintained at: https://github.com/maxray88/xiaohongshu-creator

See `references/github-workflow.md` for upload/push workflow.

## Content Strategy

Content strategy is **orthogonal** to publishing mechanics. The same pipeline (content → images → publish → analytics) works for any content vertical.

### Strategy Pivots
When the user pivots content strategy:
1. **Don't redo infrastructure** — image pipeline, publish scripts, and cron are strategy-agnostic
2. **Only content changes** — titles, body text, cover queries, key points
3. **Save strategy docs** to `references/` for future reference
4. **Reusable assets** — bg images from old strategy may not fit new theme; always search new images

### Current Strategy: 泛心理与情绪树洞 (2026-05-21)
- **Niche**: 职场反内耗 / 恋爱清醒脑 / 社交焦虑自救 / 当代年轻人精神状态实录
- **Format**: 金句图文 or 沉浸式树洞
- **Tone**: 温柔但不软弱，清醒但不冷漠，像朋友深夜聊天
- **Cover style**: Warm paper texture with keyword highlighting (S6 optimized) — user explicitly rejected heavy AI feel (glow effects, thick outlines, bright gradients, perfect geometry) in favor of hand-drawn/painterly/natural styles
- **Full strategy + 80+ topics + 30-day calendar**: See `references/treehole-strategy.md`

### Cover Design Style Guide (2026-05-21)
- **User explicitly rejected**: "heavy AI feel" — glow effects, thick stroke outlines, bright gradient backgrounds, perfect geometric shapes
- **User prefers**: hand-drawn / painterly / natural styles — paper textures, watercolor washes, sketch lines, warm muted palettes, slight rotations/tilts
- **Current approved style**: Warm paper texture with keyword highlighting (S6 optimized) featuring:
  * Subtle paper grain texture via layered radial gradients
  * Watercolor blob backgrounds in warm/cool tones
  * Hand-drawn title with keyword highlighting (bold, larger size, warm accent color)
  * Accent underline with gradient fill
  * Key points as cards with left accent border, slight rotation, and shadow
  * Keyword highlighting within key points — accent color, larger size, subtle shadow. To highlight keywords, wrap them in `**double asterisks**` or `<angle brackets>` in the key point text.
  * Scribble line and corner doodle decorations (✏️📝💭✨)
  * Brand mark in bottom right
- **Always generate 3-6 style variants** before asking user to choose; render all via Playwright, upload to Feishu for review
- **6 style templates** (S1-S6) tested and saved to `/tmp/xhs_styles/` — see `references/cover-style-templates.md` for gallery
- **Feishu image delivery**: Use `execute_code` with Feishu image API (upload → get image_key → send image message). Do NOT rely on `send_message` with `media` param for images — unreliable.
  * Hand-drawn title with keyword highlighting (bold, larger size, warm accent color)
  * Accent underline with gradient fill
  * Key points as cards with left accent border, slight rotation, and shadow
  * Keyword highlighting within key points (accent color, larger size, subtle shadow)
  * Scribble line and corner doodle decorations (✏️📝💭✨)
  * Brand mark in bottom right
- **Always generate 3-6 style variants** before asking user to choose; render all via Playwright, upload to Feishu for review
- **6 style templates** (S1-S6) tested and saved to `/tmp/xhs_styles/` — see `references/cover-style-templates.md` for gallery
- **Feishu image delivery**: Use `execute_code` with Feishu image API (upload → get image_key → send image message). Do NOT rely on `send_message` with `media` param for images — unreliable.

### Previous Strategy: 冷知识科普 (archived)
- See `references/cold-facts-strategy.md` and `references/30day-calendar.md`

### Batch Generation Workflow
For generating N posts at once + setting up cron auto-publish, see `references/batch-generation-workflow.md`.

### Check if session is valid
```bash
$PYTHON -c "
import json, os, datetime
cookies_file = os.path.expanduser('~/.xiaohongshu-creator/cookies.json')
if os.path.exists(cookies_file):
    with open(cookies_file) as f:
        cookies = json.load(f)
    print(f'✅ Cookies file exists ({len(cookies)} cookies)')
    for c in cookies:
        if c.get('expires', 0) > 0:
            exp = datetime.datetime.fromtimestamp(c['expires'])
            print(f'  {c[\"name\"]}: expires {exp}')
else:
    print('❌ No cookies found. Run login first.')
"
```

**Cross-check with `~/.xiaohongshu-creator/published_topics.txt`** — if this file has entries but analytics returns empty, the session has been server-side invalidated even if cookies are locally valid. Run `xhs_login.py --manual` to re-authenticate.

### Clear session
```bash
rm -f ~/.xiaohongshu-creator/cookies.json ~/.xiaohongshu-creator/*_state.json
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `playwright not installed` | `$PYTHON -m pip install playwright && $PYTHON -m playwright install chromium` |
| `Cookies file not found` | Run `xhs_login.py` first |
| `Session expired` | Re-run `xhs_login.py` to get fresh cookies |
| `Cookies not expired but still redirected to login` | **Server-side session invalidation**: session cookies (`galaxy_creator_session_id`, `access-token-creator`) can be locally valid but server-invalidated. Key indicators: `redirectReason=401` in URL, page shows login form. `acw_tc` refresh alone does NOT fix this — must re-login. Debug: connect via CDP and check page URL/content. See `references/session-learnings-2026-05-23.md`. |
| `Page.goto timeout` | The creator platform is slow; the script uses `wait_until="commit"` to handle this |
| `Could not find title/content input` | Page may not have fully loaded; check the browser window manually |
| `Could not find publish button` | Button may have a different label; check the DOM and update selectors |
| `event.isTrusted` check blocks all programmatic clicks | Use `btn._onPublish()` directly — see `references/session-learnings-2026-05-17.md` |
| `xhs-publish-btn` innerHTML is empty | Normal — it's a closed-shadow DOM Custom Element. Use `_onPublish()` method. |
| PyAutoGUI click doesn't work | On macOS Retina: no DPR multiplication needed. But `_onPublish()` is more reliable. |
| Upload fails | Ensure images are JPG/PNG/WebP, max 32MB each, max 18 images |
| Bot detection / CAPTCHA | Use `--headless=false` (default) and ensure cookies are from a real login |
| Login not detected | Use `--manual` flag and press Enter after logging in |
| "Already logged in" but can't publish | Playwright Chrome is a separate instance — you must log in again in the new window |
| Form inputs not found after upload | The publish form (title/content) only renders AFTER an image is uploaded |
| Playwright click fails on tabs | Use `page.evaluate()` JS click instead — tabs may be outside viewport |
| Analytics shows no data | Data updates hourly; wait after publishing |
| JS syntax error in `page.evaluate` | Python triple-quoted strings: use `\\\\n` not `\\n`, `\\\\d` not `\\d` in JS code. See `references/playwright-environment.md` |
| `OSError: invalid pixel size` with emoji font | Pillow cannot render Apple Color Emoji. Use Playwright HTML rendering or CDN PNG approach. See `references/session-learnings-2026-05-18.md` |
| Cover emoji shows as blank/boxes | Same root cause — Pillow's FreeType driver cannot handle bitmap-based color emoji fonts. Switch to Playwright HTML rendering. |
| Content generator outputs `__AGENT_PROCESS__` and stops | Expected behavior — the script cannot call LLM from subprocess. Agent must: (1) read prompt from `/tmp/xhs_content_prompt.txt`, (2) generate JSON via LLM, (3) save to `post_data.json`, (4) re-run with `--from-json`. See `references/session-learnings-2026-05-18-p2.md`. |
| Analytics likes/comments data swapped | **Platform column order: 曝光, 评论, 点赞, 收藏, 分享** (NOT 点赞 before 评论). Check `parse_note_data()` in xhs_analytics.py. See `references/session-learnings-2026-05-18-p2.md`. |
| `KeyError: '\\n  "titles"'` when running content generator | Prompt template JSON examples use single `{}` instead of escaped `{{}}`. Fix: ensure `templates/xhs_content_prompt_template.md` uses `{{}}` for all JSON example braces. See `references/session-learnings-2026-05-18-p2.md`. |
| Comment input not clickable on www.xiaohongshu.com | The `#content-textarea` has a `not-active` overlay. Use `force=True`: `page.click('#content-textarea', force=True)` or JS `el.click()`. See `references/session-learnings-2026-05-19.md`. |
| Direct /explore/ URL returns 404 on www.xiaohongshu.com | error_code=300031 "当前笔记暂时无法浏览". Must navigate via profile page click (SPA routing), not direct URL. See `references/session-learnings-2026-05-19.md`. |
| xhs_engage.py browse returns empty | Inspiration page SPA doesn't render parseable text. Use `xhs_hashtags.py` instead for trending topics. Needs DOM-based parsing fix. |
| Note card click doesn't navigate to note | `.note-item <a>` has zero-size rect (display:contents). Use `<section>` element rect for clicking. See `references/session-learnings-2026-05-19.md`. |
| `el.click is not a function` in page.evaluate | Element matched is not an HTMLElement (may be Vue component root). Use `document.querySelector()` with more specific selector, or use `page.locator()` + `page.click()` instead. |
| Note card getBoundingClientRect returns nan | XHS search page `.note-item` elements return `nan` for `getBoundingClientRect()`. Use `item.offsetWidth`/`item.offsetHeight` instead. See `references/session-learnings-2026-05-19.md`. |
| page.goto() to /explore/ URL returns 404 | Direct navigation to `www.xiaohongshu.com/explore/<id>` always returns 404 (error_code=300031). Must navigate via `page.mouse.click()` on note card from search/profile page. See `references/session-learnings-2026-05-19.md`. |
| `arguments` not defined in page.evaluate | Python Playwright `page.evaluate("expr")` does NOT support `arguments[0]` syntax. Use `page.evaluate("expr", arg)` second parameter instead. See `references/session-learnings-2026-05-19.md`. |
| `#content-textarea` null after navigation | Note page still loading after SPA navigation. Always use `page.wait_for_selector('#content-textarea', timeout=10000)` before interacting. See `references/session-learnings-2026-05-19.md`. |
| `page.goto` timeout on publish page | Use `wait_until="domcontentloaded"` instead of `"commit"` for XHS creator platform. Wrap in try/except. See session learnings. |
| `Cookies not expired but redirected to login` | Server-side session invalidation (`redirectReason=401`). Must re-run `xhs_login.py`. See `references/session-learnings-2026-05-23.md`. |
| `Session invalidation, cookie refresh didn't fix` | `acw_tc` refresh alone is insufficient — session cookie (`galaxy_creator_session_id`) requires re-login. |
| **Cookie injection recovery** (session invalid but cookies not expired) | If `cookies.json` has valid session cookies (check `galaxy_creator_session_id` expiry), inject them via CDP: connect to Chrome via Playwright, call `context.add_cookies(cookies)`, then navigate to creator platform. This re-validates the session server-side WITHOUT manual login. See `references/session-learnings-2026-05-26.md`. |
| **Chrome debug port not running** | Start Chrome with `terminal(background=true)`: `/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug --no-first-run`. Wait for port with `execute_code` + `urllib.request.urlopen('http://127.0.0.1:9222/json/version')`. See `references/session-learnings-2026-05-26.md`. |
| **Publish button not found but form filled** | `xhs-publish-btn` innerHTML is empty (closed shadow DOM). Call `_onPublish()` directly via `page.evaluate()`: `document.querySelector('xhs-publish-btn')._onPublish()`. See `references/session-learnings-2026-05-26.md`. |
| Title truncated to 20 chars, publish button disabled | XHS title max is 20 Chinese characters. If title-with-emoji is exactly 20 chars, the emoji may be stripped during truncation, causing validation failure. Ensure title ≤20 chars WITHOUT emoji first; move emoji to body or use as stand-alone emoji. See `references/session-learnings-2026-05-25.md`. |
| **Chrome instance isolation** — `browser_navigate` can't use `xhs_login` cookies | `browser_navigate` uses Hermes's own Chrome (`/var/folders/...`), completely separate from `xhs_login`'s Chrome (`/tmp/chrome-debug`). Cookies are NOT shared. Use `xhs_login` Chrome window directly for manual ops. |
| `xhs_login` timeout | Use `terminal` tool with 600s timeout (interactive QR scan takes minutes). Never `execute_code`. See `references/session-learnings-2026-05-24.md`. |
| `ECONNREFUSED 127.0.0.1:9222` on publish | Chrome debug port not running. Start with `--remote-debugging-port=9222`. Check: `lsof -i :9222`. |

## Anti-Detection Technical Guidelines

**Core principle**: When adding anti-detection, preserve proven script logic and inject human-like behaviors only at interaction points. Do NOT rewrite scripts from scratch.

### What TO Do
- Use `browser.contexts[0]` instead of `browser.new_context()` — reuses real Chrome context, less detectable
- Replace `page.click()` with Bezier-curve human mouse movement + random press duration
- Replace `page.type()` with per-character random delay typing
- Add random delays (0.5–2s) between critical steps
- Navigate using `page.evaluate("window.location.href = '...'")` when CDP-connected (uses Chrome's network, not Python's)
- Use `wait_until="domcontentloaded"` not `"commit"` for XHS pages

### What NOT To Do
- Do NOT override User-Agent
- Do NOT use `add_init_script()` — injects detectable JS
- Do NOT create fresh `browser.new_context()` — creates automation-labeled context
- Do NOT launch a new Chrome instance — connect to existing Chrome via CDP
- Do NOT rewrite script structure from scratch — inject into proven logic

### Cookie/Session Troubleshooting
- `acw_tc` expires ~20min locally; server re-issues on visit (no re-login needed)
- Session cookies (`galaxy_creator_session_id`, `access-token-creator`) have no local expiry; server revokes independently
- If redirected to login with `redirectReason=401` even with valid local cookies → server-side session invalidation → must re-run `xhs_login.py`
| `Session invalidation, cookie refresh didn't fix` | `acw_tc` refresh alone is insufficient — session cookie (`galaxy_creator_session_id`) requires re-login. |
| **Cookie injection recovery** (session invalid but cookies not expired) | If `cookies.json` has valid session cookies (check `galaxy_creator_session_id` expiry), inject them via CDP: connect to Chrome via Playwright, call `context.add_cookies(cookies)`, then navigate to creator platform. This re-validates the session server-side WITHOUT manual login. See `references/session-learnings-2026-05-26.md`. |
| **Chrome debug port not running** | Start Chrome with `terminal(background=true)`: `/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug --no-first-run`. Wait for port with `execute_code` + `urllib.request.urlopen('http://127.0.0.1:9222/json/version')`. See `references/session-learnings-2026-05-26.md`. |
| **Publish button not found but form filled** | `xhs-publish-btn` innerHTML is empty (closed shadow DOM). Call `_onPublish()` directly via `page.evaluate()`: `document.querySelector('xhs-publish-btn')._onPublish()`. See `references/session-learnings-2026-05-26.md`. |
| Title truncated to 20 chars, publish button disabled | XHS title max is 20 Chinese characters. If title-with-emoji is exactly 20 chars, the emoji may be stripped during truncation, causing validation failure. Ensure title ≤20 chars WITHOUT emoji first; move emoji to body or use as stand-alone emoji. See `references/session-learnings-2026-05-25.md`. |
| Cover title/subtitle too small | User preference: titles must be ≥130px with stroke+glow, subtitles ≥68px. Never use the old 100px/52px sizes — user explicitly rejected them. |
| Cover key point text too small | User preference: key point text must be **88px** (2x from 44px) with accent stroke + 3-layer glow. Use `--kp-emojis` for themed emoji circles (88px font, 128px circle) or `--kp-image-queries` for per-key-point theme images (128px circle-cropped). |
| Cover emoji circles too small | User preference: emoji circles must be **128px** (2x from 64px) with **88px** font. Number circles also 128px with 56px font. |
| `xhs_auto_publish.py` cover queries don't match topic | Known issue: `--topic` flows to content generation but cover image search queries may still use hardcoded values. Manually verify cover relevance or use `xhs_image_pipeline.py` directly with correct `--query`. |
| Long content via CLI triggers security scan timeout | Content >~200 chars or with many emojis in CLI args gets blocked. Use Python API instead: `asyncio.run(publish(image_paths, title, content, cdp, draft_only))`. |
| Multi-image upload times out | Uploading 6+ images can exceed Playwright's default timeout. Script auto-scales wait time (20s + 5s/image) and falls back to one-by-one upload if batch fails. |
| `page.goto` timeout on publish page | Use `wait_until="domcontentloaded"` instead of `"commit"` for XHS creator platform. Wrap in try/except. See session learnings. |
| `Cookies not expired but redirected to login` | Server-side session invalidation (`redirectReason=401`). Must re-run `xhs_login.py`. See `references/session-learnings-2026-05-23.md`. |
| `Session invalidation, cookie refresh didn't fix` | `acw_tc` refresh alone is insufficient — session cookie (`galaxy_creator_session_id`) requires re-login. |
| **Cookie injection recovery** (session invalid but cookies not expired) | If `cookies.json` has valid session cookies (check `galaxy_creator_session_id` expiry), inject them via CDP: connect to Chrome via Playwright, call `context.add_cookies(cookies)`, then navigate to creator platform. This re-validates the session server-side WITHOUT manual login. See `references/session-learnings-2026-05-26.md`. |
| **Chrome debug port not running** | Start Chrome with `terminal(background=true)`: `/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug --no-first-run`. Wait for port with `execute_code` + `urllib.request.urlopen('http://127.0.0.1:9222/json/version')`. See `references/session-learnings-2026-05-26.md`. |
| **Publish button not found but form filled** | `xhs-publish-btn` innerHTML is empty (closed shadow DOM). Call `_onPublish()` directly via `page.evaluate()`: `document.querySelector('xhs-publish-btn')._onPublish()`. See `references/session-learnings-2026-05-26.md`. |
| Title truncated to 20 chars, publish button disabled | XHS title max is 20 Chinese characters. If title-with-emoji is exactly 20 chars, the emoji may be stripped during truncation, causing validation failure. Ensure title ≤20 chars WITHOUT emoji first; move emoji to body or use as stand-alone emoji. See `references/session-learnings-2026-05-25.md`. |
| **Chrome instance isolation** — `browser_navigate` can't use `xhs_login` cookies | `browser_navigate` uses Hermes's own Chrome (`/var/folders/...`), completely separate from `xhs_login`'s Chrome (`/tmp/chrome-debug`). Cookies are NOT shared. Use `xhs_login` Chrome window directly for manual ops. |
| `xhs_login` timeout | Use `terminal` tool with 600s timeout (interactive QR scan takes minutes). Never `execute_code`. See `references/session-learnings-2026-05-24.md`. |
| `ECONNREFUSED 127.0.0.1:9222` on publish | Chrome debug port not running. Start with `--remote-debugging-port=9222`. Check: `lsof -i :9222`. |

## Anti-Detection Technical Guidelines

**Core principle**: When adding anti-detection, preserve proven script logic and inject human-like behaviors only at interaction points. Do NOT rewrite scripts from scratch.

### What TO Do
- Use `browser.contexts[0]` instead of `browser.new_context()` — reuses real Chrome context, less detectable
- Replace `page.click()` with Bezier-curve human mouse movement + random press duration
- Replace `page.type()` with per-character random delay typing
- Add random delays (0.5–2s) between critical steps
- Navigate using `page.evaluate("window.location.href = '...'")` when CDP-connected (uses Chrome's network, not Python's)
- Use `wait_until="domcontentloaded"` not `"commit"` for XHS pages

### What NOT To Do
- Do NOT override User-Agent
- Do NOT use `add_init_script()` — injects detectable JS
- Do NOT create fresh `browser.new_context()` — creates automation-labeled context
- Do NOT launch a new Chrome instance — connect to existing Chrome via CDP
- Do NOT rewrite script structure from scratch — inject into proven logic

### Cookie/Session Troubleshooting
- `acw_tc` expires ~20min locally; server re-issues on visit (no re-login needed)
- Session cookies (`galaxy_creator_session_id`, `access-token-creator`) have no local expiry; server revokes independently
- If redirected to login with `redirectReason=401` even with valid local cookies → server-side session invalidation → must re-run `xhs_login.py`
- See `references/session-learnings-2026-05-23.md` for full diagnostic workflow