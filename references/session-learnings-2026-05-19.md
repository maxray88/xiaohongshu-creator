# Session Learnings 2026-05-19

## Posting Comments on www.xiaohongshu.com via CDP

### Problem
The `xhs_comments.py` script only reads data from `creator.xiaohongshu.com`. User wanted to post comments on the main XHS site (`www.xiaohongshu.com`) on notes that had zero comments.

### Solution
Used CDP to connect to already-logged-in Chrome and post comments directly on www.xiaohongshu.com.

### Key Technical Findings

1. **Direct /explore/ URLs return 404** (error_code=300031 "当前笔记暂时无法浏览")
   - Navigating directly to `https://www.xiaohongshu.com/explore/<note_id>` always fails
   - Must navigate via profile page click (SPA routing)
   - Profile page: `https://www.xiaohongshu.com/user/profile/<user_id>`

2. **Note cards on profile page**
   - Selector: `.note-item` (class `note-item static-layout`)
   - Each card has an `<a href="/explore/<id>">` link
   - Clicking the card opens the note via SPA (URL changes to `/explore/<id>?xsec_token=...`)

3. **Comment input activation**
   - Comment textarea: `#content-textarea` (class `content-input`)
   - Has a `not-active` overlay div that intercepts pointer events
   - **Must use `force=True`** in Playwright click: `page.click('#content-textarea', force=True)`
   - JS fallback: `document.querySelector('#content-textarea').click()`

4. **Send button**
   - Selector: `button.btn.submit` (class `btn submit gray`)
   - Text: "发送"
   - Also has a "取消" (cancel) button next to it

5. **Verification**
   - After sending, check page text for comment content
   - Screenshot saved to `/tmp/xhs_comment_result.png`

### Working Flow
```
1. Connect to Chrome CDP (port 9222)
2. Open new tab, navigate to profile page
3. Wait 8s for SPA to load
4. Scroll to notes section
5. Find .note-item cards, get their positions
6. Click target note card at center coordinates
7. Wait 6s for note page to load
8. Click #content-textarea with force=True
9. Type comment with page.keyboard.type()
10. Click button.btn.submit with force=True
11. Wait 4s, verify comment in page text
```

### Confirmed Working
- ✅ Posted first comment on "小新的幸福生活太治愈了🌸" (zero comments → 1 comment)
- Comment: "太治愈了！小新那种简单快乐的能力，成年人真的该学学"

### xhs_engage.py Browse Issue
- `xhs_engage.py --action browse` returns empty results
- The creator platform inspiration page (`/new/inspiration`) is a SPA
- Text-based parsing doesn't find topic content
- Needs DOM-based parsing or different selectors

### Analytics Column Order (Reconfirmed)
- Platform column order: **曝光, 评论, 点赞, 收藏, 分享**
- NOT: 曝光, 点赞, 评论, 收藏, 分享
- Fixed in `xhs_analytics.py` `parse_note_data()`: numbers[1]=comments, numbers[2]=likes
