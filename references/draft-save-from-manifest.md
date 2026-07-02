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

## Notes

- `--draft true` saves to the draft box without publishing.
- Images must be pre-compressed (≤150KB each, total ≤300KB) — see `opencli-xhs-workflow.md` for compression.
- This pattern is preferred over manual UI-based draft save because it avoids DataTransfer injection issues.
- The draft box may contain stale entries from failed attempts; use `draft-clear` before creating new drafts if needed.
