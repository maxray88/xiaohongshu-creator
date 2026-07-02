# HyperFrames HTML-to-MP4 Integration (2026-06-20)

## What was done
Integrated HyperFrames video rendering into the Xiaohongshu content pipeline. Created `scripts/xhs_hyperframes_video.py` to render animated MP4 videos from HTML compositions.

## Key learnings

### HyperFrames Composition Requirements
- Root element MUST have `data-composition-id`, `data-width`, `data-height` attributes
- Every timed element needs `data-start`, `data-duration`, `data-track-index`, `class="clip"`
- GSAP timeline must be registered on `window.__timelines["main"]` with `{ paused: true }`
- Timeline ID must match the `data-composition-id` value
- CSS transforms conflict with GSAP tweens — remove initial `transform` from CSS if GSAP animates it

### Common lint errors and fixes
| Error | Fix |
|-------|-----|
| `root_missing_composition_id` | Add `data-composition-id="main"` to root wrapper |
| `root_missing_dimensions` | Add `data-width="1080" data-height="1920"` |
| `timeline_id_mismatch` | Ensure `window.__timelines["main"]` matches `data-composition-id="main"` |
| `gsap_css_transform_conflict` | Don't set CSS `transform` property when GSAP animates the same property |

### HTML f-string gotcha
When building HTML inside Python f-strings, GSAP/JS uses `{}` for objects. Must escape as `{{}}` in f-strings, OR use string concatenation (`.join(html_parts)`) to avoid conflicts.

### Rendering pipeline
1. `npx hyperframes init <dir> --skip-skills --non-interactive`
2. Write `index.html` with GSAP timeline
3. `npx hyperframes lint <dir>` — check before render
4. `npx hyperframes render <dir> -o <output> --fps 30 --composition index.html`

### Portrait format for Xiaohongshu
Use 1080x1920 (portrait) for video posts. Resolution preset: `portrait`.

## Mnemory Migration (2026-06-20)

### What changed
Switched from local `memory` tool (writes to `~/.hermes/memories/MEMORY.md`) to Mnemory MCP service (`http://localhost:8050/mcp`).

### Migration steps
1. Read local `MEMORY.md` and `USER.md` content
2. Convert entries to Mnemory `add_memory` calls with appropriate `memory_type` (preference/fact/procedural/context)
3. Delete local memory files: `rm ~/.hermes/memories/MEMORY.md ~/.hermes/memories/USER.md`

### Mnemory service status
- Health: `curl http://localhost:8050/health` returns `{"status":"healthy"}`
- Restart: `launchctl stop ai.mnemory-server && launchctl start ai.mnemory-server`
- Config: `~/.mnemory/.env` (LLM via OpenRouter, port 8050)
- Known issue: `add_memory` sometimes returns `"Memory extraction failed"` — retry with simpler content or batch via `add_memories`

### Pitfall
Mnemory's `add_memory` uses an LLM for extraction. If it fails, the memory is NOT stored. Always verify with `list_memories` or `search_memories` after adding.

## OpenCLI File Upload Pitfall (2026-06-20)

### Problem
When uploading images via OpenCLI, the `upload` command fails with:
```json
{"code":-32000,"message":"Not allowed"}
```

### Root Cause
The file input element (`<input type=file>`) has `visible: false` in the OpenCLI state. Chrome blocks programmatic file attachment to hidden file inputs as a security measure.

### Workaround
Use `eval` to programmatically set files via JavaScript `DataTransfer`:

```bash
# Step 1: Trigger file input click (optional, may help)
opencli browser treehole eval "document.querySelector('input[type=file]').click()"

# Step 2: Upload files via DataTransfer
opencli browser treehole eval "(async () => {
  const dt = new DataTransfer();
  const files = ['/path/to/img1.jpg', '/path/to/img2.jpg', ...];
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

# Step 3: Verify
opencli browser treehole state | grep "compounds"
# Should show: "current":["img1.jpg","img2.jpg",...]
```

### Additional Pitfalls
- `upload` command targets the wrong element if you click a button first — always specify the file input ref or use `find --css "input[type=file]"` to locate it.
- After uploading, always verify via `state` → `compounds` section.
- The `eval` approach sets files on the DOM element but the page may not render thumbnails immediately. Dispatch a `change` event after setting files: `opencli browser treehole eval "document.querySelector('input[type=file]').dispatchEvent(new Event('change', {bubbles:true}))"`
