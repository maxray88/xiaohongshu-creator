# CLI Contract: `bin/reply_to_own_comments.py`

项目类型：单项目 CLI（cron 复用）。对 cron 的契约与既有 `seed_test_comments.py` 对齐：空 stdout + rc 0 = 正常/无事；非零 rc 且输出含报告 = 投递 alert。

## Invocation

```
python3 bin/reply_to_own_comments.py [--live] [--max-posts N] [--limit-comments M]
                                     [--max-replies N] [--report]
```

Flags（默认支环境均可）：
- `--live`：实发（US2 发布路径）；缺省为 dry-run。明确规则：**不带 `--live` 即 dry-run**（只读 CDP：构造 publisher → connect → 单帖扫描 → 打印计划 → 写 ledger `dry_run: true` 行；不写 `reply_counter.json`）。
- `--max-posts N`：单次扫描自己最多 N 篇笔记，默认 5。
- `--limit-comments M`：每帖最多向 LLM/回复队列取 M 条评论，默认 10。
- `--max-replies N`：本轮最多回复数，仍被 `reply_counter.json` 日上限 3 封顶（N 默认=剩余额度）。
- `--report`：只读打印 `reply_ledger.jsonl` 可读导出（不触 CDP）。

## Inputs / config resolution

按优先级合成（CLI > 进程环境 > job 文件 `~/.hermes/data/xhs_treehole/engagement_job.json`）：

- `own_profile_url` **或** `own_user_id`（必须有其一；否则 rc 2，用法错误）
- `expect_nick` 或 `XHS_EXPECT_NICK`（**必填**；CLI/env/job 三处皆缺 → rc 2。自回复排除与 thread fact 均依赖它，Round B 起不再警告放行）
- `xsec_token` **不需要**：per-note token 由 `list_profile_notes` 从 profile DOM 取得
- 帖子/评论的 URL token 不入库、不在 argv（避免出现在 ps）

## Behavior contract

1. **Dry-run**（无 `--live`）：只读 CDP 发现（connect → per-note scan → thread-fact 过滤），输出计划（`[DRY-RUN] would reply to ...`）；写 ledger `dry_run: true`、`status: planned` 行；dry-run 不调 LLM（零生成配额消耗）；不写 `reply_counter.json`（与 live 计数隔离）。敌意评论出现即标注并提前结束（`aborted=hostile`），同样写 48h stop、不写计数器。
2. **Live**：gate 顺序 = 端口 9229 allowlist → `ENGAGEMENT_STOP` → 日上限 3（`reply_counter.json` 损坏/不可读 → rc 1）→ 敌意停机窗口（`reply_state.json` 解析失败/坏 ISO → rc 1）→ 配置 gates（`expect_nick` 必填）→ publisher lazy → connect → 逐帖扫描 → thread fact 过滤 → 逐条按扫描顺序处理：敌意出现即中止本轮并写 48h stop → LLM 生成（`call_llm`，persona=创作者，temperature 0.7）→ `score_content(short_form=True)` ≥ 7.0 才发（不过 → ledger `skipped`/`below_threshold`）→ 先写 intent 行（`status: posted, posted_at: null`，flush+fsync）→ `respond_comment(...)` → 成功补 done 行（`posted_at` 落盘）并 +1 counter → `CDPError` 则记 `failed` 行且不扣 counter。`failed > 0` 不中断；全批失败（`failed == eligible`）→ rc 1；否则 rc 0。
3. **输出形状（live / dry-run 同形）**：开始行 `• [reply] notes scanned=N, pending=M`；每条动作 `[DRY-RUN] would reply to <feed 前 8> comment <评论前 8> by <作者>: <预览>`（live 不逐条打印回复正文，只记 ledger）；结尾 `• [reply] done: planned=N posted=N skipped=M failed=K`（敌意中止时为 `done: planned=N posted=N aborted=hostile`）；空 stdout（一切正常且 0 动作）也允许。
4. **退出码**：0 ok（含全跳过）；1 安全拒绝/LLM 整体不可用（FR-017 口径：整批失败才非零；**单条失败仍 0**）/ CDP 失败；2 用法错误。
5. **Cron wrapper** `bin/run_reply_own_comments.sh`：导出与既有 seed wrapper 相同的 LLM 代理 env（`LLM_API_URL/KEY/MODEL`）后 `--live`；同样不传任何 feed/token 参数。

## Output / state files (all under `~/.hermes/data/xhs_treehole/`)

- `reply_counter.json`（写入时裁剪 >45 天键）
- `reply_ledger.jsonl`（FR-015 导出源；`--report` 读它；malformed 行跳过并警告）
- `reply_state.json`（`hostile_stop_until`，ISO8601）
- `ENGAGEMENT_STOP`（既有 kill-switch，共享）

## Failure semantics (mirror of FR-017)

- 单条评论：空生成 → 记 `failed`（`error: empty_generation`）；评分不过 → 记 `skipped`（`reason: below_threshold`）；`CDPError`/发布异常 → 记 `failed`（`error` 截断 200 字）且**不扣 counter**；其余评论继续；run 结尾 `failed=K` 汇报；仅当全批失败（`failed == eligible`，零发布零 clean-skip）rc 才为 1，否则 rc 0。Intent 无 done 的孤儿行 → 下次运行打印「疑似未完成的发布」警告并人工复核，不自动重发。
- LLM 整体不可用：全部待办标注失败、零发布、rc 1。
- CDP 连接失败 / 9229 未登录 / 身份不符：rc 1，零发布。

## 不得/禁止（安全边界，与 spec 一致）

- 永不触碰 9222/9224；永不回复他人帖子、私信、二级线程；永不自我回复；敌意停机窗口内零 CDP。
