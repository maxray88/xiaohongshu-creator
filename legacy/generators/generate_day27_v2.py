"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day27_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 27 V2 素材生成
V1: 珊瑚橘→暖杏粉 (warm sunset peach, warm comfort)
V2: 深夜蓝→星月紫 (midnight blue → starry purple, night introspection)
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

# ─── Color Palette: 深夜蓝→星月紫 (completely different from V1's coral/apricot) ─
# V1 was warm coral/apricot → V2 is cool midnight blue / starry purple
C = {
    "bg_start": "#0B1026",        # deep midnight blue
    "bg_mid": "#1A1028",          # dark purple-blue
    "bg_end": "#0F0A1E",          # deep dark purple
    "card_bg": "rgba(20, 18, 40, 0.85)",  # translucent dark card (glassmorphism)
    "card_border": "rgba(255, 215, 0, 0.15)",  # gold border
    "text_main": "#F0E6FF",       # soft lavender-white
    "text_sub": "#B8A9D4",        # muted lavender
    "text_soft": "#8B7EAD",       # soft mauve
    "accent": "#FFD700",          # warm gold (pops against dark)
    "accent_dark": "#DAA520",     # darker gold
    "accent_light": "#FFED4A",    # bright gold highlight
    "accent_glow": "#C9A84C",     # muted gold glow
    "divider": "rgba(255, 215, 0, 0.15)",   # gold divider
    "watermark": "rgba(255, 215, 0, 0.12)",
    "shadow": "rgba(0, 0, 0, 0.4)",
    "step_accent": "#FFD700",
    "step_bg": "rgba(255, 215, 0, 0.06)",
}

# ─── V2 Content — EXACT SAME TEXT AS V1 ─────────────────────────────────
# Title matches V1 exactly
V2_TITLE = "刷完朋友圈，我emo了一整个晚上"
SERIES = "当代年轻人精神状态实录"
V2_ANGLE = "深夜星空视角 — 在安静中看见自己的光，比别人的朋友圈更亮"
EMOTION_TAG = "拒绝比较"

# Card content — verbatim from V1, only visual style changes
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

