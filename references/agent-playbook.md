---
name: agent-playbook
description: >
  Complete playbook for agents operating the xiaohongshu-creator skill.
  Covers architecture, workflow, all known bugs (with root causes + fixes),
  and anti-detection best practices. Write in Chinese.
metadata:
  hermes:
    tags: [xiaohongshu, agent-playbook, bugs, anti-detection]
    category: social-media
---

# Xiaohongshu-Creator Agent Playbook

> **TL;DR**: This skill automates Xiaohongshu (小红书) creator platform operations — content generation, cover rendering, login, publishing (draft or live), analytics, and engagement. Uses Playwright CDP mode connected to a live Chrome instance. **Always read this doc first** before touching any script.

---

## Architecture

```
~/.hermes/skills/xiaohongshu-creator/
├── SKILL.md                          # Main workflow (what to do)
├── scripts/
│   ├── xhs_config.py                 # Shared: URLs, paths, selectors, timeouts
│   ├── xhs_browser.py                # Shared: cookie I/O, CDP connect, page factories
│   ├── xhs_utils.py                  # Shared: Bezier mouse, delays, force_click, screenshots
│   ├── xhs_auto_publish.py           # 🚀 Orchestrator: content → images → publish (full pipeline)
│   ├── xhs_content_generator.py      # Outputs LLM prompt → agent generates JSON → saves post_data.json
│   ├── xhs_image_pipeline.py         # Bing search → download → cover rendering (Playwright HTML)
│   ├── xhs_publish.py                # CDP → upload → fill form → _onPublish/_onSave (v11 with warm-up)
│   ├── xhs_login.py                  # Open Chrome, save cookies to ~/.xiaohongshu-creator/cookies.json
│   ├── xhs_analytics.py              # Fetch account metrics and per-note stats
│   ├── xhs_hashtags.py               # Trending hashtag research
│   ├── xhs_comments.py               # Comment management (list/reply/post)
│   ├── xhs_engage.py                 # Auto-like + auto-comment on explore posts
│   └── render_covers.py              # Standalone cover renderer (HTML → PNG)
├── templates/
│   └── xhs_content_prompt_template.md  # LLM prompt for content generation (anti-AI rules here)
├── references/
│   ├── ai-detection-failure-2026-06-03.md
│   ├── new-account-strategy.md
│   ├── session-learnings-2026-05-*.md   # Per-session bug learnings
│   └── cover-style-s6-optimized.md      # Approved cover design specs
└── .git/
```

**Python path (always use venv):**
```bash
PYTHON=python3  # Python 3.11 required
```

**Data directory:** `~/.xiaohongshu-creator/` (cookies, session state, engagement history)

**GitHub repo:** `https://github.com/maxray88/xiaohongshu-creator` (branch: `main`)

---

## Workflow

### 1. Login (one-time / session expired)

```bash
$PYTHON xhs_login.py --manual
```

Opens Chrome with QR/SMS login. Wait for user to complete login, then press Enter. Cookies saved to `~/.xiaohongshu-creator/cookies.json`.

### 2. Generate Content (topic → JSON)

```bash
$PYTHON xhs_content_generator.py --topic "蜡笔小新妈妈美伢的辛酸史" --style emotional --emoji "😭" --output /tmp/xhs_post
```

**Important**: This script does NOT call LLM. It:
1. Outputs `__AGENT_PROCESS__` + saves prompt to `/tmp/xhs_content_prompt.txt`
2. **Agent must**: read prompt → generate JSON via built-in LLM → save as `post_data.json`
3. Re-run with `--from-json /tmp/xhs_post/post_data.json` to continue (image search + cover render)

### 3. Publish / Save Draft

```bash
# Save as draft (DEFAULT — safe)
$PYTHON xhs_publish.py --title "标题" --content "正文" --images "cover.jpg"

# Actually publish (must explicitly pass --publish)
$PYTHON xhs_publish.py --title "标题" --content "正文" --images "cover.jpg" --publish
```

**Full pipeline via orchestrator:**
```bash
$PYTHON xhs_auto_publish.py --topic "xxx" --style emotional --emoji "😭"
```

---

## Publish Script Flow (xhs_publish.py v11)

