# V3 run notes
- sector: culture (draw sectors 全是 web/产品类; culture 的编辑叙事/纸质印刷气质最接近深夜情感卡片; runner-up health 只有治愈单点, 无叙事载体)
- direction: page-is-the-object, seed 380975057 (未选熟悉的 uneven-photographs: 那是情感账号默认语录拼贴 look; 且 uneven-photographs / place-carries-it 都要真实照片, assets.mjs 四源全 ENOTFOUND, 离线不可行)
- redraws: 0 (方向一次成立, 无 statable reason 重打)
- idea: On these cards, 没发出去的深夜消息 becomes 一封可以捧在手里的信 (纸面 + 信封折角 + 邮票 + 邮戳).
- competitor test: 把主语换成其他情感账号(语录截图/真人出镜流)句子不成立, 通过.
- motif: 未寄出的信封 (折角信封 + 树字邮票 + 邮戳圆环), 贯穿 6 卡, 纯 SVG 平色绘制.
- sample: ~/.hermes/data/xhs_treehole/day_20261102_day106 (LATEST 非 _v2; post_data.json + 密度参考)
- imagery: assets.mjs 试一次, 四源 ENOTFOUND; 纯代码 motif, 无外部图. report 记录 open collections unreachable from build sandbox.
- motion 层 + scroll scenes: SKIP (静态 JPG, brief 6/7 豁免).
- deviations (brief > skill): 固定 1080x1440 不做三断点 / Noto Sans SC / 只钉 1080 卡宽 / one live thing 豁免改跨卡 motif / browser gate 外部执行.

## fix round 1 (2026-11-03, inspector FAILs adjudicated)
- what changed per card:
  - 01 cover: contrast (.night/.cap/.footword mu->tx); deleted kicker pill "情绪树洞连载" (top right-aligns night only).
  - 02 scene: contrast (same + SVG 夜 text mu->tx); deleted kicker pill; motif wrapped in placed g1 colour-field band (padding 92px, SVG 680x366, envelope body f1->f0 so it reads on the band), footer void now <112px.
  - 03 insight: contrast; deleted kicker pill; motif wrapped in g1 band (padding 104px, SVG 640x336, envelope f1->f0).
  - 04 method: contrast; deleted kicker pill; inserted placed g1 motif band (padding 64px, 560x340 envelope+树 stamp+postmark) between steps and cap, closing the ~572px void to <112px.
  - 05 gentle: contrast only (.night/.cap/.footword mu->tx; kicker kept per scope; decorative letter-line rect fills keep mu as non-text).
  - 06 cta: contrast; kicker kept per scope; motif moved into g1 band (padding 72px, SVG 500x416, envelope f1->f0); CTA "评论区聊聊" span->real <button type="button"> (native focus, min-height 44px, flat accent, no border/shadow).
- contrast note: mu now used only for non-text (.sring strokes, card_05 letter bars); all running text uses tx ink token.
- lint: `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_v3/` -> 0 FAIL 0 WARN (kept clean).
- defenses (no code change, by design):
  - [palette-cream]: background IS the design_tokens.json ground for the dealt theme; brand tokens outrank the skill cream rule (brief §0).
  - [no-title] on 02-06 + [name-only-title] on cover: only the cover carries the title by card-system design (masters/README.md); a repeated h1 on every card would break the 6-card spine.
  - [focal-point] (36px "too small"): inspector vw math targets desktop web, but these are fixed 1080x1440 posters rendered to JPG; type scale comes from tokens (coverTitle 56/800, cardTitle 36/700) and is verified in the JPG, not in CSS vw.
  - [first-action] on non-CTA cards: only card_06 has an action by design; cards 01-05 are editorial per the card-system spec.

## fix round 2 (2026-11-03, PM re-gate)
- 05 gentle / 06 cta: deleted kicker pill "情绪树洞连载" (line 42 -> `<div class="top" style="justify-content:flex-end;">` + night only, same treatment as 01-04 round 1). Series identity stays in footer only. Unused `.pill` CSS rule kept, same as 01-04 (surgical, lint clean). Resolves 3.4:1 contrast FAILs + card_06 hero-words FAIL (kicker no longer concatenated into hero).
- card_02 "316px gap at ~936px": viewport artifact, change nothing. Measured last-screen capture (page-y 765-1440): light run ~930-1269 (~339px incl. 19px cap line; longest contiguous ~202px) = white envelope body on the placed g1 band + band padding + cap-to-footer footer rhythm (~118px, same margin-top:auto footer as all 6 cards). JPG verified composed: g1 motif band closed on both sides, cap line, footer (mini envelope + footword) pinned at card bottom edge. Inspector slices the 1440px poster into 675px fold viewports, so light motif pixels read as a "gap". No dead zone in the poster.
- card_04 hero-void (WARN, 33% voidBox 450x540 at 630,135): viewport artifact, change nothing. The box is the right side of the first 675px fold screen beside left-aligned editorial text; JPG verified composed (steps -> placed g1 motif band with envelope+树 stamp+postmark -> cap -> footer, round 1 band already closed the ~572px void). Same fold-viewport-vs-poster geometry as card_02.
- lint: `node .claude/skills/design-taste-frontend/scripts/lint.mjs design/masters_v3/` -> 0 FAIL 0 WARN (kept clean).
