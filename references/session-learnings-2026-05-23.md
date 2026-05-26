# Session Learnings — 2026-05-23

## Root Cause: Server-Side Session Invalidation

**Symptom**: `xhs_publish.py` redirects to `https://creator.xiaohongshu.com/login?source=&redirectReason=401&lastUrl=%2Fpublish%2Fpublish...` — page shows login form even though cookie file shows cookies are valid.

**Root Cause**: Session cookies (`galaxy_creator_session_id`, `access-token-creator.xiaohongshu.com`) were **server-side invalidated**. The server actively revoked the session (likely due to security policy, IP change, or extended inactivity). Local cookie timestamps may show "valid" but the server rejects them.

**Key diagnostic indicators**:
- URL contains `redirectReason=401` → server rejected the session
- Page has 1 button `[登 录]` and 6 inputs → on login page, not creator dashboard
- Cookie `acw_tc` expired (local timestamp check) → security token timed out
- All pages in CDP context redirect to login

**What DOESN'T fix it**:
- Refreshing `acw_tc` token via CDP navigation (server still rejects session)
- Removing expired cookies from file
- Using `browser.contexts[0]` vs `new_context()`

**What DOES fix it**: Re-run `xhs_login.py` to get a fresh session cookie from the server.

**Cookie expiration vs server invalidation**:
- `acw_tc` expires in ~20min locally — server issues new one on visit (fixable without re-login)
- `galaxy_creator_session_id` has no local expiry — server revokes it independently (requires re-login)

## Diagnostic Workflow Used

1. **Read cookie file** — check `expires` timestamps, look for `acw_tc` and `galaxy_creator_session_id`
2. **CDP inspect** — connect to Chrome, add cookies, navigate via `page.evaluate("window.location.href = '...'")`, check page URL after navigation
3. **If URL shows login page** → session is server-side invalid, re-login required
4. **If URL shows creator page** → session valid, problem is page structure/selectors

```python
# CDP inspection template
await page.goto("about:blank")
await asyncio.sleep(1)
await page.evaluate("window.location.href = 'https://creator.xiaohongshu.com/publish/publish?from=menu&target=image';")
await asyncio.sleep(10)
print(f"URL: {page.url}")  # Login page = session invalid
```

## Anti-Detection Rewrite Lesson

**Mistake made**: Rewrote `xhs_publish.py` from scratch using a new `browser_controller.py` abstraction that connected to Chrome with different flags. Lost proven patterns:
- `home-first` navigation before publish URL
- Tab detection + switch logic
- `domcontentloaded` wait + double-navigate
- `_onPublish()` JS call

**Correct approach**: Keep the original `xhs_publish.py` logic intact (it's been battle-tested across many sessions), then inject anti-detection at specific points:
- Replace direct `page.click()` → `human_click_element()` with Bezier mouse movement
- Replace direct `page.type()` → `human_type_text()` with random per-character delay
- Add `random_delay()` between critical steps
- Use `browser.contexts[0]` instead of `browser.new_context()`
- DO NOT override User-Agent
- DO NOT use `add_init_script()`

## Updated Scripts This Session

| Script | Change |
|--------|--------|
| `xhs_publish.py` | Restored original core logic; added Bezier human_click, human_type_text, random_delay; uses browser.contexts[0] |
| `xhs_login.py` | Added Chrome binary path detection for macOS (`/Applications/Google Chrome.app/...`); removed hardcoded User-Agent override |

## CDP vs Python Network Stack

Python's `subprocess` / `urllib` network stack may be routed differently than Chrome's network in sandboxed environments (Hermes agent). When CDP-connected to an existing Chrome:
- **Use**: `page.evaluate("window.location.href = '...'")` — routes through Chrome's network
- **Avoid**: `page.goto()` from Python subprocess — may timeout in sandboxed environments with different network access

This matters for cookie refresh and page navigation in automated workflows.

## Screenshot Locations

All publish/debug screenshots saved to: `/tmp/xhs_screenshots/`

Naming convention:
- `01_home_*` — after home page load
- `02_tab_*` — after tab detection
- `03_uploaded_*` — after image upload
- `05_content_*` — after content fill
- `finish_*` — after publish/draft save
- `inspect_*.png` — CDP diagnostic screenshots
- `fix_result.png` — cookie refresh attempt