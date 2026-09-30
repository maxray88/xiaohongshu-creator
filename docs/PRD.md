# 01_XHS_Daily_Post · PRD — 情绪树洞 小红书每日自动发布流水线

> **Version:** v2.0 · **Date:** 2026-08-27 · **Owner:** Hermes (PM) · **Status:** Draft → Review
> **Stack:** Hermes cron + CDP (`cdp_publish.py`/`chrome_launcher.py`) + Chrome Profile + Playwright/ComfyUI/Hyperframes + Open Design.app
> **Tooling note (per request):**  UI设计类工作使用 **Open Design.app**，图片和视频类工作通过 **Hyperframes** 和 **ComfyUI**（均已安装在本地，ComfyUI `http://127.0.0.1:8188` 常驻，Hyperframes 本地CLI/库）。

---

## 1. 背景与问题

### 1.1 现状
- 运营“情绪树洞”系列已持续 50 天（`day_20260827_day50`），每日产出：图文笔记（6 张 1080×1440 卡片 + 长文）与竖版视频笔记（6 段拼剪，1080×1920，TTS 配音）。
- 流水线 01:00–06:00 全自动：V1/V2 内容生成（LLM）→ HTML 渲染 → 图文/视频草稿 → 清理 → 自检。
- 核心资产：`~/.hermes/data/xhs_treehole/day_*`（素材）与 `published_content.json`（已发布主题账本），`~/02_Cronjobs_Projects/01_XHS_Daily_Post/` 为主工程目录（`bin/`/`core/`/`generators/`）。

### 1.2 痛点（已验证）
| 痛点 | 影响 | 已有缓解 |
|---|---|---|
| LLM 夜间 403/429 导致整日无素材（8-26 01:00/02:00 5/5 providers 全挂） | 当天无图文/视频，草稿空 | 已将 01:00/02:00 固定到 `deepseek-v4-flash/opencode-go` 并重建 fallback |
| 主题/标题重复、SEO 红线回归（标题超长、首句无 emotion_tag、hashtags 缺品牌词） | 搜索与推荐双降 | 06:00 自检硬门拦截 |
| V1/V2 文本不一致（图文与视频标题分叉） | 同一天两条笔记标题不同 | 文本 diff 校验 + 06:00 跨文件一致性校验 |
| 渲染/合成对“昨天素材”重干浪费 | 无谓 Chrome/ffmpeg | today-guard（仅当天渲染/合成/发布） |
| 地域限流（openrouter/gemini）在国内不可用 | fallback 失效 | 已替换为 CN 可用模型（deepseek/qwen） |
| 07-30 TTS 读文件名/页码、截图横屏空白 | 成品质量 | TextExtractor + viewport 1080×1440@2x + 绝对路径 file:// |
| Chrome 非 headless 在 cron 下无 GUI 失败 | 发布中断 | `XHS_CHROME_HEADLESS=1` wrapper |

---

## 2. 产品目标与成功指标

### 2.1 目标
- **零人工干预的日更**：每日自动完成“内容 → 渲染 → 草稿”并进入 XHS 草稿箱，人工仅需点击“发布”。
- **内容质量稳定**：符合 SEO/标签/主题红线，可搜索、可推荐、视觉一致。
- **可观测与可恢复**：失败可自检告警、次日自动重试、7 天滚动清理。

### 2.2 北极星 & KPI
| 指标 | 定义 | 目标 |
|---|---|---|
| **日更成功率** | 01:00–05:00 全链路成功天数/总天数 | ≥97% |
| **草稿到达率** | 每天图文+视频各 1 份进入草稿箱 | 100%（today-guard 下） |
| **红线合规率** | 06:00 自检无 [合规] 告警天数 | 100% |
| **主题不重复** | 连续 30 天无语义重复 | 100% |
| **发布时间命中** | `best_post_time` 落 20:00–23:00 | 100% |
| **渲染可用性** | 02:30 渲染 6/6 JPG | ≥99% |
| **视频合成时延** | 04:00 端到端 <5 min | p95 <5 min |
| **草稿标题一致性** | V1/V2/post_data 同标题 | 100% |

---

## 3. 用户与场景

### 3.1 角色
- **运营者（你）**：设定主题方向、审草稿、一键发布。
- **读者**：在小红书夜间情绪高峰（20:00–23:00）消费“情绪树洞”内容，互动于评论区。
- **Hermes（PM/Builder/Reviewer）**：自动化执行与自检。

### 3.2 典型旅程
1. 每日 01:00–02:00 自动生成 `你总在讨好…` / `休息羞耻…` 等主题（10 词主题库轮换）。
2. 02:30 渲染 6 张卡（HTML→JPG），03:00 图文草稿、04:00 视频合成、05:00 视频草稿。
3. 06:00 自检静默或 Feishu 告警。
4. 运营者白天打开 `creator.xiaohongshu.com → 草稿箱` 审阅 → 发布。

