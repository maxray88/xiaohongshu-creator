"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day29_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Generate V2 card HTMLs for day 29 — 高敏感不是缺陷，是天赋
V2 uses a completely different visual style from V1's warm orange amber:
  → "星夜紫蓝" (Starry Purple Blue) — cool, dreamy, celestial
"""

import os

OUT_DIR = os.path.expanduser("~/.hermes/data/xhs_treehole/day_20260730_day29_v2/images")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Shared base style (completely different from V1's warm orange) ──
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@400;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(160deg, #1A0533 0%, #0D1B2A 45%, #002626 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}

/* Celestial glow orbs */
body::before {
    content: '';
    position: absolute;
    top: -180px;
    right: -120px;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(179,157,219,0.15) 0%, rgba(128,203,196,0.05) 50%, transparent 70%);
    pointer-events: none;
}

body::after {
    content: '';
    position: absolute;
    bottom: -150px;
    left: -100px;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(128,203,196,0.12) 0%, rgba(179,157,219,0.05) 50%, transparent 70%);
    pointer-events: none;
}

/* Star dust overlay */
.stardust {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(1.5px 1.5px at 15% 25%, rgba(255,255,255,0.20) 0%, transparent 100%),
        radial-gradient(1px 1px at 35% 10%, rgba(255,255,255,0.15) 0%, transparent 100%),
        radial-gradient(2px 2px at 55% 30%, rgba(255,255,255,0.18) 0%, transparent 100%),
        radial-gradient(1px 1px at 75% 15%, rgba(255,255,255,0.15) 0%, transparent 100%),
        radial-gradient(1.5px 1.5px at 90% 40%, rgba(255,255,255,0.12) 0%, transparent 100%),
        radial-gradient(1px 1px at 10% 60%, rgba(255,255,255,0.10) 0%, transparent 100%),
        radial-gradient(2px 2px at 45% 70%, rgba(255,255,255,0.14) 0%, transparent 100%),
        radial-gradient(1px 1px at 70% 80%, rgba(255,255,255,0.10) 0%, transparent 100%),
        radial-gradient(1.5px 1.5px at 25% 85%, rgba(255,255,255,0.12) 0%, transparent 100%),
        radial-gradient(1px 1px at 60% 90%, rgba(255,255,255,0.08) 0%, transparent 100%),
        radial-gradient(1.5px 1.5px at 82% 55%, rgba(179,157,219,0.20) 0%, transparent 100%),
        radial-gradient(1px 1px at 5% 45%, rgba(128,203,196,0.18) 0%, transparent 100%);
    pointer-events: none;
    z-index: 1;
}

.card {
    position: relative;
    width: 840px;
    padding: 50px 44px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 2;
}

/* Glowing accent line */
.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(179,157,219,0.6) 30%, rgba(128,203,196,0.6) 70%, transparent 100%);
    border-radius: 2px;
}

/* Double line bottom */
.card::after {
    content: '';
    position: absolute;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    width: 80px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(179,157,219,0.3) 50%, transparent 100%);
}

.watermark {
    position: absolute;
    bottom: 28px;
    right: 44px;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 13px;
    font-weight: 300;
    color: rgba(179,157,219,0.25);
    letter-spacing: 1px;
    z-index: 3;
}

.page-num {
    position: absolute;
    bottom: 28px;
    left: 44px;
    font-size: 13px;
    font-weight: 300;
    color: rgba(179,157,219,0.25);
    letter-spacing: 1px;
    z-index: 3;
}

/* ─── Typography ─── */
.tag {
    font-size: 20px;
    font-weight: 400;
    color: #80CBC4;
    letter-spacing: 4px;
    margin-bottom: 28px;
    padding: 6px 22px;
    border: 1px solid rgba(128,203,196,0.25);
    border-radius: 24px;
    background: rgba(128,203,196,0.06);
}

.big-title {
    font-size: 88px;
    font-weight: 900;
    color: #E0E0E0;
    letter-spacing: 12px;
    line-height: 1.3;
    text-align: center;
    margin-bottom: 14px;
    text-shadow: 0 0 40px rgba(179,157,219,0.15);
}

.medium-title {
    font-size: 40px;
    font-weight: 500;
    color: #CE93D8;
    letter-spacing: 6px;
    line-height: 1.5;
    text-align: center;
    margin-top: 4px;
}

.highlight {
    font-size: 40px;
    font-weight: 700;
    color: #B39DDB;
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 12px;
    width: 100%;
    text-shadow: 0 0 30px rgba(179,157,219,0.10);
}

.highlight-sub {
    font-size: 30px;
    font-weight: 400;
    color: #B0BEC5;
    letter-spacing: 3px;
    line-height: 1.6;
    text-align: center;
}

.quote {
    font-size: 28px;
    font-weight: 350;
    color: #B0BEC5;
    letter-spacing: 3px;
    line-height: 1.9;
    text-align: center;
    margin-bottom: 2px;
}

.body-text {
    font-size: 26px;
    font-weight: 350;
    color: #B0BEC5;
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}

.step-num {
    font-size: 36px;
    font-weight: 500;
    color: #80CBC4;
    letter-spacing: 4px;
    line-height: 1.4;
    text-align: center;
    margin-bottom: 6px;
}

.step-title {
    font-size: 30px;
    font-weight: 600;
    color: #CE93D8;
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 10px;
}

.step-desc {
    font-size: 22px;
    font-weight: 350;
    color: #90A4AE;
    letter-spacing: 2px;
    line-height: 1.7;
    text-align: center;
    margin-bottom: 16px;
    padding: 0 24px;
}

.small-text {
    font-size: 20px;
    font-weight: 300;
    color: #90A4AE;
    letter-spacing: 2px;
    text-align: center;
}

.cta-border {
    margin-top: 12px;
    padding: 7px 22px;
    border: 1px solid rgba(128,203,196,0.25);
    border-radius: 24px;
    color: #80CBC4;
    font-size: 22px;
    font-weight: 400;
    letter-spacing: 3px;
    background: rgba(128,203,196,0.06);
}

.spacer { height: 12px; }
.spacer-lg { height: 24px; }

/* ─── Per-type adjustments ─── */
.cover .big-title {
    font-size: 96px;
    letter-spacing: 16px;
    margin-bottom: 18px;
}
.cover .medium-title {
    font-size: 40px;
    color: #CE93D8;
    margin-top: 8px;
}

.scene .quote {
    font-size: 28px;
    font-weight: 350;
    color: #B0BEC5;
}

.insight .highlight {
    font-size: 36px;
    padding: 16px 24px;
    background: rgba(179,157,219,0.08);
    border-radius: 12px;
    text-align: center;
    width: 100%;
    border: 1px solid rgba(179,157,219,0.15);
}
.insight .highlight-sub {
    margin-top: 4px;
}

.method .step-num {
    color: #80CBC4;
}

.gentle .highlight {
    font-size: 40px;
    color: #CE93D8;
    margin-bottom: 20px;
}
.gentle .quote {
    font-size: 28px;
    font-weight: 350;
    color: #B0BEC5;
}

.cta .big-title {
    font-size: 88px;
    letter-spacing: 14px;
    margin-bottom: 10px;
}
.cta .medium-title {
    font-size: 40px;
    color: #CE93D8;
    margin-bottom: 24px;
}
.cta .body-text {
    font-size: 26px;
    font-weight: 350;
    color: #B0BEC5;
}

.step-divider {
    width: 60px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(128,203,196,0.3) 50%, transparent 100%);
    margin: 6px auto;
}
"""


