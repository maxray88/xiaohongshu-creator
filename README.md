# 01_XHS_Daily_Post — 情绪树洞 小红书每日自动发布流水线

## 目录结构

```
01_XHS_Daily_Post/
├── bin/          # cron 入口脚本（Hermes cron 经 ~/.hermes/scripts/ 的 shim 转发到这里）
│   ├── _xhs_common.sh            # 共享 shell 函数：Chrome 清理（精确匹配，只杀流水线自己的）+ venv 解释器解析
│   ├── render_xhs_cards.sh       # 02:30 V2 HTML→JPG 渲染入口 → core/render_xhs_cards.py
│   ├── check_content_quality.py  # 02:15 内容质量门（11 维启发式评分 ≥7.0，渲染前拦截）
│   ├── check_xhs_login.py        # 02:45 登录健康探针（CDP 发布页登录态，03:00 前告警）
│   ├── publish_xhs_image.sh      # 03:00 图文存草稿入口 → core/xhs_image_draft.py
│   ├── assemble_xhs_treehole.sh  # 04:00 视频合成入口 → core/_cron_assemble.py
│   ├── publish_xhs_video.sh      # 05:00 视频发布入口 → core/xhs_video_draft.py
│   ├── cleanup_xhs_treehole.py   # 05:30 清理 7 天前旧素材
│   ├── check_xhs_pipeline.py     # 06:00 流水线完整性自检（no_agent watchdog）
│   ├── run_performance_tracker.sh# 06:30 创作者中心表现数据抓取 → core/xhs_performance_tracker.py
│   ├── run_humanize.sh           # 01:30 文本去 AI 味 → core/humanize_text.py
│   └── open_xhs_creator.sh       # 手动开有头 Chrome（CDP 9222）用于登录/排查
├── core/         # 流水线核心 Python（旧脚本已归档至 legacy/）
│   ├── _cron_assemble.py          # 合成主脚本：TTS提取/清洗/生成(含重试) + ffmpeg
│   ├── render_xhs_cards.py        # V2 卡片 CDP 截图（视口 1080×1440@2x）+ manifest 回填
│   ├── xhs_image_draft.py         # 图文上传草稿（today-guard + CDP 头图/文案填表）
│   ├── xhs_video_draft.py         # 视频上传草稿（登录检查+上传+等待处理+填表+验证）
│   ├── theme_rotation.py          # 主题轮换校验（V1/V2 与最近 3 天不重复，供 02:15/06:00 复用）
│   ├── humanize_text.py           # 去 AI 味规则引擎（正文 + HTML 双入口）
│   ├── build_v2_local.py          # V2 本地确定性构建（luminance-remap 换色，无 LLM）
│   ├── xhs_performance_tracker.py # 创作者中心数据抓取 + save-to-like ratio
│   ├── content_regression.py      # 内容红线的独立回归检查（不依赖当日数据）
│   └── hyperframes_pipeline.py    # hyperframes CLI 封装（Ken Burns/安全边距/TTS 时序），不可用时回落 ffmpeg
├── generators/   # 每日内容生成辅助
│   └── render_card.py             # 01:00 V1 卡 Playwright 渲染器（LLM cron 引用）
│       # 逐日生成器不再落盘：LLM cron 每天动态生成并运行，历史版本见 legacy/generators/
├── design/       # 视觉设计层
│   ├── design_tokens.json         # 配色/字号/间距 token
│   ├── validate_theme.py          # 主题轮换校验（Open Design 选主题时用，与 core/theme_rotation.py 同源）
│   └── masters/                   # 设计母版（仅 README）
├── workflows/    # 工作流定义
│   └── comfy_xhs_card.json        # ComfyUI 卡片生成工作流
├── tools/        # session-Bash wrapper，以干净终端-like 环境跑命令（给 `claude` CLI 用）
├── tests/        # 回归测试（python3 -m pytest tests/ -v，10 文件 1547 行）
│   ├── test_tts_slicing.py        # TTS 六卡切片不变量 + day62 真实 fixture
│   ├── test_theme_rotation.py     # 主题轮换规则单测
│   ├── test_render_manifest.py    # 渲染 manifest 回填（虚标 images_rendered 的反例）
│   ├── test_pipeline_check.py     # 06:00 watchdog 各检查项
│   ├── test_quality_selfheal.py   # 02:15 质量门自愈路径
│   ├── test_humanize.py           # 去 AI 味规则（含 因此/然而/3.14/第一次 反例）
│   ├── test_perf_tracker.py       # 表现追踪分页与解析
│   ├── test_content_regression.py # 红线回归
│   ├── test_draft_shared.py       # 草稿保存与计数校验
│   └── test_cleanup.py            # 清理脚本的滚动窗口与退出码
├── legacy/       # 旧/弃用脚本存档，34 个 .py / 13504 行（仅存档，详见 legacy/README.md）
└── README.md
```

