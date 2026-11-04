# run_notes_pb — B 套（masters_b_split_stage）

SAMPLE COPY —— 上线前替换（本套全部文案为中性 compositing sample，与 deck 同密度同口吻，页脚已标母版样张）

## deal 记录（两次 deal，同一 subject 不同 seed）
- 命令 1：`draw.mjs --sector culture --brief "深夜树洞小红书卡片" --sections showcase,proof,how-it-works,about,cta --tone warm --keep palette,type --options 3`
  候选池：page-is-the-object / split-stage / place-carries-it
- 命令 2（不同 seed 做法：加 `--tone editorial` 重打，候选池完全不同，记录在案）：`draw.mjs ... --tone editorial --keep palette,type --options 3`
  候选池：contact-sheet / editorial-report / name-as-monument
- 全表 seed（--direction 落表时记录）：split-stage 全表 seed 977848630（tone warm，2026-11-04）；editorial-report 全表 seed 1694702842（tone editorial，2026-11-04）
- redraw：0 次。第一次 deal 即遇到可用方向，第二次 deal 为 SPEC 要求的对照池，无需 redraw。

## 落选 4 个（各一句话）
- page-is-the-object：与 V4（live）同构，SPEC 明令 B/C 不许选，且轮换的意义就是换 motif。
- place-carries-it：需一张全幅地点照撑起 6 卡，一轮半月撑不住（V4 否决 uneven-photographs / place-carries-it 的同款理由）。
- contact-sheet：Needs many pictures（档案抽屉式陈列），我们只有 4 张已验证档案照，装不满（uneven-photographs 同款死法）。
- name-as-monument：巨字纪念碑式，6 卡全巨字则 scene/insight/method/gentle/cta 无位置可放，树洞李雪琴口吻会被体量压住；不如 split-stage 的栏与 editorial-report 的轴线能装下 6 种位置。

## 选中：split-stage（B）
- 存活论证：每卡只需 1 张照片（上半固定照片井＋下半纸色阅读栏），4 张档案照以不同裁剪复用即够（letter 42%/65%/55%、postcard 58%/30%、moon 20%），无需新图，不碰“很多照片/全幅地点照”红线。
- 脊柱论证：cover（信纸井＋钩子）/ scene（明信片井＋四行现场）/ insight（密集信纸井＋长论点）/ method（三 stub＋短井）/ gentle（大月亮井＋居中安慰）/ cta（回执井＋按钮），6 位置各有处放。

## idea（一句话，两空已填，动工前完成）
- 在这套卡里，没说出口的加班夜 becomes 一间一半照片一半话的放映室：上半是档案里真实的夜（家书/明信片/月亮），下半是纸色栏里慢慢说的话。
- 竞品测试：主语换成普通情感语录号，“每日一句晚安 becomes 一间一半照片一半话的放映室”不成立（语录号没有档案实拍的夜可放，上半栏无物可展）；只有树洞来信（写了没发出去的话等一个收件人）成立。通过。
- live 动作：收藏本页，评论区聊聊你几点走（card_06 真按钮）。
- motif（与 V4 彻底换血）：上下分栏舞台——顶部固定照片井（深底 #201a14 贴边）＋纸色阅读栏，交界一条 16px accent 色带贯穿 6 卡；无邮票、无齿孔打孔线、无邮戳圆环、无页脚 ministamp。

