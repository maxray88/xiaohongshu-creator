# Cron Maintenance Notes — Xiaohongshu

> Created: 2026-06-21 | Updated: 2026-07-07 | Operational patterns observed during cron audit & prompt refresh

## Why jobs multiply

- **Content lines**:同一个账号常同时运营多个内容线（fun facts、情绪树洞、30天挑战、职场搞钱）。每条线可能拥有独立的 generate → images → publish pipeline。
- **Layered responsibilities**: 一个内容线可能拆成「内容生成」、「配图」、「保存草稿」、「发布」等多个 job，导致同一账号下 job 数量膨胀。
- **Legacy paused jobs**: 历史实验或临时任务经常被暂停而非删除，残留 configuration 噪音。

## Current recommended structure (2026-07-07)

After cleanup, the treehole account uses a **3-job overnight pipeline** (01:00–03:00 CST window):

| job_id | name | schedule | purpose | state |
|--------|------|----------|---------|-------|
| 250be2028330 | 情绪树洞-每日内容生成+配图 | 0 1 * * * | Main content + HyperFrames 6 static covers | scheduled |
| d9578136eea3 | 情绪树洞-每日内容生成(30天) | 0 2 * * * | Second-pass visuals (`_v2`), deeper angle | scheduled |
| ebf775e37292 | 情绪树洞-每日保存草稿 | 0 3 * * * | OpenCLI draft save only (no publish) | scheduled |

**Rules**:
- 01:00 and 02:00 must NOT share the same output directory. Use `_v2` suffix for the 02:00 job.
- 03:00 reads manifest from 01:00 (or 02:00 `_v2` if 01:00 failed).
- All jobs share the same `opencli doctor`-resolved profile alias for the same Xiaohongshu login. The high-level `opencli xiaohongshu publish` command does not need a session argument.
- Human publishes manually from the draft box; auto-publish is disabled.
- **Do not pass `--topics` to publish; append hashtags to the body instead.**
- **Never return `[SILENT]` from a draft-save cron; always emit a concrete success report or an explicit "today has no manifest" report.**
- **Do not use `--window background` with `opencli xiaohongshu publish`; it breaks file-input discovery in Playwright.**

## Safe update pattern

1. `cronjob action='list'` 发现全部 jobs。
2. 识别 target jobs（按 name、skill 关联）。
3. 检查 `last_run_at`、`last_status`、`enabled`、`state`。
4. 只更新 `prompt`，不动 `schedule` / `repeat` / `enabled`（除非用户明确要求）。
5. 更新后报告：job name, ID, schedule, state, next run time.

## Prompt injection checklist

在 cron prompt 中必须包含的要素：
- [ ] 版本上下文：OpenCLI v1.8.4, profile alias, daemon port
- [ ] 登录验证：打开 `/user/profile/me` 检查 URL，`opencli doctor` 不能作为登录凭证
- [ ] 图片压缩规则：`ffmpeg -y -i INPUT -vf "scale=640:-2" -q:v 60 OUTPUT`
- [ ] 发布命令格式：`opencli xiaohongshu publish ... --images /path/a.jpg,/path/b.jpg`
- [ ] 错误处理：发布失败时压缩重试一次，仍失败则中止报告
- [ ] 结果验证：`opencli xiaohongshu creator-notes-summary --limit 1`
- [ ] 工具禁则：禁止 `computer_use` / `browser_*`
- [ ] 配图工具：HyperFrames v0.6.115（静态 1080×1920）+ OpenDesign v0.3.0（`.octopus` → PNG，仅 `convert` 子命令）
- [ ] 上传 fallback：`opencli browser upload` 返回 -32000 时，使用 `eval` + JS DataTransfer 注入
- [ ] 输出规范：仅 `_v2` 后缀目录写第二版 visuals，避免与 20:00 主目录冲突

## Validation History

### 2026-07-07 (job ebf775e37292)
- Manifest: `/tmp/xhs_treehole/day_20260707/manifest.json` (old schema with `body` field)
- Login: `logged_in: true`, username `静坐着呢的情绪树洞`
- 6 images: 2 exceeded 150KB → compressed with ffmpeg to ~13KB each
- Draft ID: `s:1cc4fc87-4293-4df2-bb9a-579c7e592603`
- Verified: `opencli xiaohongshu drafts -f yaml` — rank 1, 6 images, matching title
- **Critical**: `--window background` caused "Image injection failed" — removed, upload succeeded
- Report: explicit success (not `[SILENT]`)

### 2026-07-06 (job ebf775e37292)
- Manifest: `/tmp/xhs_treehole/day_20260706/manifest.json`
- Login: `logged_in: true`, username `静坐着呢的情绪树洞`
- 6 images: all under 150KB, total ~0.66MB
- Draft ID: `s:e2bd78f6-7cd7-4a52-9692-fe0b6c473952`
- Verified: `opencli xiaohongshu drafts -f yaml`
- `--window background` unexpectedly succeeded (may be timing/page-state dependent)
- Report: explicit success (not `[SILENT]`)
