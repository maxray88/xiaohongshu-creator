"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day12_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 12 V2 (第二版差异化配图)
Topic: 恋爱脑清醒指南 (恋爱清醒脑)
Color Scheme v2: 暗夜深蓝 → 琥珀金 (与 v1 柔粉完全相反)
Renderer: html-fallback
"""
import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

# ─── Paths ───────────────────────────────────────────────────────────────
BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
TODAY = datetime.now().strftime("%Y%m%d")
DAY_NUM = 12

day_dir = os.path.join(BASE, f"day_{TODAY}_day{DAY_NUM}_v2")
img_dir = os.path.join(day_dir, "images")
os.makedirs(img_dir, exist_ok=True)

# ─── Color Palette v2: 暗夜深蓝 → 琥珀金 ────────────────────────────────
# Opposite of v1's soft pink/cream — dark, dramatic, auroral
C = {
    "bg_start": "#0F0C29",
    "bg_mid": "#1A1A3E",
    "bg_end": "#24243E",
    "text_main": "#F5E6D3",
    "text_sub": "#B8A99A",
    "text_soft": "#8A7D6F",
    "accent": "#E8B840",      # amber gold
    "accent_dark": "#C49428",  # darker gold
    "accent_glow": "#E8B84022",  # very faint gold glow
    "divider": "#3A2A1A44",
    "watermark": "rgba(200,180,150,0.18)",
    "navy_dark": "#0A0817",
    "line_accent": "#E8B84033",
}

# ─── V2 Copy Angle: "主权自我" (self-sovereignty) ──────────────────────
# Same core message, but framed as empowerment / reclaiming self-agency
# instead of v1's softer "awakening" tone

CARDS = [
    {
        "type": "cover",
        "lines": [
            ("tag", "\u604b\u7231\u6e05\u9192\u8111"),
            ("big", "\u4f60\u7684\u4eba\u751f"),
            ("big_sub", "\u4f60\u4e3b\u5bfc"),
            ("medium", "\u522b\u628a\u5fc3\u4ea4\u7ed9\u522b\u4eba\u4f60\u7684\u559c\u60b2"),
            ("body", "\u2014\u2014 \u604b\u7231\u8111\u6e05\u9192\u6307\u5357 \u2014\u2014"),
        ]
    },
    {
        "type": "scene",
        "lines": [
            ("tag", "\u505c\u6b62\u81ea\u6211\u6d88\u8017"),
            ("highlight", "\u4f60\u662f\u5426\u66fe\u7ecf\u8fd9\u6837\uff1a"),
            ("body", "\u7ffb\u5b8c\u4ed6\u7684\u793e\u4ea4\u5a92\u4f53\u540e"),
            ("body", "\u5728\u6df1\u591c\u91cc\u96be\u8fc7\u5230\u7761\u4e0d\u7740\uff1b"),
            ("body", "\u7b49\u4ed6\u7684\u6d88\u606f\u7b49\u5230\u592a\u9633\u5347\u8d77\uff1b"),
            ("body", "\u628a\u4ed6\u7684\u4e00\u4e3e\u4e00\u52a8\u5f53\u6210\u4f60\u7684\u60c5\u7eea\u6307\u5357\u3002"),
            ("spacer", ""),
            ("body", "\u8fd9\u4e0d\u662f\u7231\uff0c\u8fd9\u662f\u60c5\u611f\u4f9d\u8d56\u3002"),
        ]
    },
    {
        "type": "insight",
        "lines": [
            ("tag", "\u771f\u76f8\u5f88\u6b8b\u9177"),
            ("big", "\u4f60\u7740\u8ff7\u7684\u4e0d\u662f\u4ed6"),
            ("big_sub", "\u662f\u201c\u88ab\u91cd\u89c6\u201d\u7684\u5e7b\u89c9"),
            ("divider", ""),
            ("body", "\u604b\u7231\u8111\u7684\u672c\u8d28\uff0c\u662f\u4f60\u628a\u81ea\u5df1\u7684\u4ef7\u503c"),
            ("body", "\u4ea4\u7ed9\u4e86\u4e00\u4e2a\u4e0d\u4f1a\u8bfb\u7684\u4eba\u3002"),
            ("spacer", ""),
            ("highlight", "\u4f60\u7684\u5feb\u4e50\u4e0d\u5e94\u8be5\u6709\u4eba\u7b7e\u6536\u6743"),
        ]
    },
    {
        "type": "method",
        "lines": [
            ("tag", "\u62ff\u56de\u4e3b\u52a8\u6743"),
            ("big", "3\u6b65\u201c\u8131\u7740\u201d\u8ba1\u5212"),
            ("spacer", ""),
            ("step", "01 \u505a\u56de\u4f60\u7684\u4e3b\u89d2"),
            ("body", "\u4ed6\u53ea\u662f\u4f60\u4eba\u751f\u5267\u60c5\u7684\u914d\u89d2\uff0c"),
            ("body", "\u522b\u8ba9\u914d\u89d2\u62ff\u4e3b\u89d2\u7684\u5267\u672c\u3002"),
            ("spacer", ""),
            ("step", "02 \u7ed9\u60c5\u7eea\u88c5\u4e2a\u201c\u622a\u6b62\u65e5\u671f\u201d"),
            ("body", "\u6bcf\u5929\u53ea\u7ed9\u4ed6\u5341\u5206\u949f\u7684\u60c5\u7eea\u5e2d\u4f4d\uff0c"),
            ("body", "\u5230\u65f6\u5c31\u6536\u56de\u3002"),
            ("spacer", ""),
            ("step", "03 \u91cd\u5efa\u4f60\u7684\u4e16\u754c\u5730\u56fe"),
            ("body", "\u628a\u66fe\u7ecf\u7528\u6765\u60e3\u5ff5\u4ed6\u7684\u65f6\u95f4\uff0c"),
            ("body", "\u7528\u6765\u53d8\u5f97\u66f4\u5f3a\u5927\u3002"),
        ]
    },
    {
        "type": "gentle",
        "lines": [
            ("tag", "\u7ed9\u4f60\u4e00\u4e2a\u62e5\u62b1"),
            ("highlight", "\u4f60\u5df2\u7ecf\u8db3\u591f\u597d\u4e86"),
            ("body", "\u4e0d\u662f\u56e0\u4e3a\u4ed6\u559c\u6b22\u4f60\uff0c\u4f60\u624d\u6709\u4ef7\u503c\u3002"),
            ("body", "\u662f\u56e0\u4e3a\u4f60\u6709\u4ef7\u503c\uff0c\u4ed6\u7684\u559c\u6b22\u624d\u683c\u5916\u73cd\u8d35\u3002"),
            ("spacer", ""),
            ("body", "\u7b49\u4f60\u771f\u6b63\u81ea\u5df1\u7684\u65f6\u5019\uff0c"),
            ("body", "\u7231\u60c5\u4e0d\u662f\u201c\u5fc5\u987b\u201d\uff0c\u662f\u201c\u6dfb\u5934\u201d\u3002"),
        ]
    },
    {
        "type": "cta",
        "lines": [
            ("tag", "\u4eca\u5929\u5c31\u505a\u51b3\u5b9a"),
            ("big", "\u9009\u62e9\u81ea\u5df1"),
            ("medium", "\u800c\u4e0d\u662f\u9009\u62e9\u88ab\u9009\u62e9"),
            ("spacer", ""),
            ("body", "\u4f60\u503c\u5f97\u7684\u662f \u201c\u5b9a\u4e0b\u6765\u201d"),
            ("body", "\u800c\u4e0d\u662f\u201c\u8dd1\u6765\u8dd1\u53bb\u201d\u3002"),
            ("divider", ""),
            ("small", "\u4f60\u662f\u54ea\u4e00\u5929\u5f00\u59cb\u6e05\u9192\u7684\uff1f"),
        ]
    },
]


# ─── HTML Template v2: 暗夜深蓝 + 琥珀金 几何风格 ────────────────────
def make_html(card_idx, card_data):
    lines_html = []
    for line_type, text in card_data["lines"]:
        if line_type == "tag":
            lines_html.append(f'<div class="tag">{text}</div>')
        elif line_type == "big":
            lines_html.append(f'<div class="big-title">{text}</div>')
        elif line_type == "big_sub":
            lines_html.append(f'<div class="big-title sub">{text}</div>')
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
        elif line_type == "divider":
            lines_html.append(f'<div class="divider-line"></div>')

    type_class = card_data["type"]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;350;400;500;700;900&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(170deg, {C['bg_start']} 0%, {C['bg_mid']} 50%, {C['bg_end']} 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    position: relative;
    overflow: hidden;
}}

/* Geometric decorative elements — sharp triangles/corners instead of circles */
body::before {{
    content: '';
    position: absolute;
    top: -60px;
    right: -60px;
    width: 300px;
    height: 300px;
    border: 2px solid {C['line_accent']};
    transform: rotate(45deg);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: 100px;
    right: -100px;
    width: 500px;
    height: 500px;
    border: 1px solid {C['line_accent']};
    border-radius: 0;
    transform: rotate(30deg);
    pointer-events: none;
}}

/* Subtle top-right triangle accent */
.tri-accent {{
    position: absolute;
    top: 40px;
    right: 40px;
    width: 0;
    height: 0;
    border-left: 60px solid transparent;
    border-right: 60px solid transparent;
    border-bottom: 80px solid {C['accent_glow']};
    pointer-events: none;
    z-index: 0;
}}

/* Bottom line accent */
.line-accent {{
    position: absolute;
    bottom: 80px;
    left: 60px;
    width: 120px;
    height: 2px;
    background: {C['accent']};
    opacity: 0.25;
    z-index: 0;
}}

.card {{
    position: relative;
    width: 880px;
    padding: 60px 60px 60px 70px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    z-index: 2;
}}

/* Left border accent line instead of top */
.card::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 10%;
    height: 80%;
    width: 3px;
    background: linear-gradient(to bottom, {C['accent']}99, {C['accent_glow']}, transparent);
    border-radius: 2px;
}}

.watermark {{
    position: absolute;
    bottom: 36px;
    right: 46px;
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
    font-size: 20px;
    font-weight: 400;
    color: {C['accent']};
    letter-spacing: 5px;
    margin-bottom: 32px;
    padding: 0 0 8px 0;
    border-bottom: 2px solid {C['accent']}55;
    text-transform: uppercase;
}}

.big-title {{
    font-size: 90px;
    font-weight: 900;
    color: {C['text_main']};
    letter-spacing: 8px;
    line-height: 1.2;
    text-align: left;
    margin-bottom: 6px;
}}

.big-title.sub {{
    font-size: 72px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 6px;
    margin-bottom: 24px;
}}

.medium-title {{
    font-size: 38px;
    font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: left;
    margin-top: 8px;
}}

.highlight {{
    font-size: 38px;
    font-weight: 700;
    color: {C['accent']};
    letter-spacing: 3px;
    line-height: 1.7;
    text-align: left;
    margin-bottom: 14px;
    width: 100%;
}}

.highlight-sub {{
    font-size: 30px;
    font-weight: 500;
    color: {C['accent_dark']};
    letter-spacing: 2px;
    line-height: 1.6;
    text-align: left;
}}

.quote {{
    font-size: 28px;
    font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 3px;
    line-height: 1.9;
    text-align: left;
    margin-bottom: 4px;
}}

.body-text {{
    font-size: 26px;
    font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: left;
    margin-bottom: 4px;
}}

.step {{
    font-size: 34px;
    font-weight: 600;
    color: {C['accent']};
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: left;
    margin-bottom: 10px;
}}

.small-text {{
    font-size: 22px;
    font-weight: 300;
    color: {C['text_soft']};
    letter-spacing: 2px;
    text-align: left;
}}

.spacer {{
    height: 18px;
}}

.divider-line {{
    width: 60px;
    height: 1px;
    background: {C['accent']}55;
    margin: 8px 0;
}}

/* ─── Per-type adjustments ─── */

.cover .big-title {{
    font-size: 100px;
    letter-spacing: 12px;
}}
.cover .big-title.sub {{
    font-size: 80px;
    margin-bottom: 18px;
}}
.cover .medium-title {{
    font-size: 30px;
    color: {C['text_soft']};
}}
.cover .body-text {{
    font-size: 22px;
    color: {C['accent']}88;
    letter-spacing: 6px;
    margin-top: 16px;
}}

.scene .highlight {{
    font-size: 36px;
    margin-bottom: 20px;
    color: {C['text_main']};
}}
.scene .body-text {{
    font-size: 26px;
    color: {C['text_sub']};
}}

.insight .big {{
    color: {C['text_main']};
}}
.insight .big-title.sub {{
    font-size: 52px;
    color: {C['accent']};
    margin-bottom: 16px;
}}
.insight .highlight {{
    font-size: 32px;
    padding: 16px 24px;
    background: {C['accent_glow']};
    border-left: 3px solid {C['accent']};
    width: 100%;
    color: {C['accent']};
}}

.method .big-title {{
    font-size: 72px;
    margin-bottom: 10px;
    color: {C['accent']};
}}
.method .step {{
    font-size: 32px;
    color: {C['accent_dark']};
    border-left: 2px solid {C['accent']}44;
    padding-left: 18px;
}}
.method .body-text {{
    font-size: 24px;
    color: {C['text_sub']};
    padding-left: 20px;
}}

.gentle .highlight {{
    font-size: 38px;
    color: {C['accent']};
    margin-bottom: 24px;
}}
.gentle .body-text {{
    font-size: 26px;
}}

.cta .big-title {{
    font-size: 96px;
    letter-spacing: 14px;
    color: {C['text_main']};
    margin-bottom: 4px;
}}
.cta .medium-title {{
    font-size: 34px;
    color: {C['accent']};
    margin-bottom: 20px;
}}
.cta .body-text {{
    font-size: 28px;
    color: {C['text_sub']};
}}
.cta .small-text {{
    margin-top: 12px;
    padding: 8px 24px;
    border: 1px solid {C['accent']}55;
    border-radius: 0;
    color: {C['accent']}BB;
}}
</style>
</head>
<body>
<div class="tri-accent"></div>
<div class="line-accent"></div>
<div class="card {type_class}">
    {''.join(lines_html)}
</div>
<div class="watermark">@情绪树洞 · v2 · {TODAY}</div>
<div class="page-num">{card_idx + 1} / {len(CARDS)}</div>
</body>
</html>"""
    return html


