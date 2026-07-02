---
name: xiaohongshu-creator
description: |
  Automate Xiaohongshu (小红书) creator platform: login, publish, analytics,
  hashtag research, comment management, and engagement automation.
  Use this skill when the user wants to publish, market, or grow their Xiaohongshu account.
metadata:
  hermes:
    tags: [xiaohongshu, creator, publish, marketing, analytics, playwright, automation, social-media]
    category: social-media
    related_skills: [xiaohongshu-content-gen]
---

# Xiaohongshu Creator Automation & Marketing

Automate login, publishing, analytics, hashtag research, and engagement on the Xiaohongshu creator platform.

## ⭐ Pitfalls: Cron-driven Draft Save (verified 2026-06-27, must-fix errors)

Five mistakes can make a perfectly installed opencli + 静坐着呢的情绪树洞 stack silently skip draft saving for **days** without any visible error. Hit on 2026-06-27, fixing the broken cron `ebf775e37292` (情绪树洞-每日保存草稿). A fourth mistake (manifest schema split — body moved to post_data.json) was added 2026-06-27 after the cron re-ran into it. A fifth (--window background breaks image upload) was found 2026-07-01. See Mistakes #1–#5 below. Prompts that say `opencli browser treehole open https://...` fail with `RuntimeError: Connection error` even when `opencli doctor` shows everything green — `treehole` is not a real profile alias. Always resolve the profile via `opencli doctor | grep Profiles` and use the real alias (typical: `pjmvbend`). The error message is misleading: it points at network when the cause is naming. **`xiaohongshu publish` (the high-level command) sidesteps this entire class of issue** — use it instead.

**2. `--topics <chinese-tag>` is a silent half-failure.** `opencli xiaohongshu publish --topics 情绪树洞,...` returns a YAML error `Could not attach topic "情绪树洞": no real topic entity appeared after selection`. But the partial state is worse than a clean error: opencli creates a draft with `title` and `images` populated yet `content` left as an empty string on disk. Verify by `opencli xiaohongshu drafts -f yaml` — `text_preview` will be empty. **Fix:** skip `--topics` entirely; append `#tag1 #tag2 ...` to the body string. Xiaohongshu auto-parses trailing hashtags from the body and works the same.

**3. `[SILENT]` swallows the failure you most need to see.** A draft-save cron that returns `[SILENT]` when manifest.json is missing is technically quiet but operationally invisible — the user only learns "skipped" when they open the Xiaohongshu creator console manually. **Refactor:** the cron should always report either a concrete success (id, image count, time) or an explicit "今天 $DATE 没有 manifest.json, 跳过" path. Never `[SILENT]` for a save-as-draft job — silence is the failure mode.

Reproducible recipe and one-line fix patches live in `references/opencli-cron-pitfalls.md`. Any new cron saving drafts to 静坐着呢的情绪树洞 should re-read that file first.

## ⭐ CRITICAL: Browser Tool Priority (2026-06-21+)

**OpenCLI is the PRIMARY browser tool for all Xiaohongshu automation.** Use `opencli browser <session> *` commands for every browser interaction — login, publish, draft save, upload images, etc.

- `opencli browser <session> open <url>` — open page (creates/owns session)
- `opencli browser <session> state` — snapshot DOM with refs
- `opencli browser <session> click <target>` — click by ref or CSS selector
- `opencli browser <session> type/fill <target> <text>` — input text
- `opencli browser <session> eval "<js>"` — evaluate arbitrary JS in page context (escape inner quotes as `"`)
- `opencli browser <session> screenshot [path]` — capture viewport

**NEVER use** `computer_use`, `browser_*` tools, or Playwright CDP for Xiaohongshu publishing. OpenCLI is the only approved tool for all browser automation on this platform.

### Verified High-Level Publish Command
```bash
opencli xiaohongshu publish "正文内容" \
  --title "标题" \
  --images /path/cover_01.jpg,/path/cover_02.jpg
```
Constraints: max 9 images, title ≤20 chars, Chrome must be logged into creator center under the bound Browser Bridge profile.

