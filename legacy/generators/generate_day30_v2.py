"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day30_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Generate V2 card HTMLs for day 30 — 懂事的孩子，长大最让人心疼
V2 uses a completely different visual style from V1's warm orange amber:
  → "薄荷冰蓝" (Mint Ice Blue) — cool, fresh, crisp, soothing
"""

import os

OUT_DIR = os.path.expanduser("~/.hermes/data/xhs_treehole/day_20260731_day30_v2/images")
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
    background: linear-gradient(160deg, #E0F7FA 0%, #E0F2F1 40%, #E8F5E9 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}

/* Fresh mint glow orbs */
body::before {
    content: '';
    position: absolute;
    top: -160px;
    right: -100px;
    width: 550px;
    height: 550px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,150,136,0.08) 0%, rgba(128,203,196,0.04) 50%, transparent 70%);
    pointer-events: none;
}

body::after {
    content: '';
    position: absolute;
    bottom: -120px;
    left: -80px;
    width: 450px;
    height: 450px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(38,166,154,0.07) 0%, rgba(129,199,132,0.04) 50%, transparent 70%);
    pointer-events: none;
}

/* Gentle leaf-like overlay */
.fresh-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(circle at 20% 30%, rgba(165,214,167,0.06) 0%, transparent 40%),
        radial-gradient(circle at 80% 70%, rgba(128,203,196,0.05) 0%, transparent 40%);
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

/* Frosted glass accent top */
.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100px;
    height: 3px;
    background: linear-gradient(90deg, transparent 0%, rgba(0,150,136,0.4) 30%, rgba(38,166,154,0.4) 70%, transparent 100%);
    border-radius: 3px;
}

/* Subtle bottom accent */
.card::after {
    content: '';
    position: absolute;
    bottom: 56px;
    left: 50%;
    transform: translateX(-50%);
    width: 70px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(0,150,136,0.2) 50%, transparent 100%);
}

.watermark {
    position: absolute;
    bottom: 28px;
    right: 44px;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 13px;
    font-weight: 300;
    color: rgba(0,105,92,0.18);
    letter-spacing: 1px;
    z-index: 3;
}

.page-num {
    position: absolute;
    bottom: 28px;
    left: 44px;
    font-size: 13px;
    font-weight: 300;
    color: rgba(0,105,92,0.18);
    letter-spacing: 1px;
    z-index: 3;
}

/* ─── Typography ─── */
.tag {
    font-size: 20px;
    font-weight: 400;
    color: #00695C;
    letter-spacing: 4px;
    margin-bottom: 28px;
    padding: 6px 22px;
    border: 1px solid rgba(0,105,92,0.20);
    border-radius: 24px;
    background: rgba(0,150,136,0.05);
}

.big-title {
    font-size: 86px;
    font-weight: 900;
    color: #004D40;
    letter-spacing: 10px;
    line-height: 1.3;
    text-align: center;
    margin-bottom: 14px;
}

.medium-title {
    font-size: 40px;
    font-weight: 500;
    color: #00897B;
    letter-spacing: 6px;
    line-height: 1.5;
    text-align: center;
    margin-top: 4px;
}

.highlight {
    font-size: 42px;
    font-weight: 700;
    color: #00695C;
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 12px;
    width: 100%;
}

.highlight-sub {
    font-size: 32px;
    font-weight: 400;
    color: #37474F;
    letter-spacing: 3px;
    line-height: 1.6;
    text-align: center;
}

.quote {
    font-size: 28px;
    font-weight: 350;
    color: #455A64;
    letter-spacing: 3px;
    line-height: 1.9;
    text-align: center;
    margin-bottom: 2px;
}

.body-text {
    font-size: 26px;
    font-weight: 350;
    color: #37474F;
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}

.step-num {
    font-size: 36px;
    font-weight: 500;
    color: #00897B;
    letter-spacing: 4px;
    line-height: 1.4;
    text-align: center;
    margin-bottom: 6px;
}

.step-title {
    font-size: 30px;
    font-weight: 600;
    color: #004D40;
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 10px;
}

.step-desc {
    font-size: 22px;
    font-weight: 350;
    color: #546E7A;
    letter-spacing: 2px;
    line-height: 1.7;
    text-align: center;
    margin-bottom: 16px;
    padding: 0 24px;
}

.small-text {
    font-size: 20px;
    font-weight: 300;
    color: #546E7A;
    letter-spacing: 2px;
    text-align: center;
}

.cta-border {
    margin-top: 12px;
    padding: 7px 22px;
    border: 1px solid rgba(0,150,136,0.20);
    border-radius: 24px;
    color: #00897B;
    font-size: 22px;
    font-weight: 400;
    letter-spacing: 3px;
    background: rgba(0,150,136,0.05);
}

.spacer { height: 12px; }
.spacer-lg { height: 24px; }

/* ─── Per-type adjustments ─── */
.cover .big-title {
    font-size: 98px;
    letter-spacing: 14px;
    margin-bottom: 18px;
}
.cover .medium-title {
    font-size: 40px;
    color: #00897B;
    margin-top: 8px;
}

.scene .quote {
    font-size: 28px;
    font-weight: 350;
    color: #455A64;
}

.insight .highlight {
    font-size: 38px;
    padding: 16px 24px;
    background: rgba(0,150,136,0.06);
    border-radius: 12px;
    text-align: center;
    width: 100%;
    border: 1px solid rgba(0,150,136,0.12);
}
.insight .highlight-sub {
    margin-top: 4px;
}

.method .step-num {
    color: #00897B;
}

.gentle .highlight {
    font-size: 40px;
    color: #00695C;
    margin-bottom: 20px;
}
.gentle .quote {
    font-size: 28px;
    font-weight: 350;
    color: #455A64;
}

.cta .big-title {
    font-size: 86px;
    letter-spacing: 12px;
    margin-bottom: 10px;
}
.cta .medium-title {
    font-size: 40px;
    color: #00897B;
    margin-bottom: 24px;
}
.cta .body-text {
    font-size: 26px;
    font-weight: 350;
    color: #37474F;
}

.step-divider {
    width: 60px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(0,150,136,0.25) 50%, transparent 100%);
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
<div class="fresh-overlay"></div>
{body_html}
<div class="watermark">@情绪树洞 · 2026-07-31</div>
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
    <div class="big-title">懂事的孩子</div>
    <div class="medium-title">长大最让人心疼</div>
    <div class="spacer"></div>
    <div class="body-text">致那个从小就「很懂事」的你</div>
</div>""",
    "1 / 6"
)

