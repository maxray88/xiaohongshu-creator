"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day28_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 28 V2 素材生成
V1: 雾霭蓝→暖灰紫 (misty blue → warm grey-purple, gentle melancholic)
V2: 暖日珊瑚→大地棕 (warm sun coral → earth brown, cozy grounded warm)
SAME text content as V1 — only visual style changed.
"""
import json, os, glob, sys, shutil
from datetime import datetime
from pathlib import Path

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
TODAY = datetime.now()
TODAY_FS = TODAY.strftime("%Y%m%d")
TODAY_STR = TODAY.strftime("%Y-%m-%d")

# ─── Day number: find today's V1 day_num ────────────────────────────────
v1_daynum = None
for mf in glob.glob(os.path.join(BASE, f"day_{TODAY_FS}_day*/manifest.json")):
    if "_v2" in mf:
        continue
    try:
        with open(mf) as f:
            data = json.load(f)
            dn = data.get("day_num", 0)
            if dn > 0:
                v1_daynum = dn
    except:
        pass

if v1_daynum is None:
    scanned_max = 0
    for mf in glob.glob(os.path.join(BASE, "day_*/manifest.json")):
        if "_v2" in mf:
            continue
        try:
            with open(mf) as f:
                data = json.load(f)
                dn = data.get("day_num", 0)
                if dn > scanned_max:
                    scanned_max = dn
        except:
            pass
    DAY_NUM = scanned_max
else:
    DAY_NUM = v1_daynum

print(f"  Day number: {DAY_NUM} (from V1 manifest)")

day_dir = os.path.join(BASE, f"day_{TODAY_FS}_day{DAY_NUM}_v2")
img_dir = os.path.join(day_dir, "images")
os.makedirs(img_dir, exist_ok=True)
print(f"  Output: {day_dir}/")

# ─── Color Palette: 暖日珊瑚→大地棕 (completely different from V1's misty blue/purple) ─
# V1 was cool misty blue/warm grey-purple → V2 is warm sun coral / earth brown
C = {
    "bg_start": "#FDF3E7",          # warm cream
    "bg_end": "#F5E0CC",            # soft peach-biscuit
    "bg_glow1": "#E8A87C33",        # coral glow
    "bg_glow2": "#D4956A33",        # terracotta glow
    "card_bg": "#FFFCF5E8",         # warm cream card
    "text_main": "#4A3728",         # deep brown
    "text_sub": "#7A5F4A",          # medium brown
    "text_soft": "#A68B75",         # light brown
    "accent": "#D48B6A",            # coral / terracotta
    "accent_dark": "#B06A4A",       # deep terracotta
    "accent_light": "#E8C4A8",      # light coral
    "accent_warm": "#F0D5B8",       # warm peach
    "divider": "#E0CFC0",           # tan divider
    "watermark": "rgba(180,130,100,0.15)",
    "shadow": "rgba(160,100,60,0.12)",
}

# ─── Card Body HTML Template ─────────────────────────────────────────────
def card_page(body_class, card_content, extra_style=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(160deg, {C['bg_start']} 0%, {C['bg_end']} 50%, {C['bg_start']} 100%);
    font-family: 'PingFang SC', 'Heiti SC', 'Noto Sans SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Warm glowing orbs */
body::before {{
    content: '';
    position: absolute;
    top: -100px;
    right: -40px;
    width: 380px;
    height: 380px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['bg_glow1']} 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -120px;
    left: -60px;
    width: 350px;
    height: 350px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['bg_glow2']} 0%, transparent 70%);
    pointer-events: none;
}}

/* Floating elements */
.floating {{
    position: absolute;
    font-size: 44px;
    opacity: 0.22;
    pointer-events: none;
    z-index: 0;
}}
.flt-1 {{
    top: 28px;
    right: 44px;
    transform: rotate(10deg);
}}
.flt-2 {{
    bottom: 36px;
    left: 32px;
    transform: rotate(-8deg);
}}

.card {{
    position: relative;
    width: 860px;
    padding: 48px 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 2;
    background: {C['card_bg']};
    border-radius: 40px 40px 40px 40px;
    box-shadow: 0 10px 48px {C['shadow']}, 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid {C['divider']}66;
}}

/* Warm accent bar at bottom */
.card::after {{
    content: '';
    position: absolute;
    bottom: 0;
    left: 80px;
    right: 80px;
    height: 4px;
    background: linear-gradient(90deg, {C['accent_light']}, {C['accent']}, {C['accent_light']});
    border-radius: 4px 4px 0 0;
}}

.tag {{
    font-size: 18px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 3px;
    margin-bottom: 18px;
    margin-top: 6px;
    opacity: 0.85;
}}

.big-title {{
    font-size: 56px;
    font-weight: 700;
    color: {C['text_main']};
    text-align: center;
    line-height: 1.3;
    letter-spacing: 4px;
}}

.medium-title {{
    font-size: 32px;
    font-weight: 400;
    color: {C['text_sub']};
    text-align: center;
    line-height: 1.5;
    margin-top: 8px;
    letter-spacing: 2px;
}}

.highlight {{
    font-size: 38px;
    font-weight: 600;
    color: {C['accent_dark']};
    text-align: center;
    line-height: 1.5;
    letter-spacing: 3px;
}}

.highlight-sub {{
    font-size: 28px;
    font-weight: 400;
    color: {C['text_sub']};
    text-align: center;
    line-height: 1.6;
    margin-top: 4px;
    letter-spacing: 2px;
}}

.quote {{
    font-size: 28px;
    font-weight: 350;
    color: {C['text_main']};
    text-align: center;
    line-height: 1.7;
    letter-spacing: 2px;
    padding: 4px 0;
}}

.body-text {{
    font-size: 24px;
    font-weight: 400;
    color: {C['text_sub']};
    text-align: center;
    line-height: 1.6;
    letter-spacing: 1px;
}}

.small-text {{
    font-size: 20px;
    font-weight: 300;
    color: {C['text_soft']};
    text-align: center;
    letter-spacing: 1px;
}}

.step {{
    font-size: 26px;
    font-weight: 600;
    color: {C['accent_dark']};
    text-align: left;
    width: 100%;
    letter-spacing: 2px;
    padding: 6px 0 2px 0;
}}

.spacer {{
    height: 16px;
}}

.cta-border {{
    display: inline-block;
    padding: 12px 36px;
    border: 2px solid {C['accent']}66;
    border-radius: 40px;
    color: {C['accent_dark']};
    font-weight: 500;
    font-size: 22px;
    letter-spacing: 4px;
    background: {C['accent_light']}22;
}}

/* Watermark */
.watermark {{
    position: absolute;
    bottom: 50px;
    right: 70px;
    font-size: 16px;
    font-weight: 300;
    color: {C['watermark']};
    letter-spacing: 2px;
    z-index: 2;
}}

/* Cover card specific */
.cover-card {{
    padding: 60px 60px;
}}
.cover-card .big-title {{
    font-size: 60px;
    margin: 2px 0;
}}
.cover-card .medium-title {{
    margin-top: 16px;
}}
.cover-card .body-text {{
    margin-top: 8px;
    color: {C['text_soft']};
}}

{extra_style}
</style>
</head>
<body class="{body_class}">
    <div class="card {('cover-card' if body_class == 'cover-body' else '')}">
        <div class="floating flt-1">☀️</div>
        <div class="floating flt-2">🍂</div>
        {card_content}
    </div>
    <div class="watermark">情绪树洞 · {TODAY_STR}</div>
</body>
</html>"""

