"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day31.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""generate_day31.py — 情绪树洞 Day 31 (V1) 卡片生成器
主题：成年人的崩溃，往往是静音的
风格：暮色玫瑰 · 温暖诗意 (dusk rose, warm poetic)
"""
import os, json

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole/day_20260801_day31")
IMG = os.path.join(BASE, "images")
os.makedirs(IMG, exist_ok=True)

TAG_SERIES = "情绪树洞 · 与自己和解"
DATE_STR = "2026-08-01"

CSS_COMMON = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;350;400;500;700&family=Noto+Serif+SC:wght@400;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(160deg, #FFF4EE 0%, #FFE9E2 50%, #FCE8EE 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}

body::before {
    content: '';
    position: absolute;
    top: -120px;
    right: -100px;
    width: 520px;
    height: 520px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,170,190,0.22) 0%, transparent 70%);
    pointer-events: none;
}

body::after {
    content: '';
    position: absolute;
    bottom: -110px;
    left: -110px;
    width: 440px;
    height: 440px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,140,160,0.14) 0%, transparent 70%);
    pointer-events: none;
}

.organic {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(circle at 28% 18%, rgba(255,190,205,0.12) 0%, transparent 50%),
        radial-gradient(circle at 72% 82%, rgba(255,170,190,0.10) 0%, transparent 50%);
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
    z-index: 2;
}

.card::before {
    content: '✦';
    position: absolute;
    top: -8px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 22px;
    color: rgba(178,74,110,0.45);
    letter-spacing: 10px;
}

.watermark {
    position: absolute;
    bottom: 36px;
    right: 46px;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 13px;
    font-weight: 300;
    color: rgba(123,36,59,0.22);
    letter-spacing: 1px;
    z-index: 3;
}

.page-num {
    position: absolute;
    bottom: 36px;
    left: 46px;
    font-size: 13px;
    font-weight: 300;
    color: rgba(123,36,59,0.22);
    letter-spacing: 1px;
    z-index: 3;
}

.tag { font-size: 20px; font-weight: 400; color: #AD3357; letter-spacing: 4px; margin-bottom: 30px; padding: 6px 20px; border: 1px solid #F6C3D2; border-radius: 24px; }
.big-title { font-size: 88px; font-weight: 700; color: #7B243B; letter-spacing: 10px; line-height: 1.3; text-align: center; margin-bottom: 14px; }
.medium-title { font-size: 42px; font-weight: 500; color: #AD3357; letter-spacing: 6px; line-height: 1.5; text-align: center; margin-top: 4px; }
.highlight { font-size: 42px; font-weight: 700; color: #AD3357; letter-spacing: 4px; line-height: 1.6; text-align: center; margin-bottom: 12px; width: 100%; }
.highlight-sub { font-size: 32px; font-weight: 500; color: #AD3357; letter-spacing: 3px; line-height: 1.5; text-align: center; }
.quote { font-size: 30px; font-weight: 350; color: #4A2C33; letter-spacing: 3px; line-height: 1.8; text-align: center; margin-bottom: 4px; }
.body-text { font-size: 28px; font-weight: 350; color: #AD3357; letter-spacing: 2px; line-height: 1.8; text-align: center; margin-bottom: 4px; }
.step-num { font-size: 38px; font-weight: 500; color: #AD3357; letter-spacing: 4px; line-height: 1.4; text-align: center; margin-bottom: 6px; }
.step-title { font-size: 32px; font-weight: 500; color: #7B243B; letter-spacing: 3px; line-height: 1.5; text-align: center; margin-bottom: 10px; }
.step-desc { font-size: 22px; font-weight: 350; color: #AD3357; letter-spacing: 2px; line-height: 1.7; text-align: center; margin-bottom: 18px; padding: 0 20px; }
.small-text { font-size: 20px; font-weight: 300; color: #AD3357; letter-spacing: 2px; text-align: center; }
.cta-border { margin-top: 12px; padding: 7px 22px; border: 1px solid #F6C3D2; border-radius: 24px; color: #AD3357; font-size: 22px; font-weight: 400; letter-spacing: 3px; }
.spacer { height: 16px; }
.step-divider { width: 60px; height: 1px; background: #F6C3D2; margin: 6px auto; }
"""