---

## 4. 范围（Scope）

### 4.1 In Scope
- 内容生成：01:00 V1（图文）+ 02:00 V2（视频卡）— 文本一致、配色轮换、SEO 红线
- 渲染：02:30 HTML→JPG（V2 横屏已修复为 1080×1440@2x）、V1 渲染（Playwright）
- 发布：03:00 图文草稿 + 05:00 视频草稿（CDP + Chrome Profile）
- 合成：04:00 `Edge-TTS zh-CN-XiaoyiNeural +10%` + ffmpeg 竖版拼剪 + 文本清洗（emoji/CTA/标题/页码过滤）
- 运维：05:30 滚动清理、06:00 自检

### 4.2 Out of Scope
- 自动点击“发布”（保留人工发布）
- XHS 评论/私信运营
- 多账号矩阵（后续版本）

---

## 5. 功能需求（FR）

### 5.1 内容生成 FR-01/02
| ID | 需求 | 验收 |
|---|---|---|
| FR-01-01 | 01:00 V1：标题 ≤18 字、第二人称+悬念、无 emoji/#/问号结尾；正文 400–900 字、纯文字、首句逐字含 emotion_tag、中段反问、结尾落回主题 | 06:00 [合规] 无告警 |
| FR-01-02 | hashtags 6–10，纯中文不带#，含“情绪树洞”+主题词+emotion_tag逐字原文+2–3大词+3–5长尾 | 同上 |
| FR-01-03 | best_post_time ∈ 20:00–23:00（优先 22:00） | 同上 |
| FR-01-04 | 主题轮换：10 库（暮色琥珀/晨雾薄荷/雾蓝海湾/玫瑰暮云/森林晨光/海盐汽水/雪松深夜/麦田晚风/莓果初雪/苔藓墨绿），与最近 3 天 V1+V2 全不重复 | 同上 |
| FR-01-05 | 去重：读 `published_content.json`，新标题与 30 条历史语义不同 | 无重复 day_num/date 格式告警 |
| FR-01-06 | 产出：`day_YYYYMMDD_dayN/post_data.json`（day_num/title/series/content_text/hashtags/best_post_time/emotion_tag）+ `manifest.json` + `images/card{1..6}_*.jpg`（1080×1440） | 目录完整 |
| FR-02-01 | 02:00 V2：复用 V1 文本逐字（仅封面 tag 色系名可换），配色与 V1 及最近 3 天 V2 不同，冷调/创意系（雾蓝海湾/雪松深夜/苔藓墨绿/暮色霓虹/晨雾薄荷/海盐汽水/月光银灰/星云紫/森林晨光/莓果初雪） | 6/6 diff 一致 |
| FR-02-02 | 产出：`day_YYYYMMDD_dayN_v2/generate.py`（写在 _v2 内）+ `images/card_v2_1..6_*.html` + `manifest.json`（title/series与V1一致、v2_angle/color_scheme、cards 6项） | 同前 |

### 5.2 渲染 FR-03
| ID | 需求 |
|---|---|
| FR-03-01 | 02:30 将 V2 的 6 个 HTML 渲染为 JPG（2160×2880 @2x，高清），仅当天 V2 才渲染（today-guard），`images_rendered=True` 且 JPG≥6 才跳过，下次自动置位 |
| FR-03-02 | 渲染路径：**分层**—— 优先 ComfyUI/Hyperframes（见 6.4），回退 CDP `file:// 绝对路径 + Emulation.setDeviceMetricsOverride 1080×1440@2x`（已验证 2160×2880） |

### 5.3 草稿 FR-04/05
| ID | 需求 |
|---|---|
| FR-04-01 | 03:00 图文草稿：读 `post_data.json` 的 `content_text` + `hashtags` 拼 `#标签`（XHS 识别要点），图片 `images/card*.jpg` 6 张，CDP 填表自动保存到草稿箱 |
| FR-05-01 | 05:00 视频草稿：`video_note.mp4`（仅接受该名，拒绝 `seg_*.mp4` 碎片），描述用 `hashtags` 带 `#` 前缀，today-guard 跳过非当天素材 |

### 5.4 合成 FR-06
| ID | 需求 |
|---|---|
| FR-06-01 | 04:00 合成：TTS 清洗 6 层（`@情绪树洞·YYYY-MM-DD X/6`签名、`.tag`/`.watermark`/`<title>`/`page-num` 跳过、emoji `So`/卡6 CTA 过滤、`len>1` 宽松），Edge-TTS 重试 3×5s，ffmpeg 1080×1920 竖版 |
| FR-06-02 | today-guard：仅合成当天 _v2（`--day` 可重跑历史） |

