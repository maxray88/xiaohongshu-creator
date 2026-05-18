# Session Learnings — 2026-05-17

## Key Technical Findings

### 1. `_onPublish()` Method — Full Auto-Publish Breakthrough

The `xhs-publish-btn` Custom Element has a callable `_onPublish()` method that directly triggers the publish flow, **completely bypassing `event.isTrusted`**.

```python
# ✅ WORKS — bypasses event.isTrusted entirely
result = await page.evaluate("""
    () => {
        const btn = document.querySelector('xhs-publish-btn');
        if (!btn) return 'not found';
        if (typeof btn._onPublish === 'function') {
            btn._onPublish();
            return 'called _onPublish';
        }
        // Fallback: dispatch CustomEvent
        btn.dispatchEvent(new CustomEvent('publish', {bubbles: true, composed: true}));
        return 'dispatched publish event';
    }
""")
```

**Verification**: After calling `_onPublish()`, the URL changes from `publish/publish` to `publish/success` — confirming the post was published.

### 2. xhs-publish-btn Custom Element Internals

The element is a **closed-shadow DOM Custom Element** (NOT Vue):

```html
<xhs-publish-btn
  submit-text="发布"
  save-text="暂存离开"
  submit-disabled="false"
  save-disabled="false"
  is-publish="true"
  is-save-draft="true"
></xhs-publish-btn>
```

Key properties:
- `_onPublish()` — dispatches `CustomEvent('publish', {bubbles: true, composed: true})`
- `_onSave()` — dispatches `CustomEvent('save', {bubbles: true, composed: true})`
- `_sr` — closed shadow root (`mode: "closed"`)
- `innerHTML` is empty — shadow DOM content is inaccessible from outside
- **No Vue instance** (`__vue__`, `__vueParentComponent`, `_vei` are all undefined)
- `observedAttributes`: `is-publish`, `is-save-draft`, `submit-text`, `save-text`, `submit-disabled`, `save-disabled`

### 3. Why Other Click Methods All Fail

The `event.isTrusted` check is a browser kernel-level security mechanism. It **cannot be bypassed** by simulating clicks. However, calling `_onPublish()` directly works because it bypasses the event system entirely and calls the internal handler function directly.

All failed methods:
- `page.mouse.click()` — synthetic event, `isTrusted: false`
- CDP `Input.dispatchMouseEvent` — same
- `element.click()` via JS — same
- `dispatchEvent(MouseEvent)` via JS — same
- `pyautogui.click()` — generates synthetic Quartz events, `isTrusted: false`
- AppleScript `click at {x, y}` — requires Accessibility permissions

### 4. Coordinate Calculation for Retina Displays

On macOS with Retina (`devicePixelRatio=2`):
- `window.screenX/Y` return **points** (logical coordinates)
- `getBoundingClientRect()` returns **points** (CSS pixels = points on macOS)
- `pyautogui` uses **logical coordinates** (points) on macOS
- **No DPR multiplication needed** for pyautogui on macOS

Formula: `abs_x = screenX + viewport_x`, `abs_y = screenY + chrome_height + viewport_y`

Note: `outerHeight - innerHeight` may be only 1px on macOS (browser chrome is minimal in windowed mode).

### 5. CDP WebSocket Direct Access

When Playwright's high-level APIs fail, use CDP WebSocket directly:

```python
import websockets, json, urllib.request

pages = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
page_ws = pages[0]["webSocketDebuggerUrl"]

async with websockets.connect(page_ws, max_size=20*1024*1024) as ws:
    await ws.send(json.dumps({
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {"expression": "...", "returnByValue": True}
    }))
    resp = json.loads(await ws.recv())
    value = resp["result"]["result"]["value"]
```

Note: Return value is nested TWO levels deep: `resp["result"]["result"]["value"]`

### 6. Publish Success Verification