# ─── HTML Template — Completely different visual style ──────────────────
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

    # Different floating elements for V2: stars + moon instead of leaves
    if type_class == "cover":
        content_wrapper = f"""
        <div class="card cover-card">
            <div class="floating-star star-1">⭐</div>
            <div class="floating-star star-2">🌙</div>
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
    background: linear-gradient(150deg, {C['bg_start']} 0%, {C['bg_mid']} 50%, {C['bg_end']} 100%);
    font-family: 'PingFang SC', 'Heiti SC', 'Noto Sans SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Starry nebula blobs */
body::before {{
    content: '';
    position: absolute;
    top: -120px;
    right: -80px;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(100, 50, 180, 0.20) 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -120px;
    left: -80px;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(50, 60, 180, 0.15) 0%, transparent 70%);
    pointer-events: none;
}}

/* Tiny twinkling stars scattered on background */
.star-bg {{
    position: absolute;
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: rgba(255, 215, 0, 0.4);
    pointer-events: none;
    z-index: 0;
}}

/* Floating elements */
.floating-star {{
    position: absolute;
    font-size: 56px;
    opacity: 0.20;
    pointer-events: none;
    z-index: 0;
    filter: drop-shadow(0 0 20px rgba(255, 215, 0, 0.1));
}}
.star-1 {{
    top: 20px;
    right: 30px;
    transform: rotate(10deg);
    animation: twinkle 3s infinite alternate;
}}
.star-2 {{
    bottom: 30px;
    left: 20px;
    transform: rotate(-15deg);
    animation: twinkle 4s infinite alternate-reverse;
}}

@keyframes twinkle {{
    0% {{ opacity: 0.15; transform: scale(0.95); }}
    100% {{ opacity: 0.30; transform: scale(1.05); }}
}}

.card {{
    position: relative;
    width: 840px;
    padding: 50px 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 2;
    background: {C['card_bg']};
    border-radius: 28px;
    box-shadow: 0 8px 50px {C['shadow']}, 0 0 60px rgba(100, 50, 180, 0.06);
    border: 1px solid {C['card_border']};
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}}

/* Top accent glow line (replaces V1's left stripe) */
.card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 60px;
    right: 60px;
    height: 3px;
    background: linear-gradient(90deg, transparent, {C['accent']}, transparent);
    border-radius: 3px;
    opacity: 0.6;
}}

.tag {{
    font-size: 16px;
    font-weight: 500;
    color: {C['accent_light']};
    letter-spacing: 4px;
    margin-bottom: 20px;
    margin-top: 4px;
    opacity: 0.75;
    text-transform: uppercase;
}}

.big-title {{
    font-size: 54px;
    font-weight: 700;
    color: {C['text_main']};
    text-align: center;
    line-height: 1.3;
    letter-spacing: 4px;
    text-shadow: 0 0 40px rgba(255, 215, 0, 0.05);
}}

.medium-title {{
    font-size: 30px;
    font-weight: 400;
    color: {C['text_sub']};
    text-align: center;
    line-height: 1.5;
    margin-top: 8px;
    letter-spacing: 3px;
}}

.highlight {{
    font-size: 38px;
    font-weight: 600;
    color: {C['accent']};
    text-align: center;
    line-height: 1.5;
    letter-spacing: 3px;
    text-shadow: 0 0 30px rgba(255, 215, 0, 0.08);
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
    font-size: 26px;
    font-weight: 350;
    color: {C['text_main']};
    text-align: center;
    line-height: 1.8;
    letter-spacing: 2px;
    padding: 3px 0;
}}

.body-text {{
    font-size: 24px;
    font-weight: 400;
    color: {C['text_sub']};
    text-align: center;
    line-height: 1.7;
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
    display: inline-block;
    font-size: 24px;
    font-weight: 600;
    color: {C['accent']};
    text-align: left;
    width: auto;
    letter-spacing: 2px;
    padding: 8px 20px;
    margin: 4px 0;
    border-radius: 30px;
    background: {C['step_bg']};
    border: 1px solid rgba(255, 215, 0, 0.08);
}}

.spacer {{
    height: 14px;
}}

.cta-border {{
    display: inline-block;
    padding: 12px 36px;
    border: 1.5px solid rgba(255, 215, 0, 0.30);
    border-radius: 40px;
    color: {C['accent']};
    font-weight: 500;
    font-size: 22px;
    letter-spacing: 4px;
    background: rgba(255, 215, 0, 0.04);
}}

/* Watermark */
.watermark {{
    position: absolute;
    bottom: 40px;
    right: 60px;
    font-size: 15px;
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
    font-size: 58px;
    margin: 2px 0;
    color: {C['text_main']};
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

# ─── Generate HTML ──────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"Day {DAY_NUM} V2: {V2_TITLE}")
    print(f"  V1 color: 珊瑚橘→暖杏粉")
    print(f"  V2 color: 深夜蓝→星月紫 (complete visual redesign)")
    print(f"  Text: EXACT same as V1 (no rewrites)")
    print("=" * 60)

    print("\n[1/3] Generating 6 HTML cards with new visual style...")
    html_files = []
    slug_map = ["cover", "scene", "insight", "method", "gentle", "cta"]
    for i, card in enumerate(CARDS):
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
    # Manifest — title must match V1 exactly
    manifest = {
        "day_num": DAY_NUM,
        "date": TODAY_STR,
        "series": SERIES,
        "title": V2_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": EMOTION_TAG,
        "color_scheme": "深夜蓝→星月紫",
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

    # Post data
    v2_content = f"""{V2_TITLE}

明明知道朋友圈都是精选片段，
还是忍不住拿自己的日常去比较。

她升职了，他恋爱了，别人的生活闪闪发光。
好像只有我还在原地踏步。

你不是在羡慕别人，你只是在低估自己。
朋友圈是别人的展览馆，你却用后台数据要求自己。

拿自己的日常和别人的高光时刻比，永远会输。

试试这样：
觉察比较的瞬间 → 告诉自己「我在比较了」
关掉手机回到现实 → 你的生活不在别人的镜头里
把羡慕变成灵感 → 用行动代替空想

你看到的美好都是真的，但你没看到的不完美也是真的。
每个人都在自己的时区里，不快也不慢，刚刚好。
你正在成为你该成为的人，别急，你的光也在亮。

今天你在羡慕别人的什么？
在评论区写下来，然后放下手机 🫂"""

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
            "#拒绝比较",
            "#停止内耗",
            "#朋友圈焦虑",
            "#治愈系",
            "#与自己和解",
        ],
        "best_post_time": "21:00-23:00",
        "cover_image": "card_v2_1_cover.jpg",
        "all_images": [c["file"] for c in manifest["cards"]],
    }

    with open(os.path.join(day_dir, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print("  ✓ post_data.json")

    # Copy script
    script_src = os.path.abspath(__file__)
    dst_script = os.path.join(day_dir, "generate_cards.py")
    if os.path.exists(script_src):
        shutil.copy2(script_src, dst_script)
        print(f"  ✓ Copied script to {dst_script}")

    print(f"\n{'=' * 60}")
    print(f"✓ Day {DAY_NUM} V2 complete! 6 cards rendered.")
    print(f"  Dir: {day_dir}")
    print(f"  Color: 深夜蓝→星月紫 (vs V1: 珊瑚橘→暖杏粉)")
    print(f"  Text: EXACT same as V1 ✓")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
