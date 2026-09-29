"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day8.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 8 自动化内容生成
Topic: 别追了，喜欢你的人不用追 (恋爱清醒脑)
Color Scheme: 暖橙→淡娜
"""

import json
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# ─── Paths ───────────────────────────────────────────────────────────────
BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
STATE_FILE = os.path.join(BASE, "current_day.txt")
TODAY = datetime.now().strftime("%Y%m%d")
DAY_NUM = 8

day_dir = os.path.join(BASE, f"day_{TODAY}")
img_dir = os.path.join(day_dir, "images")
os.makedirs(img_dir, exist_ok=True)

# ─── Color Palette: 暖橙→淡娜 ─────────────────────────────────────────
C = {
    "bg_start": "#FEF6F0",
    "bg_end": "#FFE4D0",
    "card_bg": "#FFFBF7",
    "text_main": "#3D2B1F",
    "text_sub": "#8B7355",
    "text_soft": "#B8957A",
    "accent": "#D4785C",
    "accent_dark": "#B85A3F",
    "accent_light": "#F0D0C0",
    "divider": "#E8D5C8",
    "watermark": "rgba(180,120,90,0.25)",
}

# ─── Content Definition ─────────────────────────────────────────────────
POST_TITLE = "别追了，喜欢你的人不用追"
SERIES = "恋爱清醒脑"
SERIES_TAG = "清醒恋爱"

CARDS = [
    {
        "type": "cover",
        "lines": [
            ("tag", SERIES),
            ("big", "别追了"),
            ("medium", "喜欢你的人不用追"),
        ]
    },
    {
        "type": "scene",
        "lines": [
            ("tag", "你是否也有过这样的经历"),
            ("quote", "你每天都在等她回复消息"),
            ("quote", "翻来覆去看她的朋友圈"),
            ("quote", "揣测她每一个表情的含义"),
            ("spacer", ""),
            ("body", "你以为再努力一点，她就会看到你的好。"),
        ]
    },
    {
        "type": "insight",
        "lines": [
            ("tag", "一个扎心的真相"),
            ("highlight", "感情从来不是靠努力得来的"),
            ("body", "你追得越紧，她逃得越远。"),
            ("body", "不被喜欢的人，连你的真诚都觉得是负担。"),
        ]
    },
    {
        "type": "method",
        "lines": [
            ("tag", "不如这样做"),
            ("step", "停下来吧"),
            ("body", "把花在她身上的时间，用来读书、运动、赚钱。"),
            ("spacer", ""),
            ("highlight", "当你不再围着一个人转"),
            ("highlight_sub", "整个世界都会为你让路"),
        ]
    },
    {
        "type": "gentle",
        "lines": [
            ("tag", "记住"),
            ("highlight", "真正喜欢你的人"),
            ("body", "不会让你猜来猜去"),
            ("body", "不会让你患得患失"),
            ("spacer", ""),
            ("quote", "她的眼神 语气 行动"),
            ("quote", "都在告诉你：我在意你"),
        ]
    },
    {
        "type": "cta",
        "lines": [
            ("big", "别追了"),
            ("medium", "对的人不用追"),
            ("spacer", ""),
            ("body", "把最好的自己"),
            ("body", "留给那个不用你追的人"),
        ]
    },
]


# ─── HTML Template ──────────────────────────────────────────────────────
def make_html(card_idx, card_data):
    lines_html = []
    for line_type, text in card_data["lines"]:
        if line_type == "tag":
            lines_html.append(f'<div class="tag">{text}</div>')
        elif line_type == "big":
            lines_html.append(f'<div class="big-title">{text}</div>')
        elif line_type == "medium":
            lines_html.append(f'<div class="medium-title">{text}</div>')
        elif line_type == "highlight":
            lines_html.append(f'<div class="highlight">{text}</div>')
        elif line_type == "highlight_sub":
            lines_html.append(f'<div class="highlight-sub">{text}</div>')
        elif line_type == "quote":
            lines_html.append(f'<div class="quote">{text}</div>')
        elif line_type == "body":
            lines_html.append(f'<div class="body-text">{text}</div>')
        elif line_type == "step":
            lines_html.append(f'<div class="step">{text}</div>')
        elif line_type == "small":
            lines_html.append(f'<div class="small-text">{text}</div>')
        elif line_type == "spacer":
            lines_html.append(f'<div class="spacer"></div>')

    type_class = card_data["type"]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;350;400;500;700&family=Noto+Serif+SC:wght@400;600;700&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(160deg, {C['bg_start']} 0%, {C['bg_end']} 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Decorative background circles */
body::before {{
    content: '';
    position: absolute;
    top: -180px;
    right: -180px;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_light']}44 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -120px;
    left: -120px;
    width: 350px;
    height: 350px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent']}22 0%, transparent 70%);
    pointer-events: none;
}}

.card {{
    position: relative;
    width: 880px;
    padding: 60px 50px;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 2;
}}

/* Decorative top accent */
.card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 70px;
    height: 3px;
    background: {C['accent']};
    border-radius: 2px;
}}

/* Decorative bottom accent (subtle line) */
.card::after {{
    content: '';
    position: absolute;
    bottom: -10px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 2px;
    background: {C['divider']};
    border-radius: 1px;
}}

.watermark {{
    position: absolute;
    bottom: 36px;
    right: 46px;
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 13px;
    font-weight: 300;
    color: {C['watermark']};
    letter-spacing: 1px;
    z-index: 3;
}}

.page-num {{
    position: absolute;
    bottom: 36px;
    left: 46px;
    font-size: 13px;
    font-weight: 300;
    color: {C['watermark']};
    letter-spacing: 1px;
    z-index: 3;
}}

/* ─── Typography ─── */
.tag {{
    font-size: 22px;
    font-weight: 400;
    color: {C['accent']};
    letter-spacing: 4px;
    margin-bottom: 36px;
    padding: 7px 22px;
    border: 1px solid {C['accent']}55;
    border-radius: 28px;
}}

.big-title {{
    font-size: 96px;
    font-weight: 700;
    color: {C['text_main']};
    letter-spacing: 10px;
    line-height: 1.3;
    text-align: center;
    margin-bottom: 18px;
}}

.medium-title {{
    font-size: 44px;
    font-weight: 500;
    color: {C['text_sub']};
    letter-spacing: 6px;
    line-height: 1.5;
    text-align: center;
    margin-top: 4px;
}}

.highlight {{
    font-size: 44px;
    font-weight: 700;
    color: {C['accent_dark']};
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 14px;
    width: 100%;
}}

.highlight-sub {{
    font-size: 34px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
}}

.quote {{
    font-size: 34px;
    font-weight: 350;
    color: {C['text_main']};
    letter-spacing: 3px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 6px;
}}

.body-text {{
    font-size: 30px;
    font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 6px;
}}

.step {{
    font-size: 42px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 4px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 18px;
}}

.small-text {{
    font-size: 22px;
    font-weight: 300;
    color: {C['text_soft']};
    letter-spacing: 2px;
    text-align: center;
}}

.spacer {{
    height: 20px;
}}

/* ─── Per-type adjustments ─── */
.cover .big-title {{
    font-size: 110px;
    letter-spacing: 14px;
    margin-bottom: 20px;
}}
.cover .medium-title {{
    font-size: 44px;
    color: {C['text_sub']};
    margin-top: 10px;
}}

.scene .quote {{
    font-size: 32px;
    font-weight: 350;
    color: {C['text_main']};
}}

.insight .highlight {{
    font-size: 40px;
    padding: 18px 28px;
    background: {C['accent_light']}33;
    border-radius: 12px;
    text-align: center;
    width: 100%;
}}

.method .highlight {{
    font-size: 38px;
    color: {C['accent_dark']};
}}
.method .highlight-sub {{
    font-size: 32px;
    color: {C['accent']};
}}

.gentle .highlight {{
    font-size: 44px;
    color: {C['accent_dark']};
    margin-bottom: 28px;
}}
.gentle .quote {{
    font-size: 32px;
    font-weight: 350;
    color: {C['text_sub']};
}}

.cta .big-title {{
    font-size: 100px;
    letter-spacing: 14px;
    margin-bottom: 14px;
}}
.cta .medium-title {{
    font-size: 44px;
    color: {C['accent']};
    margin-bottom: 30px;
}}
.cta .body-text {{
    font-size: 30px;
    font-weight: 350;
    color: {C['text_soft']};
}}
</style>
</head>
<body>
<div class="card {type_class}">
    {''.join(lines_html)}
</div>
<div class="watermark">@情绪树洞 · {TODAY}</div>
<div class="page-num">{card_idx + 1} / {len(CARDS)}</div>
</body>
</html>"""
    return html