```
1. Resolve CDP WebSocket URL from Chrome debug port (9222)
2. Connect via playwright.chromium.connect_over_cdp()
3. Use browser.contexts[0] (NOT new_context) — reuse real Chrome context
4. Load cookies from ~/.xiaohongshu-creator/cookies.json
5. 🔥 WARM-UP: browse explore feed, scroll, click a post, like, comment, go back to home
   - Duration: random 3-8 minutes (breaks "new tab → publish" pattern)
6. Navigate to home page (clear SPA state)
7. Navigate to publish URL (double-navigate to force SPA re-render)
8. Detect & switch to "上传图文" tab (Bezier-curve click)
9. Upload images (file input, wait 20s + 5s per image)
10. Fill title (human-like typing, random per-char delay)
11. Fill content (human-like typing)
12. Hide overlays (tippy, popup blockers)
13. Save draft via _onSave() OR publish via _onPublish()
14. Verify result (check URL + page text)
15. Screenshot at each step to /tmp/xhs_screenshots/
```

**Key anti-detection techniques already baked in:**
- `browser.contexts[0]` instead of `new_context()`
- Bezier-curve mouse movement for all clicks
- Random per-character typing delay
- Random delays between critical steps
- Warm-up browsing before publishing (3-8 min, random actions)
- Cron schedules randomized across 10:00-20:00

---

## 🐛 Known Bugs, Root Causes & Fixes

### CRITICAL: Account Flagged by AI Detection (2026-06-03)

**Bug**: Even `draft-only` mode triggers account restriction. User reported: "草稿保存就触发风控/限号".

**Root Cause**: 5-layer detection:
1. Browser fingerprint (CDP artifacts) — partially addressed
2. **Behavioral sequence** (fixed login→upload→fill→save) — NOT addressed
3. Content fingerprint (AI text patterns) — partially addressed
4. Temporal patterns (fixed cron intervals) — NOT addressed
5. Session context (fresh cookie + immediate script action) — NOT addressed

**Fix**: Added `warm_up_session()` to xhs_publish.py — simulates 3-8 min of natural browsing (explore → scroll → click post → like → comment → home) before any publishing. Cron schedules randomized to 10:00-20:00.

**Recovery path**: Flagged account rests 2-4 weeks with zero automation. New accounts: 30+ days manual posting before any automation.

---

### Bug: `_onSave()` Returns OK But Draft Never Persists

**Symptom**: `_onSave()` returns `save-ok`, form clears, but draft count stays 0.

**Root Cause**: **Session degradation from repeated CDP reconnects.** After 3+ `connect_over_cdp()` cycles on the same Chrome debug port:
- `galaxy_creator_session_id` gets out of sync between Python CDP client and Chrome's native session
- `_onSave()` returns client-side validation pass (`save-ok`) but server silently drops the write

**Fix**:
- Close and restart Chrome fresh for each publish run
- Never reuse the same debug port session across multiple posts
- If cookie injection recovery was needed mid-run, do NOT call `_onSave()` — restart Chrome first

**Reference**: `references/session-learnings-2026-06-03.md`

---

### Bug: Wrong Page Selected After Double-Navigate

**Symptom**: After double-navigate to publish URL (to force SPA re-render), script finds blank page, no title input.

**Root Cause**: `browser.contexts[0].pages` accumulates across multiple publish runs:
- `pages[0]` = original creator tab (has filled form, correct state)
- `pages[-1]` = blank upload page from the most recent navigation

**Fix**: Always iterate pages and verify the target:
```python
for page in ctx.pages:
    title_val = page.evaluate("document.querySelector('#title')?.value")
    if title_val:
        target_page = page
        break
```

**Reference**: `references/session-learnings-2026-06-03.md`

---

### Bug: `page.screenshot()` Times Out on XHS Creator Platform

**Symptom**: `TimeoutError: Page.screenshot: Timeout 30000ms exceeded.` with "waiting for fonts to load" hanging.

**Root Cause**: Playwright's screenshot on a CDP-connected XHS creator page hangs during font-loading phase. Playwright waits for fonts but the wait can hang even after fonts are "loaded."

**Fix**: Wrap `page.screenshot()` in try/except with extended timeout (60s), skip silently if it fails (non-critical).

**Reference**: `references/session-learnings-2026-06-06.md`

---

### Bug: Content Generator Outputs `__AGENT_PROCESS__` and Stops

**Symptom**: Script runs, outputs `__AGENT_PROCESS__`, saves prompt to `/tmp/xhs_content_prompt.txt`, then exits. No JSON generated.

