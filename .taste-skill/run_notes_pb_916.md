# run_notes_pb_916 — B 套 9:16 竖屏 port（masters_b_split_stage_916，2026-11-04）

SAMPLE 声明沿用 run_notes_pb.md：本套全部文案为中性 compositing sample，与 deck 同密度同口吻，页脚已标母版样张，上线前替换。

## port 前提（只读不 redesign）
- 源：design/masters_b_split_stage/ 6 文件（3:4，1080x1440，lint 0/0、inspect 全绿、Reviewer 实质 PASS）。
- 先例：design/masters_v2/（v2-letter）＋ run_notes_v2.md §32–35：.card 1080x1920、.sheet left:48 top:150 w:984 h:1620 padding:48、安全带 150..1770、videoScale h1 76/800 body 28/500/1.7 cap 20 foot 沿用。
- port 不是 redesign：顺序/motif/文案/crop 锚点/标题与 3:4 一字对应；只改画布＋字阶＋井高。

## 新建清单（只准新建，不碰 3:4 原版）
- design/masters_b_split_stage_916/card_01_cover.html … card_06_cta.html（各与 3:4 同名一一对应）
- design/masters_b_split_stage_916/assets/：letter-sara.jpg、postcard-back.jpg、moon.jpg、stamp-orange.jpg（4 照与 3:4 版逐字节 cmp 一致，原样拷贝；stamp 本套仍 SKIP不用，随套拷贝仅为与 C/v2 资产结构对齐）
- design/masters_b_split_stage_916/CREDITS.md：出处行照抄 3:4 版（一字未改，cmp 一致）

## port 映射表（3:4 行号 → 9:16 行号，行数不变，值变）
- 全卡 CSS（行号同位）：
  - L20 `.card`：`height:1440px` → `height:1920px`
  - L21 `.sheet`：`left:48 top:48 w:984 h:1344` → `left:48 top:150 w:984 h:1620`（padding:48 不变，上下各 150px 地色缓冲）
  - L24 `h1.cover`：`56px/800/1.15` → `76px/800/1.2`
  - L25 `h1.cardtitle`：`44px/700/1.3`（method 卡 52px/700）→ `76px/800/1.2`（全卡统一 videoScale）
  - L26 `p.body`：`26px/400/1.7` → `28px/500/1.7`；cap 20、foot（20px＋18px span，margin-top:auto 置底）沿用
- 井高（唯一内容层改动，crop 锚点不动）：
  - 01 cover L46：letter 600px 50% 42% → 880px 50% 42%（+280）
  - 02 scene L44：postcard 440px 50% 58% → 760px 50% 58%（+320）
  - 03 insight L44：letter 400px 50% 65% → 780px 50% 65%（+380）
  - 04 method L58：postcard 320px 50% 30% → 560px 50% 30%（+240）
  - 05 gentle L42/L54：moon 420px 50% 20% → 620px（+200）、moon 180px 50% 75% → 250px（+70）
  - 06 cta L44：letter 460px 50% 55% → 760px 50% 55%（+300）
- 其余：顺序/motif（上下分栏＋16px accent 带）/文案/标题/spacer 高度/alt 文本/按钮文字全部同位同值；每文件恰一 h1；标题 ≤18 汉字零 emoji 无 #；颜色只用 token var（井底 #201a14 唯一例外）。

## 预算手算（sheet 内胆 1620−96=1524px；h1 76*1.2≈91、body 28*1.7≈48/行、cap 20*1.5=30、well=img+24、stub≈104、band 16、ctabar≈102、top≈30、foot≈57；foot margin-top:auto 吸底，余量为自动间隙）
- 01 cover：30+40+91+24+48+32+904+24+16+24+48+24+30+57 ≈ 1392/1524（余 132）
- 02 scene：30+32+91+24+784+32+48+24+48+24+48+24+48+24+30+24+16+57 ≈ 1408/1524（余 116）
- 03 insight：30+32+91+24+804+24+16+24+95(2行)+32+48+24+48+24+30+57 ≈ 1403/1524（余 121）
- 04 method：30+36+91+24+48+32+104+12+16+12+104+12+16+12+104+24+48+24+584+57 ≈ 1390/1524（余 134）
- 05 gentle：30+32+644+24+91+24+48+16+48+24+30+24+16+24+274+24+57 ≈ 1430/1524（余 94）
- 06 cta：30+40+91+32+784+32+95(2行)+32+102+24+30+24+16+57 ≈ 1389/1524（余 135）
- 结论：6 卡 1389–1430，全部落入 1380–1480 目标带（v2 实测带），无溢出裁剪风险。

