# OpenCLI → 小红书发布工作流

> Created: 2026-06-21 | Primary browser tool for all 小红书 automation
> Updated: 2026-06-21 — Added high-level publish command, login verification step, session naming from `opencli doctor`

## Quick Reference

```bash
# OpenCLI prerequisites
opencli doctor                          # Check connectivity (must be green)
opencli skills list                     # List available site adapters

# Discover session/profile alias from `opencli doctor` → Profiles section
# Use the exact alias (e.g., pjmvbend), do not hardcode unless user specifies.

# Browser session lifecycle
opencli browser <session> open <url>    # Open page (creates/owns session)
opencli browser <session> click <ref>   # Click by numeric ref or CSS selector
opencli browser <session> state         # Snapshot DOM with refs
opencli browser <session> bind          # Bind to existing tab
opencli browser <session> unbind        # Release binding
opencli browser <session> close         # Close session
opencli browser <session> tab list      # List bound tabs

# Navigation & interaction
opencli browser <session> click [N]     # Click by numeric ref
opencli browser <session> click "div.foo" # Click by CSS selector
opencli browser <session> fill [N] "文本"  # Fill input (verified)
opencli browser <session> type [N] "文本"  # Type (may trigger autocomplete)
opencli browser <session> select [N] "选项" # Select dropdown
opencli browser <session> upload [N] file1.jpg file2.jpg # Upload files
opencli browser <session> keys Enter    # Keyboard shortcuts
opencli browser <session> scroll down   # Scroll viewport
opencli browser <session> eval "js()"   # Run JS; IIFE to avoid scope conflicts

# Reading state
opencli browser <session> get title     # Page title
opencli browser <session> get url       # Current URL
opencli browser <session> get text [N]  # Element text
opencli browser <session> get value [N] # Input value (verify after type)
opencli browser <session> network       # Capture API responses
opencli browser <session> console       # Read console / JS errors
```

## ⭐ Login Verification (REQUIRED before any flow that needs login)

`opencli doctor` showing **Extension: connected** only proves the Browser Bridge is alive — it does **not** prove Chrome is logged into xiaohongshu.

Run this first:
```bash
opencli browser <session> open "https://www.xiaohongshu.com/user/profile/me"
opencli browser <session> get url
```
If the URL contains `/login?redirectPath=...`, the session is **not logged in**. Stop and ask the user to log in.

## High-Level Publish Command (preferred when logged in)

```bash
opencli xiaohongshu publish "正文内容" \
  --title "标题" \
  --images ./a.jpg,./b.png

# Text-image card mode (creator center 文字配图)
opencli xiaohongshu publish "正文内容" \
  --title "标题" \
  --card-text "第一张\n第二行|||第二张" \
  --card-style "边框"
```

Fail conditions:
- Not logged in → redirects to `/login?redirectPath=...`
- Creator page unavailable
- Images missing for required mode

When any of the above happen, fall back to the detailed UI workflow below.

## Complete UI Publish Flow (fallback when high-level command is not suitable)

### 1. Open Publish Page
```bash
opencli browser <session> open https://creator.xiaohongshu.com/publish/publish
opencli browser <session> wait time 3
```

### 2. Take Initial State
```bash
opencli browser <session> state
# Note: [N] refs for title input, content textarea, image upload, tags, save/draft button
```

### 3. Fill Title
```bash
opencli browser <session> fill <title_ref> "你的标题"
opencli browser <session> get value <title_ref>  # Verify
```

### 4. Fill Content
```bash
opencli browser <session> fill <content_ref> "正文内容..."
```

### 5. Upload Images
```bash
# Method A: Direct upload (works if file input is visible)
opencli browser <session> upload <upload_ref> /path/to/img1.jpg /path/to/img2.jpg

# Method B: If upload fails with "Not allowed" (file input is hidden/visible=false):
# Step 1: Trigger the file input's click via eval to make it accessible
opencli browser <session> eval "document.querySelector('input[type=file]').click()"
# Step 2: Use eval to programmatically set files via DataTransfer
opencli browser <session> eval "(async () => {
  const dt = new DataTransfer();
  const files = ['/path/to/img1.jpg', '/path/to/img2.jpg'];
  for (const f of files) {
    const resp = await fetch(f);
    const blob = await resp.blob();
    const file = new File([blob], f.split('/').pop(), { type: blob.type });
    dt.items.add(file);
  }
  const input = document.querySelector('input[type=file]');
  input.files = dt.files;
  return 'Uploaded ' + input.files.length + ' files';
})()"
# Step 3: Verify files are attached
opencli browser <session> state | grep "compounds"
# Expected: "current":["img1.jpg","img2.jpg",...]
```

**Critical pitfall**: `opencli browser upload` returns `{"code":-32000,"message":"Not allowed"}` when the file input has `visible: false` in the state. This is a Chrome security restriction. Use the eval-based workaround above.

**Important**: After attaching files via eval, always dispatch a `change` event to trigger page upload logic:
```bash
opencli browser <session> eval "document.querySelector('input[type=file]').dispatchEvent(new Event('change', {bubbles:true}))"
```