> `legacy/` 内每个文件顶部都插了 `_archived_guard.py`（`sys.exit(2)` 守卫）——
> 其中 4 个语法完好且会真的向小红书上传存草稿，手滑就能往草稿箱塞一条笔记。

## 代码在哪：三层结构约定

这是本项目最重要的一条约定，回答"某个逻辑的真身到底在哪"。**改动前先读这一节。**

同名文件分布在三个地方，是三件不同的事，各有硬性约束：

| 层 | 位置 | 是什么 | 能不能改/挪 |
|---|---|---|---|
| **① shim 层** | `~/.hermes/scripts/` | 11 个 164–723 字节的薄 wrapper，唯一职责是转发到本项目 `bin/`+`core/`。cron 只认它们 | **必须原地留着**，不能迁、不能改成 symlink |
| **② 上游快照** | 本项目 `vendor/xhs/` | `cdp_publish.py`（4892 行）等 4 个文件，取自独立仓库 `white0dew/XiaohongshuSkills`（MIT），**2026-09-27 vendored 进来** | 尽量不改；改了就与上游分叉了，细节见 `vendor/xhs/README.md` |
| **③ 项目实现** | 本项目 `bin/` + `core/` | 真实业务逻辑，100% 在项目里 | 改逻辑只改这里 |
| **④ 解释器依赖** | `~/.pyenv/versions/3.11.15/` (pyenv 全局) | mlx / mlx-audio（Qwen3-TTS TTS 引擎）/ playwright / websockets，**数百 MB 二进制，故意留在项目外** | 由 `bin/_xhs_common.sh` 的 `$XHS_PY` 指向 |

### 为什么 vendor 进来（2026-09-27）

原先 CDP 依赖放在 `~/.hermes/xhs_skills/scripts/`，是上游的独立 git 仓库。
已确认 **73 处引用全部在本项目内，无任何其它项目引用** —— 它已经从「共享库」
退化为本项目的单点外部依赖。而跨仓库改一次代码要开两个 repo，且没有共同历史
可追溯，凌晨的 cron 出问题时更难判断是哪边改坏的。

现在项目**自包含**：代码和测试都在同一个仓库、同一条历史里。
上游仓库仍在原处、未被改动，将来要同步上游修复仍可直接对比。

`feed_explorer.py`（771 行搜索/评论爬虫）项目内**一次都没用**，但
`cdp_publish.py:78` 顶层硬 import 它的 11 个符号，缺文件会在 import 阶段炸 ——
所以一并带上。`account_manager.py` **没有** vendor：两处引用都自带容错。


### 为什么 shim 不能改成 symlink

Hermes cron 的 `script` 字段只接受 `~/.hermes/scripts/` 下的相对路径，且 scheduler
会解析真实路径并要求文件**物理位于**该目录内 —— 跳出目录的 symlink 会被拒绝
（报 `Blocked: script path resolves outside the scripts directory`）。这是历史踩过的坑，
所以 shim 是"物理入口"而非"链接"。

**shim 写法约定：透明转发。** 转发 `sys.argv`、传播退出码、不吞参数、不加业务逻辑。
（`cleanup_xhs_treehole.py` 曾吞掉 `sys.argv`，已补齐。）

