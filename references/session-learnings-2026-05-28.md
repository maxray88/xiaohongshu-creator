# Session Learnings — 2026-05-28

## Day 5 Cron: Content Generated, Publish Failed

### What Happened
- Day 5 cron ran: topic "用ChatGPT写文案，一小时50元实操全过程"
- Content and 3 covers generated successfully ✅
- Publish step failed — session server-side revoked

### Bug 1: `--style realism` is invalid
The cron instructions (received as a job payload) used `--style realism`, which is NOT a valid style for `xhs_content_generator.py`. Script exits with error.

**Valid styles**: `auto | funny | emotional | inspirational | savage | warm`

**Fix**: Always use `--style emotional` for 副业/赚钱/职场 content.

Note: `references/cron-daily-workflow.md` already documents this correctly. The bug was in the cron job instructions themselves, not the skill.

### Bug 2: `--draft-only` flag does not exist
`xhs_publish.py` has no `--draft-only` argument. Draft mode is the default (saves as draft without clicking publish). Passing `--draft-only` causes CLI error "unrecognized arguments".

### Bug 3: Cookie Injection Recovery FAILS for Fully Revoked Sessions
Tried injecting cookies from `cookies.json` (galaxy_creator_session_id expires 2026-06-24) via CDP, then navigating to creator.xiaohongshu.com.

**Result**: ❌ Still redirected to login page. 1 login element found.

**Diagnosis**: `galaxy_creator_session_id` was **fully revoked** by the server (cookies file was dated 2026-05-25, `acw_tc` refresh cookies were also expired May 25). Cookie injection cannot re-validate a fully revoked session — re-login is required.

**Contrast with 2026-05-26**: That session recovered via cookie injection because the session was only **temporarily** invalidated while cookies were still fresh. When cookies themselves are stale (locally expired `acw_tc`) or session is fully revoked server-side, cookie injection does NOT work.

### Session Expiry Timeline
From today's cookies file:
- `acw_tc`: expired **2026-05-25** (multiple entries, all past)
- `ets`, `a1`, `webId`, `websectiga`: expire 2026-06+ (still valid)
- `galaxy_creator_session_id`: expires 2026-06-24 (still within window, but revoked server-side)
- `access-token-creator`: expires 2026-06-24

The `acw_tc` cookies were already expired locally — this is the key signal. When `acw_tc` is expired and refresh fails, the server has fully revoked the session.

### Corrective Action for Cron Sessions
When cookie injection fails (redirects to login after cookie add):
1. **Do NOT** retry cookie injection — it won't work twice
2. **Do NOT** call `xhs_login.py --manual` — times out in cron
3. Send Feishu alert: "Session fully revoked — manual re-login required"
4. Content and covers remain at `/tmp/xhs_daily/dayN/` — reuse them after re-login
5. Log the failure, exit cron gracefully

### Content Generated
- `/tmp/xhs_daily/day5/content.txt` — post body + hashtags ✅
- `/tmp/xhs_daily/day5/post_data.json` — structured data ✅
- `/tmp/xhs_daily/day5/covers/cover_1.jpg` — cover variant 1 ✅

### Action Items
1. Remove `--draft-only` from cron workflow docs (not a real flag)
2. Clarify cookie injection recovery: "only works for temporary invalidation with fresh acw_tc cookies — not for fully revoked sessions"
3. Add pre-flight check: if `acw_tc` cookies are locally expired (timestamp in the past), skip publish attempt and alert immediately
4. The skill's cron-daily-workflow.md already has correct `--style emotional` — good, no change needed