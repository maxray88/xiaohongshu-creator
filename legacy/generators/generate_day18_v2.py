"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day18_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 18 V2 第二版配图生成
Topic: 社交焦虑自救指南 (社交焦虑自救)
V2 Angle: 你不是脆弱，你只是太善良 — 从「自我怀疑」到「内在力量」
V2 Color: 深墨绿→雾蓝 (vs V1 柔粉→米白)
Renderer: html-fallback
"""
import json, os, time
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
TODAY = "20260722"
V2_DIR = os.path.join(BASE, f"day_{TODAY}_day18_v2")
IMG_DIR = os.path.join(V2_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

# ─── V2 Color Palette: 深墨绿→雾蓝 (deep verdant → misty blue) ───
# Completely opposite of V1's soft pink/cream — cool, grounded, nature-inspired
C = {
    "bg_start":       "#1B2E35",  # deep pine green
    "bg_end":         "#2C3E50",  # slate blue
    "accent":         "#E8C87A",  # warm gold / honey (high contrast accent)
    "accent_dark":    "#D4A854",  # darker gold
    "accent_light":   "rgba(232,200,122,0.10)",
    "text_main":      "#F0F4F8",  # ice white
    "text_sub":       "#D5DFE8",  # light grey-blue
    "text_soft":      "#A0B4C8",  # muted steel blue
    "text_muted":     "#6A8099",  # dark grey-blue
    "divider":        "rgba(160,180,200,0.20)",
    "glow_gold":      "rgba(232,200,122,0.08)",
    "glow_teal":      "rgba(27,46,53,0.6)",
    "card_bg":        "rgba(240,244,248,0.04)",
    "pill_bg":        "rgba(232,200,122,0.15)",
    "step_circle":    "#E8C87A",
    "step_text":      "#1B2E35",
}

# ─── HTML Templates ──────────────────────────────────────────────────────────

CSS_COMMON = f"""@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@200;300;400;500;700;900&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: 1080px; height: 1440px; margin: 0; padding: 0;
    background: linear-gradient(165deg, {C['bg_start']} 0%, {C['bg_end']} 65%, #1A2B3A 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex; flex-direction: column; justify-content: center;
    align-items: flex-start;
    position: relative; overflow: hidden;
}}
/* Soft gold glow from bottom */
body::before {{
    content: ''; position: absolute;
    bottom: -200px; right: -150px;
    width: 550px; height: 550px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['glow_gold']}, transparent 70%);
    pointer-events: none; z-index: 0;
}}
/* Subtle teal light top-left */
body::after {{
    content: ''; position: absolute;
    top: -180px; left: -120px;
    width: 400px; height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(232,200,122,0.05), transparent 70%);
    pointer-events: none; z-index: 0;
}}
/* Geometric grid overlay — subtle modern texture */
.texture {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(160,180,200,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(160,180,200,0.04) 1px, transparent 1px);
    background-size: 80px 80px;
    pointer-events: none; z-index: 1;
}}
.card {{
    position: relative; z-index: 2;
    padding: 75px 85px;
    width: 100%; height: 100%;
    display: flex; flex-direction: column;
}}
/* Vertical accent bar on left */
.vertical-bar {{
    position: absolute; left: 40px; top: 10%;
    width: 3px; height: 80%;
    background: linear-gradient(to bottom, {C['accent']}66, {C['accent']}22, transparent);
    border-radius: 2px; pointer-events: none; z-index: 1;
}}
/* Small geometric diamond decoration */
.diamond {{
    position: absolute; top: 40px; right: 50px;
    width: 24px; height: 24px;
    border: 2px solid {C['divider']};
    transform: rotate(45deg);
    pointer-events: none; z-index: 1;
}}
.diamond-2 {{
    position: absolute; bottom: 50px; left: 45px;
    width: 16px; height: 16px;
    border: 1.5px solid {C['divider']};
    transform: rotate(45deg);
    pointer-events: none; z-index: 1;
}}
.watermark {{
    position: absolute;
    bottom: 40px; left: 85px;
    font-size: 12px; font-weight: 300;
    color: {C['text_muted']}; letter-spacing: 2px; z-index: 3;
    opacity: 0.5;
}}
.page-num {{
    position: absolute;
    bottom: 40px; right: 85px;
    font-size: 12px; font-weight: 300;
    color: {C['text_muted']}; letter-spacing: 1px; z-index: 3;
    opacity: 0.4;
}}
/* Series tag */
.series-tag {{
    font-size: 16px; font-weight: 400;
    color: {C['accent']}; letter-spacing: 5px;
    margin-bottom: 24px;
    padding: 5px 18px;
    border: 1px solid {C['divider']};
    display: inline-block;
    opacity: 0.85;
}}
/* Typography */
.title-xl {{
    font-size: 82px; font-weight: 900;
    color: {C['text_main']};
    letter-spacing: 6px; line-height: 1.15;
    margin-bottom: 6px;
}}
.title-lg {{
    font-size: 56px; font-weight: 700;
    color: {C['text_sub']};
    letter-spacing: 5px; line-height: 1.2;
    margin-bottom: 4px;
}}
.title-md {{
    font-size: 34px; font-weight: 500;
    color: {C['accent']};
    letter-spacing: 4px; line-height: 1.5;
}}
.text-body {{
    font-size: 26px; font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 2px; line-height: 2;
    margin-bottom: 3px;
}}
.text-light {{
    font-size: 22px; font-weight: 300;
    color: {C['text_soft']};
    letter-spacing: 2px; line-height: 1.8;
}}
.text-muted {{
    font-size: 18px; font-weight: 300;
    color: {C['text_muted']};
    letter-spacing: 2px; line-height: 1.8;
}}
.highlight-title {{
    font-size: 38px; font-weight: 700;
    color: {C['accent']};
    letter-spacing: 4px; line-height: 1.5;
    margin-bottom: 12px;
}}
.quote-block {{
    font-size: 28px; font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 2px; line-height: 2;
    padding: 18px 24px;
    margin: 10px 0;
    border-left: 3px solid {C['accent']}66;
    background: {C['card_bg']};
}}
.cta-tag {{
    display: inline-block;
    font-size: 17px; font-weight: 400;
    color: {C['accent']};
    letter-spacing: 3px;
    padding: 8px 22px;
    border: 1px solid {C['divider']};
    margin-top: 18px;
}}
.spacer {{ height: 14px; }}
.spacer-sm {{ height: 8px; }}
.spacer-lg {{ height: 28px; }}
/* Steps */
.step-item {{
    display: flex; align-items: flex-start;
    gap: 14px; margin-bottom: 16px;
}}
.step-num {{
    display: flex; align-items: center; justify-content: center;
    width: 34px; height: 34px; border-radius: 50%;
    background: {C['step_circle']}; color: {C['step_text']};
    font-size: 14px; font-weight: 700; flex-shrink: 0;
    font-family: 'Noto Sans SC', sans-serif;
}}
.step-text {{
    font-size: 24px; font-weight: 400;
    color: {C['text_sub']};
    letter-spacing: 2px; line-height: 1.6;
    padding-top: 3px;
}}
/* Pill tag */
.pill {{
    display: inline-block;
    padding: 6px 20px;
    background: {C['pill_bg']};
    color: {C['accent']};
    font-size: 15px; font-weight: 400; letter-spacing: 2px;
    border-radius: 20px;
    margin-bottom: 14px;
}}
/* Divider */
.divider {{
    width: 50px; height: 1.5px;
    background: {C['accent']}88;
    margin: 8px 0 16px 0;
}}
/* Accent box */
.accent-box {{
    display: inline-block;
    padding: 12px 24px;
    border: 1px solid {C['divider']};
    background: {C['card_bg']};
    margin-bottom: 14px;
}}
.accent-box .ab-text {{
    font-size: 26px; font-weight: 500;
    color: {C['accent']}; letter-spacing: 3px;
}}
/* Hashtags row */
.hashtags {{
    position: absolute;
    bottom: 80px; left: 85px;
    font-size: 13px; font-weight: 300;
    color: {C['text_muted']};
    letter-spacing: 2px; line-height: 2;
    z-index: 3; opacity: 0.5;
}}
/* Number display for cover */
.num-display {{
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 120px; font-weight: 900;
    color: {C['accent']};
    opacity: 0.06;
    position: absolute; right: 60px; top: 40px;
    line-height: 1;
    pointer-events: none; z-index: 1;
}}
"""

def wrap_body(inner_html, page_num):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=1080">
<style>{CSS_COMMON}</style>
</head>
<body>
<div class="texture"></div>
<div class="vertical-bar"></div>
<div class="diamond"></div>
<div class="diamond-2"></div>
<div class="card">
{inner_html}
</div>
<div class="watermark">@情绪树洞 · v2 · 2026.07.22</div>
<div class="page-num">{page_num} / 6</div>
</body>
</html>"""

