# run_notes_pc — C 套（masters_c_editorial_report）

SAMPLE COPY —— 上线前替换（本套全部文案为中性 compositing sample，与 deck 同密度同口吻，页脚已标母版样张）

## deal 记录（与 B 套同一两次 deal，见 run_notes_pb.md）
- 命令 1（tone warm）：候选池 page-is-the-object / split-stage / place-carries-it
- 命令 2（tone editorial不同 seed 做法）：候选池 contact-sheet / editorial-report / name-as-monument
- 全表 seed：split-stage 977848630（tone warm）；editorial-report 1694702842（tone editorial），均 2026-11-04 落表记录
- 落选 4 个一句话理由见 run_notes_pb.md（page-is-the-object 与 V4 同构禁选；place-carries-it 需全幅地点照；contact-sheet 需很多照片；name-as-monument 装不下 6 脊柱）。
- redraw：0 次。

## 选中：editorial-report（C）
- 存活论证：每卡只需 1 条刊头照片带（单裁剪），4 张档案照以不同裁剪复用即够（letter 42%/65%、postcard 58%/100% 0、moon 20%、stamp 20% 邮资凭证图），满足"同一家族复用不同裁剪"（direction sheet 原话）；dealt picsum 城市氛围图刻意不用（对树洞主题不诚实，SPEC 禁摆拍式 stock）；folio 页码刻意不做（lint numbering 禁令）。
- 脊柱论证：cover（刊头带＋大标题＋色页收束）/ scene（刊头带＋色页装两行现场）/ insight（刊头带＋色页装长论点）/ method（三 chip 色页＋邮资凭证图）/ gentle（大月亮刊头带＋居中色页）/ cta（邮戳角刊头带＋色页装按钮），6 位置各有处放。

## idea（一句话，两空已填，动工前完成）
- 在这套卡里没说出口的加班夜 becomes 一本深夜年鉴：刊头照片带＋起排轴线＋整块双色页像被编辑过一样认真对待。
- 竞品测试：主语换成普通情感语录号，"每日一句晚安 becomes 一本深夜年鉴"不成立（语录号没有表现性忠诚这种值得认真编辑的内容骨）；只有树洞的 6 卡脊柱（cover/scene/insight/method/gentle/cta）配得上年鉴式编排。
- live 动作：收藏本页，评论区聊聊（card_06 真按钮）。
- motif（与 V4 彻底换血）：年鉴刊头＋轴线＋色块——每卡顶部一条刊头照片带（深底 #201a14），标题起排、正文单栏，步骤/引言/按钮落在整块 g1 色页（method 用 g0 chip 套叠）；无邮票贯穿、无齿孔打孔线、无邮戳圆环、无页脚 ministamp（邮票仅在 04 出现一次做邮资凭证图非 motif）。

## copy deck（与 .taste-skill/copy_deck.md 同密度同口吻，sample；与 B 套同文案便于轮换对照）
- 01 cover：下班了，你却不敢走 / 工位上多坐的那半小时，今晚一次说清楚。/ 今晚十点，树洞开门。/ 把这封信先收藏好明晚接着聊。
- 02 scene：领导没走你也不敢动 / 同事的键盘还在响，你把伸向关机键的手又收了回去。/ 明明活早就干完了却打开文档假装还在忙。/ 你说这班到底是加给谁看的？/ 你说再待一会儿心里已经吵了三轮走还是留。/ 下班羞耻是工位上多坐的那半小时。
- 03 insight：被看见努力才有安全感 / 心理学里有个说法，叫表现性忠诚。当安全感绑在被看见努力上，离开就等于冒险。/ 可领导真的在看你几点走吗？大多时候人家只是在忙自己的事。/ 你脑补的那些评判多半是心里的回声。
- 04 method：三秒钟，练习准时走 / 有点傻但真的管用。今晚就试一次。/ 一，默念三秒我的下班我做主。/ 二直接站起来收拾包。不解释不道歉。/ 三出门别回头，轻快会追上你。/ 世界不会塌掉反而轻快不少。
- 05 gentle：你不是不努力 / 你只是太会看人脸色了。对自己好一点怎么就这么难呢？/ 把期待还给别人把温柔留给自己。今晚准时下班的你也值得被肯定。/ 晚安明天见。
- 06 cta：今晚，你几点走的？/ 评论区聊聊你因为谁多坐过那半小时？点个收藏明天想走就理直气壮。/ [按钮] 去评论区聊聊 / 每晚十点，树洞准时开门。
- 零编造：无 proof/引用/数据/评价，表现性忠诚出自 deck 原文。

