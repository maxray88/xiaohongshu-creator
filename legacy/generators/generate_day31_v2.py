"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day31_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Generate V2 card HTMLs for day 31 — 成年人的崩溃，往往是静音的
V2 uses a completely different visual style from V1's warm dusk-rose (暮色玫瑰):
  → "午夜星河" (Midnight Galaxy) — deep indigo-violet starfield, gold & lavender glow
Card TEXT is identical to V1 (only visual style changes).
"""
import os

OUT_DIR = os.path.expanduser("~/.hermes/data/xhs_treehole/day_20260801_day31_v2/images")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Shared base style (completely different from V1's warm rose) ──
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@400;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(160deg, #141B3C 0%, #1D2B5E 45%, #2A1E4F 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}

/* Deep-space nebula glows */
body::before {
    content: '';
    position: absolute;
    top: -160px;
    right: -120px;
    width: 560px;
    height: 560px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(140,120,255,0.16) 0%, rgba(90,110,220,0.06) 50%, transparent 72%);
    pointer-events: none;
}

body::after {
    content: '';
    position: absolute;
    bottom: -140px;
    left: -100px;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(242,200,121,0.08) 0%, rgba(180,150,255,0.05) 50%, transparent 72%);
    pointer-events: none;
}

/* Star field */
.stars {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(1.6px 1.6px at 12% 18%, rgba(255,255,255,0.85) 50%, transparent 50%),
        radial-gradient(1.2px 1.2px at 24% 64%, rgba(255,255,255,0.55) 50%, transparent 50%),
        radial-gradient(1.8px 1.8px at 34% 12%, rgba(242,200,121,0.70) 50%, transparent 50%),
        radial-gradient(1.2px 1.2px at 46% 80%, rgba(255,255,255,0.50) 50%, transparent 50%),
        radial-gradient(1.6px 1.6px at 58% 26%, rgba(180,170,255,0.70) 50%, transparent 50%),
        radial-gradient(1.2px 1.2px at 68% 58%, rgba(255,255,255,0.55) 50%, transparent 50%),
        radial-gradient(1.8px 1.8px at 78% 14%, rgba(255,255,255,0.80) 50%, transparent 50%),
        radial-gradient(1.2px 1.2px at 86% 44%, rgba(242,200,121,0.55) 50%, transparent 50%),
        radial-gradient(1.5px 1.5px at 20% 88%, rgba(255,255,255,0.45) 50%, transparent 50%),
        radial-gradient(1.3px 1.3px at 64% 90%, rgba(255,255,255,0.50) 50%, transparent 50%),
        radial-gradient(1.4px 1.4px at 90% 74%, rgba(180,170,255,0.55) 50%, transparent 50%),
        radial-gradient(1.2px 1.2px at 8% 48%, rgba(255,255,255,0.45) 50%, transparent 50%),
        radial-gradient(3.2px 3.2px at 16% 28%, rgba(242,200,121,0.22) 50%, transparent 50%),
        radial-gradient(3.6px 3.6px at 70% 42%, rgba(180,170,255,0.20) 50%, transparent 50%),
        radial-gradient(3.0px 3.0px at 44% 74%, rgba(255,255,255,0.14) 50%, transparent 50%),
        radial-gradient(3.4px 3.4px at 88% 82%, rgba(242,200,121,0.18) 50%, transparent 50%);
    pointer-events: none;
    z-index: 1;
}

.card {
    position: relative;
    width: 860px;
    padding: 54px 46px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 2;
}

/* Fine gold frame */
.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    border: 1px solid rgba(242,200,121,0.28);
    border-radius: 20px;
    pointer-events: none;
}

.card::after {
    content: '✦ ✦';
    position: absolute;
    top: 18px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 15px;
    color: rgba(242,200,121,0.6);
    letter-spacing: 14px;
    background: linear-gradient(160deg, #141B3C 0%, #1D2B5E 45%, #2A1E4F 100%);
    padding: 0 14px;
}

.watermark {
    position: absolute;
    bottom: 30px;
    right: 46px;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 13px;
    font-weight: 300;
    color: rgba(244,240,255,0.32);
    letter-spacing: 1px;
    z-index: 3;
}

.page-num {
    position: absolute;
    bottom: 30px;
    left: 46px;
    font-size: 13px;
    font-weight: 300;
    color: rgba(244,240,255,0.32);
    letter-spacing: 1px;
    z-index: 3;
}

/* ─── Typography ─── */
.tag {
    font-size: 20px;
    font-weight: 400;
    color: #F2C879;
    letter-spacing: 4px;
    margin-bottom: 30px;
    padding: 6px 22px;
    border: 1px solid rgba(242,200,121,0.40);
    border-radius: 24px;
    background: rgba(242,200,121,0.07);
}

.big-title {
    font-size: 88px;
    font-weight: 900;
    color: #F7F3FF;
    letter-spacing: 10px;
    line-height: 1.3;
    text-align: center;
    margin-bottom: 14px;
    text-shadow: 0 0 40px rgba(160,140,255,0.35);
}

.medium-title {
    font-size: 42px;
    font-weight: 500;
    color: #C9BEF5;
    letter-spacing: 6px;
    line-height: 1.5;
    text-align: center;
    margin-top: 4px;
}

.highlight {
    font-size: 42px;
    font-weight: 700;
    color: #F2C879;
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 12px;
    width: 100%;
}

.highlight-sub {
    font-size: 32px;
    font-weight: 400;
    color: #D9D2F7;
    letter-spacing: 3px;
    line-height: 1.6;
    text-align: center;
}

.quote {
    font-size: 30px;
    font-weight: 350;
    color: #E7E1FF;
    letter-spacing: 3px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}

.body-text {
    font-size: 28px;
    font-weight: 350;
    color: #D9D2F7;
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}

.step-num {
    font-size: 38px;
    font-weight: 500;
    color: #F2C879;
    letter-spacing: 4px;
    line-height: 1.4;
    text-align: center;
    margin-bottom: 6px;
}

.step-title {
    font-size: 32px;
    font-weight: 600;
    color: #F7F3FF;
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 10px;
}

.step-desc {
    font-size: 22px;
    font-weight: 350;
    color: #C4BCEA;
    letter-spacing: 2px;
    line-height: 1.7;
    text-align: center;
    margin-bottom: 16px;
    padding: 0 24px;
}

.small-text {
    font-size: 20px;
    font-weight: 300;
    color: #C4BCEA;
    letter-spacing: 2px;
    text-align: center;
}

.cta-border {
    margin-top: 12px;
    padding: 7px 22px;
    border: 1px solid rgba(242,200,121,0.45);
    border-radius: 24px;
    color: #F2C879;
    font-size: 22px;
    font-weight: 400;
    letter-spacing: 3px;
    background: rgba(242,200,121,0.08);
}

.spacer { height: 14px; }
.spacer-lg { height: 26px; }

/* ─── Per-type adjustments ─── */
.cover .big-title {
    font-size: 96px;
    letter-spacing: 12px;
    margin-bottom: 18px;
}
.cover .medium-title {
    font-size: 44px;
    color: #C9BEF5;
    margin-top: 8px;
}
.cover .body-text {
    font-size: 28px;
    color: #A9A0D9;
    margin-top: 20px;
}

.scene .line {
    width: 100%;
    padding: 16px 26px;
    margin-bottom: 18px;
    background: rgba(255,255,255,0.05);
    border-left: 4px solid rgba(242,200,121,0.75);
    border-radius: 10px;
    font-size: 28px;
    font-weight: 400;
    color: #E7E1FF;
    letter-spacing: 2px;
    line-height: 1.7;
    text-align: left;
}
.scene .line .hl { color: #F2C879; font-weight: 500; }
.scene .foot { font-size: 24px; font-weight: 350; color: #A9A0D9; letter-spacing: 2px; margin-top: 26px; text-align: center; }

.insight .hlbox {
    font-size: 40px;
    font-weight: 700;
    color: #F7F3FF;
    padding: 20px 28px;
    background: rgba(150,130,255,0.12);
    border: 1px solid rgba(180,170,255,0.35);
    border-radius: 14px;
    text-align: center;
    width: 100%;
    margin-bottom: 30px;
    line-height: 1.5;
    box-shadow: 0 0 36px rgba(150,130,255,0.12) inset;
}
.insight .qbox {
    width: 100%;
    padding: 30px 34px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    font-size: 27px;
    font-weight: 350;
    color: #D9D2F7;
    letter-spacing: 2px;
    line-height: 1.9;
    text-align: left;
}
.insight .qbox .mark { color: #F2C879; font-weight: 500; }
.insight .sub { font-size: 30px; font-weight: 500; color: #C9BEF5; letter-spacing: 3px; margin-top: 30px; }

.method .m-step {
    width: 100%;
    margin-bottom: 20px;
    padding: 20px 26px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
}
.method .m-num {
    width: 54px; height: 54px;
    margin: 0 auto 12px auto;
    border-radius: 50%;
    background: linear-gradient(135deg, #F2C879 0%, #D9A24E 100%);
    color: #1A2140;
    font-size: 26px;
    font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    letter-spacing: 0;
    box-shadow: 0 0 22px rgba(242,200,121,0.35);
}

.gentle .big-q {
    font-family: 'Noto Serif SC', serif;
    font-size: 34px;
    font-weight: 400;
    color: #E7E1FF;
    letter-spacing: 3px;
    line-height: 2.0;
    text-align: center;
    padding: 0 10px;
}
.gentle .big-q .rose { color: #F2C879; font-weight: 600; }
.gentle .heart {
    margin-top: 44px;
    font-size: 64px;
    color: rgba(242,200,121,0.6);
    text-shadow: 0 0 30px rgba(242,200,121,0.4);
}
.gentle .hug { font-size: 26px; font-weight: 400; color: #C9BEF5; letter-spacing: 6px; margin-top: 22px; }

.cta .big-title { font-size: 88px; letter-spacing: 12px; margin-bottom: 12px; }
.cta .medium-title { font-size: 42px; color: #C9BEF5; margin-bottom: 30px; }
.cta .chatbox {
    width: 100%;
    padding: 26px 30px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(242,200,121,0.35);
    border-radius: 16px;
    font-size: 26px;
    font-weight: 400;
    color: #E7E1FF;
    letter-spacing: 2px;
    line-height: 1.9;
    text-align: center;
    margin-bottom: 26px;
}
.cta .chatbox .hl { color: #F2C879; font-weight: 500; }
.cta .body-text { font-size: 28px; font-weight: 350; color: #C9BEF5; }

.step-divider {
    width: 60px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(242,200,121,0.4) 50%, transparent 100%);
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
<div class="stars"></div>
{body_html}
<div class="watermark">@情绪树洞 · 与自己和解 · 2026-08-01</div>
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
    <div class="big-title">成年人的崩溃</div>
    <div class="medium-title">往往是静音的</div>
    <div class="spacer"></div>
    <div class="body-text">致每一个假装「没事」的你</div>
</div>""",
    "1 / 6"
)

