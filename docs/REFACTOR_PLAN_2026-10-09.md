# XHS_Daily_Post 重构方案（可执行版）

- 版本：**v2 · 2026-10-09**（v1 为只读诊断报告，已过 Reviewer 审查并订正）
- 状态：**已审查 · 可执行**。v1 结论为 FAIL（不可直接照做），本版已消化全部订正
- 上游：v1 诊断 `/tmp/xhs_refactor_report.md`（306 行）· Reviewer 报告 `/tmp/xhs_refactor_review_out.txt`（130 行，11 条 BUG）
- 范围：`core/` + `bin/` + `tests/` + `generators/` + `design/`（`vendor/xhs/` 快照 6195 行仅作参照，**不拆**）
- 方法：逐文件 `wc -l` + `grep import/except/sys.path/BASE/sleep` 实测；**不跑 `bin/` 脚本、不碰 Chrome**

> **给 Reviewer / Builder 的说明**：本文档是执行规格。每步 §4-Sx 都写明了目标模块、来源行号、影响文件、验证命令、回滚方式。所有数字均经 PM 独立复验（见 §7 证据链）。

---

## 1. 本版相对 v1 的订正（Reviewer 11 条 + PM 2 条）

| # | v1 声称 | 实测 | 处置 |
|---|---|---|---|
| **R1** | `_cron_assemble` 13 个顶层 def | **14 个**（漏 `read_post_data:61`） | 已订正，全文改 14 |
| **R2** | quality 侧比对在 `:161-231` | L161 是自愈逻辑；**真实比对在 `:222-257`** | 已订正 |
| **R3** | `time.sleep` 20 处 | **19 处**（v1 附录自列加总即 19） | 已订正 |
| **R4** | `assemble:555` timeout=120/300 | **180**（120/300 是同文件 301/402/442 行的值） | 已订正 |
| **R5** | §4「必须按此序」S1 先 / §6「S2 第 1 做」 | **两处打架**；且 S1/S2/S3 代码上相互独立，**不存在拓扑依赖** | 见 §3，统一为 S1→S3→S2 |
| **R6** | tracker(467 行 GOD-FILE) 无处置 | v1 自定三个 GOD-FILE，方案只处置两个 | 见 §5，补 T1/T2 |
| **R7** | `except Exception` 35 处 | **41 处**（v1 附录自列加总即 41） | 已订正 |
| **R8** | `tab_lifecycle:51` 是「默认参」 | :51 是 **docstring 用法示例**；真实默认在 `:194-195` getattr 回退 | 已订正 |
| **R9** | `find_latest` 行号 `v1:63-81/v2:75-101` 疑似笔误 | **完全正确**（image `find_latest_v1_dir:63`、video `find_latest_v2_dir:75`） | **PM 驳回 Reviewer 此条** |
| **R10** | 「TTS **计费**」 | 项目用 **edge-tts（免费）** | 已订正；「不可重跑」的理由改为**耗时+当日时效** |
| **R11** | `_has_emoji` 三处「逐字一致」 | 逻辑一致，但 `quality:66` 版**无 docstring**（另两处有 So/Sk 注释） | 措辞精确化 |
| **PM-1** | `test_draft_shared` 只覆盖 video | L65-68 **有** image 身份测试，但仅断言函数同一性 | 结论正确、措辞订正（Reviewer 复核认可） |
| **PM-2** | — | `core/draft_shared.py`（拟建）与 `tests/test_draft_shared.py`（已存）**不构成命名风险**（不同目录、pytest 只收 `test_*`） | Reviewer 独立确认 |

**一处模式**：v1 的**附录表格逐项加总都是对的**（sleep 19、except 41），但**正文汇总句写错**。疑似汇总时手误 —— 本版所有汇总数字已从附录重新加总核对。

---

## 2. 诊断结论（数字订正后仍成立）

**规模**：实现代码 35 个 `.py` **7296 行**（core 14 文件 3319 + bin 4 文件 985 + generators 111 + design 89 + tests 15 文件 2792）；`vendor/` 6195 行不计入。

**健康度：C** —— 正确性已修好（2026-09-27 审计 17 个 HIGH 清零、15 个测试文件守门），但结构债会持续制造「改一漏二」类 bug。

**前置承认（已修复，不再立项）**：
- `core/manifest_title.py:45-83` 已统一 title 三落法
- `core/tab_lifecycle.py:45-208` 已统一 tab 生命周期（5 处共用 `ManagedPublisher`）