# ─── Card 1: cover ───
CARD1 = """
<style>
    .cover .orb {
        position: absolute;
        top: 120px;
        left: 50%;
        transform: translateX(-50%);
        width: 260px;
        height: 260px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,170,190,0.30) 0%, transparent 70%);
        z-index: 0;
    }
    .cover .big-title { font-size: 96px; letter-spacing: 12px; margin-bottom: 18px; }
    .cover .medium-title { font-size: 44px; color: #AD3357; margin-top: 8px; }
    .cover .body-text { font-size: 28px; color: #8A5A63; margin-top: 20px; }
    .cover .cover-card { padding-top: 90px; }
</style>
<div class="card cover cover-card">
    <div class="orb"></div>
    <div class="tag">__SERIES__</div>
    <div class="big-title">成年人的崩溃</div>
    <div class="medium-title">往往是静音的</div>
    <div class="spacer"></div>
    <div class="body-text">致每一个假装「没事」的你</div>
</div>
"""

# ─── Card 2: scene ───
CARD2 = """
<style>
    .scene .scene-tag { font-size: 20px; font-weight: 400; color: #AD3357; letter-spacing: 4px; margin-bottom: 40px; padding: 6px 20px; border: 1px solid #F6C3D2; border-radius: 24px; }
    .scene .line {
        width: 100%;
        padding: 16px 26px;
        margin-bottom: 18px;
        background: rgba(255,255,255,0.55);
        border-left: 4px solid #E8A0B4;
        border-radius: 10px;
        font-size: 28px;
        font-weight: 400;
        color: #4A2C33;
        letter-spacing: 2px;
        line-height: 1.7;
        text-align: left;
    }
    .scene .line .hl { color: #AD3357; font-weight: 500; }
    .scene .foot { font-size: 24px; font-weight: 350; color: #8A5A63; letter-spacing: 2px; margin-top: 26px; }
</style>
<div class="card scene">
    <div class="scene-tag">是不是你</div>
    <div class="line">白天被骂，笑着点头说「<span class="hl">好的，我马上改</span>」</div>
    <div class="line">深夜躲进浴室，<span class="hl">热水混着眼泪</span>一起流</div>
    <div class="line">开车回家，在停车场<span class="hl">坐半小时</span>才敢上楼</div>
    <div class="line">明明很难过，却说「<span class="hl">没事，我挺好的</span>」</div>
    <div class="foot">成年人的崩溃，都藏在没人看见的角落</div>
</div>
"""

# ─── Card 3: insight ───
CARD3 = """
<style>
    .insight .hlbox {
        font-size: 40px;
        font-weight: 700;
        color: #7B243B;
        padding: 18px 26px;
        background: rgba(255,214,224,0.35);
        border-radius: 12px;
        text-align: center;
        width: 100%;
        border: 1px solid #F6C3D2;
        margin-bottom: 30px;
        line-height: 1.5;
    }
    .insight .qbox {
        width: 100%;
        padding: 30px 34px;
        background: rgba(255,255,255,0.6);
        border-radius: 14px;
        font-size: 27px;
        font-weight: 350;
        color: #4A2C33;
        letter-spacing: 2px;
        line-height: 1.9;
        text-align: left;
    }
    .insight .qbox .mark { color: #AD3357; font-weight: 500; }
    .insight .sub { font-size: 30px; font-weight: 500; color: #AD3357; letter-spacing: 3px; margin-top: 30px; }
</style>
<div class="card insight">
    <div class="tag">心理洞察</div>
    <div class="hlbox">崩溃不是软弱，<br>是你一个人撑了太久</div>
    <div class="qbox">心理学里有个词，叫「<span class="mark">情绪劳动</span>」——我们每天都在扮演情绪稳定的大人。可情绪不会消失，它只会累积。被咽下去的眼泪，最后都会变成深夜的失眠、清晨的疲惫。</div>
    <div class="sub">允许自己崩溃，是另一种勇敢</div>
</div>
"""

