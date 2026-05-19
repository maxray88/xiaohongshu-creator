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

4. **Send button**: `button.btn.submit`

### Confirmed Working
- ✅ Posted first comment on "小新的幸福生活太治愈了🌸" via CDP
- ✅ `xhs_comments.py --action post` with `--note-url` or `--profile + --note-index`

---

## Auto-Engage: Like + Comment on Hot Posts via CDP

### Problem
`xhs_engage.py --action auto-engage` only browsed trending topics but couldn't actually like/comment on posts.

### Solution
Rewrote `xhs_engage.py` with full CDP-based like + comment on `www.xiaohongshu.com`.

### Key Technical Findings

1. **Search page**: `https://www.xiaohongshu.com/search_result?keyword=<kw>&source=web_search_result_notes`
2. **Note cards**: `<section class="note-item">` — use `offsetWidth`/`offsetHeight` for dimensions (getBoundingClientRect returns nan)
3. **Navigation**: `page.mouse.click(cx, cy)` at card center — direct page.goto() to /explore/ URLs returns 404
4. **Like button**: `.like-wrapper` (verified working)
5. **Comment flow**: `wait_for_selector('#content-textarea')` → `force=True` click → type → `button.btn.submit`
6. **Go back**: `page.go_back()` → wait 3s (or re-goto search URL)
7. **Rate limiting**: 10 likes/hour, 5 comments/hour
8. **wait_for_selector**: Always wait for `.like-wrapper` and `#content-textarea` before clicking (page may still be loading)

### Confirmed Working
- ✅ Full flow: search → click → like → comment → go back
- ✅ `--niche anime` for anime-specific comment templates
- ✅ 2 likes + 1 comment on 蜡笔小新 search results, no errors (2026-05-19)

---

## Full Auto-Publish (Agent-Driven)

### Workflow
1. Agent generates content directly (titles, body, CTA, hashtags, cover designs)
2. Write `post_data.json` + `content.txt` to `/tmp/xhs_post/<topic>/`
3. Run `xhs_image_pipeline.py` for covers
4. Run `xhs_publish.py --title "..." --content "$(cat content.txt)" --images cover.jpg`
5. Verify in note manager

### Confirmed Working
- ✅ Published "小新爸爸广志的7个悲催瞬间😭" (2026-05-19 11:05)

---

## Known Issues

- `xhs_engage.py --action browse` returns empty (SPA parsing issue, use `xhs_hashtags.py` instead)
- Analytics column order: 曝光, 评论, 点赞, 收藏, 分享 (NOT 点赞 before 评论)