# ─── Card 1: Cover ──────────────────────────────────────────────────────────
CARD1 = wrap_body("""\
<div class="series-tag">社 交 焦 虑 自 救</div>
<div class="num-display">01</div>
<div class="title-xl">你不是脆弱</div>
<div class="title-lg">你只是太善良</div>
<div class="divider"></div>
<div class="title-md">社交焦虑自救指南</div>
<div class="spacer-lg"></div>
<div class="text-light">—— 敏感不是缺陷，是你灵魂的深度 ——</div>
""", "1")

# ─── Card 2: Scene ──────────────────────────────────────────────────────────
CARD2 = wrap_body("""\
<div class="series-tag">那些无声的瞬间</div>
<div class="highlight-title">「我是不是又说错话了？」</div>
<div class="text-body">发出去的消息，反复检查措辞</div>
<div class="text-body">聚会结束后，在脑子里回放每一句话</div>
<div class="text-body">别人随口一句评价，你记了三天</div>
<div class="spacer"></div>
<div class="quote-block">你不是「想太多」。你是太在意别人的感受，以至于忘了照顾自己。</div>
<div class="spacer"></div>
<div class="text-light">你的敏感，是你与这个世界深度连接的天线。</div>
""", "2")

# ─── Card 3: Insight ────────────────────────────────────────────────────────
CARD3 = wrap_body("""\
<div class="series-tag">换个角度</div>
<div class="accent-box"><span class="ab-text">社交焦虑的真相</span></div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">1</div>
    <div class="step-text"><b>高共情力</b> — 你能察觉他人情绪的细微波动，这是天赋，不是诅咒</div>
</div>
<div class="step-item">
    <div class="step-num">2</div>
    <div class="step-text"><b>深度自省力</b> — 你反复思考是因为你在寻找更好的方式，不是自我折磨</div>
</div>
<div class="step-item">
    <div class="step-num">3</div>
    <div class="step-text"><b>自我保护机制</b> — 焦虑是警报器，它在提醒你：这个地方，你需要更温柔地对待自己</div>
</div>
<div class="spacer"></div>
<div class="text-light">焦虑不是你的敌人。它是你内心那个过于尽责的保安。</div>
""", "3")