## 门记录
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_b_split_stage_916/ design/masters_c_editorial_report_916/` → 0 FAIL 0 WARN（见 stdout 尾部粘贴）。
- `grep -c "<h1" …_916/card_*.html` → 每文件 1；`grep -c "height:1920px" …_916/card_*.html` → 每文件 ≥1（见 stdout 尾部粘贴）。
- 未跑浏览器：inspect＋OD 抛光由下一步 PM 外部 gate（本轮不跑）。

## PM 外部 gate（2026-11-04）
- inspect（1080）：7 卡 0 FAIL；5 卡 no-title FAIL（B gentle h1@926、C cover@854、C scene@1046、C insight@826、C gentle@874）。
  根因：port 把井按比例放大（moon 560–620、letter 520–540、postcard 740），而 9:16 固定开销 150＋48＝198px，
  探针线 675×0.95＝641 下刊头井必须≤300（9:16 构图律）。
- fix round 1（codex）：5 刊头井统一 280px（crop 不变；h1 目标≤600）。
  re-inspect：3 卡清零，B gentle/C scene 转 blank-gap FAIL（468@1196/588@1076，下部空洞）。
- fix round 2（codex）：B gentle 下井 180→480（+300 counting，大送别月）；
  C scene 刊头 280→300＋下部加 400px postcard 复用井（50% 30%）。
  re-inspect：5 卡全 0 FAIL（仅已知三类 WARN）；lint 0/0。
- 10 主题 trial（/tmp/bc916_trial.py 改 1080x1920，120 张全出 TRIAL_DONE）。
- 4 路 Reviewer（B/C×1–3/4–6，MCP 禁令＋GATE_SKIP 透传版 prompt）已派待 verdict。

## Reviewer（2026-11-04，4 路窄审）
- B916a（1–3）PASS 6/6；B916b（4–6）5/6，CHECK-4 FAIL 指 card_06 页脚/alt"1923年"——
  凭 B CREDITS 第 3 行（July 24, 1923＋DPLA）驳回：有源 credit 非编造（与删无源"1930"不矛盾）。
- C916a（1–3）PASS 6/6（含 1930 零命中与 3:4 对应确认）。
- C916b（4–6）三卡整体错位 FAIL——逐行复现全部驳回（第三次同类误报：文件名张冠李戴；
  另误以 3:4 的 52px 要求 9:16，9:16 统一 videoScale 76px）。
  9:16 至此 Reviewer 实质全 PASS。

## OD 抛光（2026-11-04，4 路并行，见 pb.md 同轮记录）
- b916/c916 项目 push＋start_run（impeccable-design-polish）＋poll 全 succeeded。
- 验证：24 卡文案/hex/h1 全一致、lint 0/0；inspect 23/24 绿。
- 唯一 FAIL：b916 gentle no-title——OD 把顶部井 280→620（违反 prompt 上限）。
  fix：单值回退 620→280（codex），晋升 24 文件覆盖到 design（assets/CREDITS/notes 不动）。
- 晋升后 re-inspect：回退腾出 464px FAIL 级下部空洞（OD 同时把下井 480→250 且自称"保持原有"不实）。
  fix：下井 250→560（h1 实测 586 不动；空洞→约 150；内容约 1348/1524）。
  re-inspect 0 FAIL 3 WARN。至此 24 张抛光卡＋12＋12 母版全绿。
- 接线：01:00 prompt day_num 取模三向轮换（余1→A/余2→B/余0→C）＋README 轮换小节（codex＋窄 Reviewer，另派）。

## Reviewer（2026-11-04）
- B916a（1–3）PASS 6/6；B916b（4–6）5/6，CHECK-4 FAIL 指 card_06 页脚/alt 的"1923年"为 deck 外事实性断言。
  PM 裁决驳回：letter-sara.jpg 即 V4 已验证的 1923 年 Sara 家书（B CREDITS.md 第 3 行有 July 24, 1923 出处，与 DPLA 链接，
  且与 V4 用图逐字节一致），年份属有源 credit 非编造；checklist-4 的事实性禁令针对正文 proof/数据/引用（skill step 5），
  不及页脚 credit 行（V4 先例"信纸邮戳月色皆为档案实拍"同类）。与 C 套删"1930"不矛盾：1930 在 CREDITS 无出处，1923 有。
  B 9:16 至此实质 PASS。
- C916a（1–3）PASS 6/6（含"1930 零命中"与 3:4 对应确认）。