### Login Verification (REQUIRED before publish)
```bash
opencli browser <session> open "https://www.xiaohongshu.com/user/profile/me"
opencli browser <session> get url
```
If URL contains `/login?redirectPath=...`, the session is **NOT logged in**. Stop and ask the user to log in via Chrome.

**Pitfall**: `opencli doctor` showing `[OK] Extension: connected` only verifies Browser Bridge connectivity. It does **not** verify that Chrome is logged into xiaohongshu.com. Always run the profile check above.

### Session Naming Convention
Discover the active session/profile from `opencli doctor` output under **Profiles**. Use the exact alias shown there (e.g., `pjmvbend`), not a hardcoded name like `treehole`, unless the user explicitly names a different session. Stable multi-step flows can use a consistent session name per task (e.g., `xhs-publish`, `xhs-warmup`).

### Bind Existing Tabs
For logged-in pages, use `opencli browser <session> bind` to attach to an existing Chrome tab. Bound sessions persist until unbind/tab close.

- `references/opencli-xhs-workflow.md` — The complete OpenCLI → Xiaohongongshu publish workflow
- `references/opencli-cron-pitfalls.md` — Verified 2026-06-27: four cron pitfalls (hardcoded session name / `--topics` empty-content bug / `[SILENT]` swallowed failures / manifest schema split → body lives in `post_data.json`) and the high-level publish recipe

### Validated content and image pipeline
```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3

# 1. Content generation (no emoji required by spec)
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \
  --topic "野原美冴的日常小趣事" --style warm --emoji "" \
  --output /tmp/xhs_treehole/day_YYYYMMDD
```

```bash
# 2. HyperFrames render (preferred)
hyperframes render \
  -o /tmp/xhs_treehole/day_YYYYMMDD/images/cover_01_main.jpg \
  --template emotional-treehole-cover \
  --width 1080 --height 1920 --theme starry-night
```

```bash
# 3. Image compression trigger (REQUIRED when blob is large)
# Rule: compress when a single image >150KB or total >300KB
ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT
```

```bash
# 4. OpenDesign convert (headless only)
opendesign convert -i <file.octopus> -o <output.png>
# NOT in cron: opendesign open (GUI)
```

```bash
# 5. Publish + verify
opencli xiaohongshu publish "正文内容" --title "标题" --images /path/a.jpg,/path/b.jpg
opencli xiaohongshu creator-notes-summary --limit 1
```

### Project-specific rules (情绪树洞, account: 静坐着呢的情绪树洞)
- **Style**: 手绘风/自然感, 无 emoji, anti-AI detection.
- **Size**: 单张 ≤150KB, 总 payload ≤300KB.
- **card-xiaohongshu template**: 1080×1440 (3:4), 3-18 张 (常用 6-9 张), 封面大字宽距 + 正文分卡 + CTA, 每张右下角作者/日期.
- **tab switching**: use `opencli browser <session> eval` with element.click() for tabs — do *not* use `opencli click` for tab switches.

---

## Alternative: OpenCLI High-Level Publish Command

The OpenCLI Xiaohongshu adapter provides a high-level `publish` command that abstracts the UI automation:

```bash
opencli xiaohongshu publish "正文内容" --title "标题" --images ./a.jpg,./b.png
# Text-image cards:
opencli xiaohongshu publish "正文内容" --title "标题" --card-text "第一张\\n第二行|||第二张" --card-style 边框
```

**This command still requires Chrome to be logged into creator center** under the bound Browser Bridge profile, but it reduces manual UI ref hunting. Use it when the account is known to be logged in and stable. If it fails with login redirects, fall back to the detailed UI workflow in `references/opencli-xhs-workflow.md`.

**Image-size failure signature**: if publish fails with `fetch failed` / `write EPIPE`, first compress images: `ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT`. Keep single image ≤150KB and total payload ≤300KB.

