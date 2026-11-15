# Research: 创作者自动回复（自己的帖子）

Date: 2026-11-15
Method: vendored source reading (`vendor/xhs/*`) — no live probing performed or implied. Findings are file:line evidence from the working tree; runtime DOM shapes on XHS are not independently verified (see "Validation step" markers).

## Decision R1 — 自己帖子发现：profile 页列举

**Decision**: 使用 vendor `XiaohongshuPublisher.list_profile_notes(profile_url=…, user_id=…)`（`vendor/xhs/cdp_publish.py:2270`），从 profile 页 DOM 提取笔记卡片。返回 `{id, xsec_token, note_url, title, cover}`（`_extract_note_cards_from_profile_dom`，`cdp_publish.py:2171-2268`）。job 文件一次性配置 `own_profile_url` 或 `own_user_id`；不做自动发现。

**Rationale**: feed id 与 xsec_token 直接可得（regex `/\/(?:explore|discovery\/item)\/([0-9a-zA-Z]{24})/`），无需额外接口；与 spec Q1=A 决策一致；fail-closed——配置错误即运行失败，而非静默找错人。

**Alternatives considered**: creator center "我的作品" 页（vendor 无现成提取器 → 需新造 DOM，拒绝）；notification mentions API（只含被 @/回复，漏掉无 @ 的普通评论（SPECFR 要的是所有他人顶层评论），拒绝）。

**Validation step**: dry-run 首次运行前，打印每篇 note 的 `{id, xsec_token 前 8 位, title}`，运营者核对数量/标题与主页一致后再跑 live。

## Decision R2 — 评论枚举：`get_feed_detail(load_all_comments=True)` + 新增 JS 提取器

**Decision**: 对每篇自己帖子调用 `get_feed_detail(feed_id, xsec_token, load_all_comments=True)`（`cdp_publish.py:1965`）。内部 `_load_feed_detail_comments`（`:1862`）可按滚动/回复展开加载评论。**Gap（已核实）：vendor 没有现成的「comment 列表结构化提取器」**——`get_feed_detail` 仅返回 raw `noteDetailMap[feedId]` JSON 串解析结果（`feed_explorer.py:666-705`），评论字段形状未被 vendor 断言；`respond_comment` 依赖 DOM 定位 + `data-comment-*` 或 `id` 属性取 comment_id（`cdp_publish.py:2310-2420`）。实现期需新增一个 JS 提取器（vendor 内新增公开方法，如 `list_feed_comments(feed_id)`，沿用该文件 `_extract_feed_comments_state` 风格），输出规范化 `[{comment_id, author, content, time, has_creator_reply}]`。

**Rationale**: 唯一能拿到 comment_id/author/content 的路径；`has_creator_reply` 必须能从 threads（子回复作者）推断以支持 FR-007/SC-003（以帖子侧事实为准）。

**Alternatives considered**: 只依赖 notification mentions（遗漏面，拒绝）；从 creator center 数据页拉（包含评论量但不含评论明细，拒绝）。

**Validation step**: dry-run 必须打印提取器原始结构的前 3 条样本；若 `noteDetailMap` 无评论字段，回退方案 = 读 `document.querySelectorAll('.comment-item')` 的 `data-comment-*`/`id` + 文本 + 子回复作者列表（实现者按 dry-run 输出定稿）。

## Decision R3 — 创作者自己在 threads 里的出现 = 已回复（thread fact 为准）

**Decision**: 对每条顶层评论，扫描其子回复作者列表；创作者昵称（identity gate 已用 `expect_nick`/probe 校验）出现即视为「已回复」。Ledger 只是加速（跳过已知已回复评论），不作为最终判定。

**Rationale**: spec SC-003（重复回复率=0，删 ledger 重跑也不复现）要求帖子侧事实优先。`expect_nick` 恰好提供创作者昵称，无需新引入账号标识。

**Alternatives considered**: 纯 ledger 去重（删除日志后重跑会重复回复，违背 SC-003 验收，拒绝）。

**Validation step**: 单测构造「子回复含创作者昵称」的 fake 结构（`noteDetailMap` 或 fake DOM 结果），断言该评论被标记为已回复。