### 5.5 运维 FR-07/08
| ID | 需求 |
|---|---|
| FR-07-01 | 05:30 清理：7 天滚动删 `day_*`，同时清理根杂项（`generate_day*.py`/`current_day.txt`/`__pycache__`/空 video），保留 `published_content.json`/`chrome_profile`/`video_upload_logs` |
| FR-08-01 | 06:00 自检：校验最新天 V1/V2/manifest/post_data/JPG×6/video_note.mp4、脚本 cron 今日 ok、红线、跨文件一致性、published_content 去重与 `YYYYMMDD` 紧凑格式；全部通过静默，异常 Feishu 告警 |

---

## 6. 非功能与体验

| 维度 | 要求 |
|---|---|
| 可用性 | cron 固定时序 01:00→06:00，单点失败不阻塞次日（today-guard） |
| 性能 | 渲染 <2 min，合成 <5 min，发布 <3 min |
| 可靠性 | TTS 重试、Chrome CDP 自动拉起、渲染幂等 |
| 可观测 | 06:00 聚合告警；每步 stdout 可审计 |
| 安全 | Chrome Profile `~/Google/Chrome/XiaohongshuProfile` 隔离（仅小红书单平台，勿与多平台混杂的 `XiaohongshuProfiles/default` 混淆）；secrets 不进仓库 |
| 合规 | 全文无 emoji（除非任务指定）、标题无 #/emoji/问号结尾 |

---

## 7. 架构与数据

### 7.1 总览
```
LLM cron 01:00 V1 ─┐
                    ├─► 02:30 render (HTML→JPG) ──► 03:00 image draft (CDP)
LLM cron 02:00 V2 ─┘                              └─► 04:00 assemble (TTS+ffmpeg) ──► 05:00 video draft (CDP)
                                                          │
                                                     05:30 cleanup + 06:00 check
```

### 7.2 目录与关键路径（不变）
- 数据：`~/.hermes/data/xhs_treehole/` — `day_YYYYMMDD_dayN` / `day_YYYYMMDD_dayN_v2` / `published_content.json`
- 工程：`~/02_Cronjobs_Projects/01_XHS_Daily_Post/bin|core|generators|legacy`
- CDP 库：`vendor/xhs/cdp_publish.py|chrome_launcher.py|feed_explorer.py|run_lock.py`（2026-09-27 vendored 进项目；上游仓库仍在 `~/.hermes/xhs_skills/` 未动）
  venv 仍在 `~/.hermes/xhs_skills/venv`（32MB 二进制，不进 Git）；Playwright 渲染用 `hermes-agent/venv`
- Chrome：`~/Google/Chrome/XiaohongshuProfile`（**单数、无 /default**，仅小红书 147M），cron headless（`XHS_CHROME_HEADLESS=1`），手动 headed
  ⚠️ 与多平台混杂的 `~/Google/Chrome/XiaohongshuProfiles/default/`（5.5G）只差一个 `s` 但不是同一目录；实际路径由 `vendor/xhs/chrome_launcher.py` 的 `PROFILE_DIR_NAME` 决定

### 7.3 Cron 引用（Hermes 限制）
`~/.hermes/cron/jobs.json` 的 `script` 必须物理位于 `~/.hermes/scripts/`；本项目 `bin/` 为真身，`~/.hermes/scripts/` 下为 6 个薄 wrapper（`exec bash/python` 绝对路径），symlink 已被拒绝。

### 7.4 数据模型
- `post_data.json`：`{day_num, title, series, content_text, hashtags[6..10], best_post_time(YYYY-MM-DD HH:MM:SS 20–23h), emotion_tag, date: YYYYMMDD}` — 03:00 与 05:00 共用
- `manifest.json`：`{day_num, date, series, title, emotion_tag, v1_color_scheme/color_scheme, v2_angle, cards:[{index,file,type}], images_rendered: bool, generated_at}`
- `published_content.json`：`[{day_num, title, date: YYYYMMDD}]` — 01:00 与 05:00 双写，day_num 唯一，date 紧凑

---

## 8. UI/UX 与工具链（本次补充）

### 8.1 原则
- **图文卡片（V1，3:4 @1080×1440）**：移动端首屏阅读，短段落、大字号、高对比、温暖诗意；封面标题+系列名一眼可识别。
- **视频卡片（V2，9:16 @1080×1920）**：全屏/缩略图双清晰，字号更大、对比更强，适配竖版沉浸。