### 2.1 三个 GOD-FILE

| 文件 | 行数 | def 数 | 职责 | 判定 |
|---|---|---|---|---|
| `core/_cron_assemble.py` | **626** | **14** | 目录解析/manifest IO/TTS 切片/edge-tts/ffmpeg 合成/主编排 | **GOD-FILE** |
| `core/xhs_performance_tracker.py` | **467** | **13** | CDP 抓取/分页/数字解析/归因/报告 | **GOD-FILE** |
| `bin/check_xhs_pipeline.py` | **447** | 8 | 制品检查/cron 状态/内容合规/标题一致/HTTP 探针 | **GOD-FILE** |

### 2.2 核心问题（P0）

```
P0-1  core/_cron_assemble.py:20-626
      业务逻辑 + I/O + 状态 + 错误处理四合一；零项目内 import（自闭环）。
      改 TTS 切片必碰 ffmpeg 代码 → 全文件回归。已出过 H12/H17 同类 bug。

P0-2  core/xhs_video_draft.py + core/xhs_image_draft.py
      复刻约 150 行：草稿计数 JS（video:40-66 vs image:31-49，仅空白风格差异）、
      找目录、导航重试（同参 attempts=3/wait=8）三套对应。
      且 xhs_image_draft:16 反向 import video 的 save_confirmed_in ——
      SAVE_MARKERS 只在 video:19-35 定义，**图文依赖视频，方向反了**。
      已有分叉实证（JS 空格风格、注释文案已不一致）。

P0-3  bin/check_xhs_pipeline.py:161-257 与 bin/check_content_quality.py:222-257
      约 40 行标题/tag/身份/rotation 比对重复。
      形态不同（problems.append vs check 评分表），属**逻辑重复非逐行复制**。
      06:00 误报/漏报直接吵醒人或掩盖故障（H9 前科）。
```

### 2.3 P1 / P2 摘要

| 级 | 问题 | 关键证据 |
|---|---|---|
| P1 | 配置魔法值无统一 | `BASE` **8 处**（三种写法）、`CDP_HOST/PORT` **5 文件**、URL 4 种字面量、timeout 8 种 |
| P1 | `_atomic_write_json` 三份复刻 | `humanize:226` / `render:18` / `quality:35`；读侧三种容错语义 |
| P1 | 三处 sh 绕过 import 入口 | `open_xhs_creator.sh:16` 手写 sys.path / `render_xhs_cards.sh:108-109` 系统 python3 / `assemble_xhs_treehole.sh:5` 不 source |
| P1 | `pick_theme` 与 `validate_rotation` 分叉 | ⚠️ **含正确性陷阱，见 §6** |
| P1 | 主题自选逻辑三处 | `quality:45-65` / `build_v2:45-101` / `design/validate_theme:20-89` |
| P2 | `except Exception` **41 处** + 6 处静默 | 无裸 `except:`（H2 已修）；约 25 处合理降级 |
| P2 | `time.sleep` **19 处**无统一退避 | 见 §7 分布表 |
| P2 | 测试失衡 | `test_tab_lifecycle.py` 509 行一家独大；draft 单向覆盖 |

---

## 3. 实施顺序（本版唯一权威，覆盖 v1 的 §4/§6 矛盾）

v1 的 §4 说「依赖拓扑决定，必须 S1 先」，§6 说「S2 第 1 做」—— **两处直接打架**。
Reviewer 进一步指出：**S1/S2/S3 三模块代码上相互独立，根本不存在真正的拓扑依赖**（v1 的「S3 依赖 S2 的手法」是方法论，不是代码依赖）。故 v1 那句「必须按此序」前提即错。

**本版按「风险 × 收益」重排：**

```
S1  拆 _cron_assemble          ← 先做：零项目内 import、有 173 行测试护着，最安全
S3  合并双检查器公共部          ← 只读检查器，改坏不写数据
── 补 image 端到端测试 ──       ← S2 的前置条件（v1 与 Reviewer 一致要求）
S2  抽 draft_shared            ← 动 03:00/05:00 live 双链路，测试补齐后才做
S4  配置 + IO 集中
S5  sh 入口统一
```

**为什么 S1 先于 S2（v1 建议顺序是反的）**：
- S1 拆的是**唯一零项目内 import 的自闭环**，拆它不牵连任何 cron 文件；TTS 切片已有 `tests/test_tts_slicing.py`（173 行）保护
- S2 动的是 **03:00/05:00 双 cron 直调链路**，且测试缺口已知（image 无端到端用例）—— 放第一步风险最高
- v1 的理由「先拿 S2 建立信心」不成立：**信心应来自最安全的一步，不是最高收益的一步**

