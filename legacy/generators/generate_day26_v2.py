"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day26_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 26 V2 素材生成
V1: 深蓝→暮光紫 (dark night, cool, "允许自己不稳定")
V2: 薄荷绿→雾灰绿 (fresh day, natural, "与情绪做朋友")
"""
import json, os, glob, sys
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
    # Fallback: scan all manifests
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

# ─── Color Palette: 薄荷绿→雾灰绿 (completely different from V1) ─────
# V1 was deep blue/purple night mood → V2 is fresh mint/sage daytime calm
C = {
    "bg_start": "#E8F5E9",        # soft mint white
    "bg_end": "#C8E6C9",          # light mint
    "card_bg": "#FFFFFFE0",       # white card
    "text_main": "#1B3A2D",       # deep forest green
    "text_sub": "#4A6B5D",        # medium sage
    "text_soft": "#7B9A8A",       # soft muted green
    "accent": "#2E7D32",          # forest green
    "accent_dark": "#1B5E20",     # deep green
    "accent_light": "#A5D6A7",    # light mint
    "accent_warm": "#66BB6A",     # vibrant green
    "divider": "#C8E6C9",        # mint divider
    "watermark": "rgba(46,125,50,0.18)",
    "shadow": "rgba(46,125,50,0.08)",
}

# ─── V2 Content ─────────────────────────────────────────────────────────
V2_TITLE = "情绪像天气，阴晴都是风景"
SERIES = "当代年轻人精神状态实录"
V2_ANGLE = "情绪不是敌人是信使 — 从「对抗情绪」到「与情绪共处」"
EMOTION_TAG = "情绪自由"

CARDS = [
    # ── Card 1: Cover ──
    {
        "type": "cover",
        "lines": [
            ("tag", "情绪树洞 · 情绪自由"),
            ("big", "情绪像天气"),
            ("big", "阴晴都是风景"),
            ("medium", "不必永远晴空万里"),
            ("spacer", ""),
            ("body", "致今天心情不太好的你"),
        ]
    },
    # ── Card 2: Scene ──
    {
        "type": "scene",
        "lines": [
            ("tag", "日常碎片"),
            ("quote", "早上还能正常出门"),
            ("quote", "下午突然什么都不想做了"),
            ("spacer", ""),
            ("quote", "别人问怎么了"),
            ("quote", "说不上来，就是不太对"),
            ("spacer", ""),
            ("body", "情绪就是这样，从不需要理由"),
        ]
    },
    # ── Card 3: Insight ──
    {
        "type": "insight",
        "lines": [
            ("tag", "一个视角"),
            ("highlight", "你不需要控制情绪"),
            ("spacer", ""),
            ("body", "焦虑 → 是身体在说「我在乎」"),
            ("body", "悲伤 → 是内心在说「我需要休息」"),
            ("body", "烦躁 → 是直觉在说「边界被触碰了」"),
            ("spacer", ""),
            ("body_small", "每一种情绪都是信息的传递"),
        ]
    },
    # ── Card 4: Method ──
    {
        "type": "method",
        "lines": [
            ("tag", "试试这样做"),
            ("step", "🌱  停下来，觉察"),
            ("body", "深呼吸三次，问自己：「我现在感受到什么？」"),
            ("spacer", ""),
            ("step", "🍃  接纳它存在"),
            ("body", "不用赶走它，也不用分析它，只是承认「它在这里」"),
            ("spacer", ""),
            ("step", "☀️  温柔放手"),
            ("body", "想象情绪像一片云，你只是看着它飘过"),
        ]
    },
    # ── Card 5: Gentle ──
    {
        "type": "gentle",
        "lines": [
            ("tag", "想对你说"),
            ("highlight", "你的情绪波动"),
            ("highlight_sub", "证明你是一个鲜活的人"),
            ("spacer", ""),
            ("quote", "快乐的时候尽情快乐"),
            ("quote", "难过的时候允许难过"),
            ("quote", "「正常」不是唯一的活法"),
            ("spacer", ""),
            ("body", "你有权利用自己的节奏活着"),
        ]
    },
    # ── Card 6: CTA ──
    {
        "type": "cta",
        "lines": [
            ("big", "今天"),
            ("medium", "你的情绪是什么形状？"),
            ("spacer", ""),
            ("body", "在评论区用一句话描述 🫂"),
            ("spacer", ""),
            ("small", "💬 评论区等你"),
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

    # Cover has special centering
    if type_class == "cover":
        content_wrapper = f"""
        <div class="card cover-card">
            <div class="floating-leaf leaf-1">🍃</div>
            <div class="floating-leaf leaf-2">🌿</div>
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
    background: linear-gradient(150deg, {C['bg_start']} 0%, {C['bg_end']} 50%, #F1F8E9 100%);
    font-family: 'PingFang SC', 'Heiti SC', 'Noto Sans SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Organic botanical blobs */
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

/* Floating leaves */
.floating-leaf {{
    position: absolute;
    font-size: 48px;
    opacity: 0.3;
    pointer-events: none;
    z-index: 0;
}}
.leaf-1 {{
    top: 30px;
    right: 40px;
    transform: rotate(30deg);
}}
.leaf-2 {{
    bottom: 40px;
    left: 30px;
    transform: rotate(-20deg);
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
    <div class="watermark">情绪树洞 · {TODAY_STR}</div>
</body>
</html>"""

# ─── Generate HTML + Screenshot ─────────────────────────────────────────
def main():
    print("=" * 60)
    print("Day 26 V2: 情绪像天气，阴晴都是风景")
    print(f"Color scheme: 薄荷绿→雾灰绿 (vs V1 深蓝→暮光紫)")
    print(f"V2 angle: {V2_ANGLE}")
    print("=" * 60)

    print("\n[1/3] Generating 6 HTML cards...")
    html_files = []
    for i, card in enumerate(CARDS):
        slug_map = ["cover", "scene", "insight", "method", "gentle", "cta"]
        slug = slug_map[i]
        html = make_html(i, card)
        html_path = os.path.join(img_dir, f"card_v2_{i+1}_{slug}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        html_files.append(html_path)
        print(f"  ✓ {html_path}")

    print("\n[2/3] Capturing screenshots with Playwright...")
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
                slug_map = ["cover", "scene", "insight", "method", "gentle", "cta"]
                img_name = f"card_v2_{i+1}_{slug_map[i]}.jpg"
                img_path = os.path.join(img_dir, img_name)

                print(f"  Capturing {os.path.basename(html_path)} → {img_name}")
                page.goto(f"file://{os.path.abspath(html_path)}", wait_until="networkidle")
                page.wait_for_timeout(2000)
                page.screenshot(path=img_path, full_page=False, quality=95)

                size = os.path.getsize(img_path)
                print(f"    Saved: {size / 1024:.1f} KB")

            browser.close()
        print("  ✓ All screenshots captured successfully")
    except Exception as e:
        print(f"  ✗ Screenshot error: {e}")
        print("  Check if playwright is installed and chromium is available.")
        sys.exit(1)

    print("\n[3/3] Creating metadata...")
    # Manifest
    slug_map = ["cover", "scene", "insight", "method", "gentle", "cta"]
    manifest = {
        "day_num": DAY_NUM,
        "date": TODAY_STR,
        "series": SERIES,
        "title": V2_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": EMOTION_TAG,
        "color_scheme": "薄荷绿→雾灰绿",
        "v2_of": f"day_{TODAY_FS}_day{DAY_NUM}",
        "renderer": "html-fallback",
        "cards": [
            {
                "index": i + 1,
                "file": f"card_v2_{i+1}_{slug_map[i]}.jpg",
            }
            for i in range(6)
        ],
        "images_rendered": True,
        "generated_at": TODAY.isoformat(),
    }

    with open(os.path.join(day_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("  ✓ manifest.json")

    # Post data (for posting if needed)
    v2_content = f"""{V2_TITLE}

早上还能正常出门，
下午突然什么都不想做了。
别人问怎么了，
说不上来，就是不太对。

情绪就是这样，从不需要理由。

你不需要控制情绪。
焦虑，是身体在说「我在乎」。
悲伤，是内心在说「我需要休息」。
烦躁，是直觉在说「边界被触碰到」。
每一种情绪，都是信息的传递。

停下来，觉察它。
接纳它存在。
再温柔地放手。

情绪像天气，阴晴都是风景。
你不必永远晴空万里。

今天你的情绪是什么形状？
在评论区告诉我吧 🫂"""

    post_data = {
        "day_num": DAY_NUM,
        "date": TODAY_STR,
        "title": V2_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": EMOTION_TAG,
        "series": SERIES,
        "content": v2_content,
        "hashtags": [
            "#情绪树洞",
            "#当代年轻人精神状态",
            "#情绪自由",
            "#情绪管理",
            "#治愈系",
            "#与自己和解",
            "#精神状态",
        ],
        "best_post_time": "21:00-23:00",
        "cover_image": "card_v2_1_cover.jpg",
        "all_images": [c["file"] for c in manifest["cards"]],
    }

    with open(os.path.join(day_dir, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print("  ✓ post_data.json")

    # Save a copy of this script as generate_cards.py in the v2 dir
    script_src = os.path.abspath(__file__)
    dst_script = os.path.join(day_dir, "generate_cards.py")
    if os.path.exists(script_src):
        import shutil
        shutil.copy2(script_src, dst_script)
        print(f"  ✓ Copied script to {dst_script}")

    print(f"\n{'=' * 60}")
    print(f"✓ Day {DAY_NUM} V2 complete! 6 cards rendered.")
    print(f"  Dir: {day_dir}")
    print(f"  Color: 薄荷绿→雾灰绿")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