**11 个 shim 全表**（判定标准：内容含 `01_XHS_Daily_Post`；注意 `run_*.sh` 和
`build_v2_local.py` 名字里没有 `xhs`，按名字 grep 会漏）：

| shim (`~/.hermes/scripts/`) | 转发到 | 字节 |
|---|---|---|
| `render_xhs_cards.sh` | `bin/render_xhs_cards.sh` | 175 |
| `check_content_quality.py` | `bin/check_content_quality.py` | 408 |
| `check_xhs_login.py` | `bin/check_xhs_login.py` | 408 |
| `publish_xhs_image.sh` | `bin/publish_xhs_image.sh` | 164 |
| `assemble_xhs_treehole.sh` | `bin/assemble_xhs_treehole.sh` | 343 |
| `publish_xhs_video.sh` | `bin/publish_xhs_video.sh` | 177 |
| `cleanup_xhs_treehole.py` | `bin/cleanup_xhs_treehole.py` | 723 |
| `check_xhs_pipeline.py` | `bin/check_xhs_pipeline.py` | 406 |
| `run_humanize.sh` | `bin/run_humanize.sh` | 167 |
| `run_performance_tracker.sh` | `bin/run_performance_tracker.sh` | 189 |
| `build_v2_local.py` | `core/build_v2_local.py` | 566 |

复核命令（新增 shim 后跑这个，别靠肉眼）：

```bash
cd ~/.hermes/scripts && for f in *; do
  grep -lq "01_XHS_Daily_Post" "$f" 2>/dev/null && echo "$f  $(wc -c < "$f")B"
done
```

改完本项目代码后，确认「项目 → cron」这条链没断（别靠肉眼）：

```bash
cd ~/02_Cronjobs_Projects/01_XHS_Daily_Post && python3 -c "
import json, os
d = json.load(open(os.path.expanduser('~/.hermes/cron/jobs.json')))
jobs = d['jobs'] if isinstance(d, dict) else d
base = os.path.expanduser('~/.hermes/scripts')
xhs, other, missing = [], [], []
for j in jobs:
    s = j.get('script')
    if not s: continue
    p = os.path.join(base, s)
    if not os.path.exists(p):
        missing.append((j.get('name', '?'), s)); continue
    body = open(p, encoding='utf-8', errors='replace').read()
    (xhs if '01_XHS_Daily_Post' in body else other).append(s)
print('XHS shim:', len(xhs), '| 其他项目:', len(other), '| MISSING:', missing or '无')
assert not missing, missing
print(sorted(xhs))
" && python3 -m pytest tests/ -q
```

预期输出：`XHS shim: 11 | 其他项目: 12 | MISSING: 无`。

> `~/.hermes/scripts/` 下共 52 个文件，其中 11 个指向本项目、**其余 41 个是别的项目的**
> （polymarket / paper-digest / comment-post / chrome_watchdog 等）。
> 改本项目时别误动它们。

### 遇到同名文件时怎么判

| 你看到 | 它是 | 去哪改 |
|---|---|---|
| `~/.hermes/scripts/render_xhs_cards.sh` | ① shim | 不用改，只是入口 |
| 本项目 `bin/render_xhs_cards.sh` | ③ 入口，导出 `XHS_CHROME_HEADLESS=1` | 只改 headless 开关/前置环境 |
| 本项目 `core/render_xhs_cards.py` | ③ **真身** | 渲染逻辑改这里 |
| `vendor/xhs/cdp_publish.py` | ② **上游快照** | 已 vendored（2026-09-27）。优先改本项目代码；真要改库，先看 `vendor/xhs/README.md` |
| `~/.hermes/data/xhs_treehole/` 下的脚本 | **不应该存在** | 数据层，脚本清走 |