## Decision R4 — 回复生成：复用既有 LLM 评分链

**Decision**: 回复内容用同款 LLM 路径生成（`core/commenting.py` 风格的 prompt：persona=创作者 + 评论原文 + 帖子标题），`score_content(short_form=True)` 打分，`QUALITY_SCORE_THRESHOLD`（7.0）过线才发（FR-012）。不过线 → 跳过并在清单标注「不合格」原因（FR-017）。生成/LLM 不可用 → 同样跳过标注（FR-017），run 结尾汇报失败数，非零退出码。

**Rationale**: 零新依赖、行为一致、可测试（fake `llm_caller` 注入）。dry-run 不调 LLM（只打印计划/节点）。

**Alternatives considered**: 预审短句库（Q2=A 已否决）；不评分直接发（违背 spec quality gate，拒绝）。

**Validation step**: 单测：全候选低于阈值 → rc 0、posts=0、输出含「不合格」原因；fake LLM 抛异常 → rc 非零、posts=0、清单全标注失败。

## Decision R5 — 状态存储：新文件、同目录、同原子写法

**Decision**: 沿用 `~/.hermes/data/xhs_treehole/`：
- `reply_counter.json`：`{YYYY-MM-DD: count}`（FR-005 独立计数器 ≤3/日；写法照抄 `_write_counter` 的 45 天裁剪）
- `reply_ledger.jsonl`：每条已回复评论一行 `{ts, feed_id, comment_id, content, dry_run}`（去重加速 + 可读导出 FR-015；可被 thread fact 纠偏）
- `reply_state.json`：`{hostile_stop_until: ISO8601|null}`（FR-008 敌意停机窗口 48h）
- 审计复用：dry-run/live 均写 `reply_ledger.jsonl`；不与播种 `engagement_log.jsonl` 混写（不污染现有分析）。

**Rationale**: 最小复制、明确隔离（配额独立 FR-005）、全是既有文件模式。

**Alternatives considered**: 复用 engagement_counter.json 加命名空间前缀（改动现有 45 天裁剪逻辑，拒绝）；SQLite（无必要的复杂度，拒绝）。

**Validation step**: 单测：counter 文件缺失时从 0 开始计数；corrupt → rc 1 fail-closed；reply_state.json 含未来 `hostile_stop_until` 时本轮直接拒绝且零 CDP。

## Decision R6 — 安全门禁：整包复用既有 9229 try-out 闸门

**Decision**: 顺序与 seed_test_comments.py 一致：端口 9229 allowlist（`TEST_ONLY_CDP_PORT`）→ `ENGAGEMENT_STOP`  kill-switch → reply 日上限（`reply_counter.json`，3/日）→ 敌意停机窗口（`reply_state.json`）→ 参数/配置 gates → 发布者构造（lazy）→ `connect` → 帖子侧 thread fact 过滤（本工具无 nickname probe；身份责任全在 `expect_nick` 字符串匹配 + 端口 9229 allowlist；`expect_nick` 配置错误会导致以错误身份发帖而不自知——这是 operator 责任边界） → LLM 生成/评分 → 发布。9229 之外任何端口一律拒绝，零 CDP。

**Rationale**: 与既有事故面模型一致（端口 allowlist + kill-switch + 身份门禁），零新安全概念，评审成本低。`expect_nick` 已在 seed 工具中存在且 job 文件同源。

**Alternatives considered**: 新增独立 `REPLY_STOP`（双 kill-switch 概念，运营困惑，拒绝）。

**Validation step**: 单测镜像现有 guardrails 测试：killed-switch/port/wrong-identity/cap 全拒且 `FakePublisher.constructed == []`。

## Decision R7 — 运行形态：bin 入口 + cron 分阶段（FR-016）

**Decision**: 新工具 `bin/reply_to_own_comments.py`（CLI），`bin/run_reply_own_comments.sh` 只包裹 `--pool?` 不适用——回复内容由 LLM 生成，故 cron 必须导出 LLM 代理 env（与既有 seed wrapper 相同）。分阶段：P1(dry-run cron/手动) → 达标后 P2 live cron（FR-016：连续 7 天 dry-run 零误判）。