### 8.2 Open Design.app（UI 设计）
- **职责**：所有界面与版式设计 — 卡片母版、主题色板、字体排印、图标/纹样、封面构图规范。
- **工作流**：
  1. 在 Open Design.app 中维护 **XHS 情绪树洞 Design System**（主题 10 库→色板→字体→组件），输出 `design_tokens.json`（色值、字阶、间距）。
  2. 导出 **母版模板**（Figma-like 布局）供 `generators/render_card.py` 与 ComfyUI 工作流消费。
  3. 版本化主题（v2_angle 命名如“月光银灰 · 月色独白治愈风”）与 manifest 的 `color_scheme/v2_angle` 对齐。
- **产出**：`design/` 目录（tokens、母版、主题预览图），供 01:00/02:00 选主题时校验“最近 3 天不重复”。

### 8.3 图片与视频 — Hyperframes + ComfyUI（本地）
- **已安装**：`ComfyUI http://127.0.0.1:8188`（常驻，`Documents/comfy/ComfyUI/.venv`），Hyperframes 本地 CLI/库。
- **分工**：
  - **ComfyUI**：主渲染管线 — ① HTML→高分卡片（可选替代 CDP 截图）② 背景生成/纹理合成（渐变、纸纹、光斑）③ 风格化（冷调/暖调 LUT、柔光）。
     - 工作流：`workflows/comfy_xhs_card.json`（输入：主题 tokens + 文本 → 输出：1080×1440/1080×1920 PNG → 转 JPG）。
     - API：`POST /prompt` 触发，`GET /history` 轮询；失败回退到 CDP `render_xhs_cards.py`。
  - **Hyperframes**：帧级处理与视频管线 — ① 卡片到视频段的转场/缩放（Ken Burns）② 1080×1920 画布填充与安全边距 ③ TTS 对齐的段时长/字幕节奏 ④ 批量帧导出与质量检查。
     - 与 `_cron_assemble.py` 的 ffmpeg 互补：Hyperframes 负责“画面运动与节奏”，ffmpeg 负责“拼接与编码”。
- **回退策略**：ComfyUI/Hyperframes 不可用或超时 → 自动回退 CDP+ffmpeg（保持日更不中断）。
- **产出校验**：同 06:00 JPG 计数与尺寸校验（2160×2880）。

### 8.4 视觉规范（摘要）
- 主题库 10 选一 + 自创需不重复；V2 必须与 V1 及最近 3 天 V2 不同。
- 字阶：封面 48–76px / 正文 25–28px（V2 更大），行距 1.5–1.9，描边/阴影保证小图清晰。
- 配色：暖系（V1） vs 冷调/创意（V2），深底白字/浅底深字高对比。

---

## 9. 内容策略（SEO 级）

- 标题 ≤18 字，第二人称+共鸣+悬念；正文 400–900 字，首句逐字含 emotion_tag，中段反问，结尾落回主题。
- hashtags 6–10：`情绪树洞` + 主题词 + emotion_tag逐字原文 + 大流量词（情绪疗愈/自我接纳/松弛感/治愈系/焦虑等），纯中文不带 #（入库），发布时加 `#` 前缀。
- best_post_time 20:00–23:00 + 内容夜间高峰；published_content 去重与 `YYYYMMDD` 紧凑格式强校验。

---

## 10. 监控与告警

- 06:00 `check_xhs_pipeline.py`：目录/JPG×6/video/各 cron 今日 ok/红线/跨文件一致性/追踪表——静默或 Feishu 告警（`feishu:oc_6d4b826f9f3cefc71e25865d5803e1fb`）。
- 建议新增：ComfyUI/Chrome 可达性探针、TTS/ffmpeg 失败率、草稿箱计数可读性监控（近期 XHS 侧边栏由 `草稿箱(1)` 文本改为图标 badge 导致 `-1`）。

---

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| LLM 夜间 403/429 | 已固化到 `deepseek-v4-flash/opencode-go` + 3 路健康 fallback（deepseek/qwen） |
| 地域限流 | 仅用 CN 可用模型 |
| XHS UI 变更 | 选择器多备选 + headed 排查窗口 |
| Chrome 非 headless 失败 | `XHS_CHROME_HEADLESS=1` |
| 磁盘膨胀 | 05:30 7 天清理 + 空目录清扫 |

---

## 12. 路线图

- **v2.0（当前）**：Open Design Design System + ComfyUI/Hyperframes 双渲染（CDP 回退）落地。
- **v2.1**：草稿箱计数新 badge 适配 + ComfyUI 工作流版本化 + Hyperframes 转场模板化。
- **v3**：多主题 A/B、小红书数据回流（阅读/互动）驱动次日主题。

---

## 13. 附录：任务分解索引

详见 `TASKS.md`（按 3-role workflow 拆解：PM→Builder→Reviewer，含依赖、验收、产出）。
