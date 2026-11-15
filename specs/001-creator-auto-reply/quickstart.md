# Quickstart: 验证创作者自动回复（自己的帖子）

前置（单次运营配置）

1. 确认 9229 Chrome 已登录测试号，且 CDP 可达：`~/.hermes/scripts/ensure_chrome.py`（或对应 watchdog）——只做查询，不做发布。
2. 在 `~/.hermes/data/xhs_treehole/engagement_job.json`（chmod 600，不入库）加字段之一：
   - `"own_user_id": "<该号 XHS user id>"` 或
   - `"own_profile_url": "https://www.xiaohongshu.com/user/profile/<id>"`
   并确保已有 `"expect_nick": "<测试号昵称>"`（**必填**；缺失 → rc 2，dry-run/live 均拒绝）。
3. LLM 代理（127.0.0.1:15721）在线是 **live 前置**；dry-run 不调 LLM，代理在线与否与 dry-run 无关。

## 场景 A — dry-run（只读 CDP，禁止发帖）

```
cd ~/02_Cronjobs_Projects/01_XHS_Daily_Post
python3 bin/reply_to_own_comments.py            # 无 --live 即 dry-run
```

期望：
- 只读连接 CDP（connect + 读评论区，零发帖、零写 `reply_counter.json`；dry-run 不调 LLM）
- 打印汇总行 `• [reply] notes scanned=N, pending=M` + 每条 `[DRY-RUN] would reply to …`（若有）（先用一小批验证提取器）
- 每条合格评论一行 `[DRY-RUN] would reply to <note>…comment … → <回复内容预览>`
- 结尾 `• [reply] done: planned=N skipped=M failed=K`
- `reply_ledger.jsonl` 出现 `dry_run: true` 行；`reply_counter.json` **不**变化

重复跑两次：第二次仍打印相同计划（thread fact 不变），说明发现是稳定的；contrived「子回复含创作者昵称」的 fake 单测才断言去重生效（见 data-model.md R3）。

## 场景 B — 无效果/无评论

自建一条无评论帖子：期望输出 `notes scanned=N, pending=0`、`rc=0`、空动作。

## 场景 C — 安全拒绝（必测）

```
PORT 换成 9224（测试夹具，不在 live Chrome）→ rc 1 且 `FakePublisher.constructed == []`（等价：真实浏览器零连接）
ENGAGEMENT_STOP 文件存在 → rc 1，零输出动作
expect_nick 必填：缺失（CLI/env/job 三处皆无）→ rc 2；`reply_counter.json` 损坏/不可读 → rc 1；`reply_state.json` 坏 ISO/非对象 → rc 1
reply_state.json 写入未来 hostile_stop_until → rc 1 零 CDP
```

## 场景 D — 单测守护（CI/容门禁）

```
python3 -m pytest tests/test_reply_own_comments.py -q -p no:rerunfailures
```

期望：全部通过；全程无真实 CDP/Chrome 触达（`FakePublisher` 注入）。

## 场景 E — 分阶段放行（FR-016）

1. 干跑 cron 手动/定时跑满 7 天，逐日核对：发现的评论清单与主页实际情况一致；误判（回了本不该回）=0。
2. 任一天发现误判 → 清零观察日，修复后重计（spec FR-016）。
3. 达标后由运营者手动：在 `run_reply_own_comments.sh` 或 cron 配置里切到 `--live`；`reply_counter.json` 每日清零 ≤3。
4. 上线后首周每天看 `--report` 输出；任何异常 → 建 `ENGAGEMENT_STOP` 立即停机。

## 验收映射

- SC-002/SC-003：场景 A/B + 单测
- SC-004：场景 C
- SC-005：`python3 bin/reply_to_own_comments.py --report` 输出
- SC-006：场景 A 与 live 的输出结构一致（同字段），仅多/少「posted vs planned」字样
- FR-016：场景 E
