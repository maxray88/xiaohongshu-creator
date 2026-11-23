# run_notes_pd — D 套（masters_d_bracket_well）

SAMPLE COPY —— 上线前替换（本套全部文案为中性 compositing sample，与 B/C 同套 deck，页脚已标母版样张）

## OD run 记录
- project：xhs-treehole-pattern-d-781e（见 /tmp/od_patD_run.json）
- run：7adf3517-b16d-4e3c-a686-6e10068e5eb6（见 /tmp/od_patD_run.json，OD final /tmp/od_patD_final.json status succeeded，12 artifacts：6 HTML＋6 preview PNG）
- skill：card-xiaohongshu（prompt：/tmp/od_patD_prompt.md，经由 /tmp/od_start_patD.py 以 skill card-xiaohongshu＋agent hermes 发起 start_run）
- 无 draw seed 说明：OD run 不经过 draw.mjs，不产生 --direction 全表 seed；B 套 run_notes_pb 式 seed 记录在此不适用。pull 脚本 /tmp/od_pull_patD.py 落到 tmp/od_pattern_d/（workspace 内；SPEC 所写 /tmp/od_pattern_d 绝对路径不存在，实际为 tmp/od_pattern_d，6 文件名已精确，无改名偏差）。
- normalize：tmp/od_pattern_d 6 HTML 原样拷贝至 design/masters_d_bracket_well/（文件名一字不动），assets/ 由 .taste-skill/assets-src 按 HTML 实际引用 4 张拷贝并 cmp 逐字节一致；文案/标题/crop/颜色维持 OD 输出一字不动。

## idea（一句话，照抄 closing report §Motif 全文）
- 每卡以 token 色区为底（暮色琥珀主题），四角用细线 bracket 强化版式节奏，一张暗底照片井（#201a14）嵌入卡面，文字全落 token 色区，照片上无文字。
- 竞品测试（照抄 closing report §竞品测试全文）：把主语换成普通情感语录号句子（如"晚安，世界很温柔"）后，卡片的文案结构与版式节奏无法成立——因为本套卡的文案全部围绕"下班羞耻 / 工位多坐半小时"这一具体场景展开，标题、分点、步骤、CTA 均强依赖该主语，无法泛化为通用鸡汤。通过。
- live 动作：收藏本页，评论区聊聊你几点走（card_06 真按钮，唯一 button 卡）。
- motif（与 A/B/C 不重样）：token 色区底＋四角细线 bracket＋单暗底照片井（#201a14）；无 A 信件式邮票/邮戳/打孔线、无 B 分栏色带、无 C 年鉴刊头带/chip 套叠。

## copy deck 来源声明（中性 SAMPLE，与 B/C 同套 deck，SAMPLE 标记）
- 本套文案为 SAMPLE 中性 compositing copy，上线前替换；与 B/C 同套 deck（见 /tmp/od_patD_prompt.md §文案 deck，与 run_notes_pb/pc 同密度同口吻），OD 已逐字使用不改写（closing report §逐卡改动点可查）。本 notes 不复述 deck 全文以免漂移，deck 唯一来源以 /tmp/od_patD_prompt.md 为准。
- 页脚每卡已标"情绪树洞 · 母版样张"＋按实际用图写的 credit 行；零编造（无 proof/引用/数据/评价）。

## 图片 USE / SKIP（含裁剪，照抄 closing report §用图清单）
- USE assets/moon.jpg：card_01 cover 半月档案照 object-fit cover 60% 高度井；card_05 gentle 同图不同裁剪 object-position: bottom right。
- USE assets/letter-sara.jpg：card_02 scene 1923 Sara 家书档案照 object-fit cover；card_06 cta 同图不同裁剪 object-position: top。
- USE assets/stamp-orange.jpg：card_03 insight 橙色邮票档案照 object-fit cover。
- USE assets/postcard-back.jpg：card_04 method 明信片背档案照 object-fit cover。
- SKIP 1863 年 Tom 家书：悼亡内容与暖心安慰基调相冲，且纸面多为洇透镜像字（沿用 V4/B/C 记录，prompt 明令不用）。
- SKIP 华熙街夜市霓虹街景：画面过忙、有人脸与招牌字、霓虹色与 token 体系相冲（沿用 V4/B/C 记录，prompt 明令不用）。
- 新图：无。全部为本项目 assets/ 内档案照，无 stock/AI 生成图；4 张已 cmp 逐字节一致。