# ─── Card Contents (EXACT SAME TEXT AS V1) ──────────────────────────────

cards = [
    # 1. Cover
    {
        "type": "cover",
        "body_class": "cover-body",
        "content": """<div class="tag">情绪树洞 · 情绪自由</div>
<div class="big-title">允许自己</div>
<div class="big-title">不快乐</div>
<div class="medium-title">不是所有的情绪都需要被解决</div>
<div class="spacer"></div>
<div class="body-text">致被「必须开心」绑架的每一个你</div>"""
    },
    # 2. Scene
    {
        "type": "scene",
        "body_class": "scene-body",
        "content": """<div class="tag">你是否也这样</div>
<div class="quote">明明很难过</div>
<div class="quote">却笑着说「我没事」</div>
<div class="spacer"></div>
<div class="quote">收到「你要开心一点」</div>
<div class="quote">反而更觉得窒息</div>
<div class="spacer"></div>
<div class="body-text">好像不快乐，就是一种失败</div>"""
    },
    # 3. Insight
    {
        "type": "insight",
        "body_class": "insight-body",
        "content": """<div class="tag">一个真相</div>
<div class="highlight">快乐不是人生的默认状态</div>
<div class="highlight-sub">感受才是</div>
<div class="spacer"></div>
<div class="body-text">悲伤、焦虑、疲惫、愤怒</div>
<div class="body-text">它们不是bug，是功能</div>
<div class="spacer"></div>
<div class="small-text">每一种情绪都在告诉你一些事</div>"""
    },
    # 4. Method
    {
        "type": "method",
        "body_class": "method-body",
        "content": """<div class="tag">试试这样</div>
<div class="step">🌧  承认它</div>
<div class="body-text">「我现在很难过」—— 把情绪说出来，它就失去了控制你的力量</div>
<div class="spacer"></div>
<div class="step">🤗  拥抱它</div>
<div class="body-text">把手放在心口，对自己说「没关系，我陪你」</div>
<div class="spacer"></div>
<div class="step">🌸  放它走</div>
<div class="body-text">情绪就像云，你不抓着它，它自然会飘走</div>"""
    },
    # 5. Gentle
    {
        "type": "gentle",
        "body_class": "gentle-body",
        "content": """<div class="tag">想对你说</div>
<div class="highlight">你不必一直快乐</div>
<div class="highlight-sub">你只需要真实地活着</div>
<div class="spacer"></div>
<div class="quote">月亮有阴晴圆缺</div>
<div class="quote">天气有雨雪风霜</div>
<div class="quote">你有喜怒哀乐</div>
<div class="spacer"></div>
<div class="body-text">这些都是你活着的证明</div>"""
    },
    # 6. CTA
    {
        "type": "cta",
        "body_class": "cta-body",
        "content": """<div class="big-title">今天</div>
<div class="medium-title">你允许自己感受什么？</div>
<div class="spacer"></div>
<div class="body-text">在评论区写下此刻真实的心情 🫂</div>
<div class="spacer"></div>
<div class="small-text cta-border">💬 评论区见</div>"""
    },
]

