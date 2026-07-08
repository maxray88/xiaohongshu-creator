# Draft Save from Manifest (2026-06-24+)

> Pattern: use a pre-generated `manifest.json` to save a Xiaohongshu draft via `opencli xiaohongshu publish --draft true`.

## Manifest format (split as of 2026-06-27+)

`manifest.json` now holds only **deck/structural** fields (images + metadata). Editorial content (body) moved to a sibling `post_data.json`. Older manifests from ≤ 2026-06-23 still had `body` inside `manifest.json`; new jobs write it separately.

**`manifest.json`** (used for: publish orchestration, image list, tag list, palette, structural metadata):
```json
{
  "date": "2026-06-27",
  "day_num": 24,
  "title": "当代年轻人的精神状态实录",
  "series": "week4-当代年轻人精神状态",
  "design_ref": "open-design:card-xiaohongshu",
  "renderer": "html-fallback",
  "image_count": 6,
  "image_size": "1080x1440",
  "images": [
    "/tmp/xhs_treehole/day_20260627/images/cover_01_main.jpg",
    "/tmp/xhs_treehole/day_20260627/images/cover_02_card1.jpg",
    "/tmp/xhs_treehole/day_20260627/images/cover_03.jpg",
    "/tmp/xhs_treehole/day_20260627/images/cover_04.jpg",
    "/tmp/xhs_treehole/day_20260627/images/cover_05.jpg",
    "/tmp/xhs_treehole/day_20260627/images/cover_06.jpg"
  ],
  "tags": ["#情绪树洞", "#心灵治愈", "#反内耗", "#精神状态", "#当代年轻人"],
  "card_structure": [...],
  "palette": ["柔粉→米白", "暖橙→淡奶", "深蓝→暮光紫", "浅绿→暖白"]
}
```

**`post_data.json`** (sibling, used for: body text + subtitle + CTA):
```json
{
  "title": "当代年轻人的精神状态实录",
  "subtitle": "白天是成年人的体面，夜里是关灯后的小崩溃。",
  "date": "2026-06-27",
  "day_num": 24,
  "body": "白天上班：成年人的体面，一点不乱。\n晚上关灯：脑子像开了八个网页，全部卡死。\n…",
  "tags": ["#情绪树洞", "#心灵治愈", "#反内耗", "#精神状态", "#当代年轻人"],
  "cover_image": "...",
  "all_images": [...],
  "image_count": 6,
  "cta": "你的精神状态，今天到哪一格？（A 满格 / B 还行 / C 靠咖啡 / D 别问）评论区见～",
  "word_count": 322
}
```

Older schemas (≤ 2026-06-23) embedded `body` directly inside `manifest.json`. The recipes below read both files with a fallback chain so they keep working across the schema split.

## Draft-save command

```bash
# Read manifest + post_data, then save draft
M="/tmp/xhs_treehole/day_20260627/manifest.json"
PD="${M%/*}/post_data.json"
PC="${M%/*}/post_content.md"

TITLE=$(python3 -c "import json; print(json.load(open('$M'))['title'])")
TAGS=$(python3 -c "import json; d=json.load(open('$M')); print(' '.join(d['tags']))")
IMAGES=$(python3 -c "import json; d=json.load(open('$M')); print(','.join(d['images']))")

# body: post_data.json['body'] → post_content.md → manifest['body']
if [ -f "$PD" ] && grep -q '"body"' "$PD" 2>/dev/null; then
  BODY=$(python3 -c "import json; print(json.load(open('$PD'))['body'])")
elif [ -f "$PC" ]; then
  BODY=$(tail -n +3 "$PC")
else
  BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d.get('body',''))")
fi

FULL_BODY="${BODY}

${TAGS}"

# ⚠️ 2026-07-01 pitfall: DO NOT use --window background with the publish command.
# It causes "Image injection failed: No file input found on page" because
# the playwright file-input finder can't locate the upload element in a
# backgrounded browser window.
opencli xiaohongshu publish "$FULL_BODY" \
  --title "$TITLE" --images "$IMAGES" \
  --draft true --site-session ephemeral \
  -f yaml 2>&1 | tail -20
```

> For legacy manifests where `body` is still embedded in `manifest.json`, the `.get('body','')` fallback covers it without branching.

## Verify draft saved

```bash
opencli xiaohongshu drafts -f yaml
```

Expected output shows the new draft at rank 1:
```yaml
- rank: 1
  id: s:50597562-aad6-404c-ab78-7964b3534fe5
  type: image
  title: 领导画饼？清醒一点
  images: 6
```

## Open a specific draft for review

```bash
opencli xiaohongshu draft-open <draft_id>
```

## Clear drafts (when needed)

```bash
opencli xiaohongshu draft-clear
```

## Validation Note (2026-07-08)

**Updated validation — 2026-07-08 execution confirms the draft-save pattern works with the high-level `opencli xiaohongshu publish --draft true` command, with the new v2 manifest schema (mint_cream palette):**