**Note**: The page may not render image thumbnails even though files are attached (confirmed in `compounds.current`). This is a known React rendering issue on Xiaohongshu's publish page.

### 6. Add Tags
```bash
opencli browser <session> fill <tags_ref> "#情绪树洞 #心灵治愈 #反内耗"
```

### 7. Save Draft (NOT Publish!)
```bash
opencli browser <session> click <draft_btn_ref>
opencli browser <session> state
# Verify: check for success toast/notification
```

## Anti-Patterns & Pitfalls

1. **NEVER click publish** — always save as draft. User reviews and publishes manually.
2. **Always verify after fill** — run `get value` after typing to catch autocomplete/React issues.
3. **Re-state after page changes** — SPAs invalidate refs. Always take fresh `state` after navigation.
4. **Use `fill` over `type` for inputs** — `fill` replaces content; `type` simulates keystrokes (may trigger autocomplete).
5. **`upload` command only works on file inputs**, not on buttons. If you click "上传图片" button first, the upload target will be the button, not the file input. Always specify the file input ref (e.g., `84`) or use `--name`/`--role` to locate it.
6. **Hidden file inputs block upload** — returns `{"code":-32000,"message":"Not allowed"}` when file input has `visible: false`. Use the `eval` + DataTransfer workaround (see Section 5 above). After uploading, dispatch a `change` event.
7. **match_level matters** — after write actions, check `match_level` in response:
   - `exact`: proceed normally
   - `stable`: element drifted softly, still OK
   - `reidentified`: ref was gone, CLI found replacement — double-check you hit the right element
8. **File input may not appear in `state` interactive elements** — use `opencli browser <session> find --css "input[type=file]"` to locate it reliably. Check the `compound` section for file attachment status.
9. **Variable scope conflicts** — page may have `input` / `fileInput` declared globally. Wrap eval JS in an IIFE `(function() { const fi = ...; return fi; })()` to avoid "Identifier has already been declared" errors.
10. **Session may go to `about:blank` after clicks** — if the page becomes blank unexpectedly, navigate back to the publish URL with `open`.

## Session Management

- **Owned sessions**: OpenCLI manages tab lifecycle. Use `opencli browser <name> open`.
- **Bound sessions**: Attach to existing tab. Use `opencli browser <name> bind`. No idle-close timer.
- **Session invalidation**: After a logout or tab close, `opencli browser <name> open` on a new URL to create a fresh session.
- **Multi-step chains**: Use `&&` to chain commands in one shell so refs don't go stale.

Example chain:
```bash
opencli browser pjmvbend state && \
opencli browser pjmvbend fill "3" "标题" && \
opencli browser pjmvbend get value "3"
```

## HyperFrames Integration

For generating 6+配图/videos per post:

1. Content generation → `xhs_content_generator.py`
2. Image/video generation → `xhs_hyperframes_video.py` or HyperFrames CLI
3. Upload to Xiaohongshu → OpenCLI `upload` command

All output saved to `/tmp/xhs_treehole/day_YYYYMMDD/` with manifest.json.

## Image Size Constraints & Workaround

The high-level `opencli xiaohongshu publish` command falls back to base64 DataTransfer injection when the Browser Bridge `setFileInput` is not allowed. Large raw images (~2.5MB total) frequently fail with:
- `code: UNKNOWN, message: 'Image injection failed: No file input found on page'`
- `fetch failed, cause: read ECONNRESET`
- `write EPIPE`

### Fix: pre-compress images with ffmpeg before publishing

```bash
mkdir -p /tmp/xhs_small
ffmpeg -y -i "$src" -vf "scale=640:-2" -q:v 60 "/tmp/xhs_small/$(basename "$src")"
```

For 6 images, this typically yields ~112KB total, which publishes reliably.

### Verified publish commands

```bash
opencli xiaohongshu publish "野原美冴 fun facts" \
  --title "野原美冴的日常小趣事" \
  --images /tmp/xhs_small/cover_01_main.jpg,/tmp/xhs_small/cover_02_embrace.jpg,/tmp/xhs_small/cover_03_enough.jpg,/tmp/xhs_small/cover_04_rest.jpg,/tmp/xhs_small/cover_05_gentle.jpg,/tmp/xhs_small/cover_06_hope.jpg
```

### Post-publish verification

```bash
opencli xiaohongshu creator-notes-summary --limit 3
```
Confirm the new note title, `published_at`, view/like/collect counts, and note ID.

## Pitfalls

- `--images` path failure is usually a size issue, not a path issue.
- `opencli doctor` green only proves the browser bridge is alive, not that Chrome is logged into xiaohongshu.com. Always run the login-verification step first.
- If you see `uploaded 6` from eval but no thumbnails, the state DOM often shows `files=cover_01_main.jpg,...` on the input and `compounds.current` reflects the attachment. A subsequent high-level publish or a manual `change` dispatch is what triggers the actual upload.
- Do NOT use `browser_*` / `computer_use` for Xiaohongshu publishing. OpenCLI owns this path.
- Do NOT hardcode the session alias (`pjmvbend` etc.) across tasks. Read it from `opencli doctor` each session.
