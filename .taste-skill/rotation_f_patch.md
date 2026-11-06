# F 进 production：01:00 prompt rotation patch（只写 patch 文件，不应用）

> Builder 不执行应用命令、不改 jobs.json（用户保留动作）。应用命令（用户执行）：
> `hermes cron edit 250be2028330` —— 把下述 NEW BLOCK 段粘入 prompt，替换 OLD BLOCK 段。

## OLD BLOCK（01:00 prompt 原文逐字引用，起止 `三向母版轮换` → `禁止跨套混搭 motif（一晚只用一套）。`）

```
- 三向母版轮换（按今晚 day_num 取模；day_num 在步骤 3 已确定）：
余 1 → A 信件 design/masters/（未寄出的信＋橙色邮票＋邮戳环＋打孔虚线每页页脚 ministamp）；
余 2 → B 分栏 design/masters_b_split_stage/（上半照片井＋下半纸色阅读栏＋16px accent 交界带无邮票）；
余 0 → C 年鉴 design/masters_c_editorial_report/（刊头照片带＋整块 g1 色页＋chip 套叠邮票仅 04 邮资凭证）。
动笔前先完整阅读选中那套的 card_01_cover.html … card_06_cta.html（6 文件与三套同名）——
版式、motif、留白节奏照抄只替换今晚的文案（标题/正文/cta）与今晚主题色（整套 token 变量重映射）；
画布、字阶、文件名、全部红线不变。禁止跨套混搭 motif（一晚只用一套）。
```

## NEW BLOCK（粘入替换旧段）

```
- 四向母版轮换（按今晚 day_num 取模；day_num 在步骤 3 已确定）：
余 1 → A 信件 design/masters/（未寄出的信＋橙色邮票＋邮戳环＋打孔虚线每页页脚 ministamp）；
余 2 → B 分栏 design/masters_b_split_stage/（上半照片井＋下半纸色阅读栏＋16px accent 交界带无邮票）；
余 3 → C 年鉴 design/masters_c_editorial_report/（刊头照片带＋整块 g1 色页＋chip 套叠邮票仅 04 邮资凭证）；
余 0 → F 拼贴 design/masters_f_atelier/（横向 accent 色票＋照片深底对比井＋井下 caption 行；folio/caption 规则沿用 F CREDITS）。
F 夜加一段：读仓库 `.taste-skill/photo_pool.json`，按 cursor 确定性换图——day D 第 k 个井（k=0…5 依次对应 cover/scene/insight/method/gentle/cta）取 `photos[(D*6+k) % N]` 的 file/caption/credit/alt，按 `(D+k)%2` 选 cropA（偶）/cropB（奇），把所选原图拷贝进当晚 day images/assets/ 并 cmp 逐字节一致；deny 段（Tom 家书 `letter-signed-tom-*.jpg`、华熙街 `huaxi-*.jpg`）永不启用。
动笔前先完整阅读选中那套的 card_01_cover.html … card_06_cta.html（6 文件与四套同名）——
版式、motif、留白节奏照抄只替换今晚的文案（标题/正文/cta）与今晚主题色（整套 token 变量重映射）；
画布、字阶、文件名、全部红线不变。禁止跨套混搭 motif（一晚只用一套）。
```

## 席位变化（C 从余0搬到余3）

| 席位（新四向 day_num%4） | 改前（三向 day_num%3） | 改后（四向） |
| 余 1 | A 信件 | A 信件（不变） |
| 余 2 | B 分栏 | B 分栏（不变） |
| 余 3 | ——（三向无此席位） | C 年鉴（从余 0 搬来） |
| 余 0 | C 年鉴 | F 拼贴（新增） |

注：旧三向余 0 的日子（day_num%3==0）改后按新规则重散列到四席；C 夜总量占比由 1/3 降为 1/4，F 夜占 1/4。

## SUPERSEDE（F-only，用户决策 2026-11-06：取消轮换，每晚固定 F＋pool 换图）

> 本节废止上节四向 block。应用命令（用户执行）：`hermes cron edit 250be2028330` —— 把下述 NEW BLOCK（F-only）粘入 prompt，替换 OLD BLOCK（四向）。

### OLD BLOCK（01:00 prompt 当前四向段逐字引用，起止 `四向母版轮换` → `禁止跨套混搭 motif（一晚只用一套）。`）

```
- 四向母版轮换（按今晚 day_num 取模；day_num 在步骤 3 已确定）：
余 1 → A 信件 design/masters/（未寄出的信＋橙色邮票＋邮戳环＋打孔虚线每页页脚 ministamp）；
余 2 → B 分栏 design/masters_b_split_stage/（上半照片井＋下半纸色阅读栏＋16px accent 交界带无邮票）；
余 3 → C 年鉴 design/masters_c_editorial_report/（刊头照片带＋整块 g1 色页＋chip 套叠邮票仅 04 邮资凭证）；
余 0 → F 拼贴 design/masters_f_atelier/（横向 accent 色票＋照片深底对比井＋井下 caption 行；folio/caption 规则沿用 F CREDITS）。
F 夜加一段：读仓库 `.taste-skill/photo_pool.json`，按 cursor 确定性换图——day D 第 k 个井（k=0…5 依次对应 cover/scene/insight/method/gentle/cta）取 `photos[(D*6+k) % N]` 的 file/caption/credit/alt，按 `(D+k)%2` 选 cropA（偶）/cropB（奇），把所选原图拷贝进当晚 day images/assets/ 并 cmp 逐字节一致；deny 段（Tom 家书 `letter-signed-tom-*.jpg`、华熙街 `huaxi-*.jpg`）永不启用。
动笔前先完整阅读选中那套的 card_01_cover.html … card_06_cta.html（6 文件与四套同名）——
版式、motif、留白节奏照抄只替换今晚的文案（标题/正文/cta）与今晚主题色（整套 token 变量重映射）；
画布、字阶、文件名、全部红线不变。禁止跨套混搭 motif（一晚只用一套）。
```

### NEW BLOCK（F-only，粘入替换旧段）

```
- 每晚固定 F 拼贴 design/masters_f_atelier/（横向 accent 色票＋照片深底对比井＋井下 caption 行；folio/caption 规则沿用 F CREDITS）。
F 换图：读仓库 `.taste-skill/photo_pool.json`，按 cursor 确定性换图——day D 第 k 个井（k=0…5 依次对应 cover/scene/insight/method/gentle/cta）取 `photos[(D*6+k) % N]` 的 file/caption/credit/alt按 `(D+k)%2` 选 cropA（偶）/cropB（奇），把所选原图拷贝进当晚 day images/assets/ 并 cmp 逐字节一致；deny 段（Tom 家书 `letter-signed-tom-*.jpg`、华熙街 `huaxi-*.jpg`）永不启用。
动笔前先完整阅读 F 套 card_01_cover.html … card_06_cta.html（6 文件）——
版式、motif、留白节奏照抄只替换今晚的文案（标题/正文/cta）与今晚主题色（整套 token 变量重映射）；
画布、字阶、文件名、全部红线不变。
```

注：旧 trial（tmp/f_rotation_trial/dayA=day201、dayB=day202 连续两天）即 F-only 场景的证明——连续夜晚 D/D+1 六井集合零交集已实测（comm 为空），无需重跑 trial。因果：cursor 公式 `(D*6+k)%12` 在连续 D 下天然平移 6 位取补集，mod-4 同余 bug（旧三向/四向取模选套导致同余日撞套）不复存在。