# ─── Card 4: Method ─────────────────────────────────────────────────────────
CARD4 = wrap_body("""\
<div class="series-tag">温柔自救</div>
<div class="highlight-title">和焦虑做朋友的 3 个练习</div>
<div class="divider"></div>
<div class="step-item">
    <div class="step-num">❶</div>
    <div class="step-text"><b>命名它</b><br><span style="font-weight:300;font-size:20px;color:#A0B4C8;">「我注意到焦虑来了」—— 觉察即分离，它就不再是你，只是流经你的一种感觉</span></div>
</div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">❷</div>
    <div class="step-text"><b>5-4-3-2-1 接地</b><br><span style="font-weight:300;font-size:20px;color:#A0B4C8;">看 5 样东西 → 摸 4 样 → 听 3 种声音 → 闻 2 种气味 → 尝 1 种味道</span></div>
</div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">❸</div>
    <div class="step-text"><b>给自己写一句话</b><br><span style="font-weight:300;font-size:20px;color:#A0B4C8;">「我安全，我有权利待在这里，我不需要完美才值得被喜欢」</span></div>
</div>
""", "4")

# ─── Card 5: Gentle ─────────────────────────────────────────────────────────
CARD5 = wrap_body("""\
<div class="series-tag">写给你的一封信</div>
<div class="quote-block">
「你总是担心自己不够好。但你知道吗，那些真正在意你感受的人，从来没有觉得你事多。他们看见的，是一个温柔而敏感的灵魂在努力地好好活着。」
</div>
<div class="spacer"></div>
<div class="text-body">你的焦虑不是你的失败。</div>
<div class="text-body">它是你内心那个小孩，</div>
<div class="text-body">在试图保护你免受伤害。</div>
<div class="spacer"></div>
<div class="text-light">抱抱那个小孩，告诉 ta：</div>
<div class="text-light">「没关系，我们已经安全了。」</div>
""", "5")

# ─── Card 6: CTA ────────────────────────────────────────────────────────────
CARD6 = wrap_body("""\
<div class="title-xl">你的敏感</div>
<div class="title-lg">是你的超能力</div>
<div class="divider"></div>
<div class="text-body">你不必成为一个「合群」的人。</div>
<div class="text-body">你需要成为一个「和自己相处舒服」的人。</div>
<div class="spacer"></div>
<div class="text-body" style="color:#E8C87A;">焦虑无法消失，但可以变小。</div>
<div class="text-body" style="color:#E8C87A;">变小到不再拦住你认识世界。</div>
<div class="spacer"></div>
<div class="cta-tag">留下你的焦虑，带走一句温暖 💛</div>
<div class="hashtags">#情绪树洞 #社交焦虑自救 #社恐自救 #敏感不是病 #高敏感 #治愈系 #温柔自救 #自我接纳</div>
""", "6")