def write_card(filename, body_html, page_num):
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>{filename}</title>
<style>
{BASE_CSS}
</style>
</head>
<body>
<div class="stardust"></div>
{body_html}
<div class="watermark">@情绪树洞 · 2026-07-30</div>
<div class="page-num">{page_num}</div>
</body>
</html>"""
    path = os.path.join(OUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✓ {filename}")


# ── Card 1: Cover ──
write_card(
    "card_v2_1_cover.html",
    """<div class="card cover">
    <div class="tag">情绪树洞 · 与自己和解</div>
    <div class="big-title">高敏感不是缺陷</div>
    <div class="medium-title">是天赋</div>
    <div class="spacer"></div>
    <div class="body-text">致每一个被说「你想太多了」的你</div>
</div>""",
    "1 / 6"
)

# ── Card 2: Scene ──
write_card(
    "card_v2_2_scene.html",
    """<div class="card scene">
    <div class="tag">你是否也这样</div>
    <div class="quote">别人一个眼神，你就能琢磨一整天</div>
    <div class="spacer"></div>
    <div class="quote">听到一点批评就浑身难受</div>
    <div class="quote">总觉得是自己哪里没做好</div>
    <div class="spacer"></div>
    <div class="quote">经常被说：「你太敏感了」</div>
    <div class="quote">「你想太多了」</div>
    <div class="spacer"></div>
    <div class="quote">有时候，真希望自己能「钝感」一点</div>