**Rationale**: 与现有调度、日志、alert 约定一致（空 stdout = 正常，非零 = 告警投递）。

**Alternatives considered**: 改 seed_test_comments.py 内嵌（职责混淆、故障域扩大，拒绝）。

## Append-only note — Round A (2026-11-15, T004 list_feed_comments)

Implemented `XiaohongshuPublisher.list_feed_comments(feed_id, creator_nick=None)` in
`vendor/xhs/cdp_publish.py` (new method only; no existing method touched). Chosen path per
R2: single `self._evaluate` call reading the already-loaded feed page — first scans
`window.__INITIAL_STATE__.note.noteDetailMap[*]` for a comments-shaped array (keys
`commentList|comments|comment_list`, else any list whose elements carry
`commentId|comment_id|id`), then falls back to `document.querySelectorAll('.comment-item')`
with `data-comment-id|data-id|comment-id|id|dataset` + sub-reply author scan
(`.sub-comment li`, `sub-reply`, `reply-item`). Optional `creator_nick` param (default None,
signature-compatible) lets the bin tool compute `has_creator_reply` from thread fact
(R3); without it the field is False. Vendor never navigates, never posts, never raises
(all failures → `{"ok": False, "comments": [], "raw_count": 0, "error"}`). No live
probing was performed; DOM fallback selectors are unvalidated against real pages.

## Append-only note — Round B (2026-11-15, T020–T024 + US3 wiring + nits)

dry-run 改为只读 CDP 接线（构造 publisher → connect → per-note scan → 打印计划 →
ledger `dry_run:true/planned`，不写 counter；删掉 `pub is None → return 0` 静默 return）。
`expect_nick` 改必填（三处缺失 → rc 2）。counter 损坏/不可读 → rc 1；
state 坏 JSON/非对象/坏 ISO → rc 1。US2 发布路径：`call_llm`（persona=创作者，
temperature 0.7，可注入）→ `score_content(short_form=True)` ≥ 7.0 →
intent 行（posted_at null，flush+fsync）→ `respond_comment(feed_id, xsec_token,
content, comment_id, comment_author, comment_snippet 前 40 字）` →
done 行 + counter +1；空生成记 failed（FR-017 全灭 → rc 1）；
CDPError 记 failed 且不扣 counter。敌意（FR-008）：逐条扫描顺序处理，遇敌意即中止
（已发布保持），写 `reply_state.json hostile_stop_until = now+48h`，
打印 `aborted=hostile`；dry-run 同语义但不写 counter。孤儿 intent（无 done）
下次运行警告并不自动重发。dry_run 行与 intent 行永不进 live 去重索引。

### Round E addendum — own-profile token from __INITIAL_STATE__

Safe-guard 路径：DOM → state fallback。own-profile 页的笔记链接本身不带
`xsec_token`（`_extract_note_cards_from_profile_dom` 全空是 own-profile 特征），
而 `window.__INITIAL_STATE__.user.notes`（MobX `_value`/`_rawValue` 原子，
`notes._value[0]` 数组 + `noteCard` unwrap） carries `xsecToken`。
`list_profile_notes` 仅在 (a) DOM 得 0 篇或 (b) DOM 全 token 为空时启用
`_extract_profile_notes_from_state`（单次 `_evaluate`、永不导航/抛异常），
按 id 对齐补 token/cover/note_url（DOM 为主、空 title 才补）；他人 profile
（DOM 有 token）不走 state 分支。形态：DOM 0 交互链接 + state 有值。
实测已完成 —— Round F 单测在 node 中执行了 vendored JS（见下条）。

### Round F addendum — own-profile notes collapse 一层修正

根因：live `user.notes._value` 为 length-5 稀疏数组、`[0]` 才是笔记数组。修复：`notes[0]` 是数组则下降一级，不限制 length。验证：真机 dry-run 后 3 篇自有帖均 `scanned=3, pending=0`；node 下执行提取 JS。真实页面形态已由 PM canlı 验证。
