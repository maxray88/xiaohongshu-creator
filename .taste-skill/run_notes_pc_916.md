# run_notes_pc_916 — C 套 9:16 竖屏 port（masters_c_editorial_report_916，2026-11-04）

SAMPLE 声明沿用 run_notes_pc.md：本套全部文案为中性 compositing sample与 deck 同密度同口吻，页脚已标母版样张上线前替换。

## port 前提（只读不 redesign）
- 源：design/masters_c_editorial_report/ 6 文件（3:4，fix round 4 后全绿：C method 顶部刊头带已补、8 处年份已去年份）。
- 先例同 B（v2-letter §32–35）：.card 1080x1920、.sheet 48/150/984/1620/padding48、安全带 150..1770、h1 76/800 body 28/500/1.7 cap 20 foot 沿用。
- port 不是 redesign：顺序/motif（年鉴刊头带＋轴线＋色页）/文案/crop 锚点/标题与 3:4 一字对应；只改画布＋字阶＋井高。

## 新建清单（只准新建不碰 3:4 原版）
- design/masters_c_editorial_report_916/card_01_cover.html … card_06_cta.html（各与 3:4 同名一一对应）
- design/masters_c_editorial_report_916/assets/：letter-sara.jpg、postcard-back.jpg、moon.jpg、stamp-orange.jpg（4 照与 3:4 版逐字节 cmp 一致原样拷贝；stamp 仅 04 方法页邮资凭证图一次出现非贯穿 motif，沿用 3:4）
- design/masters_c_editorial_report_916/CREDITS.md：出处行照抄 3:4 版（一字未改，cmp 一致）

## port 映射表（3:4 行号 → 9:16 行号，行数不变，值变）
- 全卡 CSS（行号同位）：
  - L20 `.card`：`height:1440px` → `height:1920px`
  - L21 `.sheet`：`left:48 top:48 w:984 h:1344` → `left:48 top:150 w:984 h:1620`
  - L25 `h1.cover`：`56px/800/1.15` → `76px/800/1.2`
  - L26 `h1.cardtitle`：`44px/700/1.3`（method 卡 52px/700）→ `76px/800/1.2`（全卡统一 videoScale）
  - L27 `p.body`：`26px/400/1.7` → `28px/500/1.7`；cap 20、panel/chip padding、ctabar 30px、foot（margin-top:auto 置底）沿用
- 井高（唯一内容层改动，crop 锚点不动）：
  - 01 cover L43/L55：letter 420px 50% 42% → 540px（+120）、letter 200px 50% 55% → 280px（+80）
  - 02 scene L43：postcard 420px 50% 58% → 740px（+320）
  - 03 insight L43/L55：letter 420px 50% 65% → 520px（+100）、letter 180px 50% 42% → 240px（+60）
  - 04 method L43/L59：postcard 刊头带 200px 50% 30% → 280px（+80）、stamp 220px 50% 20% → 300px（+80；腾预算沿用 fix4 比例）
  - 05 gentle L43/L55：moon 420px 50% 20% → 560px（+140）、moon 160px 50% 70% → 260px（+100）
  - 06 cta L45：postcard 480px 100% 0 → 760px 100% 0（+280，邮戳邮票角锚点不动）
- 其余：顺序/motif/文案/标题/spacer 高度/panel-chip 结构/alt 文本/按钮文字全部同位同值；每文件恰一 h1；标题 ≤18 汉字零 emoji 无 #；颜色只用 token var（井底 #201a14 唯一例外）。

## 预算手算（内胆 1524px；h1≈91、body≈48/行、cap 30、well=img+24、chip≈88、panel=64+内容、ctabar≈102、top≈30、foot≈57；余量由 margin-top:auto 吸收）
- 01 cover：30+32+564+32+91+24+48+32+154+24+304+24+57 ≈ 1416/1524（余 108）
- 02 scene：30+32+764+24+91+24+176+24+48+24+48+24+30+57 ≈ 1396/1524（余 128）
- 03 insight：30+32+544+24+91+24+159+32+48+24+30+24+264+24+57 ≈ 1407/1524（余 117）
- 04 method：30+32+304+24+91+24+48+32+360+24+48+24+324+57 ≈ 1422/1524（余 102）
- 05 gentle：30+36+584+28+91+24+176+24+30+24+284+24+57 ≈ 1412/1524（余 112）
- 06 cta：30+40+91+32+784+32+95(2行)+32+166+24+30+57 ≈ 1413/1524（余 111）
- 结论：6 卡 1396–1422，全部落入 1380–1480 目标带无溢出裁剪风险。

## 门记录
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_b_split_stage_916/ design/masters_c_editorial_report_916/` → 0 FAIL 0 WARN（见 stdout 尾部粘贴）。
- `grep -c "<h1" …_916/card_*.html` → 每文件 1；`grep -c "height:1920px" …_916/card_*.html` → 每文件 ≥1（见 stdout 尾部粘贴）。
- 未跑浏览器：inspect＋OD 抛光由下一步 PM 外部 gate（本轮不跑）。

## PM 外部 gate（2026-11-04）
- 9:16 首轮 inspect：7 卡 0 FAIL；5 卡 no-title FAIL（h1 在 826–1046）。
  根因：port 把井按比例放大而 9:16 有 198px 固定顶部开销，探针线 675×0.95＝641 下刊头井必须≤300（9:16 构图律）。
- fix round 1（codex）：5 刊头井统一 280px。re-inspect：5 卡 no-title 全清但 B gentle/C scene 转 blank-gap FAIL（468@1196/588@1076）。
- fix round 2（codex）：B gentle 下井 180→480、C scene 刊头 280→300＋下部加 400px postcard 复用井（50% 30%）。
  re-inspect：2 卡全 0 FAIL（仅已知三类 WARN）；lint 0/0。
- 10 主题 trial（/tmp/bc916_trial.py 改 1080x1920，120 张全出 TRIAL_DONE）。

## Reviewer（claude -p，4 路窄审）
- B916a（1–3）PASS 6/6；B916b（4–6）5/6，CHECK-4 FAIL 指 card_06 页脚/alt"1923年"无出处——
  PM 凭 B CREDITS 第 3 行（July 24, 1923＋DPLA 链接）驳回：有源 credit 非编造（与 C 套删无出处"1930"不矛盾）。
  B 9:16 实质 PASS。
- C916a（1–3）PASS 6/6（含 1930 零命中与 3:4 对应确认）。
- C916b（4–6）CHECK-1/4/5/6 四项 FAIL 称 method/gentle/cta 内容三向轮错位——
  PM 逐文件逐行复现全部驳回：card_04 h1:45 即 method 标题＋postcard 刊头:43＋stamp:59；
  card_05 h1:45 即 gentle 标题＋moon:43/:55；card_06 h1:43 即 cta 标题＋postcard:45＋真按钮:50。
  所引行号内容与文件事实逐项不符（第三次同类误报：v2-B、C1 均为审阅员跨文件名张冠李戴）；
  另 CHECK-1 误以 3:4 的 52px 要求 9:16（9:16 统一 videoScale 76px，见 port 映射表 L26）。
  C 9:16 实质 PASS，无需改动。
