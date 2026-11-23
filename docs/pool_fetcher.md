# 照片池自动补给 Fetcher（00:30 nightly）

新 cron 任务：`情绪树洞-照片池自动补给(00:30)`，schedule `30 0 * * *`，
deliver `feishu:oc_6d4b826f9f3cefc71e25865d5803e1fb`，agent 模式，
workdir 为本仓库根目录。

## 任务（每次运行）

1. 读 `.taste-skill/photo_pool.json`（记 N=照片数，deny 列表，
   cursor 公式只读不改）与 `.taste-skill/assets-src/credits.json`
  （记已有 ref/file 集合）。
2. 若 N ≥ 48：什么都不做，报告"池已满（N），fetch 0"并退出。
   否则目标追加 **6 张**（上限 6/晚）。
3. 在 Wikimedia Commons 搜索清晨/档案候选：
   私人日常生活 / 纸片档案，约 1900–1940：信件、邮票、明信片、
   月夜、海面月光、街灯、安静老街、信封。
   **不要**：肖像、人群、现代霓虹、商业街夜景。
   仅限 `commons.wikimedia.org` / `upload.wikimedia.org`。
4. 对每位候选执行质量门（全过才收；任一失败则 SKIP 并试下一位，
   循环直到收满 6 或 Commons 无更多候选；不足 6 就收实际通过数，
   最少 0，如实报告，绝不拿 rejects 凑数）：
   - G1 license：Commons API `imageinfo` + `extmetadata`
    （`LicenseShortName` / `UsageTerms` / `Artist`）必须为
     PD 或 CC0；CC BY / CC BY-SA / CC BY-NC 一律跳过。
     优先 `creditRequired=false`。存疑则 fail-closed 跳过。
   - G2 size：同一 imageinfo 的 width/height，长边 ≥ 1400px。
   - G3 content：**下载后用眼睛看图**：无可辨认人脸
    （远景不可辨剪影可接受）；无悼亡/死亡内容；无霓虹灯、
     无繁忙现代商业；无水印/图库品牌（明信片原印刷字/邮票本身可接受）。
   - G4 tone：与现有 12 张同 spirit——sepia/安静/档案感
    （信件、邮票、月光、夜灯、静街、信封）。
   - G5 dedupe：file、`ref`/pageid 或近似重复已在 credits.json
     或 photo_pool.json 中，或命中 `deny` glob，则跳过。
   - G6 真实性：credit 行与 `saved` 时间戳必填。
5. 下载通过者**原图**到 `.taste-skill/assets-src/`，
   文件名小写 kebab-case、只描述画面内容（如 `moonlit-harbor-postcard.jpg`）。
6. 每张在 `credits.json` 追加一条（既有 schema，不改旧条目）：
   file/media/ref/title/creator/creatorUrl/date/license/licenseCode/
   licenseUrl/creditRequired/page/via/image/width/height/bytes/credit/
   notes/saved（saved=本次 UTC ISO 时间）。
7. 每张在 `photo_pool.json` 的 `photos` 末尾追加一条
   （不碰既有 12 条、cursor、deny、version）：
   short/file/caption/credit/alt/cropA/cropB，
   仿既有条目口吻（中文短 caption/credit/alt）。
   cropA: h∈[590,700] 的整数，pos 如 "50% 40%"；
   cropB: 同一合法区间内**不同构图**（不同 h 或不同 pos）。
8. 禁止事项：不改 01:00 任务 `250be2028330` 及其 prompt、
   不改 cursor 公式、不碰 `masters_f_atelier/`、不碰无关任务、
   不 git commit。

## 上报（stdout）

job id、本次新增 short 列表、拒绝候选数 + 主因、
执行后池大小 N。若 6 张未收满，说明原因。
