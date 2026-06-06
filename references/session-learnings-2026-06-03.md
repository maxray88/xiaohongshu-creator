# Session Learnings — 2026-06-03 (Day 08 Run)

## Signal: `_onSave()` Returns OK But Draft Never Persists

**Symptom:**
- `document.querySelector('xhs-publish-btn')._onSave()` returns `save-ok`
- SPA re-renders (form clears, URL unchanged)
- But draft count stays 0, draft not visible in list
- Cannot verify by navigating to `/draft` or `/draft/list` (both return "页面不存在")

**Root Cause: Session Degradation from Repeated CDP Reconnects**

After 3+ `playwright.chromium.connect_over_cdp(ws_url)` cycles on the same Chrome debug port (`--remote-debugging-port=9222`):
- `galaxy_creator_session_id` gets out of sync between Python CDP client and Chrome's native session state
- `_onSave()` calls the same API but the server silently drops the write
- `_onSave()` returns `save-ok` because the client-side validation passes — the actual network response may be 200 but the data doesn't commit

**Recovery Steps (in order of reliability):**

1. **Fresh Chrome restart (most reliable):**
   ```bash
   # Kill Chrome with the debug profile
   killall "Google Chrome" 2>/dev/null
   # Remove state (keep cookies.json for re-injection)
   rm -f /tmp/chrome-debug/SingletonLock
   # Restart Chrome fresh
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir=/tmp/chrome-debug \
     --no-first-run
   # Re-login to get fresh session
   xhs_login.py --manual
   ```

2. **Cookie injection recovery (if cookies still fresh):**
   - Connect via CDP
   - `context.add_cookies(cookies)` 
   - Navigate to creator.xiaohongshu.com
   - Only works if `acw_tc` cookie hasn't expired locally (< 20 min since last visit)
   - See `session-learnings-2026-05-28.md` — confirmed failure case when `acw_tc` was expired

**Prevention:**
- Minimize CDP reconnects during a single publish run
- If session was recovered mid-run via cookie injection, do NOT call `_onSave()` — close and restart Chrome instead
- For multi-post cron runs: start fresh Chrome for each post, don't reuse the same debug port session across posts

---

## Signal: Correct Page Index is `ctx.pages[0]`, Not `pages[-1]`

**Symptom:**
- After navigating to publish page twice (double-navigate pattern to force SPA re-render), `ctx.pages[-1]` returns a **blank upload page** (no title input found)
- The actual filled form page is `ctx.pages[0]`

**Pattern:**
```
pages[0] = Original creator tab (has title input, form filled, correct state)
pages[1] = Second tab opened by double-navigate
pages[-1] = blank upload page from the most recent navigation
```

**Always verify the target page:**
```python
for i, page in enumerate(ctx.pages):
    title_val = page.evaluate("document.querySelector('#title')?.value")
    print(f"page[{i}]: title='{title_val}'")
    if title_val:
        target_page = page
        break
```

**Takeaway:** When running `xhs_publish.py` multiple times in the same CDP session, pages accumulate. Do NOT assume `pages[-1]` is the right one. Always scan for the page with form state.

---

## Signal: Session Invalidation Mid-Run (Day 08 case)

**Timeline:**
1. Content generated, covers rendered
2. First publish attempt → session invalid (redirectReason=401)
3. Cookie injection recovery succeeded — navigated to creator.xiaohongshu.com, form was filled
4. `_onSave()` returned ok but form cleared
5. Session was degraded from the injection recovery — subsequent `_onSave()` calls unverified

**Lesson:**
- If session invalidates mid-run and requires cookie injection to recover, the session is now partially degraded
- The recovered session is usable for reading/navigating, but `_onSave()` / `_onPublish()` reliability drops
- Best practice: if cookie injection recovery was needed, complete the post manually or close/reopen Chrome before continuing automated steps

---

## Verified Working: Fresh Chrome + `_onSave()` 

With a clean Chrome session (no CDP reconnects, no injection recovery):
- `_onSave()` returns `save-ok`
- Draft appears in creator dashboard
- Verified working on 2026-05-29

**Environment that breaks it:**
- 3+ CDP reconnects to same Chrome debug port
- Cookie injection mid-session (signals session out-of-sync)
- Extended CDP session (> 30 min with multiple operations)

---

## Post-Data Available for Manual Recovery

Content for Day 08 ("别追了，喜欢你的人不用追"):
- **JSON**: `/tmp/xhs_day08/post_data.json`
- **Covers**: `/tmp/xhs_day08/covers/cover_2.jpg` (recommended), `cover_1.jpg`, `cover_3.jpg`
- **Title**: `追了3年才发现：他只是不爱你而已` (14 chars)
- **Body**: 322 chars (hook → story → value list → CTA)
- **Hashtags**: `#恋爱清醒脑 #情感共鸣 #扎心文案 #女性成长 #拒绝恋爱脑 #人间清醒 #情感树洞 #当代年轻人 #清醒恋爱 #自我成长`