**Root Cause**: **Expected behavior.** The script CANNOT call LLM from subprocess. It outputs a prompt for the agent to process.

**Fix**: Agent workflow:
1. Read prompt from `/tmp/xhs_content_prompt.txt`
2. Generate JSON via built-in LLM (follow the prompt template in `templates/xhs_content_prompt_template.md`)
3. Save JSON to `{output_dir}/post_data.json`
4. Re-run with `--from-json {output_dir}/post_data.json` to continue to image generation + publish

**Reference**: `references/session-learnings-2026-05-18-p2.md`

---

### Bug: `KeyError: '\n  "titles"'` in Content Generator

**Symptom**: Template processing fails with JSON parsing error.

**Root Cause**: Prompt template uses single `{}` for JSON example braces. Python's `.format()` or f-string interprets `{}` as format placeholders.

**Fix**: Ensure `templates/xhs_content_prompt_template.md` uses `{{}}` for all JSON example braces.

**Reference**: `references/session-learnings-2026-05-18-p2.md`

---

### Bug: Analytics Likes/Comments Data Swapped

**Symptom**: Analytics shows likes as comments and vice versa.

**Root Cause**: Platform column order is: **曝光, 评论, 点赞, 收藏, 分享** — NOT 点赞 before 评论 as one might expect.

**Fix**: Check `parse_note_data()` in `xhs_analytics.py` — the parsing assumes the correct column order.

**Reference**: `references/session-learnings-2026-05-18-p2.md`

---

### Bug: Direct `/explore/<id>` URL Returns 404 on www.xiaohongshu.com

**Symptom**: Navigating to `www.xiaohongshu.com/explore/xxx` returns 404 (error_code=300031).

**Root Cause**: XHS SPA routing — explore items are only accessible via profile page click or search result navigation, not direct URLs.

**Fix**: Navigate via `page.mouse.click()` on a note card from the search/profile page. Use `page.go_back()` to return to search results after interacting.

**Reference**: `references/session-learnings-2026-05-19.md`

---

### Bug: `getBoundingClientRect()` Returns `nan` on Note Cards

**Symptom**: `item.getBoundingClientRect()` returns `{left: nan, top: nan, ...}` for note cards.

**Root Cause**: XHS `.note-item` elements use `display: contents` or similar rendering tricks that break `getBoundingClientRect()`.

**Fix**: Use `item.offsetWidth` / `item.offsetHeight` instead. Click at `offsetWidth/2`, `offsetHeight/2` relative to the element.

**Reference**: `references/session-learnings-2026-05-19.md`

---

### Bug: Comment Input Not Clickable (`not-active` Overlay)

**Symptom**: `page.click('#content-textarea')` fails with "Element is not clickable."

**Root Cause**: The textarea has a `not-active` overlay div that blocks click events.

**Fix**: Use `page.click('#content-textarea', force=True)` or JS `el.click()`.

**Reference**: `references/session-learnings-2026-05-19.md`

---

### Bug: `page.evaluate()` `arguments[0]` Not Supported in Python Playwright

**Symptom**: `page.evaluate("arguments[0]", expr)` fails with `arguments is not defined`.

**Root Cause**: Python Playwright's `page.evaluate(expr, arg)` passes `arg` as the second parameter to the JS function, NOT as `arguments[0]`.

**Fix**: Use `page.evaluate("(arg) => expr", arg)` with an explicit function parameter.

**Reference**: `references/session-learnings-2026-05-19.md`

---

### Bug: `#content-textarea` Null After SPA Navigation

**Symptom**: After navigating to a note page, `page.click('#content-textarea')` fails because the element doesn't exist yet.

**Root Cause**: Note page is still loading after SPA navigation. The comment textarea renders asynchronously.

**Fix**: Always use `page.wait_for_selector('#content-textarea', timeout=10000)` before interacting.

**Reference**: `references/session-learnings-2026-05-19.md`

---

### Bug: Save Draft Button Not Found (Shadow DOM)

**Symptom**: Cannot find or click the save/publish button using `page.locator()`.

**Root Cause**: `xhs-publish-btn` is a Custom Element with a **closed shadow DOM**. `locator()` cannot pierce closed shadow roots.

**Fix**: Call `_onSave()` or `_onPublish()` directly via JS:
```python
await page.evaluate("document.querySelector('xhs-publish-btn')._onSave()")
```