工作量合计 **19–31h（3–4 天）**。每天只合一步，每步前后全量 `pytest` 留底。

---

## 4. 分步执行规格

### 通用回滚策略

新模块 + **旧函数转发共存一版**（deprecation shim），cron 入口路径不变；`git checkout` 以文件为粒度；每步前后各跑一次 `python3 -m pytest tests/ -q` 留底。

### 通用验证（每步必跑）

```
python3 -m pytest tests/ -q          # 全绿
python3 -m pyflakes core/<新模块>     # 零警告
```

**禁跑 `bin/` 真实发布脚本。**

---

### S1 · 拆 `core/_cron_assemble.py`（626 行 → 编排壳）

**目标新文件**（均在 `core/`）：

| 新模块 | 内容 | 来源行号 |
|---|---|---|
| `core/tts_slicing.py` | `clean_tts_text` / `_truncate_tts` / `get_card_texts` | `70-220` |
| `core/ffmpeg_build.py` | `get_audio_duration` / `_valid_mp4` / `generate_tts` / `build_segments` / `concat_segments` / `cleanup` | `221-495` |
| 保留 `_cron_assemble.py` | `find_latest_day:20` / `resolve_dirs:32` / `read_manifest:51` / `read_post_data:61` / `main:496` + 编排 | — |

**影响范围**：仅 `core/_cron_assemble.py` 改 import + `tests/test_tts_slicing.py` 改 import 源。

**⚠️ 必须原样保留的语义**：
- `main` 在 `:555` 嵌套调 `bin/render_xhs_cards.sh`，**`timeout=180`**（不是 120/300 —— 那是同文件 301/402/442 行的值）
- `assemble` 的 subprocess 语义（`capture_output=True, text=True`）逐字保留

**风险：高** —— 04:00 是主链路，改坏即当日无视频（**理由：耗时 + 当日时效**，非「TTS 计费」；edge-tts 免费）。
**验证**：`test_tts_slicing` + `test_render_manifest` + 干跑 `python3 core/_cron_assemble.py --help`（不合成）。
**回滚**：单文件 `git checkout core/` 即可（无其他文件依赖新模块）。

**顺带处置**：`core/hyperframes_pipeline.py`（33 行，名不副实 —— 自称"不可用时回落 ffmpeg"实则无回落逻辑，`json/os` 未使用，AUDIT LOW 遗留）→ 并入 `ffmpeg_build` 或删除。

---

### S3 · 合并双检查器公共部

**目标新文件**：`core/content_checks.py`
**内容**：`_has_emoji` / 容错读 `_load` / 标题一致性比对 / rotation 比对
**来源**：`pipeline:144-257` + `quality:66-231` 的公共部

**影响范围**：`bin/check_xhs_pipeline.py` + `bin/check_content_quality.py` + 3 个测试文件改 import。

**重复清单**（须一并收进）：

| 项 | 位置 | 说明 |
|---|---|---|
| `_has_emoji` | `content_regression:25` / `pipeline:144` / `quality:66` | 逻辑逐字一致；**quality 版无 docstring**（另两处有 So/Sk 注释） |
| 内容合规比对 | `pipeline:161-257` vs `quality:222-257` | ~40 行；**quality 侧行号已订正**（v1 误写 161-231，那段是自愈逻辑） |
| `pick_theme` 收敛 | `build_v2_local:84-101` → `validate_rotation` | ⚠️ **见 §6 陷阱，未解决前不得动** |

**风险：中**（v1 标"中高"，PM 下调）—— 06:00 是**只读检查器**，改坏最多误报，不破坏数据。有 `test_pipeline_check` + `test_quality_selfheal` + `test_content_regression` 三重网。

**回滚**：新模块函数与旧 `_content_compliance` 并存一版，**diff 输出一致**才切。

**注意**：`quality:161` 是 `used = set(last_v1) | ...`（V2 自愈重建），**不要**把它当成合规比对搬走。

---

### ── 补 image 端到端测试（S2 前置）──

现状：`tests/test_draft_shared.py`（82 行）L65-68 有 `test_image_script_shares_save_markers`，但**仅断言** `im.save_confirmed_in is vd.save_confirmed_in`（函数同一性），**无 image 端到端保存流程用例**。

