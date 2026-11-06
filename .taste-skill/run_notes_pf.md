# run notes · pattern F ateliér 拼贴 3:4 masters（SAMPLE compositing）

- Builder SPEC：6 张 1080x1440 母版卡；网络仅 commons / upload.wikimedia.org；只写 design/masters_f_atelier/**、.taste-skill/run_notes_pf.md、追加 credits.json、新增原图到 .taste-skill/assets-src/；无 agent 派生、无 review、无 commit；遇阻即停不降格。

## 用的 recipes（内容配方沿用 E 不变只换皮）
- card_01 cover：Hero Question 式（钩子提问首屏；topline 开门时间＋h1＋lead＋closing 收束）
- card_02 scene：Atmospheric Thesis 式（现场氛围三段＋末句论点收束）
- card_03 insight：Pull Quote 式（核心句放大＋两段论述＋closing）
- card_04 method：Marginalia Essay 式（三步编号行＋SAVE hook closing）
- card_05 gentle：Atmospheric Thesis 式（安慰氛围＋落款收束）
- card_06 cta：Closing Note 式（提问＋真按钮＋开门时间收束）
- 文案与 E 轮逐字一致（含标点取舍），出自 .taste-skill/copy_deck.md day106 SAMPLE deck，上线前替换；未编造 proof/引用/数据/评价；alt 文本只描述照片本身。

## motif 色票拼贴（与 A/B/C/D/E 不重样）
- idea 句：纸面 g0 ＋ 一张横向 accent 实心色票（宽 66% 圆角 22 无描边，内放槽位词 46px 大字＋票角 folio n/6 不补零）＋ 照片进 #201a14 深底对比井（沿用 E 式 padding 12 / radius 24 / img radius 12，无 border 无 shadow）＋ 井下 caption 行；色票与照片井做负 margin 叠压（仅 cover 为 .ticket+.well 相邻，叠压 28px 吃色票底部留白；其余卡井后跟正文，margin 归零不压字）。
- 与竞品区分：A 信件（邮票邮戳打孔）／B 分栏（上图下纸＋横向 accent 带）／C 年鉴（刊头照片带＋整块 g1 色页＋chip 套叠）／D bracket（四角 accent 折角）／E 左竖书脊栏；本套无邮票、无横向交界带、无刊头带、无折角、无竖栏，横向色票＋叠压拼贴为唯一贯穿件。
- 竞品测试：把主语换成普通情感语录号句子（例：愿你被世界温柔以待）放进这张横向色票会文不对题，因为票内是刊物结构标签与页码（封面／现场／观点／方法／安慰／行动＋n/6），不是装饰性英文，证明 motif 与树洞连载结构绑定通过。
- data-od-id：沿用 E 同槽位（cover-title/sub/photo/closing、scene-title/p1/p2/p3/photo/thesis、insight-title/quote/photo/p2/closing、method-title/lead/steps/photo/closing、gentle-title/p1/photo/p2/signoff、cta-title/p1/photo/button/note、card-footer）；新 motif 件用 f-ticket／f-slot／f-folio／f-caption；cover-topline 保留（E 同名 id，置于 caption 之后 h1 之前）。
- 字阶：h1 cover 58px 其余 50–52px；正文 lead 27／body 26／quote 33／closing 27／signoff 26／caption 20；字体沿用 Noto Sans SC 400;500;700;800；class 避开 lint（无 eyebrow 类、无零填充编号中文一二三、无 uppercase＋tracking＋微标签、无默认字体）。
- 卡内除照片井底 #201a14 外只用 token 变量；整段标准 10 主题 style 块照抄 E（card_01）取值与 design/design_tokens.json 逐字一致零视觉差。

## 图片 USE/SKIP＋裁剪
- USE night-lamp-tiffany.jpg（CC0 2477x3400）：card_01 高 700px 井 object-position 50% 26%。
- USE main-street-rocky-hill.jpg（PD 1590x1021）：card_02 高 600px 井 50% 45%（右端远处小人影不可辨认，裁剪居中避开）。
- USE envelope-1920-feb.jpg（PD 3735x2826）：card_03 高 600px 井 50% 30%（邮票邮戳在右上）。
- USE moonlight-atlantic-nypl.jpg（PD TIFF→1920px JPG 落盘 1920x1299）：card_04 高 590px 井 50% 40%。
- USE moonlit-waves-cape-cod.jpg（PD 3363x2155）：card_05 高 640px 井 50% 45%。
- USE night-lamp-print.jpg（CC0 3371x4833）：card_06 高 620px 井 50% 28%（灯具习作在上部）。
- SKIP（协议）：W.carter 系 CC BY-SA 4.0 五张（Holma Marina 月海 1/2、New moon setting 1、Rixö quarry 日月、Tuntorp 雪树月）、Morning fog in Kemeri（CC BY-SA）；SKIP（尺寸）：NBY 两张月海小图（长边＜1400）；BACKUP 未启用：Envelope 1920 March 11（PD）、South Main Street Dayton 1910（PD）；SKIP（基调沿用 E）：Tom 家书悼亡、华熙街夜市。
- 考证：Commons API imageinfo ExtMetadata（LicenseShortName/UsageTerms/Artist）PD 或 CC0 才要；creditRequired 均为 false；原图落 .taste-skill/assets-src/ 短名小写连字符，credits.json 按既有 schema 追加 6 条（含 ref pageid、page/image/thumb、width/height/bytes、credit 行、saved）；拷贝至 design/masters_f_atelier/assets/ cmp 逐字节一致。
- 六图目检：无可辨认人脸、无悼亡内容、无霓虹招牌、无水印（明信片原印标题／邮戳／手写寄语非水印，与 E 轮口径一致）、长边≥1400。

## 门记录
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_f_atelier/` → 0 FAIL, 0 WARN（色票用 accent 实心面、无 hairline/shadow/gradient/mono/编号零填充/kicker 类）。
- `grep -c "<h1"` → 6 文件各 1；标题最长 10 字（≤18），零 emoji。
- `grep -l "<button"` → 仅 card_06_cta.html；远端 src 计数 0。
- `grep -c "html\[data-theme" card_01_cover.html` → 10。
- `for f in design/masters_f_atelier/assets/*; do cmp ...` → 6/6 一致。
- Chrome headless 截 card_01（8123 现成服务，未新起）→ /tmp/f_cover.png 出图正常：色票（封面＋1/6）完整、叠压 28px 只吃票底留白、700px 灯井、caption＋topline＋h1＋lead＋closing＋页脚全在 1440 内；另抽截 card_04（内容最多卡）→ 无溢出、步骤块圆角完整、页脚在画布内。
- `grep -c "PLACEHOLDER\|TODO\|FIXME"` → 6 文件各 0。
- `git status --short` → 本轮新增／修改仅允许文件（6 卡 HTML、assets×6、CREDITS.md、run_notes_pf.md、credits.json 追加、assets-src×6）；另有仓库既有未提交改动（masters_v3 删除等）非本轮产生，未触碰。

## fix 轮补记（F 轮三处对账结论，本轮 rotation 施工前复验）
- copy 标点：F 6 卡 h1/lead/closing 与 E 轮 deck（copy_deck.md day106 SAMPLE）逐字一致含标点取舍（例 cover h1「下班了，你却不敢走」58px、`，`全角逗号；closing「把这封信先收藏好，明晚接着聊。」句号收束）；上线前替换 SAMPLE 文案时标点口径照此。
- quote：card_03 insight 为 Pull Quote 式（核心句 h1 放大＋两段论述 p2＋closing 收束），quote 字阶 33px 与 body 26 区分；本轮 trial 未动文案层。
- caption：6 卡 `f-caption`＋页脚 `.credit`＋井图 `alt` 成套且与 CREDITS.md 现值逐字一致（tiffany 暖黄台灯/rocky-hill 1910 主街/feb 1920 贴票信封/atlantic 1901 月夜海/waves 月夜海浪/print 1936 夜灯习作）；pool 建设时 6/6 复核通过，无缺件。

## rotation/pool 设计（F 进 production）
- photo_pool.json（agent 唯一真相源，version 1）：photos 12 张＝旧 4（letter-sara/stamp-orange/postcard-back/waxing-half-moon，cropA 取 E 卡现值 715/42%、760/30%、690/45%、815/38%）＋F 6（cropA 取 F CREDITS 现值）＋本轮 2（dayton 街景 600/40%、may 信封 600/30%）；每张 caption/credit/alt 成套，alt 仅描述照片本身；cropB 为不同构图同合法区间（moon/sara 的 cropB 直接复用 E 第二裁剪 proven 值）。
- deny：`letter-signed-tom-*.jpg`（悼亡）、`huaxi-*.jpg`（霓虹杂乱＋人脸），覆盖 credits.json 内 Tom 家书与华熙街夜市两条 SKIP。
- cursor 数学：day D 第 k 井取 photos[(D*6+k)%12]，crop 按 (D+k)%2 取 A（偶）/B（奇）。N=12 时连续两天 6 井零重合：day201→idx 6..11，day202→idx 0..5，交集为空（trial 实测 comm 为空）；一般地 (D*6+k)%12 在 D 奇偶翻转时整体平移 6 位，正好是补集，偶 D 用 0..5、奇 D 用 6..11。
- 本轮新增 2 图考证：South Main Street Dayton ca.1910（commons:75037335，PD，1600x998，街景远处小人影不可辨认、右上英文标题为明信片原印）；Envelope 1920 May（commons:117381454，PD，1780x1443，与 F 二月信封同通信人 Paulette→Florence Taylor，Bordeaux 18-5-1920 邮戳＋25c 绿色 Semeuse 邮票）；credits.json 按既有 schema 追加 2 条（saved 2026-11-06T12:45:25.000Z），pool 可用数 10→12。
- patch 文件：`.taste-skill/rotation_f_patch.md`（old block 由 jobs.json 逐字提取已校验 `old in prompt == True`；new block 四向余1→A/余2→B/余3→C/余0→F＋F 夜 pool 换图段；C 从余0搬到余3对照表；应用命令 `hermes cron edit 250be2028330` 由用户执行，Builder 未执行、未改 jobs.json）。
- trial（tmp/f_rotation_trial/dayA=day201、dayB=day202）：F 套复制＋SAMPLE deck 不上线＋按 cursor 换 6 井 src/caption/credit/alt＋assets 短名拷入。结论：lint 两家各 0 FAIL 0 WARN；A/B 6 井图零重合（comm 空）；assets 12/12 cmp 一致；12 文件各 10 主题块、h1 各 1、button 仅 card_06、远端 src 0；cover headless 出图 2160x2880（=1080x1440 @2x）motif 完整无溢出；`check_content_quality.py` 主函数硬编码 BASE 为生产路径且含 V2 自愈写（atomic_write_json 进生产 day 目录），trial 无 post_data/manifest 且禁写生产——未对其运行，未伪造通过，对等项已逐项手验；F 只有 3:4，trial 只验 3:4，video 链消费 V1 3:4 渲染（core/build_v2_local.py 全量拷 assets），916 手工链不受影响。

## F-only 决策（2026-11-06 用户决策：取消轮换，每晚固定 F＋pool 换图）
- 用户决策：不要 mod-4 轮换，每晚固定用 F（design/masters_f_atelier/）；pool cursor 公式不变、语义改为每晚连续 D=day_num；patch 文件 SUPERSEDE 节为准，应用命令 `hermes cron edit 250be2028330` 由用户执行。
- bug 复盘三行：(1)同余 bug——旧三向 day_num%3 与新四向 day_num%4 席位重散列，旧余0日（C 夜）会被重分到四席，C/F 占比与历史预期错位；(2)trial 为何没暴露——trial 取 dayA=201/dayB=202 只验了 F 夜内 pool 换图零重合，未覆盖跨套余数重映射；(3)为何 F-only 天然免疫——取消取模选套后无同余可言，cursor `(D*6+k)%12` 在连续 D 下平移 6 位取补集，连续两晚六井集合天然零交集。
