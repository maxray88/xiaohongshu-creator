"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day17.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 17 自动化内容生成
Topic: 内向的人，不需要变外向 (社交焦虑自救)
Color Scheme: 深蓝→暮光紫
"""
import json
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# ─── Paths ───────────────────────────────────────────────────────────────
BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
STATE_FILE = os.path.join(BASE, "current_day.txt")

# Double-check day number from state file + scanned manifests
def determine_day():
    # Read state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            last_day = int(f.read().strip())
    else:
        last_day = 0
    
    # Scan existing manifests
    import glob
    scanned_max = 0
    for mf in glob.glob(os.path.join(BASE, "day_*/manifest.json")):
        try:
            with open(mf) as f:
                data = json.load(f)
                dn = data.get("day_num", 0)
                if dn > scanned_max:
                    scanned_max = dn
        except:
            pass
    
    day = max(last_day, scanned_max) + 1
    return day, last_day, scanned_max

DAY_NUM, last_day, scanned_max = determine_day()
TODAY = datetime.now().strftime("%Y%m%d")

day_dir = os.path.join(BASE, f"day_{TODAY}_day{DAY_NUM}")
img_dir = os.path.join(day_dir, "images")
os.makedirs(img_dir, exist_ok=True)

# ─── Color Palette: 深蓝→暮光紫 ────────────────────────────────────────
C = {
    "bg_start": "#0F172A",
    "bg_end": "#1E1B4B",
    "card_bg": "#1A1B3A",
    "text_main": "#E8E0F0",
    "text_sub": "#B8B0D0",
    "text_soft": "#8880AA",
    "accent": "#A78BFA",
    "accent_dark": "#C4B5FD",
    "accent_light": "#2D2B5A",
    "divider": "#3D3B6A",
    "watermark": "rgba(167,139,250,0.20)",
}

# ─── Content Definition ─────────────────────────────────────────────────
POST_TITLE = "内向的人，不需要变外向"
SERIES = "社交焦虑自救"
SERIES_TAG = "内向力量"

CARDS = [
    {
        "type": "cover",
        "lines": [
            ("tag", SERIES),
            ("big", "内向的人"),
            ("medium", "不需要变外向"),
        ]
    },
    {
        "type": "scene",
        "lines": [
            ("tag", "你是否有过这样的时刻"),
            ("quote", '\u201c你怎么不说话？\u201d'),
            ("quote", '\u201c性格要开朗一点嘛\u201d'),
            ("quote", '\u201c多出去走走就好了\u201d'),
            ("spacer", ""),
            ("body", "你努力模仿外向的人"),
            ("body", "但每次社交过后，都疲惫不堪"),
        ]
    },
    {
        "type": "insight",
        "lines": [
            ("tag", "不用改变"),
            ("highlight", "内向不是缺陷"),
            ("highlight_sub", "是上天给你的礼物"),
            ("spacer", ""),
            ("body", "你的安静，是一种力量"),
            ("body", "你的独处，是一种滋养"),
        ]
    },
    {
        "type": "method",
        "lines": [
            ("tag", "接纳自己"),
            ("step", "享受独处时光"),
            ("body", "读书、写字、听歌，都是你的充电方式。"),
            ("spacer", ""),
            ("step", "不需要为沉默道歉"),
            ("body", "不想说话的时候，温柔地笑一笑就好。"),
            ("spacer", ""),
            ("step", "保护自己的能量边界"),
            ("body", "选择让你舒服的社交，拒绝消耗你的场合。"),
        ]
    },
    {
        "type": "gentle",
        "lines": [
            ("tag", "要记住"),
            ("highlight", "你不需要变成"),
            ("highlight", "别人期待的样子"),
            ("spacer", ""),
            ("quote", "你的内向，让你的内心世界无比丰盈"),
            ("quote", "你在自己的节奏里，闪闪发光"),
        ]
    },
    {
        "type": "cta",
        "lines": [
            ("big", "内向的人"),
            ("medium", "不需要变外向"),
            ("spacer", ""),
            ("body", "做自己就好"),
            ("body", "你的安静，也是你独有的光芒"),
            ("spacer", ""),
            ("small", "评论区说说你的故事"),
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
            if text:
                lines_html.append(f'<div class="quote">{text}</div>')
            else:
                lines_html.append(f'<div class="spacer"></div>')
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

/* Decorative background - star-like dots for depth */
body::before {{
    content: '';
    position: absolute;
    top: -200px;
    right: -200px;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_light']}66 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -150px;
    left: -150px;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent']}33 0%, transparent 70%);
    pointer-events: none;
}}

/* Subtle dot pattern overlay */
.dot-overlay {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image: radial-gradient({C['accent']}11 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 1;
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
    background: {C['accent']}88;
    border-radius: 2px;
}}

/* Decorative bottom accent */
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
    text-shadow: 0 0 10px {C['accent']}33;
}}

.big-title {{
    font-size: 96px;
    font-weight: 700;
    color: {C['text_main']};
    letter-spacing: 10px;
    line-height: 1.3;
    text-align: center;
    margin-bottom: 18px;
    text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}}

.medium-title {{
    font-size: 44px;
    font-weight: 500;
    color: {C['text_sub']};
    letter-spacing: 6px;
    line-height: 1.5;
    text-align: center;
    margin-top: 4px;
    text-shadow: 0 1px 10px rgba(0,0,0,0.2);
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
    text-shadow: 0 0 15px {C['accent']}44;
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
    color: {C['accent_dark']};
    letter-spacing: 4px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 18px;
    text-shadow: 0 0 10px {C['accent']}33;
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
    background: {C['accent_light']}66;
    border-radius: 12px;
    text-align: center;
    width: 100%;
    border: 1px solid {C['accent']}33;
}}
.insight .highlight-sub {{
    margin-top: 8px;
}}

.method .step {{
    color: {C['accent_dark']};
}}
.method .body-text {{
    margin-bottom: 8px;
}}

.gentle .highlight {{
    font-size: 44px;
    color: {C['accent_dark']};
    margin-bottom: 28px;
    text-shadow: 0 0 20px {C['accent']}55;
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
.cta .small-text {{
    margin-top: 10px;
    padding: 8px 24px;
    border: 1px solid {C['accent']}55;
    border-radius: 28px;
    color: {C['accent']};
}}
</style>
</head>
<body>
<div class="dot-overlay"></div>
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
            page.wait_for_timeout(1000)
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
    "color_scheme": "深蓝→暮光紫",
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
    "内向的人，不需要变外向\n\n"
    "你是否有过这样的时刻：\n"
    '\u201c你怎么不说话？\u201d \u2014 \u201c性格要开朗一点嘛\u201d \u2014 \u201c多出去走走就好了\u201d\n'
    "你努力模仿外向的人，但每次社交过后，都疲惫不堪。\n\n"
        "内向不是缺陷，是上天给你的礼物。\n"
        "你的安静，是一种力量。\n"
        "你的独处，是一种滋养。\n\n"
        "接纳自己：\n"
        "享受独处时光 — 读书、写字、听歌，都是你的充电方式。\n"
        "不需要为沉默道歉 — 不想说话的时候，温柔地笑一笑就好。\n"
        "保护自己的能量边界 — 选择让你舒服的社交，拒绝消耗你的场合。\n\n"
        "你不需要变成别人期待的样子。\n"
        "你的内向，让你的内心世界无比丰盈。\n"
        "你在自己的节奏里，闪闪发光。\n\n"
        "内向的人，不需要变外向。\n"
        "做自己就好。\n"
        "你的安静，也是你独有的光芒。"
    ),
    "hashtags": [
        "#社交焦虑自救", "#内向力量", "#情绪树洞", "#社恐不是病",
        "#内向的人不需要变外向", "#治愈系", "#自我接纳", "#心灵鸡汤"
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
    print(f"  标题: {POST_TITLE}  |  配色: 深蓝→暮光紫")
    print(f"  双重校验: state={last_day}, scanned_max={scanned_max}")
    print(f"{'='*60}\n")

    render_all_cards()
    save_metadata()
    update_state()

    print(f"\n{'='*60}")
    print(f"  ✓ Day {DAY_NUM} 全部完成!")
    print(f"  素材目录: {img_dir}")
    print(f"  共 {len(CARDS)} 张配图")
    print(f"{'='*60}")
