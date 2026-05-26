# Session Learnings — 2026-05-25

## Day 2 Cron Publish Failure

### What Happened
- Cron job for Day 2 (AI tools post) ran but failed at draft-save step
- Two compounding issues:

#### Issue 1: Session Server-Side Invalidation
- Navigating to `creator.xiaohongshu.com` → redirected to `/login` (redirectReason=401)
- Cookies were locally valid but session was revoked server-side
- This is NOT detectable from cookie file age — `galaxy_creator_session_id` can have no expires or far-future expires while server has revoked it
- **Diagnosis**: Connect via CDP, navigate to creator.xiaohongshu.com, check if redirected to /login

#### Issue 2: Login Unavailable in Cron Context
- `xhs_login.py --manual` timed out after 5 minutes
- The script waits for user to scan QR / complete SMS + press Enter
- In cron (no user present), this can never complete → always times out
- **Fix needed**: Session must be pre-validated before cron job runs, OR cron job must skip if session invalid

### Form Validation Failure (secondary issue)
Even when session was briefly available (before session invalidation was confirmed), the publish form showed:
```
Publish button: disabled
```
- Title was truncated to 20 chars: `打工人必备5个AI副业工具，最后一个太猛` (20 chars)
- The emoji 🤯 was stripped (not counted in 20-char limit, but still caused validation failure)
- Content (530 chars) was filled successfully
- Draft save button `button:has-text("存草稿")` could not be found (scroll timeout)
- **Root cause**: Title failed validation (likely too long OR emoji stripped) → form not valid → publish button disabled → draft button may not render

### Title Character Limit Issue
- XHS title input: max 20 Chinese characters
- Emoji at end of title: "打工人必备5个AI副业工具，最后一个太猛了🤯" = 21 chars (emoji counts as 1)
- Script truncated to 20 chars, stripping the emoji
- Title without emoji may have triggered different validation behavior
- **Lesson**: When title is near 20 chars and has trailing emoji, consider removing emoji from title OR ensure the title-with-emoji is ≤20 chars (emoji counted as 1)

### Pre-Flight Session Validation (CRITICAL for Cron)
Before any publish attempt in cron context, ALWAYS validate session first:

```python
# Quick session check (run before publish)
async def validate_session(page):
    await page.goto('https://creator.xiaohongshu.com/',
                    wait_until='domcontentloaded', timeout=15000)
    if 'login' in page.url.lower():
        return False  # Session invalid
    return True
```

If session invalid in cron:
1. **Do NOT** call `xhs_login.py --manual` — it will timeout
2. Send alert notification (Feishu if configured)
3. Log failure, mark day as needing manual intervention
4. Exit gracefully

### Cron Notify Script Requires Environment Variables
`scripts/cron_notify.py` requires `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_HOME_CHANNEL` in `~/.hermes/.env`. Without these, it fails silently. The script already prints the error, but in cron context the stderr may not be visible.

**Check**:
```bash
grep FEISHU ~/.hermes/.env || echo "Feishu env not set"
```

### Draft Save Button Selector
- Script uses `button:has-text("存草稿")` — this exists in the DOM
- But `scroll_into_view_if_needed` timeout (30s) suggests the button is conditional
- Draft save button only appears when form is valid (publish button enabled)
- If form validation fails → publish disabled → draft button may not be scrolled into view
- **Fix**: Always validate form state BEFORE trying to scroll draft button; if publish is disabled, diagnose why before trying draft save

### Published Content (Success Before Failure)
- `/tmp/xhs_day2/content.txt` — full body content generated ✅
- `/tmp/xhs_day2/post_data.json` — structured data ✅
- `/tmp/xhs_day2/covers/cover_1.jpg` — primary cover ✅ (3 variants)
- These are reusable once session is re-established

### Action Items
1. Add pre-flight session validation to xhs_publish.py (before form filling)
2. Add graceful failure with notification when session invalid in cron
3. Fix title generation to respect 20-char limit including trailing emoji
4. The `--style "realism"` in make-money-xiaohongshu SKILL.md is invalid — use `--style "auto"` instead