**Reference**: `references/session-learnings-2026-05-29.md`

---

### Bug: Pillow Cannot Render Color Emoji (`OSError: invalid pixel size`)

**Symptom**: `ImageFont.truetype("Apple Color Emoji.ttc", size)` throws `OSError: invalid pixel size`.

**Root Cause**: Pillow's FreeType driver cannot handle bitmap-based color emoji fonts.

**Fix**: Use Playwright HTML rendering for emoji (browser renders color emoji natively), or CDN PNG approach. Never use Pillow for emoji.

**Reference**: `references/session-learnings-2026-05-18.md`

---

### Bug: Session Invalidated Mid-Run (Cookie Injection Recovery)

**Symptom**: Script gets redirected to login with `redirectReason=401` mid-publish.

**Root Cause**: Server-side session invalidation. Local cookies may be valid (not expired) but server has revoked the session.

**Fix hierarchy**:
1. Try cookie injection via CDP: `context.add_cookies(cookies)` + re-navigate (only works if `acw_tc` still fresh < 20 min)
2. If injection fails → run `xhs_login.py --manual` for fresh session
3. If session was recovered mid-run, restart Chrome before continuing `_onSave()` calls

**Reference**: `references/session-learnings-2026-05-23.md`, `references/session-learnings-2026-05-28.md`

---

### Bug: `_onSave()` Works Only on Fresh Chrome

**Symptom**: `_onSave()` works on first run but fails on subsequent runs in the same session.

**Root Cause**: After cookie injection recovery, the session is partially degraded. The recovered session works for reading/navigation but `_onSave()`/`_onPublish()` reliability drops.

**Fix**: If cookie injection was needed to recover session, do NOT call `_onSave()`. Close and restart Chrome, re-login, then continue.

---

### Bug: Title Truncation at 20 Chars Breaks Publish

**Symptom**: Title with emoji at exactly 20 chars causes publish button to be disabled.

**Root Cause**: XHS truncates the title to 20 chars, stripping the emoji. The truncated title may fail validation.

**Fix**: Ensure title text portion is ≤18 chars (reserve 2 for emoji). Script truncates to 20 chars and warns.

**Reference**: `references/session-learnings-2026-05-25.md`

---

### Bug: `page.goto()` Timeout on Publish Page

**Symptom**: `wait_until="commit"` hangs indefinitely on XHS creator platform pages.

**Root Cause**: XHS creator platform is a slow SPA. Some resources never fully load.

**Fix**: Use `wait_until="domcontentloaded"` instead. Wrap in try/except for timeout fallback.

---

### Bug: Analytics Returns Empty `{}` When Session Invalid

**Symptom**: `xhs_analytics.py` returns `{"notes": []}` or `{"dashboard": {}}`.

**Diagnosis**:
1. Check `~/.xiaohongshu-creator/published_topics.txt` — if entries exist but analytics empty → session server-side invalidated
2. Cross-validate with Chrome CDP — check if creator platform redirects to login
3. Check cookie age — >7 days likely stale
4. Empty + no cookies file = fresh account / no posts yet

---

## 🚫 Anti-Detection Do's and Don'ts

### DO:
- Use `browser.contexts[0]` (reuse real Chrome context)
- Bezier-curve mouse movement for all clicks
- Random per-character typing delay
- Random delays between critical steps
- Navigate via `page.evaluate("window.location.href = '...'")` when CDP-connected
- Use `wait_until="domcontentloaded"` for XHS pages
- Warm-up browsing before publishing (3-8 min, random actions)
- Randomize cron schedules (10:00-20:00)

### DON'T:
- Override User-Agent
- Use `add_init_script()` (injects detectable JS)
- Create `browser.new_context()` (automation-labeled context)
- Launch new Chrome instance (connect to existing via CDP)
- Rewrite script structure from scratch (inject into proven logic)
- Use `wait_until="commit"` (times out on XHS)
- Use `getBoundingClientRect()` on XHS note cards (returns nan)
- Use Pillow for emoji rendering (OSError)
- Navigate directly to `/explore/<id>` (returns 404)

---

## 📝 Cron Job Management

**Do NOT use shell commands.** Use the `cronjob` MCP tool:

| Op | Tool Call |
|----|-----------|
| Create | `cronjob(action='create')` |
| List | `cronjob(action='list')` |
| Delete | `cronjob(action='remove')` |
| Pause/Resume | `cronjob(action='pause/resume')` |
| Edit | `cronjob(action='edit', job_id=..., --schedule=...)` |