### Pitfalls (verified, 2026-06-27 情绪树洞 自动保存链路踩坑记录)

**Pitfall 1 — `--topics` 会让 publish 流程半途终止并清空 content 字段.**
症状: `error: "Could not attach topic \"<词>\": no real topic entity appeared after selection"`. 即使 publish 的 `status` 最终变 `✅ 暂存成功`, 草稿里 `content` 字段会被截为 **空字符串**, `images` 还有, 但没有正文. 这是最隐蔽的失败模式 — UI 上看起来"成功了".

根因: 小红书的话题库只能识别官方 / 已收录的话题. 自定义词 (如 `情绪树洞`, `野原美冴`) 找不到实体, opencli 会放弃流程后段.

修复: **永远不要传 `--topics`**. 把所有 `#话题` 直接拼到正文末尾, 小红书会自动识别为 hashtag:

```bash
# 不要这么写
opencli xiaohongshu publish "$BODY" --title "$T" \
  --images "$IMGS" --topics "情绪树洞,心灵治愈,反内耗" --draft true

# 这么写
FULL_BODY="${BODY}

${TAGS}"  # 例如: "#情绪树洞 #心灵治愈 #反内耗 ..."
opencli xiaohongshu publish "$FULL_BODY" --title "$T" \
  --images "$IMGS" --draft true
```

**Pitfall 2 — 不要硬编码 session 别名, e.g. `opencli browser treehole open ...`.**
症状: 7 天连续 `RuntimeError: Connection error`. 这条错误不是网络问题, 是错把"自定义名字"当成"profile 别名"用.

根因: opencli profile 别名是 **opencli doctor ➜ Profiles** 那行输出的小写字母数字 ID (用户的实例上是 `pjmvbend`). 其他名字 (`treehole`, `xhs-publish`, `xhs-draft-check` 等) 虽然能 accept, 但不会命中真实 Chrome session, 会触发 daemon 端 connection 失败.

修复: 永远不要用 `opencli browser <session> *` 这条低层路径去做小红书发布. **只用高层 `opencli xiaohongshu publish --draft true`**. 这个高层命令不依赖任何 browser session 别名. 如确需浏览器层操作, 先 `opencli doctor` 查 `Profiles:` 下的别名, 然后用那个别名:

```bash
# 查看真实 profile
opencli doctor | grep 'Profiles:' -A 2
# 预期输出: • pjmvbend: connected v1.0.20
SESSION=$(opencli doctor | grep -oE '• [a-z0-9]+:' | head -1 | tr -d '• :')
echo "$SESSION"  # 输出: pjmvbend
opencli browser "$SESSION" open "https://creator.xiaohongshu.com/publish/publish"
```

**Pitfall 3 — `[SILENT]` 别吞掉所有信号.**
症状: 22:30 草稿保存 cron 连续一周"看起来正常" — last_status: ok, 但草稿箱里空空如也. 用户侧收到的消息是 0 条, 无法知道发生了什么.

根因: prompt 写了 "若 manifest 不存在则直接跳过", 加 SILENT 模式, 让所有边缘场景 (manifest 不存在 / 网络抖 / UI 选择失败) 都静默吃完, 用户完全感知不到.

修复: 草稿保存 / 发布类 cron **必须发报告**. 唯一可 [SILENT] 的场景是上一次执行就是几小时内且结果完全没变. 即使是 "今天没素材", 也要明确说 "今天 (YYYYMMDD) 没找到 manifest, 跳过草稿保存. 请检查上游 20:00 主任务" — 不能吃声.