# ─── Generate HTML files ─────────────────────────────────────────────────
for card in cards:
    html = card_page(card["body_class"], card["content"])
    fname = f"card_v2_{cards.index(card)+1}_{card['type']}.html"
    fpath = os.path.join(img_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ {fname}")

# ─── Create/Update V2 manifest.json ──────────────────────────────────────
# Read V1 title from V1 manifest
v1_title = "允许自己不快乐"
v1_series = "情绪树洞 · 情绪自由"
v1_emotion = "情绪自由"
v1_path = os.path.join(BASE, f"day_{TODAY_FS}_day{DAY_NUM}", "manifest.json")
if os.path.exists(v1_path):
    try:
        with open(v1_path) as f:
            v1_data = json.load(f)
        v1_title = v1_data.get("title", v1_title)
        v1_series = v1_data.get("series", v1_series)
        v1_emotion = v1_data.get("emotion_tag", v1_emotion)
    except:
        pass

manifest = {
    "day_num": DAY_NUM,
    "date": TODAY_STR,
    "series": v1_series,
    "title": v1_title,
    "emotion_tag": v1_emotion,
    "v1_color_scheme": "雾霭蓝→暖灰紫",
    "v2_angle": "温暖疗愈 · 大地能量",
    "color_scheme": "暖日珊瑚→大地棕",
    "cards": [
        {"index": 1, "file": "card_v2_1_cover.html", "type": "cover"},
        {"index": 2, "file": "card_v2_2_scene.html", "type": "scene"},
        {"index": 3, "file": "card_v2_3_insight.html", "type": "insight"},
        {"index": 4, "file": "card_v2_4_method.html", "type": "method"},
        {"index": 5, "file": "card_v2_5_gentle.html", "type": "gentle"},
        {"index": 6, "file": "card_v2_6_cta.html", "type": "cta"},
    ],
    "images_rendered": False,
    "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
}

manifest_path = os.path.join(day_dir, "manifest.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"  ✓ manifest.json")

print(f"\n✅ V2 cards generated for Day {DAY_NUM} ({TODAY_STR})")
print(f"   Color: {manifest['color_scheme']}")
print(f"   Title: {manifest['title']}")
print(f"   Date:  {manifest['date']}")
