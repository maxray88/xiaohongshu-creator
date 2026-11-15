# Feature Specification: 创作者自动回复（自己的帖子）

**Feature Branch**: `001-creator-auto-reply`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "Spec-kit to adjust the commenting mechanism so that it scans own posts and comments only the user's comments automatically" — after one clarifying round: scan the test account's OWN posts and automatically reply to (the people who commented on) them as the creator; test account only.

## 背景（既有事实，供计划阶段引用）

- 现有「情绪树洞」子系统已包含：通用 supportive 评论播种（`bin/seed_test_comments.py`，9229 测试号，CDP 端口 allowlist、ENGAGEMENT_STOP kill-switch、每日硬上限、pool 预审文案、两阶段标记、身份门禁），以及一套**休眠中的回复线程脚手架**（核心模块中已有敌意检测、每帖回复上限、回复节流等原语，但没有被调度激活）。
- 现有工具的缺口：它只会把预审好的 supportive 评论发到**固定的一条帖子**上；它不会发现「自己的帖子」、不会读自己帖子下的新评论、也不会以创作者身份回复。

## Clarifications

### Session 2026-11-15

- Q: 系统如何得知测试号「自己的帖子」在哪？ → A: job 文件中运营者一次性配置 `own_profile_url` 或 `user_id`（Option A），系统直接读；不做 DOM 自动发现。
- Q: 运行中途 LLM 代理不可用 / 某条回复生成或质量判定失败怎么办？ → A: 跳过该条并在清单标注原因（LLM不可用/不合格），处理其余；run 结尾汇报失败数；下次运行自动重试（去重以帖子侧事实为准）（Option A）。
- Q: 上线初期如何调度？ → A: 分阶段：先 dry-run 手动/cron 观察 ≥1 周，验证发现质量后，由运营者手动切换 live cron（Option A）。
- Q: dry-run 观察期放行到 live 的门槛是什么？ → A: 连续 7 天 dry-run 零误判（误回他人评论/回复了自己已发布的/敌意被回复即清零重计）；漏判只警告不阻断放行（Option A）。
- Q: FR-004 原「dry-run 不触浏览器」与发现流程冲突怎么办？ → A: 运营者决策 = 只读 CDP（导航+读，禁止发帖，不写 live 计数器）；plan/quickstart 同步修订（2026-11-15）。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 发现自己自己帖子下的新评论 (Priority: P1)

运营者（9229 测试号）每天运行/调度一次扫描：系统列出该账号自己发布的笔记，逐帖检查评论区，识别出「我（创作者）还没有回复过」的他人的新评论，并产出一份待回复清单。

**Why this priority**: 没有「发现」就没有回复；这也是与既有固定 feed 播种的根本区别。VP1 之后链路可独立演示（scan → 待办列表），验证发现的准确率后再接自动回复。

**Independent Test**: 在测试号上造一条带 2 条新评论的帖子 → 运行扫描 → 产出恰好这 2 条且只含未回复评论 → 再跑一次输出为空（去重有效）。

**Acceptance Scenarios**:

1. **Given** 测试号拥有 3 篇帖子，其中 1 篇有 2 条创作者未回复的评论、1 篇全部已回复、1 篇无评论，**When** 扫描，**Then** 清单只包含未回复的 2 条，含帖子、评论作者、评论内容、评论时间。
2. **Given** 上一条清单已被标记处理，**When** 再次扫描，**Then** 不产生重复项。
3. **Given** 帖子详情页不可访问（删除/隐私/违规），**When** 扫描，**Then** 该帖被跳过并记日志，其余帖子不受影响。

---

### User Story 2 - 以创作者身份自动回复评论 (Priority: P2)

运营者开启自动模式后，系统对 User Story 1 找出的每条合格评论自动生成一条创作者回复并发布；每条评论最多回复一次；每日总量受硬上限约束；遇敌意评论即停。

**Why this priority**: 这是最终价值出口，但必须建立在「发现」稳定的基础上，否则会对错误对象高频施暴。

**Independent Test**: 造一条含敌意评论的帖子 + 一条普通评论 → 运行 → 普通评论被回复且内容上下文相关；敌意评论未被回复且触发停机窗口；`ENGAGEMENT_STOP` 存在时整个动作全拒绝、零 CDP 副作用。

**Acceptance Scenarios**:

1. **Given** 发现 2 条合格新评论，**When** 自动回复流程，**Then** 产出 2 条与评论内容相关的回复，且每条评论下有且仅有一条作者为创作者的回复。
2. **Given** 某评论已被创作者回复过，**When** 再次扫描/回复，**Then** 不重复回复。
3. **Given** 某评论被判定为敌意（含举报/辱骂等关键词），**When** 处理，**Then** 不回复该评论，记录并进入敌意停机窗口（48 小时内不再自动回复）。
4. **Given** 当日已回复数达到硬上限，**When** 继续发现新评论，**Then** 停止回复，等到次日。
5. **Given** `ENGAGEMENT_STOP` 文件存在或 CDP 不可达，**When** 任何回复动作，**Then** 拒绝执行且不触碰浏览器。

---

### User Story 3 - 人工审核与一键停机 (Priority: P3)

运营者能随时查看最近的自动回复记录（回复了什么、对谁、何时），并通过单一开关文件/环境变量彻底停机；误回错号（非 9229）时门禁直接杀掉进程。

**Why this priority**: 安全与可审计是既有 try-out 体系的核心风格；此功能比通用播种更接近「公开主页自证」场景，事故半径更大。

**Independent Test**: 从 REPLY 日志重建一列「已回复」清单与帖子评论区实际状态一致；删掉日志文件重来能恢复去重（以评论区实际状态为准）；把端口改成主号 → 门禁拒绝且零副作用。

**Acceptance Scenarios**:

1. **Given** 已发生自动回复，**When** 读取审计日志，**Then** 每条含时间、帖子、评论、回复内容、dry-run/live 标记。
2. **Given** 重置审计日志后重跑，**When** 帖子下已有创作者回复，**Then** 不重复回复（以帖子侧事实为准，日志只是缓存）。
3. **Given** 运行目标不是 9229，**When** 启动，**Then** 端口门禁拒绝、零浏览器连接。

---

### Edge Cases

- 自己的帖子数量超过单次扫描负荷（几十篇）→ 只处理最近 N 篇或最近 M 条未回复评论，超额顺延到下次。
- 评论区加载失败 / 页面结构变化 → 跳过该帖并日志，不重试风暴；连续多次失败可告警。
- 同一评论被多个账号用相同文字提问 → 去重键必须基于评论 ID 而非文本。
- 创作者自己在评论区的回复 → 永远不计入「待回复」（不能自我回复循环）。
- 删除/隐藏评论、xsec_token 过期 → 记日志跳过，不阻塞其他帖子。
- 9229 浏览器未登录 / 身份不符 → 拒绝执行（fail-closed），不打 post。
- 大量评论涌入（活动/爆款）→ 当日硬上限封顶，剩余顺延。
- LLM 代理整体不可用 → 本轮全部待办标注失败、零回复、汇报失败数；下次运行重试（不 fail-stop，沿用逐条跳过语义）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST 列举测试号（9229）自己发布的笔记，来源为本地 job 文件中运营者一次性配置的 `own_profile_url` 或 `user_id`（不自动发现 DOM）；至少包含标识、标题、URL/token。
- **FR-002**: System MUST 对每篇笔记提取评论列表（含评论 ID、作者、内容、时间、是否已有创作者回复）。
- **FR-003**: System MUST 识别「创作者未回复」的他人评论为待办项；创作者自己的评论永远排除。
- **FR-004**: System MUST 支持 dry-run 与 live 两种模式。dry-run 只读 CDP：允许连接 9229、导航自己的帖子页、滚动/读取评论区；禁止发帖、禁止写入 live 计数器（`reply_counter.json`）；ledger 可写 `dry_run: true` 记录；dry-run 产出与 live 同形状的计划（planned=N skipped=M failed=K）。（2026-11-15 决策修订：原「不触浏览器」无法覆盖发现流程，已与运营者确认改为只读 CDP）
- **FR-005**: System MUST 提供每日自动回复硬上限：独立计数器，≤ 3/日（与既有播种的 ≤ 3/日互不占用）。
- **FR-006**: System MUST 复用既有安全闸门：端口 9229 allowlist、`ENGAGEMENT_STOP` 一键停机、身份门禁（昵称一致才放行）、CDP 不可达 fail-closed。
- **FR-007**: System MUST 对每条待办只回复一次（跨运行去重）；去重以「评论区是否已有创作者回复」为准，审计日志为辅。
- **FR-008**: System MUST 对敌意评论不回复，并触发既有敌意停机窗口（48 小时）。
- **FR-009**: System MUST 保证单条帖子内创作者回复数不超过每线程上限（REPLY_MAX_PER_THREAD，默认 2）。
- **FR-010**: System MUST 记录审计日志（时间、帖子、评论、回复、模式、干跑/实发）。
- **FR-011**: System MUST 只回复「他人对自己帖子的评论」——不回复帖子本身、不回复私信、不回复他人帖子、不自我回复。
- **FR-012**: 回复内容合格标准 MUST 可判定：LLM 按评论上下文生成（依赖 LLM 代理 127.0.0.1:15721 在线）；每条回复须通过与既有评论播种同等的质量门槛（score ≥ QUALITY_SCORE_THRESHOLD，活跃配置值）；不过则不回复；dry-run 同样消耗 LLM quota。
- **FR-013**: System MUST 对「哪些评论值得回复」给出明确判定：他人 + 未被创作者回复过 + 非敌意 + 顶层评论；不区分评论类型；容量由 FR-005 硬上限封顶；二级线程不递归。
- **FR-014**: System MUST 在帖子不可访问或该帖评论加载失败时跳过该帖，继续处理其余帖子（不阻塞、不重试风暴）。
- **FR-015**: System MUST 提供审计日志的可读导出（谁、何时、哪帖、回了什么），供人工复核。
- **FR-016**: live 切换 MUST 以 dry-run 门禁为前置：连续 7 天 dry-run 零误判（误回他人评论/回复了自己已发布的/敌意被回复即清零重计）；漏判只警告不阻断放行；达标后由运营者手动切换至 live cron。
- **FR-017**: 某条评论的回复生成或质量判定失败时，System MUST 跳过该条并在待办清单标注原因（LLM不可用/不合格），不阻塞同批其余评论，run 结尾汇报失败数，失败项留待下次运行自动重试。