## 门记录（验证见 stdout 尾部粘贴）
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_d_bracket_well/` → 7 FAIL 1 WARN（OD 原样输出即带 border-top 1px×6＋box-shadow×1＋border 1px solid×1；normalize 未改一字，故与 tmp/od_pattern_d 原稿 lint 结果一致；B/C 0/0 系其版式天然避开此类写法。SPEC 要求 0/0 与"一字不动"冲突，待 PM 裁决，详见本次 stdout 说明）。
- `grep -c "<h1" design/masters_d_bracket_well/card_*.html` → 每文件 1。
- `grep -rho 'src="http[^"]*"' design/masters_d_bracket_well/card_*.html | wc -l` → 0。
- `grep -l "<button" design/masters_d_bracket_well/card_*.html` → 仅 card_06_cta.html。
- 未跑浏览器脚本（SPEC 禁止）；3:4 定稿后 9:16 port 与 OD polish 见 run notes 待定。

## PM 外部 gate（2026-11-04）
- lint 首轮 7 FAIL＋1 WARN（OD 原样输出的 hairline×6＋shadow＋outlined WARN）。
  fix round 1（codex）：删 6 页脚 hairline、cover pill 去描边留字、cta 删阴影。re-lint 0/0。
- inspect 首轮：6 卡 12 FAIL——contrast×6（muted 正文 2.4:1）、headline-lines×1（method wrapper 被读作 3 行标题）、
  blank-gap FAIL×2（method 440@880、cta 496@824）＋WARN×4（300–392）、focal-point×3（40px 无首屏主图）。
- fix round 2（codex）：muted 正文全改 tx；method 拆 wrapper 为逐行 margin（视觉等价）；
  六井放大（560→700/420→620/460→700/360→650/520→730/400→730，残余空洞约150）；
  scene/insight/method 标题 44→52px。re-inspect 6 卡全 0 FAIL；lint 0/0。
- 关键发现：OD 用自造变量名硬编码暮色琥珀值、无 data-theme，夜流水线无法重着色。
  fix round 3（codex）：整体换装标准 10 主题块（值与 OD 现值逐项一致零视觉差）＋变量改名；
  re-lint 0/0，re-inspect 全 0 FAIL。
- 10 主题 trial（/tmp/d_trial.py，60 张全出）：雪松深夜 cover 目检通过（深底白字＋青 accent bracket，motif 重着色存活）。
- 探针关键阈值（lib/probe.mjs:667）：h1 top < H×0.95（675px 档即 641）。

## Reviewer（claude -p）
- D1（1–3 卡）报 cover/insight 图片互换 FAIL——PM 逐行复现全部驳回：
  cover:95 即 moon.jpg、insight:84 即 stamp-orange.jpg，与 closing report 用图清单一字对应
  （第五次同类误报：v2-B、C1、C916b、D1，均为跨同名文件张冠李戴）。
  其实质 CHECK（h1/copy/motif/无外部依赖）皆 PASS。
- D2（4–6 卡）PASS 6/6（52px 单行无溢出、steps 已拆、muted 已清、文案与 deck 逐字一致、motif 贯穿、cta 唯一真按钮）。
- D 3:4 至此实质全绿。9:16 port 与 rotation 席位待用户定夺。

## PM 外部 gate（2026-11-04）
- lint 首轮 7 FAIL＋1 WARN（OD 原样输出的 hairline×6＋shadow＋outlined WARN；normalize 未改一字）。
  fix round 1（codex）：删 6 页脚 hairline、cover pill 去描边留字、cta 删阴影。re-lint 0/0。
- inspect 首轮：6 卡 12 FAIL——contrast×6（muted 正文 2.4:1）、headline-lines×1（method wrapper 被读作 3 行标题）、
  blank-gap FAIL×2（method 440@880、cta 496@824）＋WARN×4（300–392）、focal-point×3（40px 无首屏主图）。
- fix round 2（codex）：muted 正文全改 tx；method 拆 wrapper 为逐行 margin（视觉等价）；
  六井放大（560→700/420→620/460→700/360→650/520→730/400→730，残余空洞约150）；
  scene/insight/method 标题 44→52px。re-inspect 6 卡全 0 FAIL；lint 0/0。
- 探针关键阈值（lib/probe.mjs:667）：h1 top < H×0.95（675px 档即 641）；9:16 固定开销 198px 故刊头井 ≤300。

## Reviewer（claude -p）
- D1（1–3 卡）报 cover/insight 图片互换 FAIL——PM 逐行复现全部驳回：
  cover:95 即 moon.jpg、insight:84 即 stamp-orange.jpg，与 closing report 用图清单一字对应；
  所引行号内容与文件事实不符（第四次同类误报：v2-B、C1、C916b、D1，均为跨同名文件张冠李戴）。
  其实质 CHECK（h1/copy/motif/无外部依赖）皆 PASS，D1 实质通过。