> Updated 2026-06-27: 三条 pitfall 由 ebf775e37292 cron 一周的失败回溯写出, 实战验证. 旧版 06-21 文档未涉及 `--topics` 这个隐藏陷阱, 此次补回.
>
> **Pitfall 5 (2026-07-01) — `--window background` causes image upload failure.** 使用 `--window background` 参数时 playwright 找不到文件上传 input 元素, 报 "Image injection failed: No file input found on page". 移除 `--window background` 即可恢复。注意: 该参数对 `xiaohongshu publish` 命令的 publish 流程影响较小 (无需在后台保持窗口, 整个流程只需几秒), 但 upload 流程需要可见窗口。修复: 不要传 `--window background`。

## File Upload Workaround (JavaScript DataTransfer Injection)

The `opencli browser <session> upload` command often returns `{"code":-32000,"message":"Not allowed"}` due to CDP security restrictions on file inputs.

**Mandatory pattern** — use `opencli browser <session> eval` with a self-invoking function to build a `DataTransfer` + `File` list and assign it to the `input[type=file]` element, then dispatch `change`:

```js
(function(){
  var fi=document.querySelector('input[type=file]');
  var dt=new DataTransfer();
  ['/path/a.jpg','/path/b.jpg'].forEach(function(p){
    var blob=new Blob([new ArrayBuffer(1)], {type:'image/jpeg'});
    dt.items.add(new File([blob], p.split('/').pop(), {type:'image/jpeg'}));
  });
  fi.files=dt.files;
  fi.dispatchEvent(new Event('change'));
})();
```

**Notes**:
- Use an IIFE to avoid variable conflicts with page scripts that may declare `input` or `fileInput` as globals (known conflicts: `input`, `fileInput`).
- The fake file content is sufficient to trigger the React re-render in many cases; if uploads still fail, re-generate compressed images first (≤150KB).
- After upload, the page may navigate to `about:blank`; re-open the publish URL if needed.

## HyperFrames + OpenDesign Content Creation Pipeline

For image-text notes (图文笔记), use this verified flow matching the user's target spec (情绪树洞, 6 images, ≤150KB/image):

### Step A: Content generation
```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_content_generator.py \
  --topic "...", --style warm --emoji "" \
  --output /tmp/xhs_treehole/day_YYYYMMDD
```

### Step B: HyperFrames static cover render (preferred)
```bash
hyperframes render \
  -o /tmp/xhs_treehole/day_YYYYMMDD/images/cover_01_main.jpg \
  --template emotional-treehole-cover \
  --width 1080 --height 1920 --theme starry-night
```
Generate 6 variants: `cover_01_main.jpg` … `cover_06_cta.jpg`.

### Step C: OpenDesign conversion (optional)
If a `.octopus` design file exists locally or after HyperFrames render:
```bash
opendesign convert -i <file.octopus> -o <output.png>
```
Do **not** use `opendesign open` in cron/automation contexts; it launches a GUI viewer.

**Open Design repo reference**: local clone at `/Users/maochundong/open-design/` contains `skills/card-xiaohongshu` template for 1080×1440 (3:4) knowledge cards. Repo build is currently blocked by Node 22 vs required ~24; see `references/opendesign-repo-status.md` for full details. Until build is fixed, use HyperFrames + the card-xiaohongshu style spec as a reference for palette/spacing/layout.

### Step D: Image compression (REQUIRED before publish)
```bash
# Compress ALL images before publish to stay under limits
ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT
```
Publish limits: single image ≤150KB, total payload ≤300KB. Default to compressing every image; failing to compress is the #1 cause of `fetch failed` / `write EPIPE` during publish.

### Step E: Upload + Publish
Prefer `opencli xiaohongshu publish --images ...` directly when images are already compressed and small.
If the publish flow requires file upload in a *custom* web form, fall back to the JS DataTransfer eval.

