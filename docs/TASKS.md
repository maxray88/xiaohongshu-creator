# TASKS — 01_XHS_Daily_Post（3-role workflow）

> **How to use:** Hermes (PM) 负责需求与指令，Builder（codex exec / patch）执行，Reviewer（claude -p / delegate_task）验收，迭代至 PASS。按波次执行，不跳步。

## Wave 0 · PRD & 基线

| ID | 任务 | Owner | 产出 |
|---|---|---|---|
| T0-01 | 定版 PRD（含 Open Design / ComfyUI / Hyperframes 补充） | PM | `docs/PRD.md` ✅ |
| T0-02 | 梳理现状：bin/core/generators/legacy 目录与 cron 8 任务基线 | PM | 本 TASKS |

---

## Wave 1 · 设计体系（Open Design.app）

| ID | 任务 | 依赖 | 验收 |
|---|---|---|---|
| T1-01 | 在 Open Design.app 新建 **XHS 情绪树洞 Design System**：10 主题色板 + 字阶/间距 tokens | — | `design/design_tokens.json` 含 10 主题 HEX、字阶、间距 |
| T1-02 | 导出 6 卡母版（cover/scene/insight/method/gentle/cta）+ 封面构图规范，关联 `v2_angle` 命名 | T1-01 | `design/masters/` + 预览图，manifest 的 `color_scheme/v2_angle` 可映射 |
| T1-03 | 主题校验器：脚本 `design/validate_theme.py` 读最近 3 天 manifest，断言新主题不重复 | T1-01 | 06:00 同源逻辑抽离，`python validate_theme.py --new 苔藓墨绿` 返回 ok/fail |

## Wave 2 · 渲染管线（ComfyUI + Hyperframes + CDP 回退）

| ID | 任务 | 依赖 | 验收 |
|---|---|---|---|
| T2-01 | ComfyUI 工作流 `workflows/comfy_xhs_card.json`：输入 tokens+文本 → 输出 1080×1440/1080×1920 PNG → JPG | T1-01 | `curl /prompt` 可触发，本地生成 2160×2880 2x |
| T2-02 | Hyperframes 帧管线：Ken Burns 缩放、1080×1920 安全边距、段时长与 TTS 对齐、批量导出 | T2-01 | 与 `_cron_assemble.py` 的 ffmpeg 互补，段时长 diff <50ms |
| T2-03 | 统一渲染入口 `core/render_xhs_cards.py` 改造：优先 ComfyUI/Hyperframes，失败回退 CDP（`file://绝对路径 + 1080×1440@2x`） | T2-01,T2-02 | 02:30 实测：ComfyUI 可用时走 ComfyUI，否则 CDP，manifest `images_rendered=True` 且 JPG≥6 |
| T2-04 | 06:00 校验对齐：JPG 计数权威（≥6）+ 尺寸校验 2160×2880，与 today-guard 同源 | T2-03 | 自检与渲染同判据 |

## Wave 3 · 内容生成加固

| ID | 任务 | 验收 |
|---|---|---|
| T3-01 | 固定 01:00/02:00 到 `deepseek-v4-flash/opencode-go`（已完成）+ 3 路健康 fallback（deepseek/qwen）| `jobs.json` 模型 pin + config fallback 已验证 |
| T3-02 | Prompt 红线回归测试：标题≤18、首句含 emotion_tag、hashtags 含品牌词+emotion_tag、best_post_time 20–23h | 06:00 [合规] 全绿 |
| T3-03 | 跨文件一致性测试：V1 manifest/post_data/V2 manifest 同标题同系列 | 同上 |

## Wave 4 · 发布与合成

| ID | 任务 | 验收 |
|---|---|---|
| T4-01 | 03:00 图文草稿：`content_text`+`hashtags` 带 `#` 前缀，`images/card*.jpg` 6 张，CDP 填表 today-guard | Feishu 草稿箱可见，06:00 ok |
| T4-02 | 04:00 合成：6 层文本清洗 + Edge-TTS 3×5s 重试 + ffmpeg 竖版，today-guard | 1.5–3 MB / 60–90s，TTS 一致性 ✅ |
| T4-03 | 05:00 视频草稿：仅 `video_note.mp4`，描述用 hashtags 带 `#`，today-guard | 同上 |
| T4-04 | 草稿箱计数新 badge 适配（近期 XHS 由 `草稿箱(1)` 文本改为图标 badge 导致 -1）| 计数可读或改用页面内容存在性校验 |

## Wave 5 · 运维与可观测

| ID | 任务 | 验收 |
|---|---|---|
| T5-01 | 05:30 清理 + 空目录清扫 | 2 删 12 留（示例），7 天滚动 |
| T5-02 | 06:00 自检：目录/JPG×6/video/各 cron 今日 ok/红线/追踪表（去重+YYYYMMDD）| 全绿静默，异常 Feishu 告警 |
| T5-03 | 新增探针：ComfyUI `127.0.0.1:8188` + Chrome 9222 可达性 | 失败早告警 |

## Wave 6 · 加固与审计（3-role 循环）

- 按 `coder-three-role-workflow` 执行：PM 读全量 → Builder patch → Reviewer delegate_task；覆盖 data-flow、wave、cross-cutting、anti-pattern、shell、daemon、domain 5 维、性能压测。
- 准出：`py_compile` + 运行时单测（TTS 清洗、manifest 一致性、渲染回退）均 PASS。

## 依赖图

```
T1-01 → T1-02 → T2-01 → T2-03 → T2-04
              ↘ T2-02 ↗
T3-* 并行
T4-01/04: 依赖 T1-02 + T2-03
T5-* 依赖全部
```

## 里程碑

- **M1 设计体系就绪**：T1 完成 + tokens 可被生成器消费
- **M2 双渲染可用**：T2 完成，02:30 可走 ComfyUI/Hyperframes
- **M3 日更全绿**：T3+T4+T5 完成，06:00 静默

