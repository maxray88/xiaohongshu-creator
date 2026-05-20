# Session Learnings 2026-05-19

## Posting Comments on www.xiaohongshu.com via CDP

### Problem
The `xhs_comments.py` script only reads data from `creator.xiaohongshu.com`. User wanted to post comments on the main XHS site (`www.xiaohongshu.com`) on notes that had zero comments.

### Solution
Used CDP to connect to already-logged-in Chrome and post comments directly on www.xiaohongshu.com. Added `--action post` to `xhs_comments.py`.

### Key Technical Findings

1. **Direct /explore/ URLs return 404** (error_code=300031 "当前笔记暂时无法浏览")
   - Navigating directly to `https://www.xiaohongshu.com/explore/<note_id>` always fails
   - Must navigate via profile page click (SPA routing)

2. **Note cards on profile/search pages**
   - Selector: `.note-item` (class `note-item static-layout`)
   - `<a>` tags inside have `display:contents` → zero-size rect
   - Must use `<section>` element rect for clicking

3. **Comment input activation**
   - `#content-textarea` has `not-active` overlay
   - **Must use `force=True`**: `page.click('#content-textarea', force=True)`
   - Always `wait_for_selector('#content-textarea', timeout=10000)` first

4. **Send button**: `button.btn.submit`

### Confirmed Working
- ✅ Posted first comment on "小新的幸福生活太治愈了🌸" via CDP
- ✅ `xhs_comments.py --action post` with `--note-url` or `--profile + --note-index`

---

## Auto-Engage: Like + Comment on Hot Posts via CDP

### Problem
`xhs_engage.py --action auto-engage` only browsed trending topics but couldn't actually like/comment on posts. User asked to fix the note card click → navigation flow.

### Root Cause Analysis
Multiple issues discovered during debugging:

1. **`getBoundingClientRect()` returns `nan`** for `.note-item` elements on XHS search pages
   - Fix: Use `item.offsetWidth`/`item.offsetHeight` instead
   - Typical dimensions: 203×208 to 203×354

2. **`page.goto()` to `/explore/` URLs returns 404** (error_code=300031)
   - Fix: Use `page.mouse.click(cx, cy)` at card center coordinates
   - Fallback: `page.click(".note-item >> nth=0")`
   - `window.history.pushState()` changes URL but doesn't trigger SPA render — don't use

3. **Python Playwright `arguments[0]` not supported** in `page.evaluate()`
   - Fix: Use `page.evaluate("expr", arg)` second parameter

4. **SPA navigation timing**: Note page elements not immediately available after click
   - Fix: Always use `wait_for_selector('.like-wrapper', timeout=10000)` and `wait_for_selector('#content-textarea', timeout=10000)` before interacting

### Solution
Rewrote `xhs_engage.py` with full CDP-based like + comment on `www.xiaohongshu.com`.

### Key Technical Findings

1. **Search page**: `https://www.xiaohongshu.com/search_result?keyword=<kw>&source=web_search_result_notes`
2. **Note card dimensions**: Use `offsetWidth`/`offsetHeight` (NOT `getBoundingClientRect()`)
3. **Navigation**: `page.mouse.click(cx, cy)` at card center (NOT `page.goto()`)
4. **Like button**: `.like-wrapper` — always `wait_for_selector` first
5. **Comment flow**: `wait_for_selector('#content-textarea')` → `force=True` click → type → `button.btn.submit`
6. **Go back**: `page.go_back()` → wait 3s (or re-goto search URL)
7. **Rate limiting**: 10 likes/hour, 5 comments/hour

### Confirmed Working
- ✅ Full flow: search → click → like → comment → go back
- ✅ `--niche anime` for anime-specific comment templates
- ✅ 2 likes + 1 comment on 蜡笔小新 search results, no errors

---

## Cover Image Enhancement: Key Points Display

### Problem
User asked to display key points from the body text on the cover image ("把正文中的关键点展现在Cover Image中").

### Solution
Modified `xhs_image_pipeline.py` `build_cover_html()` to include a numbered key points list in the center of the cover.

### Changes
- Added `key-points-area` section in cover HTML (positioned at 38% from top)
- Numbered circles (1-5) with accent color background
- Key point text: 36px, white, with text shadow
- Title area reduced to 100px to make room
- Gradient overlay adjusted (15%/35%/55%/75%)
- CLI: Added `--key-points` nargs parameter

### Cover Layout (v3)
```
┌─────────────────────────────┐
│  Title (100px) + Emoji      │  ← Top area
│  Subtitle (52px)            │
├─────────────────────────────┤
│  ① Key point 1              │  ← Center area
│  ② Key point 2              │    (numbered list)
│  ③ Key point 3              │
│  ④ Key point 4              │
│  ⑤ Key point 5              │
├─────────────────────────────┤
│  CTA question (48px)        │  ← Bottom area
│  [Button]                   │
└─────────────────────────────┘
```

### Confirmed Working
- ✅ Published "大人也要玩玩具！解压神器推荐😍" with 5 key points on cover
- ✅ Published "高颜值巧克力｜看到就沦陷了😍"

---

## Full Auto-Publish (Agent-Driven)

### Workflow
1. Agent generates content directly (titles, body, CTA, hashtags, cover designs)
2. Write `post_data.json` + `content.txt` to `/tmp/xhs_post/<topic>/`
3. Run `xhs_image_pipeline.py` for covers (with `--key-points` for body highlights)
4. Run `xhs_publish.py --title "..." --content "$(cat content.txt)" --images cover.jpg`
5. Verify in note manager

### Confirmed Working
- ✅ Published "小新爸爸广志的7个悲催瞬间😭" (2026-05-19 11:05)
- ✅ Published "大人也要玩玩具！解压神器推荐😍" with key points cover
- ✅ Published "高颜值巧克力｜看到就沦陷了😍"

---

## Cron Jobs

Two automated cron jobs were set up and later paused by user:

1. **xhs_engage_auto** — Every 4 hours: auto-like (3) + auto-comment (2) on "蜡笔小新" posts
2. **xhs_auto_publish_funfacts** — Every 6 hours: auto-publish a random Shinchan Fun Facts post (20 rotating topics)

Both were paused on 2026-05-20 per user request.

---

## Known Issues

- `xhs_engage.py --action browse` returns empty (SPA parsing issue, use `xhs_hashtags.py` instead)
- Analytics column order: 曝光, 评论, 点赞, 收藏, 分享 (NOT 点赞 before 评论)
- `getBoundingClientRect()` returns `nan` for `.note-item` elements — use `offsetWidth`/`offsetHeight`
- `page.goto()` to `/explore/` URLs returns 404 — must use `page.mouse.click()` on note cards
- Python Playwright `page.evaluate()` does NOT support `arguments[0]` syntax