### Key Entities *(include if feature involves data)*

- **OwnPost**: 测试号自己发布的一篇笔记（标识、标题、URL/token、可访问性、评论数）。
- **PendingComment**: 一篇帖子下一条待回复的他人评论（评论 ID、作者、内容、时间、所属帖子）。
- **CreatorReply**: 创作者对某条评论已发布的回复（对应评论 ID、内容、时间、模式）。
- **ReplyLedger**: 跨运行去重与配额统计的持久化记录（按日计数、按评论 ID 去重；可被帖子侧事实纠偏）。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 扫描 5 篇帖子（共计评论 ≤ 50 条）在单次运行内完成，不超过一次 CDP 连接生命周期。
- **SC-002**: 漏回复率 = 0：运行后，帖子下每一条「他人 + 无创作者回复 + 非敌意」的评论，要么本轮被回复、要么被明确标注跳过原因（配额耗尽/线程上限/敌意/不可访问）。
- **SC-003**: 重复回复率 = 0：对同一条评论连续运行 3 次，回复数不超过 1。
- **SC-004**: 事故半径可控：9229 身份不符时零评论被发布；`ENGAGEMENT_STOP` 存在时零 CDP 调用。
- **SC-005**: 运营者可在 1 分钟内从审计日志读出「今天自动回复了哪些评论、回了什么」。
- **SC-006**: dry-run 输出与 live 执行结果在集合关系上一致（计划 = 实际，除 CDP 失败外）。

## Assumptions

- 目标账号固定为 9229 测试号（无限复活/对应昵称）；不覆盖主号（9224/9222），不覆盖私信、不覆盖他人帖子。
- 沿用既有 try-out 风格：fail-closed 安全闸门、人审兜底、先 dry-run 再 live、节奏节流。
- xsec_token 通过既有本地 job 文件机制注入（不入库）；身份期望昵称沿用既有 `expect_nick` 约定；`own_profile_url`/`user_id` 以同一 job 文件机制配置（不入库）。
- 上线分阶段：dry-run 观察 ≥1 周（门禁 = 连续 7 天零误判，见 FR-016）后由运营者手动切换 live cron。
- 去重以帖子侧事实（是否已有创作者回复）为准，审计日志（reply ledger）只做加速与配额统计。
- 回复目标仅限「顶层他人评论」；二级回复线程不递归。
- 帖子列表来源沿用账号 profile 页列举（limit 可配），不依赖开放平台 API。