# ── Card 2: Scene ──
write_card(
    "card_v2_2_scene.html",
    """<div class="card scene">
    <div class="tag">是不是你</div>
    <div class="line">白天被骂，笑着点头说「<span class="hl">好的，我马上改</span>」</div>
    <div class="line">深夜躲进浴室，<span class="hl">热水混着眼泪</span>一起流</div>
    <div class="line">开车回家，在停车场<span class="hl">坐半小时</span>才敢上楼</div>
    <div class="line">明明很难过，却说「<span class="hl">没事，我挺好的</span>」</div>
    <div class="foot">成年人的崩溃，都藏在没人看见的角落</div>
</div>""",
    "2 / 6"
)

# ── Card 3: Insight ──
write_card(
    "card_v2_3_insight.html",
    """<div class="card insight">
    <div class="tag">心理洞察</div>
    <div class="hlbox">崩溃不是软弱，<br>是你一个人撑了太久</div>
    <div class="qbox">心理学里有个词，叫「<span class="mark">情绪劳动</span>」——我们每天都在扮演情绪稳定的大人。可情绪不会消失，它只会累积。被咽下去的眼泪，最后都会变成深夜的失眠、清晨的疲惫。</div>
    <div class="sub">允许自己崩溃，是另一种勇敢</div>
</div>""",
    "3 / 6"
)