**Schedule format**: ISO timestamp `2026-06-05T14:00:00+08:00` for one-shot. Cron expression `0 14 * * *` for recurring. **Never** use `"at 2026-06-05 14:00"` or `"once at ..."`.

**Cron pitfalls**:
- Prompts must be self-contained (no prior session context)
- Create in batches of ≤5 to avoid rate limiting
- Subagents may truncate prompts — put full prompts directly in cron jobs
- Cron sessions have no current-chat context

---

## 📊 Content Anti-AI Rules

Always enforce these when generating or reviewing content:

| Rule | Do | Don't |
|------|----|-------|
| Opening | Start with personal feeling: "我觉得", "说实话" | Open with "姐妹们/集美们/宝藏XX" |
| Emoji | ≤3 scattered randomly | 1 per line / packed at end |
| Paragraphs | Mix lengths, at least 1 ≥3 lines | All paragraphs exactly 1-2 lines |
| Grammar | Include casual markers (吧/呢/啊/嘛) | Grammatically perfect |
| Closing | Open question: "你们呢？" | Direct CTA: "收藏关注" |

**Forbidden phrases**: "码住！", "收藏了！", "太棒了吧！", "这也太…了！", "日常打卡", "点赞关注收藏", "评论区告诉我", "大家怎么看"

---

## 🆕 New Account Strategy

See `references/new-account-strategy.md` for full 4-phase plan:
1. **Phase 1**: Isolation (new Chrome profile, new IP, new phone number)
2. **Phase 2**: Pure manual warm-up (14 days, no scripts)
3. **Phase 3**: First post manual
4. **Phase 4**: Script involvement with warm-up enabled

---

## 🔧 Quick Troubleshooting

| Problem | First Action |
|---------|-------------|
| `playwright not installed` | `pip install playwright && playwright install chromium` |
| `Cookies file not found` | Run `xhs_login.py --manual` |
| Redirected to login page | Check `published_topics.txt` → if has entries, session invalidated → `xhs_login.py --manual` |
| `_onSave()` returns ok but draft missing | Restart Chrome fresh → re-login |
| Analytics returns empty | Check session validity + cookie age |
| Content generator stops at `__AGENT_PROCESS__` | Normal — generate JSON via LLM, save as `post_data.json`, re-run with `--from-json` |
| Screenshot times out | Non-critical, skip it (wrapped in try/except) |
| Cron never fires | Check schedule format — must be ISO timestamp without "at" prefix |

---

## 📌 Files That Should NEVER Be Edited

- **`xhs_publish.py`** — Only patch small changes (warm-up, delays). Never rewrite. Contains ~5 years of battle-tested DOM selectors and `_onPublish()` logic.
- **`xhs_browser.py`** / **`xhs_utils.py`** / **`xhs_config.py`** — Shared modules. Only patch if fixing a genuine bug.
- **`scripts/` directory structure** — All other scripts import from these shared modules. Breaking the import chain breaks everything.

When in doubt, **read existing code first** before writing new code. The shared modules have the right patterns already.

---

## 📚 Quick Reference: File Purposes

| File | Purpose |
|------|---------|
| `xhs_auto_publish.py` | Full pipeline: content → images → publish |
| `xhs_content_generator.py` | Generates LLM prompt → agent → JSON |
| `xhs_image_pipeline.py` | Bing search + cover rendering |
| `xhs_publish.py` | CDP publish/draft (v11 with warm-up) |
| `xhs_login.py` | Login + cookie save |
| `xhs_analytics.py` | Fetch metrics |
| `xhs_hashtags.py` | Hashtag research |
| `xhs_comments.py` | Comment management |
| `xhs_engage.py` | Auto-like + auto-comment |
| `xhs_content_prompt_template.md` | LLM prompt with anti-AI rules |

---

## 📝 When to Save New Findings

After encountering a new bug or fix:
1. **Save to `references/session-learnings-YYYY-MM-DD.md`** with: symptom, root cause, fix, prevention
2. **Update this playbook** if the bug is generic enough to affect other agents
3. **Update `SKILL.md` troubleshooting table** if it's a common issue
4. **Patch the script** if there's a code fix needed

---

*Last updated: 2026-06-06*
*Bugs cataloged: 18+ | Fixes applied: 15+*
