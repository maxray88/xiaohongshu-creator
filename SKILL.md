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
│   ├── xhs_login.py                      # Login: open Chrome, save cookies
│   ├── xhs_publish.py                    # Publish: upload images + post
│   ├── xhs_analytics.py                  # Analytics: account & post metrics
│   ├── xhs_hashtags.py                   # Hashtag research & trending topics
│   ├── xhs_comments.py                   # Comment management
│   ├── xhs_engage.py                     # Engagement automation
│   └── render_covers.py                  # Cover image renderer (Playwright + HTML)
└── references/
    ├── xiaohongshu-content-gen.md        # Content generation guide
    ├── xiaohongshu-marketing.md          # Marketing strategy guide
    ├── playwright-environment.md          # Technical reference
    ├── xiaohongshu-publish-page-deep-dive.md  # Publish page DOM deep reference
    ├── best-practices.md                  # Best practices & pitfalls
    ├── cdp-mode-with-patchright.md       # CDP + Patchright setup
    ├── image-acquisition-and-composition.md  # Image acquisition guide
    ├── openverse-search-findings.md         # Openverse search limitations for anime characters
    ├── xiaohongshu-mcp-server-setup.md   # MCP server setup
    ├── session-learnings-2026-05-15.md   # Session learnings (2026-05-15)
    ├── session-learnings-2026-05-16.md   # Session learnings (2026-05-16)
    └── session-learnings-2026-05-17.md   # Session learnings (2026-05-17) — `_onPublish()` breakthrough, Retina coords, GitHub workflow
    └── github-workflow.md                # GitHub upload workflow
```

**Python**: Use the Hermes agent venv Python for all scripts:
```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
```

**Data directory**: `~/.xiaohongshu-creator/` (cookies, session state)

## Prerequisites

Playwright and Chromium should already be installed in the Hermes venv. If not:

```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON -m pip install playwright
$PYTHON -m playwright install chromium
```

> ⚠️ **Important**: Always use the venv Python path above, NOT system python3.

## Workflow

### Step 1: Login (First Time / Session Expired)

```bash
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_login.py --manual
```

> 💡 Use `--manual` flag for the most reliable login flow. Complete SMS login in the Chrome window, then press Enter in the terminal.

### Step 2: Generate Content

See `references/xiaohongshu-content-gen.md` for the full content generation guide.

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
    --output /tmp/xhs_covers
```

This single command searches Bing, downloads images, and renders 3 cover variants.

**Alternative — step by step**:
1. Search & download: Use `xhs_image_pipeline.py --query "..." --output /tmp/xhs_covers` (saves to `_images/` subdir)
2. Render covers: Use `render_covers.py --bg /path/to/image.jpg --title "..." --output /tmp/cover.jpg`
3. Pick the best cover and publish with `xhs_publish.py`

See `references/image-acquisition-and-composition.md` for the full workflow.

**⚠️ Pillow emoji limitation**: `ImageFont.truetype("Apple Color Emoji.ttc", size)` throws `OSError: invalid pixel size`. Pillow cannot render color emoji fonts. Use Playwright HTML rendering or emoji CDN PNGs instead.

**Font choices for covers**:
- **Title**: Comic Sans MS Bold 112px (playful, matches anime theme)
- **Subtitle**: Arial Rounded Bold 60px
- **CTA**: STHeiti Medium 54px
- **Button**: STHeiti Medium 42px
- **Emoji**: Rendered natively by browser (108px) — perfect color
- **Reliable in sandbox**: `STHeiti Medium.ttc`, `Comic Sans MS Bold.ttf`, `Arial Rounded Bold.ttf`
- **Avoid**: `PingFang.ttc` — may fail with `OSError` in sandbox

**Xiaohongshu-style cover design (v2)**:
- Real photo backgrounds with gradient overlay (top/bottom dark, center transparent)
- Accent color lines (16-18px) at top and bottom edges
- Top title area: ~380px with gradient overlay
- Bottom CTA area: ~280px with pill-shaped button
- CTA asks personal question (not yes/no) to encourage comments
- 1080×1440 (3:4 portrait)

### Step 3: Research Hashtags

```bash
# Get trending hashtags with competition analysis
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_hashtags.py \
  --category 全部 --limit 20 --analyze
```

### Step 4: Publish

```bash
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \
  --title "标题" \
  --content "正文内容 #标签" \
  --images /path/to/image1.jpg /path/to/image2.jpg
```

The publish script will:
1. Automatically fill the title and content fields
2. Upload the specified images
3. **Automatically click the publish button** via `_onPublish()` — no manual interaction needed!

> ✅ **Fully Automatic Publishing** (since 2026-05-17): The `xhs-publish-btn` Custom Element's `_onPublish()` method is called directly via JS, bypassing `event.isTrusted`. No manual click required.

> ⚠️ **CRITICAL**: Do NOT click the sidebar "发布笔记" button (class `publish-video`, at viewport ~x=80, y=90). That's a NAVIGATION button that goes to the publish page. The actual publish button is `xhs-publish-btn` inside the form. Use `_onPublish()` to trigger it.

### Step 5: Track Performance

```bash
# View account overview and post metrics
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_analytics.py
```

## 📊 Marketing & Growth

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

Monitor and manage comments on your posts:

```bash
# List all notes with comment counts
$PYTHON xhs_comments.py --action list

# Filter by note title
$PYTHON xhs_comments.py --action list --note-title "蜡笔小新"

# Batch reply (lists notes with comments)
$PYTHON xhs_comments.py --action batch-reply --message "感谢支持！💕"
```

> ⚠️ **Note**: The creator platform shows comment counts but direct comment reply may require the main XHS app. Use this script for monitoring and analytics.

### Engagement Automation

Automate engagement activities to grow your account:

```bash
# Browse trending topics
$PYTHON xhs_engage.py --action browse --category 知识 --limit 15

# Auto-engage with trending posts
$PYTHON xhs_engage.py --action auto-engage --category 知识 --likes 5 --comments 3

# View engagement history
$PYTHON xhs_engage.py --action history
```

> ⚠️ **Rate Limits**: Max 10 likes/hour, 5 comments/hour. The script enforces these limits automatically.

> ⚠️ **Warning**: Use auto-engage responsibly. Excessive automation may trigger bot detection. The creator platform is primarily for publishing and analytics — full engagement features require the main XHS app.

## GitHub Repository

The skill is maintained at: https://github.com/maxray88/xiaohongshu-creator

See `references/github-workflow.md` for upload/push workflow.

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
| JS syntax error in `page.evaluate` | Python triple-quoted strings: use `\\n` not `\n`, `\\d` not `\d` in JS code. See `references/playwright-environment.md` |
| `