# ── Card 2: Scene ──
write_card(
    "card_v2_2_scene.html",
    """<div class="card scene">
    <div class="tag">你是否也这样</div>
    <div class="quote">从小到大，你最常被夸的</div>
    <div class="quote">就是一个词：「懂事」</div>
    <div class="spacer"></div>
    <div class="quote">想要什么东西，从来不敢说</div>
    <div class="quote">怕被拒绝，更怕给人添麻烦</div>
    <div class="spacer"></div>
    <div class="quote">别人生气了，你下意识道歉</div>
    <div class="quote">明明不是你的错</div>
    <div class="spacer"></div>
    <div class="quote">你总是在照顾所有人的情绪</div>
    <div class="quote">除了你自己的</div>
</div>""",
    "2 / 6"
)

# ── Card 3: Insight ──
write_card(
    "card_v2_3_insight.html",
    """<div class="card insight">
    <div class="tag">换个角度看</div>
    <div class="highlight">你的懂事，是在用沉默换取安全感。</div>
    <div class="highlight-sub">小时候你以为——</div>
    <div class="highlight-sub">只要够乖、够懂事、够不麻烦别人</div>
    <div class="highlight-sub">就会被爱、被认可、被好好对待</div>
    <div class="spacer"></div>
    <div class="highlight-sub">可长大后的世界告诉你——</div>
    <div class="highlight-sub">越懂事，越容易被忽略</div>
    <div class="highlight-sub">越付出，越被当作理所当然</div>
    <div class="spacer"></div>
    <div class="highlight-sub">这不是你的错。</div>
    <div class="highlight-sub">你只是用错了爱自己的方式。</div>
</div>""",
    "3 / 6"
)

# ── Card 4: Method ──
write_card(
    "card_v2_4_method.html",
    """<div class="card method">
    <div class="tag">试着这样做</div>
    <div class="step-num">01</div>
    <div class="step-title">停下来，问问自己</div>
    <div class="step-desc">每次想答应别人之前，先问自己：我是真的想帮，还是不敢拒绝？觉察自己的讨好模式。看见它，就是改变的开始。</div>
    <div class="step-divider"></div>
    <div class="step-num">02</div>
    <div class="step-title">从小事开始练习说「不」</div>
    <div class="step-desc">不想参加的饭局就说不，不想帮的忙就说没空。你会发现——世界不会崩塌，反而更尊重你了。</div>
    <div class="step-divider"></div>
    <div class="step-num">03</div>
    <div class="step-title">把自己的需求放在第一位</div>
    <div class="step-desc">每天做一件只为自己做的事。不是自私，是你终于开始爱自己了。先照顾好自己的心，才有余力温柔待人。</div>
</div>""",
    "4 / 6"
)

# ── Card 5: Gentle ──
write_card(
    "card_v2_5_gentle.html",
    """<div class="card gentle">
    <div class="tag">想对你说</div>
    <div class="highlight">你不需要那么懂事。</div>
    <div class="quote">你已经够好了。</div>
    <div class="spacer"></div>
    <div class="quote">从今天开始，</div>
    <div class="quote">试着把「我想要」</div>
    <div class="quote">放在「别人需要」前面。</div>
    <div class="spacer"></div>
    <div class="quote">你的感受很重要。</div>
    <div class="quote">你的需求很重要。</div>
    <div class="quote">你本身，就值得被爱——</div>
    <div class="quote">不需要用「懂事」来换。</div>
    <div class="spacer"></div>
    <div class="quote">愿你能成为自己的光，</div>
    <div class="quote">而不是永远照亮别人。</div>
</div>""",
    "5 / 6"
)

# ── Card 6: CTA ──
write_card(
    "card_v2_6_cta.html",
    """<div class="card cta">
    <div class="tag">说说话吧</div>
    <div class="big-title">你也是那个</div>
    <div class="medium-title">懂事的孩子吗？</div>
    <div class="spacer"></div>
    <div class="body-text">评论区说说你的故事</div>
    <div class="spacer"></div>
    <div class="body-text">你有没有因为「太懂事」而委屈过？</div>
    <div class="body-text">现在学会对自己好了吗？</div>
    <div class="spacer"></div>
    <div class="body-text">💬 从今天开始，学着爱自己</div>
</div>""",
    "6 / 6"
)

print(f"\n✅ All 6 V2 card HTMLs generated in {OUT_DIR}")