**必须补齐**：image 链路的计数 JS / 找目录 / 导航重试 / 保存确认各一条，与 video 侧对称。
**风险：极低** —— 只加测试，不动实现。

---

### S2 · 抽 `core/draft_shared.py`

**目标新文件**：`core/draft_shared.py`
**内容**：`SAVE_MARKERS` / `save_confirmed_in` / `get_draft_count` / `find_latest_*`（V1/V2 合一）/ `navigate_publish_page`（合一）

**来源**：

| 项 | video | image |
|---|---|---|
| 计数 JS | `40-66` | `31-49` |
| 找目录 | `find_latest_v2_dir:75-101` | `find_latest_v1_dir:63-81` |
| 导航重试 | `navigate_publish_page:103-125` | `navigate_publish_page:83-100` |
| `SAVE_MARKERS`/`save_confirmed_in` | `19-35`（唯一定义） | `:16` 反向 import |

**两个 draft 只留上传填表差异。**

**影响范围**：`core/xhs_video_draft.py` + `core/xhs_image_draft.py` + `tests/test_draft_shared.py`。

**命名说明**：新建 `core/draft_shared.py` 与已存 `tests/test_draft_shared.py` **不冲突**（不同目录；pytest 只收集 `test_*`，新模块不会被误收）。

**风险：高** —— 03:00/05:00 双 cron 直调，改坏即双链路无草稿；JS 字符串差一空格即计数失效。
**验证**：`test_draft_shared`（**已补 image 用例**）+ `test_publish_guard` + `test_tab_lifecycle`。
**回滚**：保留旧函数作 thin wrapper 转发到 `draft_shared` 一版，cron 入口不动。

---

### S4 · 配置与 IO 集中

**目标新文件**：

| 新模块 | 内容 | 来源 |
|---|---|---|
| `core/xhs_config.py` | `BASE`/`PROJ`/`CDP_HOST`/`CDP_PORT`/URL/超时/主题池常量 | 8 + 5 + 4 + 8 处 |
| `core/io_utils.py` | `atomic_write_json` + 容错 `load_json` | `humanize:226`/`render:18`/`quality:35`/`tracker:31-46` 四合一 |

**一并收走的阈值**：`TITLE_MAX=18`（`publish_guard:26` + `quality:98-231` + `content_regression:55-163` 三处各自定义，今日同值，一调即三分叉）、`CONTENT 400-900`、`assemble:89` TTS 截断 300。

**影响范围**：8 个 BASE 文件 + 5 个 CDP 文件 + 4 个 sh，**逐文件小 PR**。

**风险：低** —— 纯常量搬家，行为不变。`xhs_config` 常量值与旧字面量**逐项断言测试**，错即 revert 单文件。
**验证**：全量 `pytest` + `test_render_manifest` + `test_cleanup`。

---

### S5 · sh 入口统一（最后）

**目标**：3 个 sh 统一 `source _xhs_common.sh` + 用 `$XHS_PY`；`open_xhs_creator` 改走 `xhs_paths`。

| 文件 | 现状问题 |
|---|---|
| `bin/open_xhs_creator.sh:16` | 手写 `sys.path.insert(vendor/xhs)` |
| `bin/render_xhs_cards.sh:108-109` | 系统 `python3` + `PYTHONPATH`，与 `$XHS_PY` 双解释器并存（文件头 18-22 行自注此坑） |
| `bin/assemble_xhs_treehole.sh:5` | 系统 `python3` 直调且**不 source** `_xhs_common.sh` |

**风险：低** —— 只动入口不碰逻辑。**验证**：`shellcheck` + `sh --help` 干跑（不实际发布）。

---

## 5. tracker 处置（补 v1 缺口 R6）

v1 亲立三个 GOD-FILE，方案却只处置两个 —— `core/xhs_performance_tracker.py`（467 行）在新文件表中**出现 0 次**，也无「暂不动+理由」。本版补上。

**现状结构**（13 个 def）：

```
模块常量:20-28   BASE/DB_PATH/PUBLISHED_PATH/CDP_HOST/CDP_PORT/SAVE_TO_LIKE_*
抓取层:49-237    PAGE_COUNT_RE / _NEXT_PAGE_JS / _read_pagination:79 /
                 _read_table_rows:100 / parse_number:130 /
                 fetch_all_note_data:146 / fetch_profile_notes:221 / _parse_title_time:230
归因层:238-295   match_notes_to_published:238 / get_ratio_tier:287
报告层:296-387   analyze_time_slots:296 / generate_report:335
编排:388+        main:388
```

