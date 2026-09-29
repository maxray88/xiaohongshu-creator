"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day32.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""generate_day32.py — 情绪树洞 Day 32 (2026-08-09) V1 + V2 卡片生成
主题：慢一点，也没关系
V1 配色：暖阳奶油 (warm cream)  |  V2 配色：夜雾青蓝 (midnight teal)
"""
import os, json
from datetime import datetime

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")
DAY_NUM = 32
DATE_STR = "2026-08-09"
TITLE = "慢一点，也没关系"
EMOTION_TAG = "慢节奏"
SERIES = "情绪树洞 · 与自己和解"

V1_DIR = os.path.join(BASE, f"day_{DATE_STR.replace('-','')}_day{DAY_NUM}")
V2_DIR = os.path.join(BASE, f"day_{DATE_STR.replace('-','')}_day{DAY_NUM}_v2")
V1_IMG = os.path.join(V1_DIR, "images")
V2_IMG = os.path.join(V2_DIR, "images")
os.makedirs(V1_IMG, exist_ok=True)
os.makedirs(V2_IMG, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Card text content (shared by V1 and V2)
# ─────────────────────────────────────────────────────────────
CARDS = {
    1: {"type": "cover",
        "lines": [
            ("tag", "情绪树洞 · 与自己和解"),
            ("big-title", "慢一点"),
            ("medium-title", "也没关系"),
            ("spacer", ""),
            ("body-text", "致每一个正在赶路的你"),
        ]},
    2: {"type": "scene",
        "lines": [
            ("tag", "你是否也这样"),
            ("quote", "身边的人都跑得好快"),
            ("quote", "朋友圈里，大家都在晒进步"),
            ("spacer", ""),
            ("quote", "只有你，好像还停在原地"),
            ("quote", "于是你越来越焦虑"),
            ("quote", "越焦虑，越不敢停下来"),
        ]},
    3: {"type": "insight",
        "lines": [
            ("tag", "我想对你说"),
            ("highlight", "慢，不是落后"),
            ("quote", "人生不是赛道，是各自的时区"),
            ("spacer", ""),
            ("quote", "有人二十岁就光芒万丈"),
            ("quote", "有人四十岁才刚刚发芽"),
            ("spacer", ""),
            ("quote", "你只是在按自己的节奏生长"),
            ("quote", "这没有错"),
        ]},
    4: {"type": "method",
        "lines": [
            ("tag", "试试这样做"),
            ("step-num", "01"),
            ("step-title", "每天留十五分钟，什么都不做"),
            ("step-desc", "发发呆，看看云，听听风声"),
            ("step-divider", ""),
            ("step-num", "02"),
            ("step-title", "把「我应该」换成「我可以」"),
            ("step-desc", "允许自己按意愿选择节奏"),
            ("step-divider", ""),
            ("step-num", "03"),
            ("step-title", "只和昨天的自己比较"),
            ("step-desc", "你不需要跑赢任何人"),
        ]},
    5: {"type": "gentle",
        "lines": [
            ("tag", "想对你说"),
            ("highlight", "你的节奏，就是最好的节奏"),
            ("quote", "慢一点，路边的花才看得清"),
            ("spacer", ""),
            ("quote", "世界很大，容得下每一种速度"),
            ("spacer", ""),
            ("quote", "你慢慢来，也值得被爱"),
        ]},
    6: {"type": "cta",
        "lines": [
            ("tag", "说说话吧"),
            ("big-title", "你最近一次"),
            ("medium-title", "慢下来，是什么时候？"),
            ("spacer", ""),
            ("body-text", "评论区聊聊你的故事"),
            ("body-text", "你又是怎么找回自己的节奏的？"),
        ]},
}

# ─────────────────────────────────────────────────────────────
# CSS builders
# ─────────────────────────────────────────────────────────────
BASE_CSS_TEMPLATE = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@400;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: {BG};
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
    top: -180px;
    right: -120px;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, {GLOW1} 0%, transparent 70%);
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
    background: radial-gradient(circle, {GLOW2} 0%, transparent 70%);
    pointer-events: none;
}

.stardust {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(1.5px 1.5px at 15% 25%, {STAR} 0%, transparent 100%),
        radial-gradient(1px 1px at 35% 10%, {STAR} 0%, transparent 100%),
        radial-gradient(2px 2px at 55% 30%, {STAR} 0%, transparent 100%),
        radial-gradient(1px 1px at 75% 15%, {STAR} 0%, transparent 100%),
        radial-gradient(1.5px 1.5px at 90% 40%, {STAR} 0%, transparent 100%),
        radial-gradient(1px 1px at 10% 60%, {STAR} 0%, transparent 100%),
        radial-gradient(2px 2px at 45% 70%, {STAR} 0%, transparent 100%),
        radial-gradient(1px 1px at 70% 80%, {STAR} 0%, transparent 100%),
        radial-gradient(1.5px 1.5px at 25% 85%, {STAR} 0%, transparent 100%),
        radial-gradient(1px 1px at 60% 90%, {STAR} 0%, transparent 100%);
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

.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, {ACCENT} 30%, {ACCENT} 70%, transparent 100%);
    border-radius: 2px;
}

.watermark {
    position: absolute;
    bottom: 28px;
    right: 44px;
    font-size: 16px;
    font-weight: 300;
    color: {WATERMARK};
    letter-spacing: 1px;
    z-index: 3;
}

.page-num {
    position: absolute;
    bottom: 28px;
    left: 44px;
    font-size: 16px;
    font-weight: 300;
    color: {WATERMARK};
    letter-spacing: 1px;
    z-index: 3;
}

.tag {
    font-size: 26px;
    font-weight: 400;
    color: {ACCENT};
    letter-spacing: 4px;
    margin-bottom: 28px;
    padding: 6px 22px;
    border: 1px solid {TAG_BORDER};
    border-radius: 24px;
    background: {TAG_BG};
}

.big-title {
    font-size: 88px;
    font-weight: 900;
    color: {TEXT_MAIN};
    letter-spacing: 12px;
    line-height: 1.3;
    text-align: center;
    margin-bottom: 14px;
    text-shadow: 0 0 40px {GLOW1};
}

.medium-title {
    font-size: 46px;
    font-weight: 500;
    color: {ACCENT};
    letter-spacing: 6px;
    line-height: 1.5;
    text-align: center;
    margin-top: 4px;
}

.highlight {
    font-size: 46px;
    font-weight: 700;
    color: {ACCENT};
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 12px;
    width: 100%;
    padding: 16px 24px;
    background: {TAG_BG};
    border-radius: 12px;
    border: 1px solid {TAG_BORDER};
    text-shadow: 0 0 30px {GLOW1};
}

.quote {
    font-size: 36px;
    font-weight: 350;
    color: {TEXT_SUB};
    letter-spacing: 3px;
    line-height: 1.9;
    text-align: center;
    margin-bottom: 2px;
}

.body-text {
    font-size: 34px;
    font-weight: 350;
    color: {TEXT_SUB};
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}

.step-num {
    font-size: 44px;
    font-weight: 500;
    color: {ACCENT};
    letter-spacing: 4px;
    line-height: 1.4;
    text-align: center;
    margin-bottom: 6px;
}

.step-title {
    font-size: 38px;
    font-weight: 600;
    color: {TEXT_MAIN};
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 10px;
}

.step-desc {
    font-size: 30px;
    font-weight: 350;
    color: {TEXT_SUB};
    letter-spacing: 2px;
    line-height: 1.7;
    text-align: center;
    margin-bottom: 16px;
    padding: 0 24px;
}

.step-divider {
    width: 60px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, {ACCENT} 50%, transparent 100%);
    margin: 6px auto;
}

.spacer { height: 12px; }
.spacer-lg { height: 24px; }

.cover .big-title { font-size: 96px; letter-spacing: 16px; margin-bottom: 18px; }
.cover .medium-title { font-size: 46px; margin-top: 8px; }
.gentle .highlight { font-size: 46px; margin-bottom: 20px; }
.cta .big-title { font-size: 88px; letter-spacing: 14px; margin-bottom: 10px; }
.cta .medium-title { font-size: 46px; margin-bottom: 24px; }
"""

