# Session Learnings — 2026-05-16

## Key Technical Findings

### 1. Image Upload is the Form Trigger

The publish page is a Single Page App (SPA) that **always defaults to the "上传视频" tab**. The image upload form (title input + editor + publish button) only appears **AFTER** an image is uploaded via the file input. This is a critical sequence: image upload → form appears → title/content can be filled.

```python
# Navigate to publish page
await page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=image",
               wait_until="commit", timeout=60000)
await asyncio.sleep(12)  # Wait for full SPA render

# Upload image via file input — this TRIGGERS the image form to appear
file_input = page.locator('input[type="file"]').first
await file_input.set_input_files(image_paths)
await asyncio.sleep(20)  # Wait for upload + form render

# NOW title input and editor are visible
```

### 2. Publish Button Selector is Critical

The publish button is a custom element (`xhs-publish-btn`) that **cannot be clicked programmatically** due to `event.isTrusted` security checks. All programmatic methods fail (Playwright click, CDP MouseEvent, JS dispatchEvent, etc.). Only a real human mouse click works.

### 3. Title Length is a Hard Limit

The title input has a **hard limit of 20 characters**. Going over causes a silent `遇到问题` error and the publish button won't work.

### 4. Tippy Popups Block Clicks

After filling the form, a `tippy-1` popup may appear and intercept pointer events. This must be dismissed before clicking the publish button.

### 5. "遇到问题" Banner is Often Stale

The `<div class="problem">` element at the top of the page is a persistent notification from previous failed attempts. It does NOT necessarily indicate a current error. Check title length separately.

### 6. Two Sets of Tabs

The SPA has duplicate tab elements — one hidden (off-screen) and one visible. Both can have `active` class simultaneously. Don't rely on tab active state to determine which content is shown.

### 7. Content with Special Characters

When content contains backticks, `${}`, newlines, or Chinese quotes, write to `/tmp/content.txt` first to avoid JS string escaping issues.

### 8. Keep Browser Open for Manual Publish Click

After filling the form, keep the browser open and ask the user to manually click the publish button. Activate Chrome repeatedly to keep it in foreground:

```python
import subprocess
subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'],
              timeout=5, capture_output=True)
```

### 9. Patch Tool Can Leak XML Artifacts

The `patch` tool can leak `</parameter>` into files. Always verify file contents after patching.

### 10. Content File Workflow

When creating content for publishing:
1. Write content to a temp file first: `/tmp/xhs_content_<topic>.txt`
2. Use `CONTENT=$(cat /tmp/xhs_content_<topic>.txt)` to load into variable
3. Pass `--content "$CONTENT"` to the publish script
4. The content file should include hashtags at the end — they'll be rendered as plain text in the editor
5. For content with special characters (backticks, `${}`, Chinese quotes), the file approach avoids JS string escaping issues

### 11. Cover Image Generation with Pillow

When no stock photo API key is available, use Pillow to generate a cover image:
- Dimensions: 1080x1440 (3:4 ratio for Xiaohongshu)
- Warm gradient background (orange to pink/yellow)
- White title box at top (~120px), white CTA box at bottom (~120px)
- Use system Chinese fonts: `/System/Library/Fonts/PingFang.ttc` or `STHeiti Medium.ttc`
- Save as PNG to `/tmp/xhs_covers/cover_<topic>.png`
- The image doesn't need to be photorealistic — a clean gradient with text works as a cover

### 12. CDP Connection Stability

- Chrome must be running with `--remote-debugging-port=9222 --user-data-dir=~/.config/xhs-chrome-profile`
- CDP URL is stored in `/tmp/xhs_cdp_url.txt`
- If `curl http://127.0.0.1:9222/json/version` times out, Chrome may need to be restarted
- The `xhs_publish.py` script connects via `p.chromium.connect_over_cdp(cdp_url)`
- Multiple Chrome renderer processes are normal — the browser process is the one that matters

### 13. Pillow Cover Image Generation

When no stock photo API is available, generate covers with Pillow:
- 1080x1440, warm gradient (orange→pink), white title box top, white CTA box bottom
- Chinese fonts: PingFang.ttc, STHeiti Medium.ttc, Hiragino Sans GB.ttc
- Save to `/tmp/xhs_covers/cover_<topic>.png`
- See `references/pillow-cover-image-template.md` for full code template
- Run with Hermes venv Python (Pillow pre-installed)

### 14. Publish Timeout Handling

The publish script waits 300s for manual click. If timeout expires:
- The form data is still filled in the browser
- Re-run the script with `--title` and `--content` to re-fill, OR
- Simply ask the user to click the publish button in the still-open Chrome window
- The browser window remains open after timeout — no need to re-navigate