引用关系（实测）：`cdp_publish` 被项目内 8 个文件 import，`chrome_launcher` 5 个，
`feed_explorer` / `run_lock` **0 个**。`account_manager` 无 import，仅在
`bin/_xhs_common.sh` 的注释里被提到（作为 profile 路径的对照来源），也是 0 依赖。
数据目录 `data/xhs_treehole/` 无散落脚本 —— 2026-08-09 已完成迁移。

### 同名不同物：一个真实的坑

`~/.hermes/scripts/ensure_chrome.py`（CDP **9229**，`ChromeProfiles/NewAccount`）与
`vendor/xhs/chrome_launcher.py` 的 `ensure_chrome()`（CDP **9222**，
`XiaohongshuProfile`）**不是同一个东西**。本项目零引用前者。
看到 `ensure_chrome` 别默认是同一个函数，先看端口和 profile 路径。

## 关键路径（保持不变）

- **数据目录**: `~/.hermes/data/xhs_treehole/` — day_* 素材、published_content.json、post_data.json
- **CDP 代码**: `vendor/xhs/` — cdp_publish.py、chrome_launcher.py、feed_explorer.py、run_lock.py
  （2026-09-27 从上游 `white0dew/XiaohongshuSkills` vendored 进来；上游仓库仍在
  `~/.hermes/xhs_skills/` 原处，未被改动）
- **虚拟环境**: CDP 脚本（`cdp_publish.py`/`chrome_launcher.py`）用 `~/.pyenv/versions/3.11.15/bin/python3` (pyenv 全局)；
  但 Playwright 渲染器 `generators/render_card.py` 依赖 playwright，只在 `~/.hermes/hermes-agent/venv/` 里有，
  手动跑渲染必须用后者（01:00 LLM cron 本身就在 agent 环境里，无需切换）
- **Chrome Profile**: `~/Google/Chrome/XiaohongshuProfile/`

  > ⚠️ 别和 `~/Google/Chrome/XiaohongshuProfiles/default/` 搞混 —— 两者只差一个
  > `s` 和 `/default`，但是**完全不同的目录**。流水线用的是**前者**（147M，仅小红书
  > 一个平台）；后者是 5.5G 的多平台混杂 profile（抖音/Google/TikTok/YouTube）。
  > 实际路径由 `vendor/xhs/chrome_launcher.py` 的 `PROFILE_DIR_NAME` 决定，
  > `bin/_xhs_common.sh` 的 `XHS_CHROME_PROFILE` 必须与之一致，否则
  > `kill_pipeline_chrome()` 匹配不到进程、清理静默失效。

## Cron 引用方式

Hermes cron 的 `script` 字段只接受 `~/.hermes/scripts/` 相对路径，且 scheduler
会解析真实路径并要求文件必须物理位于 `~/.hermes/scripts/` 内 —— **symlink 指向目录
外会被拒绝**（报 `Blocked: script path resolves outside the scripts directory`）。
因此在 `~/.hermes/scripts/` 保留的是 **11 个**薄 shim 文件（非 symlink），
它们用绝对路径 `exec`/`subprocess` 本项目的 `bin/`+`core/` 脚本：

```
~/.hermes/scripts/publish_xhs_image.sh       -> exec bash 本项目/bin/publish_xhs_image.sh
~/.hermes/scripts/assemble_xhs_treehole.sh   -> exec bash 本项目/bin/assemble_xhs_treehole.sh
~/.hermes/scripts/publish_xhs_video.sh       -> exec bash 本项目/bin/publish_xhs_video.sh
~/.hermes/scripts/render_xhs_cards.sh        -> exec bash 本项目/bin/render_xhs_cards.sh
~/.hermes/scripts/run_humanize.sh            -> exec bash 本项目/bin/run_humanize.sh
~/.hermes/scripts/run_performance_tracker.sh -> exec bash 本项目/bin/run_performance_tracker.sh
~/.hermes/scripts/cleanup_xhs_treehole.py    -> subprocess 本项目/bin/cleanup_xhs_treehole.py
~/.hermes/scripts/check_xhs_pipeline.py      -> subprocess 本项目/bin/check_xhs_pipeline.py（传播退出码）
~/.hermes/scripts/check_content_quality.py   -> subprocess 本项目/bin/check_content_quality.py
~/.hermes/scripts/check_xhs_login.py         -> subprocess 本项目/bin/check_xhs_login.py
~/.hermes/scripts/build_v2_local.py          -> subprocess 本项目/core/build_v2_local.py
```