</div>""",
    "2 / 6"
)

# ── Card 3: Insight ──
write_card(
    "card_v2_3_insight.html",
    """<div class="card insight">
    <div class="tag">换个角度看</div>
    <div class="highlight">高敏感，是一种天赋。</div>
    <div class="highlight-sub">你能感受到别人忽略的美好——</div>
    <div class="highlight-sub">一朵花的香气、一杯茶的温度、</div>
    <div class="highlight-sub">一首歌里藏着的情绪。</div>
    <div class="spacer"></div>
    <div class="highlight-sub">你有深刻的共情力——</div>
    <div class="highlight-sub">你总是能第一时间察觉到身边的人</div>
    <div class="highlight-sub">是不是需要帮助。</div>
    <div class="spacer"></div>
    <div class="highlight-sub">你的直觉准得惊人——</div>
    <div class="highlight-sub">因为你接收到了别人忽略的信号。</div>
</div>""",
    "3 / 6"
)

# ── Card 4: Method ──
write_card(
    "card_v2_4_method.html",
    """<div class="card method">
    <div class="tag">试试这样</div>
    <div class="step-num">01</div>
    <div class="step-title">给独处留时间</div>
    <div class="step-desc">每天给自己15分钟，不刷手机、不说话，就只是静静地和自己待着。这是你的充电时间。</div>
    <div class="step-divider"></div>
    <div class="step-num">02</div>
    <div class="step-title">学会做减法</div>
    <div class="step-desc">减少不必要的社交、减少信息摄入。你不是冷漠，你是在保护自己的能量。</div>
    <div class="step-divider"></div>
    <div class="step-num">03</div>
    <div class="step-title">把敏感变成超能力</div>
    <div class="step-desc">用你的细腻去创作、去倾听、去理解这个世界。敏感的人，往往也是最温柔的人。</div>
</div>""",
    "4 / 6"
)

# ── Card 5: Gentle ──
write_card(
    "card_v2_5_gentle.html",
    """<div class="card gentle">
    <div class="tag">想对你说</div>
    <div class="highlight">你的敏感不是弱点。</div>
    <div class="quote">是你感受这个世界的方式。</div>
    <div class="spacer"></div>
    <div class="quote">敏感让你更容易受伤，</div>
    <div class="quote">也让你更容易感动。</div>
    <div class="spacer"></div>
    <div class="quote">当你学会保护自己，</div>
    <div class="quote">这份敏感就会变成你身上</div>
    <div class="quote">最温柔的光。</div>
    <div class="spacer"></div>
    <div class="quote">世界需要你这样细腻的人。</div>
</div>""",
    "5 / 6"
)

# ── Card 6: CTA ──
write_card(
    "card_v2_6_cta.html",
    """<div class="card cta">
    <div class="tag">说说话吧</div>
    <div class="big-title">你也是</div>
    <div class="medium-title">高敏感的人吗？</div>
    <div class="spacer"></div>
    <div class="body-text">评论区说说你的故事</div>
    <div class="spacer"></div>
    <div class="body-text">你有没有因为「太敏感」而困扰过？</div>
    <div class="body-text">又是怎么和自己和解的？</div>
    <div class="spacer"></div>
    <div class="body-text">💬 高敏感人群抱团取暖</div>
</div>""",
    "6 / 6"
)

print(f"\n✅ All 6 V2 card HTMLs generated in {OUT_DIR}")