## 图片 USE / SKIP（含理由）
- USE letter-sara.jpg：01（刊头带 42%）、03（刊头带 65%），两处不同裁剪均避开顶部蓝色 letterhead。
- USE postcard-back.jpg：02（刊头带 58%）、06（邮戳邮票角 100% 0），两处不同裁剪。
- USE moon.jpg：05（刊头带 20%）。
- USE stamp-orange.jpg：仅 04（邮资凭证图 20% 紧裁剪），C 套唯一一次出现非贯穿 motif（见 CREDITS.md 出处行）。
- SKIP tom 家书 / huaxi 夜市：理由同 B 套（沿用 V4 记录）。
- 新图：无（无需开档搜索，4 张复用即够 editorial"同一家族复用"要求）。

## 门记录
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_c_editorial_report/` → 0 FAIL 0 WARN（见 stdout 尾部粘贴）。
- `grep -c "<h1" design/masters_c_editorial_report/card_*.html` → 每文件 1（见 stdout 尾部粘贴）。
- 手算内容高度（sheet 内胆 1248px）：01 约998 / 02 约1031 / 03 约1043 / 04 约1029 / 05 约1011 / 06 约1097，页脚 margin-top:auto 吸底（V4 同构）。
- 未跑浏览器：inspect＋trial 由 PM 外部 gate。

## PM 外部 gate（2026-11-04，见 run_notes_pb.md 同轮记录）
- 首轮 11/12 FAIL 系 assets 缺失破图伪影；补齐后重跑剩 C-01/C-03/C-04/C-05 各 1 FAIL（no-title×3＋focal-point×1）。
- fix round 1：刊头井 480→440、method 标题 44→52px、C cover 下部加 200px letter 复用井。
- fix round 2：四井 440→420（探针线 H×0.95=641.25，h1 目标 ≤620）；C gentle 下部加 160px moon 复用井。
  re-inspect 5 卡清零仅 C insight 回弹 blank-gap 300@988。
- fix round 3：C insight panel/cap 后 foot 前加 180px letter 复用井（50% 42%），re-inspect 0 FAIL 3 WARN。
- 10 主题 trial 60 张全出，构造保证＋抽检通过。12 卡（B/C）至此全绿待 Reviewer。

## Reviewer（claude -p）
- C1（1–3 卡）报"三卡文案图片整体错位一位"FAIL——PM 逐行复现全部驳回：
  card_01 h1=下班了 cover＋letter 42%、card_02 h1=领导没走 scene＋postcard 58%、card_03 h1=被看见＋letter 65%，与 deck 一字对应。
  唯一属实子项：明信片"1930年代/1930年"年份在 CREDITS 无出处（letter 的 1923 有出处保留）→ 进 fix round 4 去年份。
- C2（4–6 卡）5/6 通过，CHECK-6 FAIL 属实：card_04 顶部无刊头照片带（top 后直接 h1），违反本 notes §20"每卡顶部一条刊头照片带"→ 进 fix round 4 加刊头带。
- fix round 4（codex）：B scene/B method/C scene/C cta 共 8 处"1930年代/1930年"去年份（"明信片…"）；
  C method 顶部加 200px postcard 刊头带（50% 30%）＋stamp 井 280→220 腾预算。lint 0/0，grep 确认 1930 零命中。
- 窄复核（C method 单卡）已派，待 verdict。