上表与「三层结构」小节的 11 个 shim 全表一致；**改逻辑时只改本项目 `bin/`+`core/` 下的真身**，
shim 无需改动。shim 的写法约定见「三层结构」一节（透明转发：转发 `sys.argv`、传播退出码）。

### 排障：cron 环境 PATH 极简，别指望 shell 默认值

Hermes cron 不走 login shell，`PATH` 里没有 `~/.pyenv/shims`，也没有 venv。
两个后果：

1. **裸 `python3` 解析到的可能不是你以为的解释器** —— 渲染路径尤其危险：
   `generators/render_card.py` 依赖 playwright，而它**只**装在
   `~/.hermes/hermes-agent/venv/`。
   01:00 LLM cron 本身跑在 agent 环境里所以没事，但**手动**跑渲染必须显式指定解释器。
2. **别在 shim 里依赖 `which python3` 之类** —— 一旦 shim 用 `which` 决定用哪个
   解释器，cron 下会拿到与交互式 shell 不同的结果，同样的脚本时好时坏。

本项目的做法是**不猜**：wrapper 里统一用 `bin/_xhs_common.sh` 里的
`$XHS_PY`（默认 `~/.pyenv/versions/3.11.15/bin/python3`），并由
`require_python()` 在解释器缺失/不可执行时**大声失败（exit 1）**，
而不是静默退化到系统 python 报一堆无关的 `ModuleNotFoundError`。

## 创作者自动回复（自己的帖子）

operator 操作说明（转述自 `specs/001-creator-auto-reply/quickstart.md`，无新增事实）：

- 前置：在 `~/.hermes/data/xhs_treehole/engagement_job.json`（chmod 600）配置
  `own_user_id` 或 `own_profile_url` 之一，并确保 `expect_nick` 已填（**必填**，
  缺失则 rc 2 拒绝）。
- dry-run（默认，不带 `--live`）：`python3 bin/reply_to_own_comments.py` —— 只读
  CDP 发现 + 打印计划 + 写 `reply_ledger.jsonl`（`dry_run: true`），不写
  `reply_counter.json`，不调 LLM。
- live 实发：`bin/run_reply_own_comments.sh`（导出 LLM 代理 env 后 `--live`）。
  分阶段放行：先 dry-run cron/手动跑满 7 天、逐日核对零误判，再手动切 `--live`
 （`reply_counter.json` 每日上限 3）。
- 一键停机：任意异常 → 建 `ENGAGEMENT_STOP` 文件立即停机（kill-switch）；
  上线首周每天看 `python3 bin/reply_to_own_comments.py --report` 输出审计。
- 敌意评论出现即中止本轮并冷却 48h（`reply_state.json`）。

## 每日流水线

| 时间 | 任务 | 入口 |
|---|---|---|
| 01:00 | V1 内容生成（LLM cron） | 生成 day_YYYYMMDD_dayN/ |
| 01:30 | 文本去 AI 味 | run_humanize.sh → core/humanize_text.py |
| 02:00 | V2 内容生成（LLM cron） | 生成 day_YYYYMMDD_dayN_v2/ |
| 02:15 | 内容质量门（script cron） | check_content_quality.py（11 维评分 ≥7.0，否则渲染前告警） |
| 02:30 | HTML→JPG 渲染 | render_xhs_cards.sh |
| 02:45 | 登录健康探针（script cron） | check_xhs_login.py（登录过期则 03:00 前告警） |
| 03:00 | 图文存草稿（script cron） | publish_xhs_image.sh |
| 04:00 | 视频合成 | assemble_xhs_treehole.sh |
| 05:00 | 视频发布草稿 | publish_xhs_video.sh |
| 05:30 | 清理旧素材 | cleanup_xhs_treehole.py |
| 06:00 | 完整性自检（no_agent） | check_xhs_pipeline.py |
| 06:30 | 表现数据抓取 | run_performance_tracker.sh → core/xhs_performance_tracker.py |