# ─── Screenshot ─────────────────────────────────────────────────────────
def render_all_cards():
    print(f"[Render] Starting Playwright rendering...\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,
        )
        for idx, card in enumerate(CARDS):
            html_content = make_html(idx, card)
            html_path = os.path.join(img_dir, f"card_{idx+1}.html")
            jpg_path = os.path.join(img_dir, f"card_{idx+1}.jpg")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            page = context.new_page()
            page.goto(f"file://{html_path}", wait_until="networkidle")
            page.wait_for_timeout(800)
            page.screenshot(path=jpg_path, full_page=False, type="jpeg", quality=95)
            page.close()

            img_size_kb = os.path.getsize(jpg_path) / 1024
            print(f"  [{idx+1}/6] card_{idx+1}.jpg  ({img_size_kb:.0f} KB)")

        browser.close()
    print(f"\n[Render] All 6 cards saved to: {img_dir}")


# ─── Metadata ───────────────────────────────────────────────────────────
MANIFEST = {
    "day_num": DAY_NUM,
    "date": TODAY,
    "series": SERIES,
    "title": POST_TITLE,
    "emotion_tag": SERIES_TAG,
    "color_scheme": "暖橙→淡娜",
    "cards": [
        {"index": i+1, "type": c["type"], "file": f"card_{i+1}.jpg"}
        for i, c in enumerate(CARDS)
    ],
    "images_rendered": True,
    "generated_at": datetime.now().isoformat(),
}

