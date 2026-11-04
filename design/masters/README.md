# Masters — 6 Card Templates (Open Design.app → generators/render_card.py + ComfyUI)

All cards share `design_tokens.json` canvas/spacing/typography. Export as `masters/*.html` references.

| Card | Purpose | Layout key |
|---|---|---|
| cover | Title + series, first-screen emotion keyword | centered title 56px + tag 18px + series caption |
| scene | Relatable everyday situation | left-aligned scene 2–3 lines, soft illustration slot |
| insight | Psychological perspective shift | quote block + accent bar |
| method | 3-step actionable exercise | numbered steps 1·2·3 with icons |
| gentle | Warm message | centered gentle copy + soft gradient |
| cta | Comment call-to-action | question + “评论区聊聊” button |

**Cover spec:** title ≤18 chars, emotion keyword in first line, safe margin 48px, high contrast (deep text on light bg or white on deep bg).

**Export:** Open Design → Export HTML masters to `design/masters/` (kept in sync with generators).
V3 (2026-11-03, taste-skill run, brief design/redesign_brief.md): 6 files above; sample copy from day_20261102_day106; live source in design/masters_v3/.
V4 OD-polish (2026-11-03, Open Design run on xhs-treehole-v4, card-xiaohongshu recipe): refined crops/type, moon-lead gentle preserved; sample copy day_20261102_day106; live source design/masters_v4/ + OD project.

## 三向轮换（2026-11-04，nightly day_num%3）
- A 信件 `design/masters/`：未寄出的信＋橙色邮票＋邮戳环＋打孔虚线每页页脚 ministamp。
- B 分栏 `design/masters_b_split_stage/`：上半照片井＋下半纸色阅读栏＋16px accent 交界带无邮票。
- C 年鉴 `design/masters_c_editorial_report/`：刊头照片带＋整块 g1 色页＋chip 套叠邮票仅 04 邮资凭证。

| day_num % 3 | 套系 | 目录 |
|---|---|---|
| 余 1 | A 信件 | `design/masters/` |
| 余 2 | B 分栏 | `design/masters_b_split_stage/` |
| 余 0 | C 年鉴 | `design/masters_c_editorial_report/` |

三套 6 卡同名（card_01_cover … card_06_cta），一晚只用一套、禁止跨套混搭 motif；01:00 任务按 day_num 取模选中一套后照抄版式/节奏/token 用法，只换今晚文案与主题色。
9:16 双生套（`*_916`）供手动 premium 视频重建；V2 流水线 remap 自动跟随 V1 轮换。
各套 SAMPLE 文案上线前替换（notes 有 SAMPLE 标记）。