# ─── Card 4: method ───
CARD4 = """
<style>
    .method .m-step { width: 100%; margin-bottom: 20px; padding: 20px 26px; background: rgba(255,255,255,0.5); border-radius: 14px; }
    .method .m-num {
        width: 54px; height: 54px;
        margin: 0 auto 12px auto;
        border-radius: 50%;
        background: #AD3357;
        color: #FFF7F0;
        font-size: 26px;
        font-weight: 500;
        display: flex; align-items: center; justify-content: center;
        letter-spacing: 0;
    }
    .method .m-title { font-size: 30px; font-weight: 600; color: #7B243B; letter-spacing: 3px; text-align: center; margin-bottom: 10px; }
    .method .m-desc { font-size: 22px; font-weight: 350; color: #4A2C33; letter-spacing: 2px; line-height: 1.7; text-align: center; }
</style>
<div class="card method">
    <div class="tag">试着这样做</div>
    <div class="m-step">
        <div class="m-num">01</div>
        <div class="m-title">给崩溃一个「合法时间」</div>
        <div class="m-desc">每天留十分钟，找个安全的地方，痛痛快快哭一场。情绪需要出口，就像雨需要落下。</div>
    </div>
    <div class="m-step">
        <div class="m-num">02</div>
        <div class="m-title">把委屈写下来</div>
        <div class="m-desc">说不出口的话，写出来会轻松很多。写下来的那一刻，情绪就有了安放的地方。</div>
    </div>
    <div class="m-step">
        <div class="m-num">03</div>
        <div class="m-title">对自己说一句「辛苦了」</div>
        <div class="m-desc">不要苛责那个崩溃的自己。你已经撑了很久，值得一句温柔的肯定。</div>
    </div>
</div>
"""

# ─── Card 5: gentle ───
CARD5 = """
<style>
    .gentle .big-q {
        font-family: 'Noto Serif SC', serif;
        font-size: 34px;
        font-weight: 400;
        color: #4A2C33;
        letter-spacing: 3px;
        line-height: 2.0;
        text-align: center;
        padding: 0 10px;
    }
    .gentle .big-q .rose { color: #AD3357; font-weight: 600; }
    .gentle .heart {
        margin-top: 44px;
        font-size: 64px;
        color: rgba(178,74,110,0.55);
    }
    .gentle .hug { font-size: 26px; font-weight: 400; color: #AD3357; letter-spacing: 6px; margin-top: 22px; }
</style>
<div class="card gentle">
    <div class="tag">想对你说</div>
    <div class="big-q">你可以在深夜偷偷流泪，<br>可以在浴室里放声大哭，<br>可以对着镜子说「<span class="rose">我好累</span>」。<br><br>这些都不可耻。<br>可耻的，是你从不肯原谅<br>那个脆弱的自己。<br><br><span class="rose">雨会停，天会亮，<br>你会好起来的。</span></div>
    <div class="heart">✿</div>
    <div class="hug">抱抱你</div>
</div>
"""

# ─── Card 6: cta ───
CARD6 = """
<style>
    .cta .big-title { font-size: 88px; letter-spacing: 10px; margin-bottom: 12px; }
    .cta .medium-title { font-size: 42px; color: #AD3357; margin-bottom: 30px; }
    .cta .chatbox {
        width: 100%;
        padding: 26px 30px;
        background: rgba(255,255,255,0.65);
        border: 1px solid #F6C3D2;
        border-radius: 16px;
        font-size: 26px;
        font-weight: 400;
        color: #4A2C33;
        letter-spacing: 2px;
        line-height: 1.9;
        text-align: center;
        margin-bottom: 26px;
    }
    .cta .chatbox .hl { color: #AD3357; font-weight: 500; }
    .cta .body-text { font-size: 28px; font-weight: 350; color: #AD3357; }
</style>
<div class="card cta">
    <div class="tag">情绪树洞 · 与自己和解</div>
    <div class="big-title">今晚，我在听</div>
    <div class="chatbox">评论区留下你的故事——<br><span class="hl">你今天，还好吗？</span><br>那些说不出口的委屈，<br>都可以留在这里。</div>
    <div class="cta-border">把你的心事，说给树洞听</div>
</div>
"""

CARDS = {
    "card_1.html": CARD1,
    "card_2.html": CARD2,
    "card_3.html": CARD3,
    "card_4.html": CARD4,
    "card_5.html": CARD5,
    "card_6.html": CARD6,
}

PAGE_NUMS = {"card_1.html": "1 / 6", "card_2.html": "2 / 6", "card_3.html": "3 / 6",
             "card_4.html": "4 / 6", "card_5.html": "5 / 6", "card_6.html": "6 / 6"}

for fname, body in CARDS.items():
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>{fname}</title>
<style>
{CSS_COMMON}
</style>
</head>
<body>
<div class="organic"></div>
{body.replace("__SERIES__", TAG_SERIES)}
<div class="watermark">@{TAG_SERIES} · {DATE_STR}</div>
<div class="page-num">{PAGE_NUMS[fname]}</div>
</body>
</html>
"""
    path = os.path.join(IMG, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {path}")

print("All 6 HTML cards generated.")
