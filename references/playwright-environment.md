# Xiaohongshu Creator Platform — Technical Reference

## Playwright Environment

- **Python**: `/Users/maochundong/.hermes/hermes-agent/venv/bin/python3`
- **Playwright**: v1.59.0 with Chromium
- **Key packages**: `playwright`, `Pillow` (for test image generation)

## Browser Launch Configuration

```python
browser = p.chromium.launch(headless=False, args=[
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
])
context = browser.new_context(
    viewport={"width": 1280, "height": 900},
    locale="zh-CN",
    timezone_id="Asia/Shanghai",
)
```

## Page Load Behavior

The creator platform is a SPA (React-based) that:
1. Loads a minimal HTML shell (~50KB)
2. Fetches JS bundles from CDN
3. Renders the UI client-side
4. Can take 5-10 seconds to fully render

**Workaround**: Use `wait_until="commit"` for navigation, then `time.sleep(8)` for SPA render.

## Publish Page Structure

### Tabs
The publish page has 4 tabs in the header:
- `上传视频` (upload video) — default active tab
- `上传图文` (upload image/text) — **this is what we need**
- `写长文` (long article)
- `发播客` (podcast)

Tab selector: `.creator-tab`
Click method: `page.evaluate()` with JS (Playwright click may fail due to viewport issues)

### File Input
- Video tab: `input[type="file"]` with `accept=.mp4,.mov,.flv,...`
- Image tab: `input[type="file"]` with `accept=.jpg,.jpeg,.png,.webp`
- The file input is hidden — use `set_input_files()` directly (no need to click)

### Form Elements (after image upload)
- **Title input**: `input[placeholder*="填写标题"]` (class: `d-text`)
  - Placeholder: "填写标题会有更多赞哦"
  - Use JS `nativeInputValueSetter` + `dispatchEvent` for React compatibility
- **Content editor**: `.tiptap.ProseMirror` (contenteditable div)
  - Use `document.execCommand('insertText', false, text)` for ProseMirror compatibility
- **Publish button**: `button` with inner text "发布"
  - Use JS click: `page.evaluate()` to find and click

### Key Selectors Summary
| Element | Selector | Method |
|---------|----------|--------|
| Image tab | `.creator-tab:has-text("上传图文")` | JS click |
| File input | `input[type="file"]` | `set_input_files()` |
| Title | `input[placeholder*="填写标题"]` | JS value setter |
| Content | `.tiptap.ProseMirror` | JS `execCommand` |
| Publish | `button` with text "发布" | JS click |

## Publish Page URL

Use the official image publish URL:
```
https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image
```

## SPA State Reset (CRITICAL)

The SPA remembers the last-active tab in localStorage. To ensure the image tab loads correctly:

```python
# 1. Navigate to home first
page.goto("https://creator.xiaohongshu.com/new/home", wait_until="commit", timeout=60000)
time.sleep(5)
# 2. Clear SPA state
page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
time.sleep(2)
# 3. Navigate to publish URL
page.goto(PUBLISH_URL, wait_until="commit", timeout=60000)
time.sleep(10)
```

## Tab Switching — CRITICAL

There are **5+ duplicate `.creator-tab` elements** in the DOM (some hidden/off-screen). Filter by visibility:

```javascript
var tabs = document.querySelectorAll('.creator-tab');
for (var tab of tabs) {
    var rect = tab.getBoundingClientRect();
    if (tab.innerText.includes('上传图文') && !tab.classList.contains('active')
        && rect.x > 0 && rect.y > 0 && rect.width > 0) {
        tab.click();
        break;
    }
}
```

## Publish Button — Known Issue

The publish button is `<xhs-publish-btn>`, a custom Vue 3 component — **NOT** a standard `<button>`. It does NOT respond to programmatic clicks (checks `event.isTrusted`).

**All click methods FAIL**: `element.click()`, `dispatchEvent`, `page.mouse.click()`, CDP `Input.dispatchMouseEvent`, keyboard shortcuts.

**Workaround**: Fill form programmatically, then instruct user to manually click "发布" in the browser. Scroll `.publish-page` container to make button visible: `container.scrollTop = 200`.

## Common Pitfalls

1. **SPA not rendering**: Wait 8+ seconds after navigation
2. **Tab not clickable**: Use JS click; filter by `rect.x > 0` (multiple duplicate tabs exist)
3. **React inputs not updating**: Use `nativeInputValueSetter` + `dispatchEvent`
4. **ProseMirror not accepting type**: Use `document.execCommand('insertText')`
5. **File input hidden**: Don't try to click it, use `set_input_files()` directly
6. **Separate Chrome instance**: Playwright opens a NEW Chrome window
7. **Session expires**: Cookies last ~30 days, re-run `xhs_login.py` when expired
8. **Image upload timing**: Wait 2 seconds after `set_input_files()` before proceeding — the upload needs time to process
9. **Publish button not responding**: `<xhs-publish-btn>` checks `event.isTrusted` — manual click required
10. **execute_code timeout**: Run `xhs_publish.py` via `execute_code` with `timeout=300`, NOT via `terminal` (120s too short)

## Python Triple-Quoted JS Strings — CRITICAL

When using `page.evaluate('''...''')` with Python triple-quoted strings:

**WRONG** — `\n` becomes an actual newline in the JS string literal, causing syntax errors:
```python
page.evaluate('''() => {
    const lines = text.split('\n');  // ← Python converts \n to real newline → JS syntax error
}''')
```

**RIGHT** — Use `\\n` (Python produces literal `\n` characters):
```python
page.evaluate('''() => {
    const lines = text.split('\\n');  // ← Python produces \n → JS sees correct escape
}''')
```

**ALTERNATIVE** — Use `String.fromCharCode(10)` to avoid the issue entirely:
```python
page.evaluate('''() => {
    const lines = text.split(String.fromCharCode(10));
}''')
```

**Regex in JS**: Same issue applies. Use `\\d` not `\d` in Python triple-quoted JS:
```python
page.evaluate('''() => {
    const hasDate = lines.some(l => /\\d{4}年/.test(l));  // ✓
}''')
```

## Creator Platform Page Structure (Discovered)

### Note Manager (`/new/note-manager`)
- Note cards: `div.note` (exact class match, NOT `[class*="note"]` which also matches `notes-container`)
- Stats order: exposure, likes, comments, (unknown), saves — as plain numbers
- Date format: `发布于 2026年05月13日 20:15`
- Actions per note: 权限设置, 置顶, 编辑, 删除

### Inspiration Page (`/new/inspiration`)
- Topic format in page text:
  ```
  话题名称
  X万人参与 · X亿次浏览
  点赞数
  示例笔记标题
  点赞数
  示例笔记标题
  ```
- Topics do NOT have `#` prefix in the raw text
- Category labels: 美食, 美妆, 时尚, 出行, 知识, 兴趣爱好

### Home Page (`/new/home`)
- Dashboard metrics in "笔记数据总览" section
- Account stats: 关注数, 粉丝数, 获赞与收藏
- Data updates hourly ("数据小时更新，暂未生成分析")

## Patch Tool Artifact Leakage — WARNING

The `skill_manage(action='patch')` tool uses XML internally (`<parameter>`, `</parameter>`).
In rare cases, these XML tags can leak into the patched file content, especially
when the patch boundary is near a line break. Always verify patched files don't
contain `</parameter>` or similar XML artifacts.