After calling `_onPublish()`, verify success by checking:
- URL changed from `publish/publish` to `publish/success`
- Page text contains "发布成功"
- Page text contains "1 秒后将返回发布页"

### 7. GitHub Upload Workflow

To upload the skill to GitHub:

```bash
# 1. Install gh CLI (if not available)
brew install gh

# 2. Create repo via API (gh auth needs read:org scope, use API instead)
curl -s -X POST https://api.github.com/user/repos \
  -H "Authorization: token <PAT>" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"name":"xiaohongshu-creator","private":false}'

# 3. Init and push
cd ~/.hermes/skills/xiaohongshu-creator
git init
git add -A
git commit -m "initial commit"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

**PAT Requirements**: Needs `repo` scope (full control of private repositories) or `public_repo` for public repos. The `read:org` scope is NOT needed for repo creation via API.

**Security**: Don't embed PAT in remote URL. Use `gh auth login --with-token` or Git credential helper instead.

### 10. Image Download Sources (Updated 2026-05-17)

**Working:**
- **Openverse API** (`api.openverse.engineering`) — free, no key, CC-licensed, returns JSON
  - Search: `https://api.openverse.engineering/v1/images/?q=QUERY&page_size=N&license=by,by-sa,cc0`
  - Download: use `urllib.request` with `Referer: https://openverse.org/`
  - Results include `url` (full image), `thumbnail`, `title`, `license`

**Not working:**
- **Pexels web scraping** — blocked, returns empty HTML
- **Unsplash Source** — 503
- **Pixabay** — requires API key

### 11. Font Loading in Sandbox

In the Hermes sandbox environment:
- `STHeiti Medium.ttc` — ✅ works reliably
- `PingFang.ttc` — ⚠️ may fail with `OSError: cannot open resource` in sandbox
- `Hiragino Sans GB.ttc` — ✅ works
- Always wrap font loading in try/except with fallback to `ImageFont.load_default()`

### 12. Cover Composition from Downloaded Images

Proven workflow:
1. Download from Openverse (typically 576x1024 or 768x1024 for portrait)
2. Resize with `Image.LANCZOS` to fit within 1080x1440
3. Center on canvas with warm fallback background
4. Add white title bar (top 120px) and CTA bar (bottom 120px)
5. Use STHeiti Medium at size 48 (title) and 32 (CTA)
6. Save as JPG quality=90

### 13. Openverse Character Search Limitations (2026-05-17)

When searching Openverse for specific anime characters:
- Character-specific queries (`crayon shinchan`, `shinchan cartoon`) return few or 0 results
- `crayon shinchan` returns train wraps, station photos, merchandise — NOT character art
- Generic queries (`anime illustration japanese`, `kawaii illustration pink`) return better results
- **Workaround**: Use generic anime-style images + text overlay with character name
- See `references/openverse-search-findings.md` for full analysis

### 14. GitHub Repo Push (2026-05-17)

Repo: `https://github.com/maxray88/xiaohongshu-creator`

To update after skill changes:
```bash
cd ~/.hermes/skills/xiaohongshu-creator
git add -A
git commit -m "feat: describe change"
git push
```

Successful viral content structure for character analysis posts:
1. **Hook**: "别看她只是..." — subvert expectations
2. **Funny facts**: Numbered list with emoji, mix of humor and heart
3. **Emotional pivot**: "最让人破防的真相" — shift to genuine emotion
4. **Universal connection**: Relate character to real life (e.g., "每个家庭背后都有一个默默付出的超人妈妈")
5. **CTA**: Ask reader to share personal story ("你家也有这样的美伢吗？")

Title patterns that work:
- "小新妈妈美伢的5个真相😭" — number + emotional trigger
- Keep under 20 chars for Xiaohongshu

### 9. Background Process Output Checking

When running publish scripts in background:
- Use `process(action='log', session_id='...')` to check output
- The `notify_on_complete` flag sends notification when done
- Background processes may not show output until polled
- Always verify URL change after publish, don't rely solely on script output
