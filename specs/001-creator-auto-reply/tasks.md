# Tasks: 创作者自动回复（自己的帖子）

**Input**: Design documents from `specs/001-creator-auto-reply/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: 本仓库约定 require 回归测试（spec 每个 Independent Test + quickstart 的 pytest 场景），测试任务照常包含，且写在实现前（red → green）。

**Organization**: 按 user story 分组；每个 story 可独立实现/测试。所有代码改动走 3-Role（Builder `codex exec` → Reviewer `claude -p`），PM 复核；**任何任务都不得触碰 9229/live Chrome/真实 job 文件**（测试全 fake）。

**Safety-critical context**: 端口 9229 allowlist、`ENGAGEMENT_STOP` 共享 kill-switch、`expect_nick` 身份门禁、dry-run 默认、`reply_counter.json` 独立 ≤3/日、`reply_state.json` 敌意 48h 停机。分析见 research.md（R1–R7）。

## Format: `[ID] [P?] [Story] Description with file path`

## Path Conventions

单项目：`bin/`、`tests/`、`vendor/xhs/`、`core/` 位于仓库根；状态文件在 `~/.hermes/data/xhs_treehole/`（不入库）。

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Verify toolchain baseline green: `python3 -m pytest tests/test_seed_guardrails.py -q -p no:rerunfailures` prints all-pass (current 46) — record output; no file changes
- [X] T002 Add operator-facing stub `bin/reply_to_own_comments.py` skeleton (argparse only, `--live`/`--max-posts`/`--limit-comments`/`--max-replies`/`--report`, exit 2 on misuse) plus header docstring capturing gate order and safety-boundary; run `python3 bin/reply_to_own_comments.py` and confirm it fails closed with "not implemented" rc 1 — specs/001-creator-auto-reply/contracts/cli.md §Invocation is the contract to follow
- [X] T003 [P] Create unit-test double `tests/helpers/`? — 当前 tests 风格：直接用 `importlib.util` 载入并 fake 注入：新增 `test_reply_own_comments.py` 统一 helper（`_mk_own_reply_module()`、`_write_job/...`）的骨架到 `tests/test_reply_own_comments.py`，先写 2 个失败测试（import 失败 → red），随 tasks 推进补齐

---

## Phase 2: Foundational (Blocking Prerequisites) ⚠️

**BLOCKS**: US1/US2/US3；先红灯测试、再实现。

- [X] T004 [P] Vendor: add public method `list_feed_comments(self, feed_id: str) -> dict[str, Any]` to `vendor/xhs/cdp_publish.py` (new method only; no edits to existing methods/tests) — see `_extract_feed_comments_state` for JS style; return `{"ok": bool, "comments": [{comment_id, author, content, created_at, has_creator_reply}], "raw_count": int, "error"?}`; support BOTH shapes: (a) `noteDetailMap[feedId]` containing comments array; (b) fallback `document.querySelectorAll('.comment-item')` with `data-comment-*`/`id` attrs + sub-reply author scan; never navigates, never posts, never raises (return dict with ok=False). Document chosen path in `specs/001-creator-auto-reply/research.md` append-only note
- [X] T005 [P] Job-file/env config loader shared helper in `bin/reply_to_own_comments.py`: resolve (CLI > env `XHS_EXPECT_NICK` / `XHS_OWN_*` > `engagement_job.json` keys `own_profile_url`|`own_user_id`|`expect_nick`)；至多一个 `own_*` 存在（冲突 = rc 2）；文件存在但 unreadable = rc 1 (fail-closed per seed convention)；不存在时必填项缺失 = rc 2；写单测（env/flag/file precedence、冲突、缺失、unreadable）
- [X] T006 [P] State files: `reply_counter.json` 读/写 + 45 天裁剪 + counter corrupt/state 坏 → rc 1 fail-closed（Round B）；`reply_state.json` `hostile_stop_until` 读/写；`reply_ledger.jsonl` 追加 + (`feed_id`,`comment_id`) 去重索引读（损坏行跳过并警告）。函数抽进 `bin/reply_to_own_comments.py` 模块级私有助手，或 `core/reply_state.py`（若违反"不引入core改动"约束则放 bin）——见 contracts/cli.md §State files
- [X] T007 Reusable gate pack wiring order (port 9229 → kill-switch → reply-cap → hostile-stop → config → publisher lazy → probe)：在 `bin/reply_to_own_comments.py` 中实现 `_gates(args)` 返回最终参数或失败原因；零 CDP 时全部可 fake 单测；格式与 `seed_test_comments.py` 平行

**Checkpoint**: Foundational 全部 green 后各 story 再开工。

---

## Phase 3: User Story 1 - 发现自己帖子下的新评论 (P1) 🎯 MVP

**Goal**: scan own notes → structured pending list；dry-run 形状可输出；零发布。

**Independent Test**: fake publisher 返回 1 篇含 2 条他人评论 + 1 条已回评论 + 1 条创作者自回复 → 输出 pending 恰好 2 条、含帖子/作者/内容/评论数；纯 dry-run、零 live。

- [X] T010 [P] [US1] tests/red: `tests/test_reply_own_comments.py::test_discovery_dry_run_lists_pending`（fake publisher：notes=2；comments={feedA: [c1 authorA, c2 creator 已回, c3 authorB], feedB: []}）→ 缺实现先 red
- [X] T011 [P] [US1] tests/red: thread-fact 去重（子回复作者 == expect_nick ⇒ 标记已回复，不进 pending）、创作者自己的评论永远排除、敌意评论（`is_hostile`）标记 hostile 不进 pending、token/id 正则校验 24-hex note id
- [X] T012 [US1] Implement discovery in `bin/reply_to_own_comments.py`: `list_profile_notes()` → per note `get_feed_detail(load_all_comments=True)` → new `list_feed_comments()` → normalize `PendingComment`（feed_id/comment_id/author/content/created_at/has_creator_reply/hostile）；帖子不可访问/加载失败 → 该帖跳过 + 警告，其余继续（FR-014）
- [X] T013 [US1] Dry-run output & ledger: `[DRY-RUN] would reply to…` 每条一行；done 汇总行 `planned=N skipped=M failed=K`；`reply_ledger.jsonl` 写 `dry_run: true` 行；**不写 `reply_counter.json`**；无行为时输出为空（cron 静默）
- [X] T014 [US1] `--report`: 只读 `reply_ledger.jsonl` 打印可读表（ts/feed/comment/dry_run/status）；malformed 行跳过并警告；不触 CDP；不读 job 文件只打印汇总

**Checkpoint**: US1 零发布可独立演示（quickstart 场景 A/B）。

---

## Phase 4: User Story 2 - 以创作者身份自动回复评论 (P2)

**Goal**: live 模式对 eligible 评论生成并发布回复、审计/配额/敌意停机全部生效。

**Independent Test**: fake 发布者 + fake LLM：2 条合格 → 2 条回复各一条、thread fact 不再 eligible；敌意 → 零回复 + `reply_state.json` 写 48h stop；counter=3 → 拒绝；`ENGAGEMENT_STOP` → rc 1、`constructed == []`。

- [X] T020 [P] [US2] tests/red: 意外评论回复路径（reply 语言 persona = 创作者）；低于 QUALITY_SCORE_THRESHOLD → 跳过且标注「不合格」；LLM 抛异常/代理不可用 → 该评论跳过继续 + 结尾 `failed=K`、K>0 但 rc 0；**全批失败 → rc 1**（FR-017）
- [X] T021 [P] [US2] tests/red: 已回复复跳过（thread fact 权威；删 ledger 用同一 fake 重跑，仍零回复）；≤3/日 硬上限；counter corrupt → rc 1 fail-closed（Round B 注）；`hostile_stop_until` 未来 → rc 1；`ENGAGEMENT_STOP` → rc 1；端口 ≠9229 → rc 1
- [X] T022 [US2] Implement generation & publish path: prompt = 创作者 persona + 帖子标题 + 评论原文；`score_content(short_form=True).average >= QUALITY_SCORE_THRESHOLD` 才发；不过 → 跳过标注；通过 → `pub.respond_comment(...)` 并按契约写 ledger/counter（发布后才写）；失败 → 记 `status: failed` 行、continue、最终汇报
- [X] T023 [US2] Two-phase mark for replies：发布前先在 ledger 写 `{status: posted, posted_at: null}`，发布后补 `posted_at`（与 seed 的 two-phase 同模式）；CDPError → 该条 `{status: failed}` 且不扣 counter；单测覆盖
- [X] T024 [US2] Cron wrapper `bin/run_reply_own_comments.sh`（克隆 seed wrapper 变量与共享库约定，导出 `LLM_API_URL/KEY/MODEL`，`--live`，空 stdout=静默）；**不入 git 新增路径泄露任何 token；feed/own_* 一律不从 wrapper 传入**；shellcheck 手审 + `bash -n`

**Checkpoint**: US2 独立跑通（quickstart 场景 A–E 全绿分类）。

---

## Phase 5: User Story 3 - 人工审核与一键停机 (P3)

**Goal**: 运营可读审计导出 + 紧急停机语义验证 + 分阶段执行指引。

- [X] T030 [P] [US3] tests: ledger 损坏行跳过并警告；`--report` 在 live/dry-run 混合日志下输出行数正确；`reply_state.json` 被 US2 写入后本工具再次运行被拒（端到端红测）
- [X] T031 [US3] `docs`: 在 `README.md` 或 `docs/` 增加一段「创作者自动回复」操作说明（operator 配置、dry-run gate、FR-016 分阶段、kill-switch、`--report`），不新增事实只复用 quickstart 内容
- [X] T032 [US3] 验收 dry-run：本地跑 `--live` with fake publisher（monkeypatched sys.modules）在 3 个 fixture 情形 → 全部 rc 0/rc 1 如契约；真实 Chrome 不接触
- [X] T033 [US3] 分阶段落地：`specs/001-creator-auto-reply/quickstart.md` 的「场景 E」与 cron 指令不一致处修正；文档化 dry-run cron 安装（operator 手动，本任务不执行安装）

---

## Phase 6: Polish & Cross-Cutting

- [X] T040 Lint: (round B, reviewer verdict appended later) `python3 -m ruff check bin/reply_to_own_comments.py vendor/xhs/cdp_publish.py tests/test_reply_own_comments.py` 无新增错误（对比 HEAD baseline）
- [X] T041 Suite green: `python3 -m pytest tests/ -q -p no:rerunfailures`（至少 tests/test_seed_guardrails.py 不 regress）
- [X] T042 Reviewer 交付包：本 tasks.md 全部勾选或标注阻塞原因 + diff stat + pytest tail；提交给 Reviewer（`claude -p`）审查（分阶段：foundational → US1 → US2 → US3 可分批提交）
- [X] T043 `git diff --stat`：仅 `bin/reply_to_own_comments.py`、`bin/run_reply_own_comments.sh`、`vendor/xhs/cdp_publish.py`、`tests/test_reply_own_comments.py`（+ 文档/spec 产物），否则回退越界改动（不动进场 WIP）

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
- US1 不依赖 US2/US3；US2 依赖 US1 的 discovery/normalize 与 foundational；US3 依赖 US2 的 ledger/state 行为
- `[P]` 已是可并行任务；implementer 按 T001..T043 顺序或按 Phase 独立交付

## Implementation Strategy

- MVP：`$speckit-tasks` → Phase 2 + Phase 3（US1）→ dry-run 人审形状 → 继续 Phase 4（live 逻辑）→ Phase 5/6
- 每个 Phase 尾跑 `pytest -p no:rerunfailures` 全绿才进下一步
- 验收证据全部落 `tmp/`（Builder 输出、Reviewer 报告），实现不外发任何 CDP/Chrome
