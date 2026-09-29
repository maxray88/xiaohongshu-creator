"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day27.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Generate 6 Xiaohongshu cards for Day 27 and capture screenshots.
Topic: Social media comparison trap — 刷完朋友圈，我emo了一整个晚上
Color scheme: 珊瑚橘→暖杏粉 (warm sunset peach)
"""

import json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

BASE = Path("/Users/maochundong/.hermes/data/xhs_treehole")
DAY_NUM = 27
TODAY = datetime.now()
DATE_STR = TODAY.strftime("%Y-%m-%d")
DAY_DIR = BASE / f"day_{TODAY.strftime('%Y%m%d')}_day{DAY_NUM}"
IMAGES_DIR = DAY_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Topic ────────────────────────────────────────────────────────────────
TITLE = "刷完朋友圈，我emo了一整个晚上"
SERIES = "当代年轻人精神状态实录"
EMOTION_TAG = "拒绝比较"

# ─── Color Palette: 珊瑚橘→暖杏粉 (warm sunset peach) ─────────────────
C = {
    "bg_start": "#FFF5F0",
    "bg_end": "#FFE8E0",
    "card_bg": "#FFFFFFE0",
    "text_main": "#4A2E25",
    "text_sub": "#7A5A4A",
    "text_soft": "#A08070",
    "accent": "#E8735A",
    "accent_dark": "#C2513A",
    "accent_light": "#FFB5A0",
    "accent_warm": "#F09070",
    "divider": "#F5D0C0",
    "watermark": "rgba(232,115,90,0.15)",
    "shadow": "rgba(232,115,90,0.10)",
}

# ─── Card Content ─────────────────────────────────────────────────────────
CARDS = [
    # ── Card 1: Cover ──
    {
        "type": "cover",
        "lines": [
            ("tag", "情绪树洞 · 拒绝比较"),
            ("big", "刷完朋友圈"),
            ("big", "我emo了一整个晚上"),
            ("medium", "你不是一个人"),
            ("spacer", ""),
            ("body", "致深夜刷手机的每一个你"),
        ]
    },
    # ── Card 2: Scene ──
    {
        "type": "scene",
        "lines": [
            ("tag", "你也这样吗"),
            ("quote", "明明知道朋友圈都是精选片段"),
            ("quote", "还是忍不住拿自己的日常去比较"),
            ("spacer", ""),
            ("quote", "她升职了，他恋爱了"),
            ("quote", "别人的生活闪闪发光"),
            ("spacer", ""),
            ("body", "好像只有我还在原地踏步"),
        ]
    },
    # ── Card 3: Insight ──
    {
        "type": "insight",
        "lines": [
            ("tag", "一个视角"),
            ("highlight", "你不是在羡慕别人"),
            ("highlight_sub", "你只是在低估自己"),
            ("spacer", ""),
            ("body", "朋友圈是别人的展览馆"),
            ("body", "你却用后台数据要求自己"),
            ("spacer", ""),
            ("body_small", "拿自己的日常和别人的高光时刻比，永远会输"),
        ]
    },
    # ── Card 4: Method ──
    {
        "type": "method",
        "lines": [
            ("tag", "试试这样做"),
            ("step", "🌅  觉察比较的瞬间"),
            ("body", "看到动态产生焦虑时，告诉自己「我在比较了」"),
            ("spacer", ""),
            ("step", "📵  关掉手机回到现实"),
            ("body", "你的生活不在别人的镜头里，而在你的呼吸中"),
            ("spacer", ""),
            ("step", "🌟  把羡慕变成灵感"),
            ("body", "不否定渴望，但用行动代替空想"),
        ]
    },
    # ── Card 5: Gentle ──
    {
        "type": "gentle",
        "lines": [
            ("tag", "想对你说"),
            ("highlight", "你看到的美好都是真的"),
            ("highlight_sub", "但你没看到的不完美也是真的"),
            ("spacer", ""),
            ("quote", "每个人都在自己的时区里"),
            ("quote", "不快也不慢，刚刚好"),
            ("quote", "你正在成为你该成为的人"),
            ("spacer", ""),
            ("body", "别急，你的光也在亮"),
        ]
    },
    # ── Card 6: CTA ──
    {
        "type": "cta",
        "lines": [
            ("big", "今天"),
            ("medium", "你在羡慕别人的什么？"),
            ("spacer", ""),
            ("body", "在评论区写下来，然后放下手机 🫂"),
            ("spacer", ""),
            ("small", "💬 评论区等你"),
        ]
    },
]

# ─── HTML Template ────────────────────────────────────────────────────────
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
        elif line_type == "body_small":
            lines_html.append(f'<div class="small-text">{text}</div>')
        elif line_type == "step":
            lines_html.append(f'<div class="step">{text}</div>')
        elif line_type == "small":
            lines_html.append(f'<div class="small-text cta-border">{text}</div>')
        elif line_type == "spacer":
            lines_html.append(f'<div class="spacer"></div>')

    type_class = card_data["type"]
    content_block = "\n".join(lines_html)

    if type_class == "cover":
        content_wrapper = f"""
        <div class="card cover-card">
            <div class="floating-leaf leaf-1">🌅</div>
            <div class="floating-leaf leaf-2">☀️</div>
            {content_block}
        </div>
        """
    else:
        content_wrapper = f"""
        <div class="card">
            {content_block}
        </div>
        """

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
    background: linear-gradient(150deg, {C['bg_start']} 0%, {C['bg_end']} 50%, #FFF0E8 100%);
    font-family: 'PingFang SC', 'Heiti SC', 'Noto Sans SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Warm sunset blobs */
body::before {{
    content: '';
    position: absolute;
    top: -80px;
    right: -60px;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_light']}77 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -100px;
    left: -80px;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_warm']}22 0%, transparent 70%);
    pointer-events: none;
}}

/* Floating elements */
.floating-leaf {{
    position: absolute;
    font-size: 48px;
    opacity: 0.25;
    pointer-events: none;
    z-index: 0;
}}
.leaf-1 {{
    top: 30px;
    right: 40px;
    transform: rotate(15deg);
}}
.leaf-2 {{
    bottom: 40px;
    left: 30px;
    transform: rotate(-10deg);
}}

.card {{
    position: relative;
    width: 860px;
    padding: 50px 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 2;
    background: {C['card_bg']};
    border-radius: 32px;
    box-shadow: 0 8px 40px {C['shadow']}, 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid {C['divider']}66;
}}

/* Left decorative stripe */
.card::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 40px;
    bottom: 40px;
    width: 4px;
    background: linear-gradient(180deg, {C['accent_light']}, {C['accent']});
    border-radius: 4px;
}}

.tag {{
    font-size: 18px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 3px;
    margin-bottom: 20px;
    margin-top: 4px;
    opacity: 0.8;
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
    color: {C['accent']};
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
    border: 2px solid {C['accent']}44;
    border-radius: 40px;
    color: {C['accent']};
    font-weight: 500;
    font-size: 22px;
    letter-spacing: 4px;
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
</style>
</head>
<body class="{type_class}-body">
    {content_wrapper}
    <div class="watermark">情绪树洞 · {DATE_STR}</div>
</body>
</html>"""