V1_COLORS = {
    "BG": "linear-gradient(160deg, #FFF6EC 0%, #FFEDDC 50%, #FBE8E4 100%)",
    "GLOW1": "rgba(255,170,140,0.20)",
    "GLOW2": "rgba(255,140,150,0.12)",
    "STAR": "rgba(255,180,140,0.18)",
    "ACCENT": "#C97B63",
    "TAG_BORDER": "rgba(201,123,99,0.30)",
    "TAG_BG": "rgba(255,237,220,0.6)",
    "WATERMARK": "rgba(201,123,99,0.30)",
    "TEXT_MAIN": "#4A2E28",
    "TEXT_SUB": "#6E4B42",
}

V2_COLORS = {
    "BG": "linear-gradient(160deg, #0B1E2D 0%, #102A3C 45%, #0E2730 100%)",
    "GLOW1": "rgba(127,209,200,0.16)",
    "GLOW2": "rgba(168,218,220,0.10)",
    "STAR": "rgba(168,218,220,0.20)",
    "ACCENT": "#7FD1C8",
    "TAG_BORDER": "rgba(127,209,200,0.28)",
    "TAG_BG": "rgba(127,209,200,0.07)",
    "WATERMARK": "rgba(168,218,220,0.28)",
    "TEXT_MAIN": "#E8F4F2",
    "TEXT_SUB": "#B8D4D4",
}