`cleanup_xhs_treehole.py` 除 7 天滚动删除 `day_*` 目录外，还会清理根目录再生的杂项
（`generate_day*.py`、`current_day.txt`、`__pycache__`、`.DS_Store`、空 `video/` 目录）；
`published_content.json`、`chrome_profile/`、`video_upload_logs/` 有意保留不删。

## 内容优化策略（SEO / 标签 / 主题）

内容层面的优化策略写在 cron 的 LLM prompt 里（`~/.hermes/cron/jobs.json`），改策略改 prompt 即可：

- **01:00 V1 生成**（`250be2028330`）：标题 ≤18 字、首句带核心情绪词；正文 400–900 字、短段落 + 反问句提互动；
  6–10 个 hashtags（品牌词「情绪树洞」+ 主题词 + emotion_tag**逐字原文** + 高流量情绪大词，大小词搭配——hashtags 数组必须有一项与 emotion_tag 完全一致，不可截短）；
  `best_post_time` 取晚间 20:00–23:00；每天从 10 个轮换主题库选全新配色（禁与最近 3 天重复）。
- **02:00 V2 生成**（`d9578136eea3`）：配色与 V1 及最近 3 天 V2 不同，冷调/创意系轮换；视频卡片字号大、对比度高。
- **03:00 图文存草稿**（`ebf775e37292` → `publish_xhs_image.sh` → `core/xhs_image_draft.py`）：纯脚本任务，无 LLM 依赖（2026-08-22 前为 LLM cron，曾因 weekly 429 quota 失败；现与 05:00 视频发布同为 no_agent script cron，不再消耗 LLM quota）。从 post_data.json 读 `content_text` + `hashtags`
  （拼成 `正文 + \n\n + #标签`——关键：标签带 `#` 前缀，XHS 只把 `#` 开头的话题链接/检索，
  空字打散只是普通文本），图片 glob `images/card*.jpg` —— 注意是**新 schema**（`content_text`/`hashtags`），
  不要回退到 `content`/`all_images`。today-guard 与 05:00 一致：最新 V1 不是今天则跳过。
- **05:00 视频发布草稿**：视频描述用当天的 `hashtags`（不再用固定 3 标签；描述内 `#` 前缀使标签可搜索，
  见 `core/xhs_video_draft.py`）；
  若当天没有素材（01:00/02:00 生成失败，最新 _v2 落到昨天），直接跳过发布避免重复草稿
  （06:00 watchdog 会以「今天没有生成新内容」告警）。
- **已发布主题追踪** `published_content.json` 是 01:00 prompt（step 8）与 05:00 video-draft tracker 的
  双写账本，一行一帖（title/day_num/date），兼作「主题不重复」的候选池。字段约定：`day_num` 取
  day 目录后缀（`day_YYYYMMDD_dayN` → N）、`date` 用紧凑 `YYYYMMDD`（与 05:00 tracker 一致，不用 `-`）；
  01:00 追加时若当天 day_num 已存在则**覆盖**而非新增（历史上曾同一天两行 + 日期格式混写，
  由 06:00 [追踪] 门硬性拦截回归）。

## 完整性自检（06:00）

`check_xhs_pipeline.py` 是 no_agent watchdog：全部通过 → 无输出、exit 0 → 静默；
任何缺失/失败 → 输出 ❌ 报告、exit 1 → 作为告警投递到 feishu 群。检查项：