## copy deck（与 .taste-skill/copy_deck.md 同密度同口吻，sample）
- 01 cover：下班了，你却不敢走 / 工位上多坐的那半小时，今晚一次说清楚。/ 今晚十点，树洞开门。/ 把这封信先收藏好，明晚接着聊。
- 02 scene：领导没走，你也不敢动 / 同事的键盘还在响，你把伸向关机键的手又收了回去。/ 明明活早就干完了，却打开文档假装还在忙。/ 你说，这班到底是加给谁看的？/ 你说再待一会儿，心里已经吵了三轮走还是留。/ 下班羞耻，是工位上多坐的那半小时。
- 03 insight：被看见努力，才有安全感 / 心理学里有个说法，叫表现性忠诚。当安全感绑在被看见努力上，离开就等于冒险。/ 可领导真的在看你几点走吗？大多时候，人家只是在忙自己的事。/ 你脑补的那些评判，多半是心里的回声。/ 不是你懒，是你太会看人脸色了。
- 04 method：三秒钟，练习准时走 / 有点傻，但真的管用。今晚就试一次。/ 一，默念三秒，我的下班，我做主。/ 二，直接站起来收拾包。不解释，不道歉。/ 三，出门别回头，轻快会追上你。/ 世界不会塌掉，反而轻快不少。
- 05 gentle：你不是不努力 / 你只是太会看人脸色了。对自己好一点，怎么就这么难呢？/ 把期待还给别人，把温柔留给自己。今晚准时下班的你也值得被肯定。/ 晚安，明天见。
- 06 cta：今晚，你几点走的？/ 评论区聊聊，你因为谁多坐过那半小时？点个收藏，明天想走就走，理直气壮。/ [按钮] 去评论区说说你几点走 / 每晚十点，树洞准时开门。
- 零编造：无 proof/引用/数据/评价，表现性忠诚出自 deck 原文。

## 图片 USE / SKIP（含理由）
- USE letter-sara.jpg：01（42% 通栏）、03（65% 密集区）、06（55% 密集区），三处不同裁剪，均避开顶部蓝色 letterhead 只取手写区。
- USE postcard-back.jpg：02（58% 手写带）、04（30% 上半带），两处不同裁剪。
- USE moon.jpg：05（20% 半月主体）。
- SKIP stamp-orange.jpg：V4 motif 核心（未寄出的信＋橙色邮票），B 轮换需换 motif，整套刻意不用（见 CREDITS.md）。
- SKIP tom 家书：悼亡内容（death / very lonely without her）与安慰基调相冲，且多洇透镜像字（沿用 V4 记录）。
- SKIP huaxi 夜市：画面过忙有人脸招牌字，霓虹色与 token 体系相冲（沿用 V4 记录）。
- 新图：无。dealt 照片（picsum 氛围图）未用——通用城市风光对树洞主题不诚实。

