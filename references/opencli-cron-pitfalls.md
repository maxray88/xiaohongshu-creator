# opencli xiaohongshu publish — Cron pitfalls (verified 2026-06-27)

Session: 2026-06-27, cron `ebf775e37292` (情绪树洞-每日保存草稿). Account: 静坐着呢的情绪树洞. Symptoms: draft box empty for ≥ 7 days, no error in delivery channel.

## Mistake #1 — Hardcoded session alias in prompts

**Wrong**:
```bash
opencli browser treehole open https://creator.xiaohongshu.com/publish/publish
```

**Error it produces**:
```
RuntimeError: Connection error.
```

**What it really means**: `treehole` is not a registered Browser Bridge profile — `opencli doctor` shows the real alias is usually `pjmvbend`. The "Connection error" wording is generic and misleading; nothing is wrong with the daemon or extension.

**Correct**:
```bash
# Resolve the actual profile alias dynamically
PROFILE=$(opencli doctor 2>&1 | awk '/Profiles:/{getline; gsub(/^[ \t•]+|:$/, ""); print; exit}')
opencli browser "$PROFILE" open https://creator.xiaohongshu.com/publish/publish
```

**Or skip the browser path entirely**: the high-level `opencli xiaohongshu publish` command knows the session itself and does not take a session argument — strongly preferred for any cron-style save-as-draft job.

## Mistake #2 — `--topics` for non-existent hashtags

**Wrong**:
```bash
opencli xiaohongshu publish "$BODY" \
  --title "..." --images "..." \
  --topics "情绪树洞,心灵治愈" \
  --draft true
```

**Error it produces**:
```yaml
ok: false
error:
  code: COMMAND_EXEC
  message: 'Could not attach topic "情绪树洞": no real topic entity appeared after selection'
  exitCode: 1
```

But before that, opencli silently already created a draft; both `opencli xiaohongshu drafts` and the API-returned id prove it exists. However the **content field is empty**:
```yaml
- id: s:9ae14dd2-10fa-4813-96b7-17ba8ef3abb6
  title: 当代年轻人的精神状态实录
  images: 6
  content: ''          # ← leaves you with a half-saved draft
```

Why: the topic-attach step happens between title/page setup and body fill. A failed topic rolls back the body write but leaves earlier state.

**Correct**: do not pass `--topics`. Append hashtags to the body string:
```bash
FULL_BODY="${BODY}

${TAGS}"   # e.g. "#情绪树洞 #心灵治愈 ..."
```

Xiaohongshu's body parser auto-recognizes leading-`#` tokens and treats them as topics for search/discovery — same downstream effect, no UI attach step.

For tagging accuracy, derive topic names from `opencli xiaohongshu search <tag>` first and only include ones that return at least one match. Custom in-house series names (情绪树洞 as a brand) will not have an entity match and should be skipped at the `--topics` layer.

## Mistake #3 — `[SILENT]` for a save-as-draft job

**Wrong** (excerpt from original cron prompt):
> 若 manifest 不存在则直接跳过。

Combined with the cron delivery contract that allows returning `[SILENT]` to suppress noise, this makes manifest-missing failures invisible. Symptom: user only notices "no draft saved today" when they manually open creator.xiaohongshu.com.

**Correct refactor**: always emit a JSON-line report:
```
日期: 2026-06-27
manifest: /tmp/xhs_treehole/day_20260627/manifest.json (存在 / 不存在)
title: <X>  | images: <N>  | draft id: <id>  | status: ✅/❌
失败原因: <原文>
```

Even when manifest is missing, emit one short line naming the checked paths. The cron delivery channel is the only feedback loop the user has for unattended runs — silence there is the failure mode, not the optimization.

## Opened 2026-06-27 vs. the documented manifest schema

Earlier (`draft-save-from-manifest.md` reference) the manifest had `title`, `body`, `tags`, `images`. The 2026-06-27 manifest split that schema:

| Field | Lives in |
|---|---|
| `title`, `tags`, `images`, `image_count`, `palette`, `card_structure`, `renderer`, `design_ref` | `manifest.json` |
| `body`, `subtitle`, `cta`, `cover_image`, `all_images`, `word_count` | `post_data.json` (same directory) |

**Recipe** (defensive, fall-back through the chain):
```bash
D=$(date +%Y%m%d)
M="/tmp/xhs_treehole/day_${D}/manifest.json"
[ ! -f "$M" ] && M="/tmp/xhs_treehole/day_${D}_v2/manifest.json"
PD="${M%/*}/post_data.json"
PC="${M%/*}/post_content.md"

TITLE=$(python3 -c "import json; print(json.load(open('$M'))['title'])")
TAGS=$(python3 -c "import json; d=json.load(open('$M')); print(' '.join(d['tags']))")
IMAGES=$(python3 -c "import json; d=json.load(open('$M')); print(','.join(d['images']))")

# body: post_data.json['body'] → post_content.md → manifest['body']
if [ -f "$PD" ] && grep -q '"body"' "$PD" 2>/dev/null; then
  BODY=$(python3 -c "import json; print(json.load(open('$PD')).get('body',''))")
elif [ -f "$PC" ]; then
  BODY=$(tail -n +3 "$PC")
else
  BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d.get('body',''))")
fi

FULL_BODY="${BODY}

${TAGS}"
opencli xiaohongshu publish "$FULL_BODY" \
  --title "$TITLE" --images "$IMAGES" --draft true \
  --site-session ephemeral --window background -f yaml 2>&1
```