- 最新一天素材目录（V1 manifest.json / post_data.json、V2 manifest.json / 6 张 JPG、video_note.mp4）
- 各脚本 cron 步骤（render/assemble/publish/cleanup/image-draft）今天运行过且状态 ok
- 内容红线（仅校验当天新生成内容）：标题 ≤18 字且必填、hashtags 6–10 且必须包含当天 emotion_tag、
  content_text 400–900 字且必填（缺失直接告警，防 03:00 发出仅标题图文）、best_post_time 在 20:00–23:00、
  V1/V2 主题与最近 3 天不重复、
  标题/系列跨文件一致（V1 manifest、V1 post_data、V2 manifest 三处同一标题与系列名，防止图文与视频两条笔记标题分叉）
- 内容环境卫生（同批红线）：正文首句必须**逐字**含当天 emotion_tag（01:00 prompt 已同步收紧并要求自然开场，
  否则搜索命中率下降——历史 7/7 天曾违反）、hashtags 必含品牌词「情绪树洞」、
  标题无 emoji / 无 # / 不以问号结尾，正文无 emoji 且至少一句反问句，标签均为纯中文不带 #
  （SEO/标签/主题硬性合规，违规会触发 feishu 告警而非静默通过）
- 已发布主题追踪（[追踪] 门）：`published_content.json` 不应有重复 `day_num`（防 01:00/05:00 重生成双追加）、
  每条 `date` 必须为紧凑 `YYYYMMDD`（防两写者格式分叉）；违反当天 feishu 告警
- 图文草稿(03:00)存于 XHS 草稿箱，内容本地无法验证、仅作提示；但任务本身的运行状态已纳入校验
  （今天跑过且 ok，否则告警，防图文草稿静默缺失）

渲染侧同源守卫：`render_xhs_cards.sh` 只在 `images_rendered=True` **且** 实际 JPG 数 ≥6 时才跳过渲染；
flag 为 True 但卡片不足 6 张时会重新渲染缺失卡片（flag 由 `render_xhs_cards.py` 无条件置位，单独信 flag
会放行残缺卡片进入 04:00 合成，与上面 watchdog「JPG 数权威」的判定同源）。
此外与 03:00 填表/05:00 发布一致，渲染只处理「今天」的新 V2：最新 `_v2` 不是今天的日期时直接跳过、
不动 Chrome（生成失败天 ~13%，重渲染昨天卡片是纯浪费）——06:00 watchdog 仍会告警当天无新内容。
04:00 合成同源：`_cron_assemble.py` 自动路径只合成今天素材（显式 `--day <date>` 不受限，供手动历史重合成）；
生成失败天不再对昨天视频做无谓重编码。

## Headless cron

render 与 publish 两个 wrapper 导出 `XHS_CHROME_HEADLESS=1`，`chrome_launcher.launch_chrome`
据此以 headless 模式启动 Chrome（cron 无需 GUI）。手动执行（`bin/*.sh` 手动跑、桌面 .app
快捷方式、登录修复）环境变量未设置，仍以 headed 模式运行。

## 手动执行

```bash
# 合成（当天最新 day）
python3 ~/02_Cronjobs_Projects/01_XHS_Daily_Post/core/_cron_assemble.py

# 渲染 V2 卡片
bash ~/02_Cronjobs_Projects/01_XHS_Daily_Post/bin/render_xhs_cards.sh

# 发布视频草稿
bash ~/02_Cronjobs_Projects/01_XHS_Daily_Post/bin/publish_xhs_video.sh

# 有头 Chrome + CDP 9222（登录/排查窗口；可被 cdp_publish 的 ensure_chrome 复用）
bash ~/02_Cronjobs_Projects/01_XHS_Daily_Post/bin/open_xhs_creator.sh
#（桌面双击快捷方式：~/Desktop/小红书创作平台CDP.command；可传 URL 参数覆盖默认发布页）

# 渲染单张 V1 卡（01:00 LLM cron 引用的 Playwright 渲染器）
python3 ~/02_Cronjobs_Projects/01_XHS_Daily_Post/generators/render_card.py input.html output.jpg

# 生成新一天内容：由 01:00/02:00 LLM cron 动态完成，手动生成请直接运行对应 cron job
# （历史逐日生成器已归档至 legacy/generators/，不再手动调用）
```
