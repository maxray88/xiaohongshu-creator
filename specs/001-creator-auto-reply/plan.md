# Implementation Plan: 创作者自动回复（自己的帖子）

**Branch**: `001-creator-auto-reply` | **Date**: 2026-11-15 | **Spec**: [specs/001-creator-auto-reply/spec.md](spec.md)

**Input**: Feature specification from `/specs/001-creator-auto-reply/spec.md`

## Summary

在 9229 测试号上，新增一个 CLI 工具 `bin/reply_to_own_comments.py`：列举自己帖子 → 逐帖 `get_feed_detail(load_all_comments=True)` 取评论 → 过滤出〔他人 + 未被自己回复 + 非敌意 + 顶层〕评论 → LLM 按上下文生成并用既有质量门槛过线 → 通过 `respond_comment` 回复 → 每日 ≤3 条、每条评论仅一条。dedupe 以帖子侧 thread fact 为权威，`reply_ledger.jsonl` 只做加速与导出；上线分阶段（先 dry-run ≥7 天零误判，再人工切 live cron）。

## Technical Context

**Language/Version**: Python 3.11（pyenv `~/.pyenv/versions/3.11.15/bin/python3`）

**Primary Dependencies**: 既有 vendored `vendor/xhs/cdp_publish.py`（`XiaohongshuPublisher`：`list_profile_notes` / `get_feed_detail` / `respond_comment` / `probe_current_nickname`）；既有 `core/commenting.py`（LLM 生成 + `score_content` 质量门槛）、`core/xhs_config.py`（`QUALITY_SCORE_THRESHOLD`）、`core/xhs_paths.py`

**Storage**: 本地 JSON/JSONL（`~/.hermes/data/xhs_treehole/reply_counter.json`、`reply_ledger.jsonl`、`reply_state.json`）

**Testing**: pytest（`python3 -m pytest tests/... -q -p no:rerunfailures`），`FakePublisher` sys.modules 注入、`importlib.util` 载入 bin 模块、不触网/不触 CDP

**Target Platform**: macOS + Chrome CDP 9229（desktop）

**Project Type**: CLI（cron 复用），单项目

**Performance Goals**: 5 篇自有帖 + ≤50 条评论单次扫描 < 一次 CDP 生命周期；≤3 条 live 回复/日

**Constraints**: dry-run 只读 CDP（导航+读，禁止发帖，不写 live 计数器）；fail-closed；端口 9222/9224 永远拒绝；LLM 代理（127.0.0.1:15721）在线前提下回复生成

**Scale/Scope**: 1 个测试号、≤~10 篇自有帖、≤3 回复/日、顶层评论

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

仓库 `.specify/memory/constitution.md` 仍为未填模板 → 无形式化 project gates。按仓库规约把关（等价性门禁，全通过）：
- ✅ 测试号专用（端口 allowlist + 身份门禁），无主号事故面
- ✅ fail-closed，dry-run 先行 + 人审抽查后 live
- ✅ 不削弱既有安全闸门（ENGAGEMENT_STOP 复用）
- ✅ 改动 → 3-Role（Builder `codex exec` + Reviewer `claude -p`），PM 复核
- ✅ 不写密钥：所有秘密走 chmod 600 job 文件/本地 env，零入库
- ✅ 不引入新依赖、不改 XHS 上游 vendor（仅新增公开提取方法）

**Post-design re-check**（Phase 1 结束后再核）：无新增违规（存储/接口/阶段均限于本地文件 + CLI；无并发、无外部新服务）。

## Project Structure

### Documentation (this feature)

```text
specs/001-creator-auto-reply/
├── plan.md          # This file
├── research.md      # Phase 0: R1-R7 decisions with file:line evidence
├── data-model.md    # Phase 1 entities + persistence files
├── quickstart.md    # validation scenarios & staged rollout
├── contracts/
│   └── cli.md       # CLI contract (flags, gates, exit codes, state files)
└── tasks.md         # (/speckit.tasks, NOT created here)
```

### Source Code (repository root)

```text
bin/
├── reply_to_own_comments.py      # NEW: CLI entry (scan → filter → LLM → reply)
├── run_reply_own_comments.sh     # NEW: cron wrapper (exports LLM proxy env, --live)
├── seed_test_comments.py         # UNCHANGED
└── _xhs_common.sh                # reused (require_python / run_project_python)

core/
└── commenting.py                 # reuse replies primitives as-is; add list_feed_comments? no — vendor

vendor/xhs/
└── cdp_publish.py                # add ONE new public method: list_feed_comments() (R2)

tests/
└── test_reply_own_comments.py    # NEW: fake publisher, dry-run/live/gates/dedupe/cap/hostile

~/.hermes/data/xhs_treehole/      # state (NOT in repo)
├── engagement_job.json           # + own_profile_url | own_user_id (operator-managed)
├── reply_counter.json            # ≤3/day, independent of seeding
├── reply_ledger.jsonl            # audit/FR-015 export; dedupe cache (thread fact wins)
└── reply_state.json              # hostile_stop_until (48h)
```

**Structure Decision**: 单项目、cron 可复用的 CLI；新入口与既有 seed 同目录同风格（lazy publisher、gate 顺序、dry-run 默认），不复用 `seed_test_comments.py` 的固定 feed 语义。vendor 仅新增提取方法，不改既有方法。

## Phase 0: Outline & Research

见 [research.md](research.md)。R1–R7 全部定案，无 NEEDS CLARIFICATION 遗留：

- R1：own posts = `list_profile_notes`（profile DOM，含 feed_id+xsec_token）
- R2：comments = `get_feed_detail(load_all_comments=True)` + 新增 JS 提取器（vendor 缺该能力——已核实，dry-run 样例需人审形状）
- R3：去重 = thread fact（子回复作者 == 创作者昵称）为权威；ledger 仅加速
- R4：生成 = LLM（`LLM_API_URL=http://127.0.0.1:15721/v1`）+ `score_content(short_form=True)` ≥ 7.0；失败/不合格 → 跳过标注（FR-017）
- R5：状态文件 3 个（counter/ledger/state），全部同目录同原子写法
- R6：安全闸整包复用（port/kill-switch/reply-cap/hostile-stop/identity probe）
- R7：cron 分阶段；dry-run 消耗 LLM quota（既定）

## Phase 1: Design & Contracts

- [data-model.md](data-model.md) — OwnPost / PendingComment / CreatorReply / ReplyLedger + 持久化文件
- [contracts/cli.md](contracts/cli.md) — CLI 契约：flags、config 解析、gate 顺序、退出码、state files、FR-017 失败语义、安全边界
- [quickstart.md](quickstart.md) — 场景 A–E：dry-run 形状 → 无评论 → 安全拒绝（端口/kill-switch/身份/敌意）→ 单测 → FR-016 分阶段放行

**Unknowns resolved**: per-note xsec_token（R1/R2）、comment_id/has_creator_reply 可获取性（R2/R3）、LLM 失败语义（FR-017）、配额隔离（R5）、上线门禁（FR-016）。

**Risk to flag**: R2 的 `list_feed_comments` JS 提取器依赖 noteDetailMap/DOM 真实形状——dry-run 样例（场景 A）是验证节点；若 XHS state 无评论字段，回退为 comment-item DOM 抓取（仍可得 id/文本/子回复作者），实现在 tasks 阶段定稿，plan 不再返工。

## Complexity Tracking

> 无 Constitution 违规需论证（模板 constitution 无 gates；规约全部通过）。本表不填。

## Phase 2 next

`$speckit-tasks` 生成任务清单；实现走 3-Role（Builder + Reviewer）。