### Step F: Save as Draft (from manifest.json)
When the user prefers manual review before publishing, save as draft instead. **Body lives in `post_data.json` (sibling of `manifest.json`), not in `manifest.json` itself** — the recipe below handles both schemas:
```bash
M="/tmp/xhs_treehole/day_YYYYMMDD/manifest.json"
PD="${M%/*}/post_data.json"
PC="${M%/*}/post_content.md"

TITLE=$(python3 -c "import json; print(json.load(open('$M'))['title'])")
TAGS=$(python3 -c "import json; d=json.load(open('$M')); print(' '.join(d['tags']))")
IMAGES=$(python3 -c "import json; d=json.load(open('$M')); print(','.join(d['images']))")

# body: post_data.json → post_content.md (skip H1) → manifest fallback
if [ -f "$PD" ] && grep -q '"body"' "$PD" 2>/dev/null; then
  BODY=$(python3 -c "import json; print(json.load(open('$PD'))['body'])")
elif [ -f "$PC" ]; then
  BODY=$(tail -n +3 "$PC")
else
  BODY=$(python3 -c "import json; d=json.load(open('$M')); print(d.get('body',''))")
fi

FULL_BODY="${BODY}

${TAGS}"
# --window background causes "Image injection failed: No file input found on page"
opencli xiaohongshu publish "$FULL_BODY" \
  --title "$TITLE" --images "$IMAGES" \
  --draft true --site-session ephemeral \
  -f yaml 2>&1 | tail -20
```
Verify with `opencli xiaohongshu drafts -f yaml`. Full reference: `references/draft-save-from-manifest.md`.
Pitfalls: `references/opencli-cron-pitfalls.md` (5 mistakes — session alias, `--topics`, `[SILENT]`, manifest schema split, `--window background`).

### Step F: Verify
```bash
opencli xiaohongshu creator-notes-summary --limit 1
```

## Video Rendering (HyperFrames)

For animated video posts (视频笔记), use `xhs_hyperframes_video.py`:
```bash
python3 scripts/xhs_hyperframes_video.py \
    --title "标题" --subtitle "副标题" --emoji "😭" \
    --cta "你家娃也这样吗？" \
    --bg /path/to/bg.jpg \
    --output /tmp/xhs_video.mp4 --duration 8 --fps 30
```
Requires: HyperFrames CLI, FFmpeg, Chrome. Composition uses GSAP timelines with `data-composition-id`, `data-width`, `data-height` on root. Lint before render. Portrait 1080x1920 for Xiaohongshu video posts.

## Login Verification Step (REQUIRED before publish)

Before any publish or login-required flow, explicitly verify login state:

```bash
opencli browser <session> open "https://www.xiaohongshu.com/user/profile/me"
opencli browser <session> get url
```

If the URL contains `/login?redirectPath=...`, the session is **NOT logged in**. Stop and prompt the user to log in via Chrome (scan QR code or SMS) rather than attempting to publish.

**Pitfall**: `opencli doctor` showing `[OK] Extension: connected` only verifies Browser Bridge connectivity. It does **not** verify that Chrome is logged into xiaohongshu.com. Always run the profile check above.

## Content Generation Pipeline

For generating 6配图 + video covers per post:

1. Content generation → `xhs_content_generator.py` (titles, body, hashtags, CTA)
2. Cover/image generation → `xhs_hyperframes_video.py` (HTML→MP4 animated covers) OR HyperFrames CLI for static 1080×1920 JPG
3. Optional design refinement → `opendesign convert` for `.octopus` assets
4. Upload to Xiaohongshu → OpenCLI `upload` command (often blocked) OR `opencli browser <session> eval` JS DataTransfer injection

Style: S6 warm paper texture with handwritten feel. No heavy AI glow effects.

**Upload rule of thumb**: `opencli browser <session> upload` is frequently blocked by CDP security (`-32000 Not allowed`). Always have the JS DataTransfer eval fallback ready.

## Cron Jobs Maintenance

Xiaohongshu automation uses multiple cron jobs that can accumulate over time: content generation, draft saving, publishing, analytics, etc. Before updating or creating new jobs, always audit existing ones to avoid duplication.