**建议拆法**：

| 步 | 新模块 | 内容 | 风险 |
|---|---|---|---|
| T1 | `core/tracker_cdp.py` | 抓取层 `49-237`（分页 JS + 表格解析 + 数字解析） | 低 |
| T2 | `core/tracker_report.py` | 归因 + 报告层 `238-387` | 低 |
| — | 保留 `xhs_performance_tracker.py` | `main:388` 编排壳 | — |

**为何可延后**：06:30 tracker 是**只读统计链路**，失败不破坏数据、不阻断发布；无 live 风险，收益（可维护性）低于 S1/S2。**建议排在 S1/S3 之后、与 S4 并行**。

---

## 6. ⚠️ 前置约束：`pick_theme` 收敛陷阱（**未解决前不得动 S3 此项**）

v1 的 P1-4 建议「`validate_rotation` 加参收敛 `pick_theme`」—— 但**未回应** `core/build_v2_local.py:10-11, 88-90` 注释中的正确性论证：

> 「`pick_theme` 内自实现该校验，**不调 `theme_rotation.validate_rotation`——那个函数额外把 V1 历史重复当作 error，会让候选全军覆没**」
>
> 「当天 V1 若已与历史重复（01:00 LLM 误读导致，如 **day77 玫瑰暮云撞 day74_v2**），会把当天 V1 的重复问题带进每个候选的判定 → **全军覆没 → V2 永远建不出来**」

**这是前科，不是洁癖。** 收敛前必须先处理该约束，否则重蹈 day77 覆辙。

**正确做法**：加参时必须显式 `check_v1_history=False`（默认值选择需论证），并补一条**回归测试**锁住 day77 场景（V1 已重复时 V2 仍能选出主题）。
**在测试就位前，S3 中此项保持不动。**

---

## 7. 证据链（PM 独立复验，非采信 v1/Reviewer）

```
wc -l 实测
  core/_cron_assemble.py                626   ✓
  core/xhs_performance_tracker.py       467   ✓
  bin/check_xhs_pipeline.py             447   ✓
  core/xhs_video_draft.py               375   ✓
  tests/test_tab_lifecycle.py           509   ✓

顶层 def 计数（grep -cE '^def '）
  _cron_assemble 14 · tracker 13 · pipeline 8 · quality 6

time.sleep 分布（19 处，逐文件加总）
  assemble:311(5) · render:96(1)/136(1.5)/143(0.3) · image:79,97,222,225,246
  video:99,122,159,281 · tracker:157(6)/193(2)/197(2)/206(2)/403(2) · login:68(3)

except Exception（core+bin）
  grep -rhoE "except Exception" → 41 处

assemble timeout
  :301(120) :380(30) :402(120) :433(120) :442(300) :555(180)   ← L555 已核实 180

find_latest 真实 def 行
  image find_latest_v1_dir:63 · video find_latest_v2_dir:75    ← v1 报告正确

quality 比对真实区间
  L161 = used = set(last_v1) | ...（自愈逻辑）
  L202 = check("标题 ≤18 字且无 emoji", ...)
  L222 = identity_ok = False, "V1 与 V2 标题不一致"    ← 真实比对起点
  L229 = validate_rotation(...)

_has_emoji 三份
  content_regression:25 / pipeline:144  有 docstring（So+Sk 说明）
  quality:66                            无 docstring，函数体逻辑一致

edge-tts 免费（非计费）
  core/_cron_assemble.py:255  subprocess.run(["which", "edge-tts"])
  core/_cron_assemble.py:16   TTS_VOICE = "zh-CN-XiaoyiNeural"

vendor 隔离
  tests/test_vendor_isolation.py:103-126  专守 vendor 不被污染
```

---

## 8. 附：v1 保留可用的部分

以下 v1 内容经复验**准确**，本版不再重复，直接引用：
- §2 文件大盘点行数表（20 文件**逐个精确命中，零编造**）
- §7 架构层次依赖图（`bin/ → core/ → vendor/xhs/` 单向成立，**无循环依赖**）
- 附录 A 耦合矩阵（`theme_rotation` 被 7 处 import 为最高）
- 附录 B 错误处理全表（41 处逐条，约 25 处合理）
- 附录 D 重复代码对照表

**注意**：v1 附录 B 汇总句写「35 处」但表格加总为 41 —— **以表格为准**。