def build_html(card_num, card, colors, v2_prefix=""):
    """Build a card HTML file."""
    css = BASE_CSS_TEMPLATE
    for key, value in colors.items():
        css = css.replace("{" + key + "}", value)
    body_parts = ['<div class="stardust"></div>']
    body_parts.append(f'<div class="card {card["type"]}">')
    for kind, text in card["lines"]:
        if kind == "spacer":
            body_parts.append('<div class="spacer"></div>')
        elif kind == "step-divider":
            body_parts.append('<div class="step-divider"></div>')
        else:
            body_parts.append(f'    <div class="{kind}">{text}</div>')
    body_parts.append('</div>')
    body_parts.append(f'<div class="watermark">@情绪树洞 · {DATE_STR}</div>')
    body_parts.append(f'<div class="page-num">{card_num} / 6</div>')
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>{v2_prefix}card_{card_num}_{card['type']}.html</title>
<style>
{css}
</style>
</head>
<body>
{chr(10).join(body_parts)}
</body>
</html>
"""


def write_manifest(v2_dir, v2_angle, color_scheme, card_files, images_rendered=False):
    cards = []
    for i in sorted(CARDS.keys()):
        cards.append({
            "index": i,
            "file": card_files[i],
            "type": CARDS[i]["type"],
        })
    manifest = {
        "day_num": DAY_NUM,
        "date": DATE_STR,
        "series": SERIES,
        "title": TITLE,
        "emotion_tag": EMOTION_TAG,
        "v1_color_scheme": "暖阳奶油",
        "v2_angle": v2_angle,
        "color_scheme": color_scheme,
        "renderer": "html-fallback",
        "cards": cards,
        "images_rendered": images_rendered,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(v2_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main():
    # ── V1: HTML cards (warm cream) ──
    for i in sorted(CARDS.keys()):
        html = build_html(i, CARDS[i], V1_COLORS, v2_prefix="")
        with open(os.path.join(V1_IMG, f"card_{i}_{CARDS[i]['type']}.html"), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"✅ V1 HTML: {V1_IMG}")

    # V1 manifest (file refs .html; rendered later to .jpg)
    write_manifest(V1_DIR, "夜雾青蓝 · 冷调静谧", "夜雾青蓝",
                   {i: f"card_{i}_{CARDS[i]['type']}.html" for i in sorted(CARDS.keys())},
                   images_rendered=False)

    # V1 post_data.json
    post_data = {
        "day_num": DAY_NUM,
        "title": TITLE,
        "content_text": (
            "最近总在深夜刷到别人「又进步了」的动态，然后盯着天花板失眠。\n\n"
            "好像所有人都在跑，只有你还在原地。\n\n"
            "可是你知道吗？\n\n"
            "树有树的生长速度，花有花的开放时节。山谷里的野樱，从不羡慕山顶的松柏。\n\n"
            "慢，不是落后。\n"
            "慢，是你还在按照自己的节奏，认真活着。\n\n"
            "你可以不追赶，可以不比较，可以允许自己今天只做一件小事，甚至可以什么都不做。\n\n"
            "人生不是比赛。\n"
            "你走的每一步，都算数。\n\n"
            "今天，试着慢下来吧。\n"
            "慢一点，也没关系。"
        ),
        "hashtags": ["情绪树洞", "与自己和解", "慢生活", "情绪疗愈", "自我接纳"],
        "best_post_time": "2026-08-09 22:00:00",
        "emotion_tag": EMOTION_TAG,
        "series": SERIES,
    }
    with open(os.path.join(V1_DIR, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print(f"✅ V1 post_data.json")

    # ── V2: HTML cards (midnight teal) ──
    for i in sorted(CARDS.keys()):
        html = build_html(i, CARDS[i], V2_COLORS, v2_prefix="v2_")
        with open(os.path.join(V2_IMG, f"card_v2_{i}_{CARDS[i]['type']}.html"), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"✅ V2 HTML: {V2_IMG}")

    # V2 manifest
    write_manifest(V2_DIR, "夜雾青蓝 · 冷调静谧", "夜雾青蓝",
                   {i: f"card_v2_{i}_{CARDS[i]['type']}.jpg" for i in sorted(CARDS.keys())},
                   images_rendered=False)
    print(f"✅ V2 manifest.json")

    # ── Update published_content.json ──
    tracker_path = os.path.join(BASE, "published_content.json")
    tracker = json.load(open(tracker_path)) if os.path.isfile(tracker_path) else []
    if not any(e.get("title") == TITLE for e in tracker):
        tracker.append({"day_num": DAY_NUM, "title": TITLE, "date": DATE_STR})
        with open(tracker_path, "w", encoding="utf-8") as f:
            json.dump(tracker, f, ensure_ascii=False, indent=2)
        print(f"✅ published_content.json updated (Day {DAY_NUM})")
    else:
        print(f"⏭ Already tracked")

    print(f"\n🎉 Day {DAY_NUM} «{TITLE}» generated (V1+V2)")


if __name__ == "__main__":
    main()