## Mistake #4 — `manifest.json` no longer has a `body` field

The docs and previous instances of this skill used the recipe `BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d['body'])")`. On 2026-06-27 that produces `KeyError: 'body'` because the body field has been moved out of the deck manifest into a sibling content file.

**Before** (this loop was hit on 2026-06-27 with the new schema):
```bash
BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d['body'])")
# KeyError: 'body'  — manifest now only carries images + tags + structure, body lives elsewhere
```

**After** (read body from `post_data.json['body']`, with post_content.md fallback):
```bash
PD="${M%/*}/post_data.json"
if [ -f "$PD" ] && grep -q '"body"' "$PD" 2>/dev/null; then
  BODY=$(python3 -c "import json; print(json.load(open('$PD'))['body'])")
elif [ -f "${M%/*}/post_content.md" ]; then
  BODY=$(tail -n +3 "${M%/*}/post_content.md")    # skip H1 title line
else
  BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d.get('body',''))")
fi
```

**Lesson**: the deck manifest is for orchestration (image paths, palette, day number). Body text is editorial data and lives in `post_data.json`. When field locations change across daily jobs, always read both — never assume a single manifest holds everything.

## What a correct mini-recipe looks like (the prompt-now)

```bash
# Step 1: locate today's manifest
D=$(date +%Y%m%d)
M="/tmp/xhs_treehole/day_${D}/manifest.json"
[ ! -f "$M" ] && M="/tmp/xhs_treehole/day_${D}_v2/manifest.json"

# Step 2: report explicitly even when missing
if [ ! -f "$M" ]; then
  echo "今天 ($D) 没有 manifest.json, 跳过草稿保存"
  exit 0
fi

# Step 3: gate on login state
LOGIN=$(opencli xiaohongshu whoami -f yaml 2>&1)
echo "$LOGIN" | grep -q "logged_in: true" || { echo "未登录, 中止"; exit 0; }

# Step 4: assemble payload — body comes from post_data.json (not manifest)
PD="${M%/*}/post_data.json"
TITLE=$(python3 -c "import json; print(json.load(open('$M'))['title'])")
TAGS=$(python3 -c "import json; d=json.load(open('$M')); print(' '.join(d['tags']))")
IMAGES=$(python3 -c "import json; d=json.load(open('$M')); print(','.join(d['images']))")
if [ -f "$PD" ]; then
  BODY=$(python3 -c "import json; print(json.load(open('$PD')).get('body',''))")
else
  BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d.get('body',''))")
fi
FULL_BODY="${BODY}

${TAGS}"

# Step 5: compress any single image >150KB before publish (ffmpeg fallback)
# ... (omitted; see SKILL.md validated content pipeline)

# Step 6: save as draft via high-level command
opencli xiaohongshu publish "$FULL_BODY" \
  --title "$TITLE" \
  --images "$IMAGES" \
  --draft true \
  --site-session ephemeral \
  -f yaml 2>&1 | tail -20

# Step 7: verify the draft is in the box
opencli xiaohongshu drafts -f yaml 2>&1 | head -20
```

Successful return signature:
```yaml
- status: "✅ 暂存成功"
  detail: '"<title>" · N张图片 · 保存成功'
```

## Mistake #5 — `--window background` hides the file-upload input

**Error it produces**:
```yaml
ok: false
error:
  code: UNKNOWN
  message: 'Image injection failed: No file input found on page. Debug screenshot: /tmp/xhs_publish_upload_debug.png'
  exitCode: 1
```

**Root cause**: `opencli xiaohongshu publish` uses Playwright to automate the creator-page file input. When `--window background` is passed, the browser window is sent to the background, and Playwright cannot find the `<input type="file">` element — it's invisible on the hidden page.

**Fix**: do not pass `--window background` to `opencli xiaohongshu publish`. The command runs in seconds (it's just form-fill + upload), so backgrounding is unnecessary. There is no visible window steal — the user won't see a Chrome window popping up because opencli manages its own headless session.

**Correct**:
```bash
opencli xiaohongshu publish "$FULL_BODY" \
  --title "$TITLE" --images "$IMAGES" \
  --draft true --site-session ephemeral \
  -f yaml 2>&1 | tail -20
```

**Detect**: if you see "No file input found on page" and images are definitely valid files, check for `--window background` in the command. Remove it and retry.

## Symptoms checklist (extended, includes Mistake #5)

If a new friend runs into this, run these four checks first:
1. `opencli doctor` — confirm profile alias under "Profiles:" is what the cron is using.
2. `opencli xiaohongshu drafts -f yaml` — does the latest run appear? Check `content:` — empty means Mistake #2 or earlier failed half-write.
3. `~/.hermes/cron/output/<job_id>/<date>.md` — the cron transcript. Look for "Connection error" (Mistake #1), "Could not attach topic" (Mistake #2), or just no transcript file (Mistake #3 — `[SILENT]` ate the run).
4. `python3 -c "import json; print(list(json.load(open('day_YYYYMMDD/manifest.json'))))"` — if `'body'` is missing from the keys, that's Mistake #4 (schema split); check sibling `post_data.json`.

Each mistake has a one- or two-line fix in this file. None require a code change to opencli — only prompt discipline.