CARDS = [CARD1, CARD2, CARD3, CARD4, CARD5, CARD6]

# ─── Render with Playwright ────────────────────────────────────────────────
def render_cards():
    print(f"[V2] Rendering {len(CARDS)} cards to {IMG_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for i, html_content in enumerate(CARDS, 1):
            out_html = os.path.join(IMG_DIR, f"card_v2_{i}.html")
            out_jpg = os.path.join(IMG_DIR, f"card_v2_{i}.jpg")

            with open(out_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            page = browser.new_page(viewport={"width": 1080, "height": 1440})
            try:
                page.goto(f"file://{out_html}", wait_until="networkidle", timeout=30000)
                time.sleep(1.5)  # let fonts render
                page.screenshot(path=out_jpg, full_page=False, type="jpeg", quality=92)
                size_kb = os.path.getsize(out_jpg) / 1024
                print(f"  Card {i}: {out_jpg} ({size_kb:.0f} KB)")
            except Exception as e:
                print(f"  Card {i} ERROR: {e}")
            finally:
                page.close()
        browser.close()

# ─── Write Manifest ─────────────────────────────────────────────────────────
def write_manifest():
    manifest = {
        "day_num": 18,
        "date": TODAY,
        "series": "社交焦虑自救",
        "title": "社交焦虑自救指南",
        "v2_angle": "你不是脆弱，你只是太善良 — 从「自我怀疑」到「内在力量」",
        "emotion_tag": "敏感力量",
        "color_scheme": "深墨绿→雾蓝",
        "v2_of": f"day_{TODAY}_day18",
        "renderer": "html-fallback",
        "cards": [
            {"index": i, "file": f"card_v2_{i}.jpg"}
            for i in range(1, 7)
        ],
        "images_rendered": True,
        "generated_at": datetime.now().isoformat(),
    }
    manifest_path = os.path.join(V2_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[V2] Manifest written: {manifest_path}")

# ─── Write post_data.json ──────────────────────────────────────────────────
def write_post_data():
    post_data = {
        "platform": "xiaohongshu",
        "day_num": 18,
        "date": TODAY,
        "series": "社交焦虑自救",
        "title": "社交焦虑自救指南",
        "emotion_tag": "敏感力量",
        "v2_angle": "你不是脆弱，你只是太善良",
        "content_text": "你不是脆弱，你只是太善良\n\n你有没有这样的时刻：\n发出去的消息，反复检查措辞\n聚会结束后，在脑子里回放每一句话\n别人随口一句评价，你记了三天\n\n你不是「想太多」。\n你是太在意别人的感受，以至于忘了照顾自己。\n\n社交焦虑的真相：\n· 高共情力 — 你能察觉他人情绪的细微波动\n· 深度自省力 — 你反复思考是因为你在寻找更好的方式\n· 自我保护 — 焦虑在提醒你更温柔地对待自己\n\n3 个温柔练习：\n❶ 命名它：「我注意到焦虑来了」— 觉察即分离\n❷ 5-4-3-2-1 接地练习：用感官回到当下\n❸ 给自己写一句话：「我安全，我不需要完美才值得被喜欢」\n\n焦虑无法消失，但可以变小。\n小到不再拦住你认识世界。\n\n你的敏感，是你的超能力。\n你不必成为一个「合群」的人。\n你需要成为一个「和自己相处舒服」的人。",
        "hashtags": [
            "#情绪树洞", "#社交焦虑自救", "#社恐自救",
            "#敏感不是病", "#高敏感", "#治愈系",
            "#温柔自救", "#自我接纳"
        ],
        "images": [f"card_v2_{i}.jpg" for i in range(1, 7)],
        "image_count": 6,
        "renderer": "html-fallback",
        "v2_of": f"day_{TODAY}_day18",
        "generated_at": datetime.now().isoformat(),
    }
    post_path = os.path.join(V2_DIR, "post_data.json")
    with open(post_path, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print(f"[V2] Post data written: {post_path}")

if __name__ == "__main__":
    render_cards()
    write_manifest()
    write_post_data()
    print("[V2] Done!")