- **Manifest schema**: Today's `manifest.json` (day_20260708_v2) uses the new v2 schema with `body` field directly in manifest (not split into post_data.json). The fallback logic handled this seamlessly. Key v2 fields: `version: "v2"`, `palette: "mint_cream"`, `differentiation` object with color_scheme/layout/typography/watermark details, `series`, `day_theme`.
- **Content generation pipeline**: HTML cards generated from `content.md` template (6 cards: cover, scene, insight, method, healing, CTA) → Playwright rendering to JPG (1080×1440) → all 6 images under 150KB (max 123KB, total 633KB). **No compression needed this run** — but the compression check step remains mandatory.
- **`--window background`**: Omitted per Mistake #5 fix. Command succeeded.
- **Login verification**: `opencli xiaohongshu whoami -f yaml` confirmed `logged_in: true`, username `静坐着呢的情绪树洞` before publish.
- **Draft verification**: `opencli xiaohongshu drafts -f yaml` confirmed draft ID `s:cbefa82e-295a-4d0b-94c1-4f89a193115b` (rank 1), 6 images, matching title.
- **Reporting**: Explicit success report emitted (not `[SILENT]`), matching the non-silent cron contract.

Successful return signature:
```yaml
- status: "✅ 暂存成功"
  detail: '"不必为所有人的情绪买单" · 6张图片 · 保存成功'
```

### v2 Manifest Schema (mint_cream palette, 2026-07-08)
The new v2 manifest includes these additional fields that the draft-save script should be aware of:
```json
{
  "version": "v2",
  "palette": "mint_cream",
  "differentiation": {
    "color_scheme": "mint_cream (薄荷绿→暖白)，与昨日 orange_cream 区分",
    "layout": "圆润卡片(36px)，大量留白，手写感排版",
    "typography": "主标题 108px，正文 42px，行高 1.85，更大留白",
    "watermark": "字号 26px，不透明度 0.7，薄荷灰绿"
  },
  "series": "情绪树洞 · 夜间差异化版",
  "day_theme": "情绪边界 · 温柔放下"
}
```

The script should still use the same fallback logic for `body` (post_data.json first, then manifest.get('body','')) since v2 manifests include body directly.

## Validation Note (2026-07-07)

**Updated validation — 2026-07-07 execution confirms the draft-save pattern works with the high-level `opencli xiaohongshu publish --draft true` command, with critical image compression requirement:**

- **Manifest schema**: Today's `manifest.json` (day_20260707) contained the `body` field directly (older schema). The fallback logic (`post_data.json` first, then `manifest.get('body','')`) handled this seamlessly. Sibling `post_data.json` also existed with identical body content.
- **Image sizes**: Two images exceeded 150KB (cover_04_action: 168,957 bytes; cover_06_cta: 172,681 bytes). Compressed both with `ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT` → ~12-13KB each. Total payload after compression ~0.56MB. **Compression step is critical** — without it, upload fails with "Image injection failed" or payload size errors.
- **`--window background`**: **FAILED this run** with `"Image injection failed: No file input found on page. Debug screenshot: /tmp/xhs_publish_upload_debug.png"`. This confirms Mistake #5 is real and the 2026-07-06 success with `--window background` was conditional (possibly page state or timing). **Mandatory fix: omit `--window background`** — the command runs in seconds and does not steal focus.
- **Login verification**: `opencli xiaohongshu whoami -f yaml` confirmed `logged_in: true`, username `静坐着呢的情绪树洞` before publish.
- **Draft verification**: `opencli xiaohongshu drafts -f yaml` confirmed draft ID `s:1cc4fc87-4293-4df2-bb9a-579c7e592603` (rank 1), 6 images, matching title.
- **Reporting**: Explicit success report emitted (not `[SILENT]`), matching the non-silent cron contract.

Successful return signature:
```yaml
- status: "✅ 暂存成功"
  detail: '"同事不是朋友，保持距离就好" · 6张图片 · 保存成功'
```

## Validation Note (2026-07-06)

Today's successful execution (cron run 2026-07-06) confirms the draft-save pattern works with the high-level `opencli xiaohongshu publish --draft true` command:

- **Manifest schema**: Today's `manifest.json` contained the `body` field directly (older schema). The fallback logic (`post_data.json` first, then `manifest.get('body','')`) handled this seamlessly.
- **Image sizes**: All 6 images were under 150KB (max ~129KB), total ~0.66MB raw. No compression needed. OpenCLI emitted a warning about 0.9MB base64 payload but upload succeeded.
- **`--window background`**: The command included `--window background` and succeeded, contrary to the 2026-07-01 pitfall note. This may indicate a fix in opencli v1.8.4+ or conditional behavior. **Safer practice remains: omit `--window background`** as documented in the recipe.
- **Login verification**: `opencli xiaohongshu whoami -f yaml` confirmed `logged_in: true` with correct username before publish.
- **Draft verification**: `opencli xiaohongshu drafts -f yaml` confirmed draft ID `s:e2bd78f6-7cd7-4a52-9692-fe0b6c473952` with 6 images and matching title.
- **Reporting**: Explicit success report emitted (not `[SILENT]`), matching the non-silent cron contract.

## Notes

- `--draft true` saves to the draft box without publishing.
- Images must be pre-compressed (≤150KB each, total ≤300KB) — see `opencli-xhs-workflow.md` for compression.
- This pattern is preferred over manual UI-based draft save because it avoids DataTransfer injection issues.
- The draft box may contain stale entries from failed attempts; use `draft-clear` before creating new drafts if needed.
