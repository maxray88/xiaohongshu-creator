# run notes · pattern E spike（guizang Editorial 6 卡脊柱，SAMPLE compositing）

- skill 版本：64d02d4（`git -C /tmp/guizang-skill rev-parse --short HEAD`）；只读引用，未拷贝其文本进 repo。
- skill 读法（转述不摘抄）：通读其 workflow 与 3:4 竖版、字阶、照片填满、品类、生产与质检 refs；
  情感类在该 skill 自评中属弱适配（氛围感装饰与该体系冲突），本次即测该边界。
  冲突处一律以 Builder SPEC 为准：跳过其传图/Pexels/AI 三问与自带 palette，
  直接用本项目 4 张已验证档案照与 design_tokens.json token 变量。

## 用的 recipes（Editorial 模式，转述命名）
- card_01 cover：Hero Question 式（钩子提问首屏）
- card_02 scene：Atmospheric Thesis 式（现场氛围＋末句论点收束）
- card_03 insight：Pull Quote 式（核心句放大＋两段论述）
- card_04 method：Marginalia Essay 式（三步以编号 marginalia 行呈现）
- card_05 gentle：Atmospheric Thesis 式（安慰氛围＋落款收束）
- card_06 cta：Closing Note 式（提问＋真按钮＋开门时间收束）

## motif（与 A/B/C/D 四套不重样）
- idea 句：每卡左侧一条 g1 书脊栏放槽位名与页码并顶置一方 accent 色块，右侧正文区放标题正文，照片只进深底对比井。
- 与竞品区分：A 信件（邮票邮戳打孔）、B 分栏（上图下纸＋横向 accent 带）、C 年鉴（刊头照片带＋整块 g1 色页＋chip 套叠）、D bracket（四角 accent 折角）；本套无邮票、无横向交界带、无刊头照片带、无折角，竖向书脊栏为唯一贯穿件。
- 竞品测试：把主语换成普通情感语录号句子（例：愿你被世界温柔以待）放进这套书脊栏会文不对题，因为栏内是刊物结构标签与页码（封面/现场/观点/方法/安慰/行动＋1/6），不是装饰性英文，证明 motif 与树洞连载结构绑定，通过。

## copy deck 来源声明（SAMPLE）
- 文案为中性 SAMPLE compositing deck，与 B/C/D 同套，逐字使用不改写；
  上线前替换。页脚每卡“情绪树洞 · 母版样张”＋按实际用图写的 credit 行。
- 未编造 proof/引用/数据/评价；alt 文本仅描述照片本身。

## 图片 USE/SKIP＋裁剪
- USE assets/moon.jpg：card_01 高 660px 井 object-position 50% 38%；card_05 同图不同裁剪 高 580px 井 object-position 80% 90%。
- USE assets/letter-sara.jpg：card_02 高 560px 井 50% 42%；card_06 同图不同裁剪 高 540px 井 50% 12%。
- USE assets/stamp-orange.jpg：card_03 高 520px 井 50% 30%。
- USE assets/postcard-back.jpg：card_04 高 400px 井 50% 45%。
- SKIP Tom 家书（悼亡内容与基调相冲）；SKIP 华熙街夜市（过忙、有人脸招牌字、霓虹色与 token 体系相冲）。
- 拷贝方式：.taste-skill/assets-src → design/masters_e_guizhang/assets/ 短名，cmp 逐字节一致。

## 门记录
- skill 自带 validate-social-deck.mjs：不适用。缺 playwright 依赖且需起浏览器渲染；
  SPEC 亦明令不跑浏览器脚本，故未跑，以 lint.mjs＋h1 计数＋无远端 src＋cta 唯一真按钮为门。
- `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_e_guizhang/` → 0 FAIL, 0 WARN
  （书脊栏用 g1 实心面＋accent 实心方块实现，无 hairline/shadow/gradient/mono/编号零填充/kicker 类）。
- `grep -c "<h1"` → 6 文件各 1；标题最长 11 字（≤18），零 emoji，标题无 #。
- `grep -l "<button"` → 仅 card_06_cta.html；远端 src 计数 0。
- 未跑浏览器脚本；9:16 port 与 OD polish 见后续。

## PM 外部 gate（2026-11-04）
- 首轮 re-inspect（目标文件，非 workspace 草稿）：6 卡 0 FAIL，仅剩已知三类 WARN＋blank-gap WARN×6（300–440px）。
- fix round 1（codex）：六井放大吃空洞（cover 660→815/scene 560→715/insight 520→760/method 400→690/gentle 580→825/cta 540→720，残余空洞目标约150px；内容终值约1050–1135/1248）＋页脚 credit 去 raw 路径统一家族句式（"X档案实拍"）。
- 注：OD 原稿数据-od-id="cover-photo"等保留；h1 52–58px 符合 videoScale；无 focal-point FAIL（井在首屏内）。
- 关键发现：OD 用自造变量名硬编码暮色琥珀值、无 data-theme，夜流水线无法重着色。
  fix round 2-equivalent（codex）：整体换装标准 10 主题块＋变量改名（值与 OD 现值逐字一致零视觉差）；
  re-inspect 6 卡全 0 FAIL(仅已知 WARN)，lint 0/0。
- 10 主题 trial（60 张全出）：雪松深夜 cover 目检通过（深底白字＋青 accent＋书脊栏"封面/1/6"＋月亮井，motif 重着色存活）。

## Reviewer（claude -p）
- E1b（1–3 卡）PASS 6/6（h1/色值/画布/文案/无外部/motif 全带行号证据）。
- E2（4–6 卡）报 method/gentle/cta 三卡内容轮错位 FAIL——PM 逐文件逐行直接读全部驳回：
  steps 在 card_04:58-60 而不在 gentle；真 button 在 card_06:59 而不在 method:59；
  三卡 h1/井图/文案各归其位（method=postcard 690／gentle=moon 825／cta=letter 720）；
  E2 自述 CHECK-4 文案"逐字一致"PASS 与 CHECK-6"内容错位"FAIL 自相矛盾——错位文案不可能逐字对上 deck；
  其溢出数（gentle ~1400/cta ~1285）亦错：实测 foot 底 1396 < 1440 无裁切，bodyH 恰 1440。
  结论：第五次同类误报（v2-B、C1、C916b、D1 本轮另一次），E2 的 PASS 项成立，FAIL 项作废。
- E 3:4 至此实质全绿。9:16 port 与 rotation 席位待用户定夺。
