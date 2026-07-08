# Xiaohongshu Publish — CDP Mode with Patchright

## Overview

**CDP mode** (`connect_over_cdp`) connects to a real, already-running Chrome instance instead of launching a new one. This is the most anti-detection-friendly approach because the browser has real user data (history, extensions, cookies, real fingerprint).

**Reference**: [当浏览器自动化遇上平台风控：一次小红书发布工具的反检测实战](https://yousali.com/posts/20260213-browser-automation-anti-detection/)

## Architecture

```
Real Chrome (CDP port 9222) ← WebSocket → Patchright sync_playwright → connect_over_cdp()
```

## Prerequisites

### 1. Start Chrome with CDP Port

```bash
# Kill existing Chrome first (macOS single instance mechanism)
pkill -f "Google Chrome"
sleep 2

# Create dedicated profile
mkdir -p ~/.config/xhs-chrome-profile

# Start Chrome with CDP
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins='*' \
  --user-data-dir="$HOME/.config/xhs-chrome-profile" \
  --no-first-run \
  --no-default-browser-check
```

**Critical**: Chrome must be **fully quit** (Cmd+Q) before starting. macOS merges new Chrome instances into existing ones, discarding command-line flags.

**Critical**: `--remote-allow-origins='*'` is required for WebSocket CDP connections. Without it, WebSocket handshake returns 403 Forbidden.

### 2. Verify CDP Port

```bash
lsof -i :9222
# Should show Chrome listening on port 9222
```

### 3. Install Dependencies

```bash
PYTHON=python3  # Python 3.11 required
$PYTHON -m pip install patchright websocket-client
```

## The 8 Pitfalls (and Solutions)

### Pitfall 1: Chrome Refuses CDP on Default Profile
**Cause**: Chrome 136+ security policy blocks remote debugging on default profile.
**Fix**: Use `--user-data-dir` pointing to a non-default directory.

### Pitfall 2: Chrome Instance Merging
**Cause**: macOS Chrome is single-instance. New launch merges into existing process, discarding flags.
**Fix**: `pkill -f "Google Chrome"` before starting. Verify with `lsof -i :9222`.

### Pitfall 3: WebSocket 403 Forbidden
**Cause**: Chrome requires `--remote-allow-origins='*'` for WebSocket CDP connections.
**Fix**: Add `--remote-allow-origins='*'` to Chrome launch command.

### Pitfall 4: Patchright HTTP Discovery Returns 400
**Cause**: Patchright 1.58+ requests `/json/version/` (trailing slash). Chrome 144 returns 400.
**Fix**: Manually resolve WebSocket URL:

```python
import http.client
import json
from urllib.parse import urlparse

def resolve_cdp_ws_url(endpoint):
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9222
    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request("GET", "/json/version")  # NO trailing slash!
    resp = conn.getresponse()
    if resp.status == 200:
        data = json.loads(resp.read())
        ws_url = data.get("webSocketDebuggerUrl")
        if ws_url:
            return ws_url
    return endpoint
```

### Pitfall 5: `urllib.request` Returns 502 on localhost
**Cause**: System proxy (ClashX, Surge, etc.) intercepts localhost requests.
**Fix**: Use `http.client.HTTPConnection` directly (bypasses system proxy).

### Pitfall 6: `new_context()` Causes ERR_CONNECTION_CLOSED
**Cause**: CDP mode's new context has isolated network stack missing DNS/TLS config.
**Fix**: Use `browser.contexts[0]` (existing context). Inject cookies via `ctx.add_cookies()`.

### Pitfall 7: `add_init_script()` Causes ERR_CONNECTION_CLOSED
**Cause**: `add_init_script()` uses CDP `Page.addScriptToEvaluateOnNewDocument`, conflicting with Chrome's own initialization.
**Fix**: Skip `add_init_script()` in CDP mode. Real Chrome already has `navigator.webdriver === undefined`.

### Pitfall 8: Overriding User-Agent Causes Fingerprint Mismatch
**Cause**: HTTP headers UA differs from `navigator.userAgent` / Client Hints.
**Fix**: Don't override UA in CDP mode.

## Complete Working Script

See `scripts/xhs_publish_cdp_sync.py` for the full implementation.

### Key Code Patterns

```python
from patchright.sync_api import sync_playwright

with sync_playwright() as pw:
    ws_url = resolve_cdp_ws_url("http://127.0.0.1:9222")
    browser = pw.chromium.connect_over_cdp(ws_url)
    
    ctx = browser.contexts[0]  # NOT new_context()
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    
    page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=image",
              wait_until="commit", timeout=60000)
    time.sleep(10)
    
    # Upload, fill form, keep browser open for manual publish click
    time.sleep(600)
```

### JS Evaluate Wrapper Pattern

**Always wrap JS in IIFE** for Patchright/CDP mode:

```python
# ❌ WRONG — causes "Illegal return statement"
page.evaluate("""
    var el = document.querySelector('input');
    if (el) return 'found';
    return 'not found';
""")

# ✅ CORRECT — IIFE wrapper
page.evaluate("""
    (function() {
        var el = document.querySelector('input');
        if (el) return 'found';
        return 'not found';
    })()
""")
```

## Comparison: launch() vs connect_over_cdp()

| Feature | `launch()` | `connect_over_cdp()` |
|---------|-----------|---------------------|
| Browser instance | New, clean | Real user's Chrome |
| `navigator.webdriver` | `true` (detectable) | `undefined` (real) |
| Cookies/bookmarks | None (must inject) | Real user data |
| DNS resolution | May fail (Chromium 147) | Works (real Chrome) |
| `new_context()` | ✅ Works | ❌ ERR_CONNECTION_CLOSED |
| `add_init_script()` | ✅ Works | ❌ ERR_CONNECTION_CLOSED |
| UA override | ✅ Recommended | ❌ Don't override |
| Anti-detection | Moderate | Best |

## When to Use CDP Mode

- **Use CDP mode** when you need maximum anti-detection (real browser fingerprint)
- **Use `launch()`** when you need isolated contexts (multiple accounts) or don't have Chrome running

## Confirmed Working (2026-05-15)

All steps verified with Patchright 1.59.1 + Chrome 148 + CDP mode:

1. ✅ Connect to Chrome via CDP
2. ✅ Inject 17 cookies
3. ✅ Navigate to publish page (target=image)
4. ✅ Active tab: 上传图文
5. ✅ Click "上传图片" button
6. ✅ Upload image via set_input_files()
7. ✅ Form renders: titleInput=true, editor=true, publishBtn=true
8. ✅ Fill title: "你以为你了解野原美冴？" (11 chars)
9. ✅ Fill content: 236 chars via execCommand
10. ✅ Find publish button: xhs-publish-btn at (588, 628)
11. ✅ Browser kept open for manual publish click

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `DevTools remote debugging requires non-default data directory` | Add `--user-data-dir` |
| Port 9222 not listening | Chrome instance merged — kill Chrome and restart |
| `Unexpected status 400` from Patchright | Use manual `resolve_cdp_ws_url()` |
| `HTTP Error 502` from urllib | System proxy — use `http.client` |
| `ERR_CONNECTION_CLOSED` | Don't use `new_context()` or `add_init_script()` |
| `Illegal return statement` in evaluate | Wrap JS in `(function(){...})()` |
| `navigator.webdriver` is `true` | CDP mode with real Chrome should be `undefined`. Don't use `add_init_script()`. |