### Audit workflow
1. Run `cronjob action='list'` to pull all jobs.
2. Filter by name/skill to identify Xiaohongshu-related jobs.
3. Check their schedules, states (paused/scheduled), and last run statuses. Look for overlapping responsibilities that should be consolidated.
4. **Prune stale paused jobs**: paused jobs from old workflows often become noise. If a job has no useful next run, remove it rather than leave it paused forever. Use `cronjob action='remove' job_id="..."`.
5. When updating a job, preserve its existing `schedule`, `repeat`, and `enabled` state unless the user explicitly asks to change them. Only update the `prompt`.

### Verified prompt template (2026-06-21)
When injecting the verified OpenCLI workflow into a cron job, include:
- OpenCLI v1.8.4 context (profile alias, daemon port awareness)
- Image compression trigger: pre-compress images when total size >300KB or single image >150KB using `ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT`
- Publish command: `opencli xiaohongshu publish "正文内容" --title "标题" --images /path/a.jpg,/path/b.jpg`
- Tool constraints: no `computer_use` or generic `browser_*` for Xiaohongshu; use `opencli browser <session> *` only when needed
- Error handling: on publish failure, compress and retry once; if it fails again, abort and report
- Post-publish verification: `opencli xiaohongshu creator-notes-summary --limit 1`

See `references/cron-maintenance-notes.md` for the operational checklist and common overlap patterns observed in real deployments.

## Recommended 2-Job Content Factory (情绪树洞, 2026-06-21)

For accounts that generate and publish image-text notes daily, use this 2-job pipeline (draft-job `3b52050d1389` removed on 2026-06-21):

| Time (CST) | Job ID example | Role |
|------------|----------------|------|
| 20:00 | `250be2028330` | 主内容生成：选题 → 正文 → HyperFrames 渲染 6 张主图 |
| 21:30 | `d9578136eea3` | 副配图/深化：读取 20:00 素材 → 第二版配图或视频帧 |

**Key rules**:
- 20:00 and 21:30 must not write to the same directory (use `_v2` suffix for the second job).
- If draft saving is needed later, re-add a 22:00 draft job reading from the latest manifest.
- All sharing of the same Xiaohongshu login session under the same `opencli browser <session>` alias.
- Human publishes manually from draft box; do not auto-publish.

## Architecture