## 门记录
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_b_split_stage/` → 0 FAIL 0 WARN（见 stdout 尾部粘贴）。
- `grep -c "<h1" design/masters_b_split_stage/card_*.html` → 每文件 1（见 stdout 尾部粘贴）。
- 手算内容高度（sheet 内胆 1248px）：01 约1082 / 02 约1067 / 03 约1003 / 04 约1101 / 05 约1027 / 06 约1053，页脚 margin-top:auto 吸底（V4 同构）。
- 未跑浏览器：inspect＋trial 由 PM 外部 gate。

## PM 外部 gate（2026-11-04）
- 首轮 inspect（assets 缺失前）：11/12 FAIL——事后证实为破图伪影（井塌陷致布局全错），仅 cta 通过。
- PM 补齐 assets/（4 张与 V4 逐字节 cmp 一致）后重跑：B-04/B-05/C-01/C-03/C-04/C-05 各 1 FAIL，
  其余 6 卡 0 FAIL。
  - no-title×4：刊头/上半图把 h1 顶出 675px fold（B gentle 780、C cover 692、C insight 684、C gentle 740）。
  - focal-point×2：method 卡最大字 44px 无首屏主图。
- 10 主题 trial（/tmp/bc_trial_trial.py 改 1080x1440 版 /tmp/bc_theme_trial.py，120 张全出）：
  雪松深夜 B cover 目检通过（深底白字＋照片井正常），其余由构造保证判 PASS。

## fix round 1（codex）
- B gentle 井 560→440；C cover/Insight/Gentle 刊头井 480→440；B/C method 标题 44→52px（V4-04 同款）；
  C cover 下部加 200px letter 复用井闭合空洞。
- re-inspect：B-04/C-04 清零；剩余 B-05/C-01/C-03/C-05 h1 在 644–652（探针线 H×0.95=641.25，仅差 3–11px）仍 FAIL；
  另缩井腾出 B gentle 404@884、C gentle 332@956 新空洞。

## fix round 2（codex，探针阈值已查源码 lib/probe.mjs:667）
- B/C gentle、C cover、C insight 井 440→420（h1 目标 ≤620 留余量）；
  B gentle 下部加 180px moon 复用井（50% 75%）、C gentle 下部加 160px moon 复用井（50% 70%）闭合空洞。
- re-inspect：4 卡全 0 FAIL（仅已知三类 WARN）；lint 0/0。

## fix round 3（codex，C insight 回弹）
- C insight 收缩腾出 blank-gap 300@988：panel/cap 后 foot 前加 180px letter 复用井（50% 42%）。
- re-inspect 0 FAIL 3 WARN；lint 0/0。12 卡至此全绿待 Reviewer。

## Reviewer（claude -p，4 路窄审）
- B1（1–3 卡）PASS 6/6；B2（4–6 卡）PASS 6/6（52px 单行、h1 进 fold 逐项带行号确认）。
- C1（1–3 卡）报"三卡整体错位"FAIL——PM 逐行复现全部驳回（h1/井/crop 与 deck 一字对应）；
  唯一属实：明信片"1930年代/1930年"年份在 CREDITS 无出处 → fix round 4 去年份。
- C2（4–6 卡）5/6 通过，CHECK-6 FAIL 属实：card_04 顶部无刊头带违反 motif。
- fix round 4（codex）：4 文件 8 处去年份；C method 顶部加 200px postcard 刊头带＋stamp 280→220。
  lint 0/0，grep 1930 零命中。
- 窄复核 C method 单卡 PASS 5/5。B/C 3:4 至此 Reviewer 实质全 PASS，进入 phase 2。

## OD 抛光（2026-11-04，4 路并行）— 结果＋晋升
- 4 run 全部 succeeded（b34/c34/b916/c916，12–16 artifacts），pull 到 tmp/od_bc/。
- PM 验证：24 卡文案逐字一致、hex 集一致、各一 h1、lint 0/0；inspect 23/24 绿。

## 轮换接线（2026-11-04，codex＋窄 Reviewer PASS 6/6）
- 01:00 job prompt 两段参照替换为 day_num 取模三向轮换（余1A 信件/余2B 分栏/余0C 年鉴，禁跨套混搭）；
  备份 jobs.json.bak-rotation-20261104-203314；JSON 合法；其余 66 job 与排期模型一字未动。
- design/masters/README.md 追加轮换小节 15 行，沿革原文未动。
- V2 remap 自动跟随 V1 轮换；9:16 双生套供手动 premium 视频重建（day107 路径已验证）。
- 唯一 FAIL：b916 gentle no-title——OD 把顶部井 280→620（违反 prompt 上限）。
  fix（codex）：单值回退 620→280，晋升 24 文件覆盖到 design/masters_*（assets/CREDITS/notes 不动）。
- 晋升后 re-inspect：顶部回退腾出 464px FAIL 级下部空洞（OD 同时把下井 480→250 且自称"保持原有"与事实不符）。
  fix（codex）：下井 250→560（h1 实测 586 不动；空洞→约 150）。
- 新建 4 项目并 push（各 11 文件全 OK）：b34-2a29 / c34-5077 / b916-fd8f / c916-ec07。
- start_run 4 发（skill impeccable-design-polish，agent hermes，prompt /tmp/od_pb34|pc34|pb916|pc916_prompt.md）。
  后台 poll（/tmp/od_poll_bc.py→/tmp/od_bc_final_*.json）。