# ─── Generate HTML + Screenshot ─────────────────────────────────────────―
def main():
    print("=" * 60)
    print(f"Day {DAY_NUM}: {TITLE}")
    print(f"Color scheme: 珊瑚橘→暖杏粉")
    print(f"Date: {DATE_STR}")
    print("=" * 60)

    print(f"\n[1/5] Creating directory: {DAY_DIR}/")
    print(f"    Images: {IMAGES_DIR}/")

    print("\n[2/5] Generating 6 HTML cards...")
    slug_map = ["cover", "scene", "insight", "method", "gentle", "cta"]
    html_files = []
    for i, card in enumerate(CARDS):
        slug = slug_map[i]
        html = make_html(i, card)
        html_path = IMAGES_DIR / f"card_{i+1}_{slug}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        html_files.append(html_path)
        print(f"  ✓ {html_path.name}")

    print("\n[3/5] Capturing screenshots with Playwright...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1080, "height": 1440},
                device_scale_factor=2,
            )
            page = context.new_page()

            for i, html_path in enumerate(html_files):
                img_name = f"card_{i+1}_{slug_map[i]}.jpg"
                img_path = IMAGES_DIR / img_name
                print(f"  Capturing {html_path.name} → {img_name}")
                page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
                page.wait_for_timeout(2000)
                page.screenshot(path=str(img_path), full_page=False, quality=95)
                size = os.path.getsize(str(img_path))
                print(f"    Saved: {size / 1024:.1f} KB")

            browser.close()
        print("  ✓ All screenshots captured successfully")
    except Exception as e:
        print(f"  ✗ Screenshot error: {e}")
        print("  Check if playwright is installed and chromium is available.")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n[4/5] Creating metadata...")
    # Manifest
    manifest = {
        "day_num": DAY_NUM,
        "date": DATE_STR,
        "series": SERIES,
        "title": TITLE,
        "emotion_tag": EMOTION_TAG,
        "color_scheme": "珊瑚橘→暖杏粉",
        "cards": [
            {"index": i + 1, "file": f"card_{i+1}_{slug_map[i]}.jpg"}
            for i in range(6)
        ],
        "images_rendered": True,
        "generated_at": TODAY.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(DAY_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("  ✓ manifest.json")

    # Post data
    post_content = (
        "刷完朋友圈，我emo了一整个晚上。\n"
        "\n"
        "明明知道朋友圈都是精选片段，\n"
        "还是忍不住拿自己的日常去比较。\n"
        "\n"
        "她升职了，他恋爱了，\n"
        "别人的生活看起来闪闪发光，\n"
        "好像只有我还在原地踏步。\n"
        "\n"
        "你不是在羡慕别人，\n"
        "你只是在低估自己。\n"
        "\n"
        "朋友圈是别人的展览馆，\n"
        "你却用后台数据要求自己。\n"
        "拿自己的日常和别人的高光时刻比，\n"
        "永远会输。\n"
        "\n"
        "试试这样做：\n"
        "觉察比较的瞬间，对自己说「我在比较了」；\n"
        "关掉手机，回到现实；\n"
        "把羡慕变成灵感，用行动代替空想。\n"
        "\n"
        "你看到的美好都是真的，\n"
        "但你没看到的不完美也是真的。\n"
        "每个人都在自己的时区里，\n"
        "不快也不慢，刚刚好。\n"
        "\n"
        "别急，你的光也在亮。"
    )

    post_data = {
        "day_num": DAY_NUM,
        "date": DATE_STR,
        "title": TITLE,
        "series": SERIES,
        "emotion_tag": EMOTION_TAG,
        "content": post_content,
        "hashtags": [
            "#情绪树洞",
            "#当代年轻人精神状态",
            "#拒绝比较",
            "#朋友圈焦虑",
            "#治愈系",
            "#与自己和解",
            "#emo"
        ],
        "best_post_time": "21:00-23:00",
        "cover_image": "card_1_cover.jpg",
        "all_images": [c["file"] for c in manifest["cards"]],
    }
    with open(DAY_DIR / "post_data.json", "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print("  ✓ post_data.json")

    print("\n[5/5] Updating published_content.json...")
    pub_path = BASE / "published_content.json"
    try:
        with open(pub_path, "r", encoding="utf-8") as f:
            published = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        published = []
    published.append({
        "day_num": DAY_NUM,
        "title": TITLE,
        "date": DATE_STR,
    })
    with open(pub_path, "w", encoding="utf-8") as f:
        json.dump(published, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Added entry: day {DAY_NUM} - {TITLE}")

    print("\n" + "=" * 60)
    print(f"✅ Day {DAY_NUM} generation complete!")
    print(f"   Directory: {DAY_DIR}/")
    print(f"   Cards:")
    for c in manifest["cards"]:
        print(f"     {c['file']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
