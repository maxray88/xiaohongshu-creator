"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day28.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Generate 6 Xiaohongshu cards for Day 28 and capture screenshots.
Topic: 允许自己不快乐 (Allow yourself to be unhappy)
  — About the liberation of accepting negative emotions instead of toxic positivity.
Color scheme: 雾霭蓝→暖灰紫 (misty blue → warm grey-purple, gentle melancholic)
"""

import json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

BASE = Path("/Users/maochundong/.hermes/data/xhs_treehole")
DAY_NUM = 28
TODAY = datetime.now()
DATE_STR = TODAY.strftime("%Y-%m-%d")
DAY_DIR = BASE / f"day_{TODAY.strftime('%Y%m%d')}_day{DAY_NUM}"
IMAGES_DIR = DAY_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Topic ────────────────────────────────────────────────────────────────
TITLE = "允许自己不快乐"
SERIES = "情绪树洞 · 情绪自由"
EMOTION_TAG = "情绪自由"

# ─── Color Palette: 雾霭蓝→暖灰紫 (gentle melancholic) ─────────────────
C = {
    "bg_start": "#F5F0F8",
    "bg_end": "#EBE4F0",
    "card_bg": "#FFFFFFE0",
    "text_main": "#3A2E45",
    "text_sub": "#6A5E75",
    "text_soft": "#9A8EA5",
    "accent": "#7C6A9E",
    "accent_dark": "#5C4A7E",
    "accent_light": "#B8A8D0",
    "accent_warm": "#A898C0",
    "divider": "#D8D0E0",
    "watermark": "rgba(124,106,158,0.15)",
    "shadow": "rgba(124,106,158,0.10)",
}

# ─── Card Content ─────────────────────────────────────────────────────────
CARDS = [
    # ── Card 1: Cover ──
    {
        "type": "cover",
        "lines": [
            ("tag", "情绪树洞 · 情绪自由"),
            ("big", "允许自己"),
            ("big", "不快乐"),
            ("medium", "不是所有的情绪都需要被解决"),
            ("spacer", ""),
            ("body", "致被「必须开心」绑架的每一个你"),
        ]
    },
    # ── Card 2: Scene ──
    {
        "type": "scene",
        "lines": [
            ("tag", "你是否也这样"),
            ("quote", "明明很难过"),
            ("quote", "却笑着说「我没事」"),
            ("spacer", ""),
            ("quote", "收到「你要开心一点」"),
            ("quote", "反而更觉得窒息"),
            ("spacer", ""),
            ("body", "好像不快乐，就是一种失败"),
        ]
    },
    # ── Card 3: Insight ──
    {
        "type": "insight",
        "lines": [
            ("tag", "一个真相"),
            ("highlight", "快乐不是人生的默认状态"),
            ("highlight_sub", "感受才是"),
            ("spacer", ""),
            ("body", "悲伤、焦虑、疲惫、愤怒"),
            ("body", "它们不是bug，是功能"),
            ("spacer", ""),
            ("body_small", "每一种情绪都在告诉你一些事"),
        ]
    },
    # ── Card 4: Method ──
    {
        "type": "method",
        "lines": [
            ("tag", "试试这样"),
            ("step", "🌧  承认它"),
            ("body", "「我现在很难过」—— 把情绪说出来，它就失去了控制你的力量"),
            ("spacer", ""),
            ("step", "🤗  拥抱它"),
            ("body", "把手放在心口，对自己说「没关系，我陪你」"),
            ("spacer", ""),
            ("step", "🌸  放它走"),
            ("body", "情绪就像云，你不抓着它，它自然会飘走"),
        ]
    },
    # ── Card 5: Gentle ──
    {
        "type": "gentle",
        "lines": [
            ("tag", "想对你说"),
            ("highlight", "你不必一直快乐"),
            ("highlight_sub", "你只需要真实地活着"),
            ("spacer", ""),
            ("quote", "月亮有阴晴圆缺"),
            ("quote", "天气有雨雪风霜"),
            ("quote", "你有喜怒哀乐"),
            ("spacer", ""),
            ("body", "这些都是你活着的证明"),
        ]
    },
    # ── Card 6: CTA ──
    {
        "type": "cta",
        "lines": [
            ("big", "今天"),
            ("medium", "你允许自己感受什么？"),
            ("spacer", ""),
            ("body", "在评论区写下此刻真实的心情 🫂"),
            ("spacer", ""),
            ("small", "💬 评论区见"),
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
            <div class="floating-leaf leaf-1">🌙</div>
            <div class="floating-leaf leaf-2">☁️</div>
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
    background: linear-gradient(150deg, {C['bg_start']} 0%, {C['bg_end']} 50%, #F0EAF5 100%);
    font-family: 'PingFang SC', 'Heiti SC', 'Noto Sans SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Soft misty blobs */
body::before {{
    content: '';
    position: absolute;
    top: -80px;
    right: -60px;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_light']}55 0%, transparent 70%);
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
    background: radial-gradient(circle, {C['accent_warm']}33 0%, transparent 70%);
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


# ─── Generate HTML + Screenshot ──────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"Day {DAY_NUM}: {TITLE}")
    print(f"Color scheme: 雾霭蓝→暖灰紫 (misty blue → warm grey-purple)")
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
        "color_scheme": "雾霭蓝→暖灰紫",
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
        "允许自己不快乐。\n"
        "\n"
        "你有没有发现，\n"
        "我们总在对自己说「要开心一点」。\n"
        "\n"
        "难过的时候，第一反应是愧疚。\n"
        "焦虑的时候，第一反应是自责。\n"
        "生气的时候，第一反应是压抑。\n"
        "\n"
        "仿佛所有的负面情绪都是 bug，\n"
        "必须马上修复，否则就是失败。\n"
        "\n"
        "但情绪不是问题，不需要解决。\n"
        "它们只是信号，需要被听见。\n"
        "\n"
        "悲伤告诉你，你失去了什么。\n"
        "焦虑告诉你，你在乎什么。\n"
        "愤怒告诉你，你的边界被触碰了。\n"
        "疲惫告诉你，你需要休息了。\n"
        "\n"
        "你不必一直快乐。\n"
        "你只需要真实地活着。\n"
        "\n"
        "试试这样：\n"
        "承认它 → 「我现在很难过」，说出来就不可怕了；\n"
        "拥抱它 → 对自己说「没关系，我陪你」；\n"
        "放走它 → 情绪就像云，你不抓着，它自然会走。\n"
        "\n"
        "月亮有阴晴圆缺，\n"
        "天气有雨雪风霜，\n"
        "你有喜怒哀乐。\n"
        "\n"
        "这些都是你活着的证明。\n"
        "今天的你，不用开心，只需要真实。"
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
            "#情绪自由",
            "#允许自己不快乐",
            "#治愈系",
            "#与自己和解",
            "#心理成长",
            "#致自己"
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