POST_DATA = {
    "platform": "xiaohongshu",
    "day_num": DAY_NUM,
    "date": TODAY,
    "series": SERIES,
    "title": POST_TITLE,
    "emotion_tag": SERIES_TAG,
    "content_text": (
        "别追了，喜欢你的人不用追。\n\n"
        "你每天都在等她回复消息，翻来覆去看她的朋友圈，"
        "揣测她每一个表情的含义。你以为再努力一点，她就会看到你的好。\n\n"
        "但感情从来不是靠努力得来的。你追得越紧，她逃得越远。"
        "不被喜欢的人，连你的真诚都觉得是负担。\n\n"
        "停下来吧。把花在她身上的时间，用来读书、运动、赚钱。"
        "当你不再围着一个人转，整个世界都会为你让路。\n\n"
        "真正喜欢你的人，不会让你猜来猜去，不会让你患得患失。"
        "她的眼神、语气、行动，都在告诉你：我在意你。\n\n"
        "别追了。对的人不用追。把最好的自己，留给那个不用你追的人。"
    ),
    "hashtags": [
        "#恋爱清醒脑", "#清醒恋爱", "#别追了", "#情绪树洞",
        "#情感共鸣", "#恋爱观", "#治愈系", "#人间清醒"
    ],
    "images": [f"card_{i+1}.jpg" for i in range(len(CARDS))],
    "image_count": len(CARDS),
    "generated_at": datetime.now().isoformat(),
}


def save_metadata():
    with open(os.path.join(day_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)
    with open(os.path.join(day_dir, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump(POST_DATA, f, ensure_ascii=False, indent=2)
    print(f"[Meta] manifest.json + post_data.json saved.")


def update_state():
    with open(STATE_FILE, "w") as f:
        f.write(str(DAY_NUM))
    print(f"[State] current_day.txt updated to {DAY_NUM}")


# ─── Main ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"{'='*60}")
    print(f"  情绪树洞 · Day {DAY_NUM} · 内容生成")
    print(f"  日期: {TODAY}  |  系列: {SERIES}")
    print(f"  标题: {POST_TITLE}  |  配色: 暖橙→淡娜")
    print(f"{'='*60}\n")

    render_all_cards()
    save_metadata()
    update_state()

    print(f"\n{'='*60}")
    print(f"  ✓ Day {DAY_NUM} 全部完成!")
    print(f"  素材目录: {img_dir}")
    print(f"  共 {len(CARDS)} 张配图")
    print(f"{'='*60}")
