# Data Model: 创作者自动回复（自己的帖子）

所有实体均为运行时内存对象 + 本地 JSON/JSONL 持久化形态。持久化根目录 `~/.hermes/data/xhs_treehole/`，不入库。

## OwnPost

| Field | Type | Notes |
|---|---|---|
| feed_id | string | 24 位 hex note id（`/explore/<id>`） |
| xsec_token | string | per-note token，来自 profile 页链接 |
| note_url | string | 完整绝对 URL（含 token 时请求成功） |
| title | string | 可能为空（profile DOM 文本） |
| cover | string | 图片 URL，可为空 |

来源：`list_profile_notes(user_id=<own_user_id> \| profile_url=<own_profile_url>, limit=N)`。
验收约束：`feed_id` 通过正则 `[0-9a-zA-Z]{24}` 强校验；无法解析的卡片跳过并计数。

## PendingComment

| Field | Type | Notes |
|---|---|---|
| feed_id | string | 所属帖子 |
| comment_id | string | XHS 评论 id（`data-comment-*`/`id` 属性；用于去重与回复定位） |
| author | string | 评论作者昵称 |
| content | string | 评论正文（已 normalize） |
| created_at | string | 若 vendor 可得则 ISO8601，否则空串并按 DOM 顺序处理 |
| has_creator_reply | bool | 子回复中出现创作者昵称 → True |
| hostile | bool | `is_hostile(content)`（`core/commenting.py` 既有关键词） |

流转：`seen → eligible（他人+未回复+非敌意）→ replied | skipped(reason)`；`eligible` 才进入 LLM 生成。

## CreatorReply

| Field | Type | Notes |
|---|---|---|
| feed_id | string | 回复目标评论所属帖子 |
| comment_id | string | 被回复评论 |
| content | string | LLM 生成、≥阈值的回复正文 |
| dry_run | bool | true=计划未执行；false=实发 |
| ts | string | ISO8601 |

写入 `reply_ledger.jsonl`。

## ReplyLedger (reply_ledger.jsonl)

每行一条 JSON 对象（= CreatorReply）。用途：FR-015 可读导出 + FR-007 去重的加速缓存；**权威去重仍以帖子侧 `has_creator_reply` 为准**（SC-003）。读回时：按 `(feed_id, comment_id)` 建索引；存在行 ⇒ 跳过 LLM（generation 已发生）。损坏行：跳过该行并警告，不阻塞运行。

## Counter / State files

- `reply_counter.json`：`{"YYYY-MM-DD": int}`，写入时裁剪 45 天前键（照抄 `_write_counter`）。超过 `REPLY_HARD_CAP_PER_DAY = 3`（FR-005 独立计数器）则拒绝 live。
- `reply_state.json`：`{"hostile_stop_until": "<ISO8601>"|null}`，敌意停机 48h（FR-008）。`now < hostile_stop_until` ⇒ 本轮拒绝，零 CDP。
- 日志 `reply_ledger.jsonl` 兼作 FR-015 导出源：`python bin/reply_to_own_comments.py --report` 可读表输出（谁、何时、哪帖）。

## 与既有实体的关系

- 复用 `EngagementSequence` 不适用（固定节拍为播种设计）；本功能是「按评论驱动即时回复」，无固定 timeline。
- `PendingComment.hostile` ⇒ 触发 `reply_state.json` 更新 + 该评论跳过。
- `CreatorReply.content` 生成链与既有 `COMMENT_THRESHOLD` 一致：`score_content(short_form=True).average >= QUALITY_SCORE_THRESHOLD`（`core/xhs_config.py`，7.0）。
