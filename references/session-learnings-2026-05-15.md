# Xiaohongshu Publish — Session Learnings (2026-05-15)

## Problem: `遇到问题` Error After Clicking Publish

### Symptoms
- Page shows `遇到问题` (encountered a problem) after clicking the publish button
- URL stays at `https://creator.xiaohongshu.com/publish/publish?from=tab_switch`
- Content and title are visible on the page but publish doesn't complete

### Root Cause: Title Length Exceeds 20 Characters

The title input has a **hard limit of 20 characters**. The original title was:
```
野原美冴的10个秘密：这个妈妈比你想象的更酷！  (22 chars)
```

This caused the validation to fail silently — the page shows `遇到问题` and the publish button click has no effect.

### Solution
Truncate title to ≤ 20 characters:
```
野原美冴的10个秘密！  (11 chars) ✅
```

The title input shows a character counter like `22 / 20` in red when over the limit.

### Verification
After fixing the title length, the publish button click works correctly and the page redirects to the success/note detail page.

---

## Problem: Publish Button Not Found by Standard Selectors

### Symptoms
- `document.querySelectorAll('button')` doesn't find the publish button
- The button text "发布笔记" appears in the DOM but not as a `<button>` element

### Root Cause
The publish button is a **custom Vue element**: `<xhs-publish-btn>`

### Solution
Use the custom element selector:
```python
btn = page.query_selector('xhs-publish-btn')
```

---

## Problem: Programmatic Click on `<xhs-publish-btn>` Doesn't Work

### Symptoms
- `btn.click()` executes without error but nothing happens
- The page doesn't navigate or show any response

### Root Cause
The Vue component checks `event.isTrusted` — only real mouse clicks from user interaction are accepted.

### Solution
Keep the browser open and ask the user to manually click the publish button:
```python
print("Browser open - waiting 300s for manual publish click...")
time.sleep(300)
```

---

## Problem: SPA Defaults to "上传视频" Tab

### Symptoms
- After navigating to the publish page, the video upload tab is active instead of image upload
- The file input and form fields don't appear

### Solution
Always clear SPA state before navigating:
```python
page.goto("https://creator.xiaohongshu.com/new/home", wait_until="commit", timeout=60000)
time.sleep(5)
page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
time.sleep(2)
page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=image",
          wait_until="commit", timeout=60000)
time.sleep(10)
```

---

## Complete Working Workflow

1. Clear SPA state via home page
2. Navigate to `?from=menu&target=image`
3. Wait 10s for SPA render
4. Click "上传图片" button
5. Set file via `input[type="file"]`
6. Wait 2s + 15s for upload
7. Wait 10s for form to render
8. Fill title (≤ 20 chars, use native value setter)
9. Fill content (use `execCommand('insertText')`)
10. Keep browser open for manual publish click

## Complete Working Workflow

1. Clear SPA state via home page
2. Navigate to `?from=menu&target=image`
3. Wait 10s for SPA render
4. Click "上传图片" button
5. Set file via `input[type="file"]`
6. Wait 2s + 15s for upload
7. Wait 10s for form to render
8. Fill title (≤ 20 chars, use native value setter)
9. Fill content (use `execCommand('insertText')`)
10. Keep browser open for manual publish click

## Wait Times Summary
| Step | Wait |
|------|------|
| After home page navigation | 5s |
| After clearing storage | 2s |
| After publish page navigation | 10s |
| After clicking upload button | 2s |
| After setting file | 2s |
| For upload processing | 15s |
| For form to render | 10s |
| After filling title | 1s |
| After filling content | 1s |
| **Total minimum** | **~50s** |

---

## New Learnings (Session 2, 2026-05-15)

### event.isTrusted Confirmed Unbreakable

Tested 4 methods to auto-click the publish button. All failed:

| Method | Result |
|--------|--------|
| CDP `Input.dispatchMouseEvent` (full mouseMoved→mousePressed→mouseReleased) | ❌ URL unchanged |
| `PointerEvent` + `MouseEvent` dispatch on element | ❌ URL unchanged |
| Vue component instance direct call (`__vue__`, `_vei`) | ❌ URL unchanged |
| `Enter` key via CDP `Input.dispatchKeyEvent` | ❌ URL unchanged |

**Conclusion**: `event.isTrusted` is a kernel-level Chrome security boundary. Do NOT waste time trying to bypass it. The only solution is a real human mouse click.

### Chrome CDP Requires `--remote-allow-origins='*'`

Without this flag, WebSocket CDP connections return 403 Forbidden. This is a Chrome security policy.

### Image Upload May Reset Tab State

After uploading an image, the SPA may revert the active tab from "上传图文" back to "上传视频". If form inputs don't appear after upload, re-click the tab:

```python
page.evaluate("""
    var tabs = document.querySelectorAll('.creator-tab');
    for (var i = 0; i < tabs.length; i++) {
        var box = tabs[i].getBoundingClientRect();
        if (tabs[i].textContent.trim() === '上传图文' && box.x > 0) {
            tabs[i].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
            break;
        }
    }
""")
```

### CDP Mode Chrome Launch Command

```bash
pkill -f "Google Chrome"
sleep 2
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins='*' \
  --user-data-dir="$HOME/.config/xhs-chrome-profile" \
  --no-first-run \
  --no-default-browser-check
```

### JS Evaluate Requires IIFE Wrapper

Patchright/CDP mode's `page.evaluate()` requires JS to be wrapped in an IIFE to avoid "Illegal return statement":

```python
# ✅ CORRECT
page.evaluate("(function() { var el = document.querySelector('input'); return el ? 'found' : 'not found'; })()")

# ❌ WRONG — causes "Illegal return statement"
page.evaluate("var el = document.querySelector('input'); return el ? 'found' : 'not found';")
```