# ── Card 4: Method ──
write_card(
    "card_v2_4_method.html",
    """<div class="card method">
    <div class="tag">试着这样做</div>
    <div class="m-step">
        <div class="m-num">01</div>
        <div class="step-title">给崩溃一个「合法时间」</div>
        <div class="step-desc">每天留十分钟，找个安全的地方，痛痛快快哭一场。情绪需要出口，就像雨需要落下。</div>
    </div>
    <div class="m-step">
        <div class="m-num">02</div>
        <div class="step-title">把委屈写下来</div>
        <div class="step-desc">说不出口的话，写出来会轻松很多。写下来的那一刻，情绪就有了安放的地方。</div>
    </div>
    <div class="m-step">
        <div class="m-num">03</div>
        <div class="step-title">对自己说一句「辛苦了」</div>
        <div class="step-desc">不要苛责那个崩溃的自己。你已经撑了很久，值得一句温柔的肯定。</div>
    </div>
</div>""",
    "4 / 6"
)

# ── Card 5: Gentle ──
write_card(
    "card_v2_5_gentle.html",
    """<div class="card gentle">
    <div class="tag">想对你说</div>
    <div class="big-q">你可以在深夜偷偷流泪，<br>可以在浴室里放声大哭，<br>可以对着镜子说「<span class="rose">我好累</span>」。<br><br>这些都不可耻。<br>可耻的，是你从不肯原谅<br>那个脆弱的自己。<br><br><span class="rose">雨会停，天会亮，<br>你会好起来的。</span></div>
    <div class="heart">✿</div>
    <div class="hug">抱抱你</div>
</div>""",
    "5 / 6"
)

# ── Card 6: CTA ──
write_card(
    "card_v2_6_cta.html",
    """<div class="card cta">
    <div class="tag">情绪树洞 · 与自己和解</div>
    <div class="big-title">今晚，我在听</div>
    <div class="chatbox">评论区留下你的故事——<br><span class="hl">你今天，还好吗？</span><br>那些说不出口的委屈，<br>都可以留在这里。</div>
    <div class="cta-border">把你的心事，说给树洞听</div>
</div>""",
    "6 / 6"
)

print(f"\n✅ All 6 V2 card HTMLs generated in {OUT_DIR}")