# ─── Screenshot ─────────────────────────────────────────────────────────
def render_all_cards():
    print(f"[Render] Starting Playwright rendering (v2)...\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,
        )
        for idx, card in enumerate(CARDS):
            html_content = make_html(idx, card)
            html_path = os.path.join(img_dir, f"card_v2_{idx+1}.html")
            jpg_path = os.path.join(img_dir, f"card_v2_{idx+1}.jpg")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            page = context.new_page()
            page.goto(f"file://{html_path}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=jpg_path, full_page=False, type="jpeg", quality=95)
            page.close()

            img_size_kb = os.path.getsize(jpg_path) / 1024
            print(f"  [{idx+1}/{len(CARDS)}] card_v2_{idx+1}.jpg  ({img_size_kb:.0f} KB)")

        browser.close()
    print(f"\n[Render] All {len(CARDS)} v2 cards saved to: {img_dir}")


# ─── Metadata ───────────────────────────────────────────────────────────
MANIFEST = {
    "day_num": DAY_NUM,
    "date": TODAY,
    "series": "恋爱清醒脑",
    "title": "恋爱脑清醒指南",
    "emotion_tag": "清醒恋爱",
    "color_scheme": "暗夜深蓝→琥珀金",
    "v2_of": f"day_{TODAY}_day{DAY_NUM}",
    "renderer": "html-fallback",
    "cards": [
        {"index": i+1, "type": c["type"], "file": f"card_v2_{i+1}.jpg"}
        for i, c in enumerate(CARDS)
    ],
    "images_rendered": True,
    "generated_at": datetime.now().isoformat(),
}

POST_DATA = {
    "platform": "xiaohongshu",
    "day_num": DAY_NUM,
    "date": TODAY,
    "series": "恋爱清醒脑",
    "title": "恋爱脑清醒指南",
    "emotion_tag": "清醒恋爱",
    "version": "v2",
    "renderer": "html-fallback",
    "color_scheme": "暗夜深蓝→琥珀金",
    "content_v2_angle": "自爱主权 — 从「情感依赖」到「自我主导」",
    "images": [f"card_v2_{i+1}.jpg" for i in range(len(CARDS))],
    "image_count": len(CARDS),
    "generated_at": datetime.now().isoformat(),
}


# ─── Main ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Write HTML & render images
    render_all_cards()

    # Write metadata
    with open(os.path.join(day_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)
    print(f"[Meta] manifest.json written")

    with open(os.path.join(day_dir, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump(POST_DATA, f, ensure_ascii=False, indent=2)
    print(f"[Meta] post_data.json written")

    print(f"\n[Done] Day {DAY_NUM} v2 complete: {day_dir}")