```
~/.hermes/skills/xiaohongshu-creator/
├── SKILL.md # This file - main workflow
├── scripts/
│   ├── xhs_config.py # Shared constants (URLs, selectors, paths, timeouts)
│   ├── xhs_browser.py # Shared browser helpers (cookie I/O, CDP, factories)
│   ├── xhs_utils.py # Shared interaction helpers (Bezier, delays, force_click)
│   ├── xhs_auto_publish.py # 🚀 Orchestrator: content → images → publish (FULL PIPELINE)
│   ├── xhs_content_generator.py # Viral content generator (titles + body + hashtags + cover designs)
│   │   ├── xhs_image_pipeline.py             # All-in-one: search → download → cover render
│   │   ├── xhs_publish.py                    # Publish: CDP → fill form → _onPublish() (v10, merged)
│   │   ├── xhs_login.py                      # Login: open Chrome, save cookies
│   │   ├── xhs_analytics.py                  # Analytics: account & post metrics
│   │   ├── xhs_hashtags.py                   # Hashtag research & trending topics
│   │   ├── xhs_comments.py                   # Comment management (list/reply/post via CDP)
│   │   ├── xhs_engage.py                     # Engagement automation (auto-engage like+comment via CDP)
│   │   └── render_covers.py                  # Cover image renderer (Playwright + HTML, standalone)
│   │   └── xhs_hyperframes_video.py          # HyperFrames HTML→MP4 video renderer (animated covers)
├── templates/
│   │   └── xhs_content_prompt_template.md  # LLM prompt template for content generation (editable)
├── references/
- `references/draft-save-from-manifest.md` — Save Xiaohongshu drafts from manifest.json using `--draft true`
- `references/session-learnings-2026-06-20.md` — HyperFrames HTML→MP4 integration, lint error fixes
- `references/session-learnings-2026-06-21.md` — Verified publish flow, image-size fix, DataTransfer workaround, commander UI navigation, tab-switch issue
- `references/opencli-publish-workflow.md` — Current OpenCLI publish recipe and constraints on Xiaohongshu publishing tools
- `references/opendesign-repo-status.md` — Open Design local repo path, build status, card-xiaohongshu template spec
- `references/card-xiaohongshu-spec.md` — Design spec summary for 1080×1440 (3:4) cards used as an overlay guidance for HyperFrames output (copy from local OpenDesign repo)
│   ├── xiaohongshu-content-gen.md        # Content generation guide & viral formula
│   ├── xiaohongshu-marketing.md          # Marketing strategy guide
│   ├── playwright-environment.md          # Technical reference
│   ├── xiaohongshu-publish-page-deep-dive.md  # Publish page DOM deep reference
│   ├── best-practices.md                  # Best practices & pitfalls
│   ├── python311-standardization.md       # ⭐ Python 3.11 standard — NO hardcoded paths
│   └── cdp-mode-with-patchright.md        # CDP + Patchright setup
│   └── ai-detection-failure-2026-06-03.md # Multi-layer detection failure & recovery
│   └── image-acquisition-and-composition.md  # Image acquisition guide
│   ├── openverse-search-findings.md         # Openverse search limitations for anime characters
│   ├── opencli-xhs-workflow.md            # OpenCLI → Xiaohongshu publish workflow
│   ├── xiaohongshu-mcp-server-setup.md   # MCP server setup
│   ├── session-learnings-2026-05-15.md   # Session learnings (2026-05-15)
│   ├── session-learnings-2026-05-16.md   # Session learnings (2026-05-16)
│   ├── session-learnings-2026-05-17.md   # Session learnings (2026-05-17) — `_onPublish()` breakthrough
│   ├── session-learnings-2026-05-18.md   # Session learnings (2026-05-18) — emoji rendering, base64 bg, content pipeline
│   ├── session-learnings-2026-05-18-p2.md # Session learnings (2026-05-18 P2) — analytics column order, prompt escaping
│   ├── session-learnings-2026-05-19.md   # Session learnings (2026-05-19) — CDP comment posting, auto-engage like+comment
│   ├── session-learnings-2026-05-20.md   # Session learnings (2026-05-20) — cover font sizes, key points on cover, navigation fixes
│   ├── session-learnings-2026-05-21.md   # Session learnings (2026-05-21) — Emoji 2x, theme images, draft mode, multi-image upload
│   ├── session-learnings-2026-05-22.md   # Session learnings (2026-05-22) — S6 hand-drawn style, keyword highlighting, 14-day auto-publish
│   ├── session-learnings-2026-05-23.md   # Session learnings (2026-05-23) — session invalidation deep dive
│   ├── session-learnings-2026-05-24.md   # Session learnings (2026-05-24) — weekly review cron, empty analytics diagnostics
│   ├── session-learnings-2026-05-25.md   # Session learnings (2026-05-25) — cron session validation, title truncation, draft save failure
│   ├── session-learnings-2026-05-28.md   # Session learnings (2026-05-28) — cookie injection failure
│   ├── session-learnings-2026-05-29.md   # Session learnings (2026-05-29) — `_onSave()` method, multiple page context issue
│   ├── session-learnings-2026-06-03.md   # Session learnings (2026-06-03) — `_onSave()` degradation, `pages[0]` vs `pages[-1]`, session recovery limits
│   ├── feishu-channel-notification.md     # Feishu IM channel messaging for publish reports
│   ├── github-workflow.md                # GitHub upload workflow
│   ├── cover-style-s6-optimized.md       # Approved warm paper texture style with keyword highlighting
│   ├── custom-cover-styling-technique.md # Advanced custom cover rendering (break default template limits)
│   └── treehole-strategy.md              # Current strategy: 泛心理与情绪树洞
```