# 情绪树洞 masters V3 改版简报（taste-skill V3 run 输入）

> 给 `.claude/skills/design-taste-frontend/SKILL.md` steps 1–9 的 runner 用。本文即 step 1 的 brief。

## 0. 不可谈判项（先读这盒）

- **画布固定 1080×1440（3:4）**，v1 规格。禁止改尺寸、禁止响应式三断点思维。
- **6 个文件，文件名必须精确**：`card_01_cover.html … card_06_cta.html`（cover/scene/insight/method/gentle/cta）。
  - 下游 02:00 / 02:30 / 04:00 任务硬依赖此命名。**2026-09-27 day82 故障先例**：改名即断流水线。
- **字体：Noto Sans SC**（`design_tokens.json` typography.fontFamily）。
- **标题 ≤18 个汉字；全篇无 emoji；标题内禁用 `#`**（06:00 watchdog 会判失败）。
- **颜色只准用 token CSS 变量**：masters 每晚被重套全部 10 个主题，写死一个色值即壊 9 个主题。
- **安全边距 48px**，圆角 24px，卡片内边距 48px（spacing tokens）。

## 1. 主题 / 受众 / 唯一行动

- **主题**：情绪树洞 nightly 小红书情感卡片（6 卡一组：cover / scene / insight / method / gentle / cta）。
- **受众**：深夜刷手机的年轻中文用户，情绪共鸣 + 求安慰。
- **唯一行动**：**收藏（SAVE，第一目标）+ 评论区留言**。每卡都为此服务：cover 负责停留，cta 负责开口。

## 2. 品牌（只从 token 取，不自创）

- 唯一来源：`design/design_tokens.json`。10 主题：
  - 浅：暮色琥珀 / 晨雾薄荷 / 雾蓝海湾 / 玫瑰暮云 / 森林晨光 / 麦田晚风 / 莓果初雪
  - 深：海盐汽水 / 雪松深夜 / 苔藓墨绿
- 字阶（coverTitle 56px/800，cardTitle 36px/700，body 26px/400/1.7，caption 20px，tag 18px/600）与 spacing（见 §0）直接映射为 CSS 变量。
- draw 命令带 `--keep palette,type`：只取构图，不取新配色/字体。

## 3. 卡片骨架 → draw 角色映射

| 卡片 | draw role | 说明 |
|---|---|---|
| cover | hero（隐含） | 情绪关键词首屏，居中大标题 |
| scene | showcase | 代入感日常场景 2–3 行 |
| insight | proof | 观点反转，quote + accent bar |
| method | how-it-works | 3 步可执行小练习 |
| gentle | about | 暖心收束，居中柔光 |
| cta | cta | 提问 + "评论区聊聊"按钮 |

- 若某 role 承载不下真实文案，runner 用 `--alternatives` 确认替代，禁止静默替换。
- Draw 命令模板（先 `--options 3`，选中后再去 `--options` 重打全表）：
  ```bash
  node <skill>/scripts/draw.mjs --sector "<最接近 --list sectors 的一项，记录选择>" \
    --brief "深夜情绪树洞小红书卡片：给年轻人的睡前安慰" \
    --sections showcase,proof,how-it-works,about,cta \
    --tone warm --keep palette,type --options 3
  ```
- 注意：`--have` **省略**（无自有素材，见 §4）。

## 4. 配图规则（诚实图片优先序）

- **无项目自有照片**。图源只走开档：`<skill>/scripts/assets.mjs` 搜索 + `--get` 下载，`--credits` 出处写进页脚。
- **硬约束：每张图必须在全部 10 个主题（浅 + 深）下存活**。做法二选一：
  - 主题无关槽位：固定对比度的图片井（image well，图内自带底/描边，不吃主题色）；
  - 纯代码绘制 motif（CSS/SVG 纹样，无外部依赖）。
- 底线：**每卡必有诚实配图或 motif**；禁止 stock 填充图，禁止伪造产品/人物照。

## 5. 文案规则（先写 copy deck，再排版）

- 用**真实历史某天目录**（`~/.hermes/data/xhs_treehole/day_*`）做样本文案，保证满密度设计；report 注明用了哪一天。
- 中文流水线规则：段落 1–3 短句；**首行钩子**；正文中间一处**反问句**；温暖**李雪琴式**口吻。
- **绝不编造** proof / 引用 / 数据 / 用户评价（skill step 5 同款禁令）。

## 6. Idea + 竞品测试

- 先列 情绪树洞 世界清单 8–12 项：深夜、树洞来信、没发出去的消息、熄灯后的宿舍、加班的地铁、未接来电、备忘录草稿、阳台风声……
- 定稿句式（开工前必须填满两空）：
  > On these cards, **[X：只属于树洞的东西]** becomes **[Y：direction 要求的装置]**.
- **竞品测试**：把句中主语换成其他情感账号。若句子依然成立 → idea 被否，重找。
- skill "one live thing" **豁免**（成品是静态 JPG，无交互）。替换为：**一个 motif 贯穿全部 6 卡**（如未寄出的信封折角 / 树洞年轮），report 点名该 motif。

## 7. 检查门

- `<skill>/scripts/inspect.mjs` house rules 全过（无 FAIL；WARN 需一句话辩护）。
- **截图只钉 1080 卡宽**（固定画布，不是网页三断点 1440/768/390）。
- 项目门：
  - 经 `generators/render_card.py` 实际渲染出图；
  - 06:00 watchdog 规则：标题 ≤18、无 emoji、hashtag 6–10 条等；
  - **每个 master 对全部 10 主题逐一预览**（浅色深色对比度都要过）。

## 8. 交付 + 运行纪律

- **离线工作，绝不在 cron 内跑**；过程文件进 `.taste-skill/`（before/after/inspect）。
- 输出到**新建 `design/masters_v3/`**，禁止覆盖现行 `design/masters/`。
- Report 必含：方向选择 + 为什么、每次 redraw + 原因、credits 行、用的是哪个 sample day 目录。
