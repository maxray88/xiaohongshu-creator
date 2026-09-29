"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day17_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 17 V2 第二版配图生成
Topic: 内向的人，不需要变外向 (社交焦虑自救)
V2 Angle: 你的安静，是你的天赋 — 从「伪装外向」到「内向者优势」
V2 Color: 暖杏→焦糖棕 (vs V1 深蓝→暮光紫)
Renderer: html-fallback
"""
import json, os, time
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
TODAY = "20260721"
V2_DIR = os.path.join(BASE, f"day_{TODAY}_day17_v2")
IMG_DIR = os.path.join(V2_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

# ─── V2 Color Palette: 暖杏→焦糖棕 (warm earthy tones, opposite of V1's cool blue) ───
C = {
    "bg_start":       "#3D2B1F",  # rich dark brown
    "bg_end":         "#6B3F2E",  # warm chestnut
    "accent":         "#E8A87C",  # warm apricot
    "accent_dark":    "#D4956A",  # golden caramel
    "accent_light":   "rgba(232,168,124,0.10)",
    "text_main":      "#FFF5EE",  # seashell white
    "text_sub":       "#F5DEB3",  # wheat
    "text_soft":      "#C4A882",  # camel
    "text_muted":     "#A0845C",  # muted tan
    "divider":        "rgba(196,168,130,0.25)",
    "glow":           "rgba(212,149,106,0.12)",
    "card_bg":        "rgba(255,245,238,0.04)",
}

# ─── HTML Templates ──────────────────────────────────────────────────────────

CSS_COMMON = f"""@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@200;300;400;500;700;900&family=ZCOOL+XiaoWei&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: 1080px; height: 1440px; margin: 0; padding: 0;
    background: linear-gradient(155deg, {C['bg_start']} 0%, {C['bg_end']} 60%, #4A2F22 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex; flex-direction: column; justify-content: center;
    align-items: flex-start;
    position: relative; overflow: hidden;
}}
/* Warm ambient glow bottom-right */
body::before {{
    content: ''; position: absolute;
    bottom: -250px; right: -180px;
    width: 650px; height: 650px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['glow']}, transparent 70%);
    pointer-events: none; z-index: 0;
}}
/* Subtle warm light top-left */
body::after {{
    content: ''; position: absolute;
    top: -200px; left: -150px;
    width: 400px; height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(232,168,124,0.06), transparent 70%);
    pointer-events: none; z-index: 0;
}}
/* Soft texture overlay - tiny dots like sand */
.texture {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: radial-gradient({C['accent_dark']}11 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none; z-index: 1;
}}
.card {{
    position: relative; z-index: 2;
    padding: 80px 90px;
    width: 100%; height: 100%;
    display: flex; flex-direction: column;
}}
/* Corner bracket top-left */
.bracket-tl {{
    position: absolute; top: 36px; left: 36px;
    width: 60px; height: 60px;
    border-left: 2px solid {C['divider']};
    border-top: 2px solid {C['divider']};
    pointer-events: none; z-index: 1;
}}
/* Corner bracket bottom-right */
.bracket-br {{
    position: absolute; bottom: 36px; right: 36px;
    width: 60px; height: 60px;
    border-right: 2px solid {C['divider']};
    border-bottom: 2px solid {C['divider']};
    pointer-events: none; z-index: 1;
}}
/* Side accent line */
.side-line {{
    position: absolute; left: 56px; top: 15%;
    width: 2px; height: 70%;
    background: linear-gradient(to bottom, {C['accent']}88, {C['accent_dark']}44, transparent);
    border-radius: 1px; pointer-events: none; z-index: 1;
}}
.watermark {{
    position: absolute;
    bottom: 44px; left: 90px;
    font-size: 13px; font-weight: 300;
    color: {C['text_muted']}; letter-spacing: 2px; z-index: 3;
    opacity: 0.5;
}}
.page-num {{
    position: absolute;
    bottom: 44px; right: 90px;
    font-size: 13px; font-weight: 300;
    color: {C['text_muted']}; letter-spacing: 1px; z-index: 3;
    opacity: 0.4;
}}
/* Typography */
.series-tag {{
    font-size: 18px; font-weight: 400;
    color: {C['accent']}; letter-spacing: 6px;
    margin-bottom: 28px;
    padding: 6px 20px;
    border: 1px solid {C['divider']};
    border-radius: 0;
    display: inline-block;
    opacity: 0.85;
}}
.title-xl {{
    font-family: 'Noto Sans SC', sans-serif;
    font-size: 96px; font-weight: 900;
    color: {C['text_main']};
    letter-spacing: 8px; line-height: 1.2;
    margin-bottom: 8px;
}}
.title-lg {{
    font-size: 64px; font-weight: 700;
    color: {C['text_sub']};
    letter-spacing: 6px; line-height: 1.2;
    margin-bottom: 6px;
}}
.title-md {{
    font-size: 40px; font-weight: 500;
    color: {C['accent']};
    letter-spacing: 4px; line-height: 1.5;
}}
.text-body {{
    font-size: 28px; font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 2px; line-height: 2;
    margin-bottom: 4px;
}}
.text-light {{
    font-size: 24px; font-weight: 300;
    color: {C['text_soft']};
    letter-spacing: 2px; line-height: 1.8;
}}
.text-muted {{
    font-size: 20px; font-weight: 300;
    color: {C['text_muted']};
    letter-spacing: 2px; line-height: 1.8;
}}
.highlight-title {{
    font-size: 42px; font-weight: 700;
    color: {C['accent']};
    letter-spacing: 4px; line-height: 1.5;
    margin-bottom: 16px;
}}
.highlight-body {{
    font-size: 32px; font-weight: 500;
    color: {C['text_sub']};
    letter-spacing: 3px; line-height: 1.8;
    margin-bottom: 6px;
}}
.quote-block {{
    font-size: 30px; font-weight: 350;
    color: {C['text_soft']};
    letter-spacing: 2px; line-height: 2;
    padding: 20px 28px;
    margin: 12px 0;
    border-left: 3px solid {C['accent']}66;
    background: {C['card_bg']};
}}
.cta-tag {{
    display: inline-block;
    font-size: 18px; font-weight: 400;
    color: {C['accent']};
    letter-spacing: 3px;
    padding: 8px 24px;
    border: 1px solid {C['divider']};
    margin-top: 20px;
}}
.spacer {{ height: 16px; }}
.spacer-sm {{ height: 10px; }}
.spacer-lg {{ height: 32px; }}
/* Steps */
.step-item {{
    display: flex; align-items: flex-start;
    gap: 16px; margin-bottom: 18px;
}}
.step-num {{
    display: flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    background: {C['accent']}CC; color: {C['bg_start']};
    font-size: 15px; font-weight: 700; flex-shrink: 0;
    font-family: 'Noto Sans SC', sans-serif;
}}
.step-text {{
    font-size: 26px; font-weight: 400;
    color: {C['text_sub']};
    letter-spacing: 2px; line-height: 1.6;
    padding-top: 4px;
}}
/* Divider */
.divider {{
    width: 60px; height: 1px;
    background: {C['divider']};
    margin: 10px 0 18px 0;
}}
/* Zine-style accent box */
.accent-box {{
    display: inline-block;
    padding: 14px 28px;
    border: 1px solid {C['divider']};
    background: {C['card_bg']};
    margin-bottom: 14px;
}}
.accent-box .ab-text {{
    font-size: 28px; font-weight: 500;
    color: {C['accent']}; letter-spacing: 3px;
}}
/* Hashtags row */
.hashtags {{
    position: absolute;
    bottom: 90px; left: 90px;
    font-size: 14px; font-weight: 300;
    color: {C['text_muted']};
    letter-spacing: 2px; line-height: 2;
    z-index: 3; opacity: 0.5;
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
<div class="bracket-tl"></div>
<div class="bracket-br"></div>
<div class="side-line"></div>
<div class="card">
{inner_html}
</div>
<div class="watermark">@情绪树洞 · v2 · 2026.07.21</div>
<div class="page-num">{page_num} / 6</div>
</body>
</html>"""

# ─── Card 1: Cover ──────────────────────────────────────────────────────────
CARD1 = wrap_body("""\
<div class="series-tag">社 交 焦 虑 自 救</div>
<div class="title-xl">你的安静</div>
<div class="title-lg">是你的天赋</div>
<div class="divider"></div>
<div class="title-md">内向的人，不需要变外向</div>
<div class="spacer-lg"></div>
<div class="text-light">—— 在喧闹的世界里，你自带宁静的力量 ——</div>
""", "1")

# ─── Card 2: Scene ──────────────────────────────────────────────────────────
CARD2 = wrap_body("""\
<div class="series-tag">那些熟悉的场景</div>
<div class="highlight-title">「你怎么不说话？」</div>
<div class="text-body">聚会上你安静地待在角落</div>
<div class="text-body">有人过来拍拍你：「放松点嘛」</div>
<div class="text-body">你笑了笑，但你知道——</div>
<div class="spacer"></div>
<div class="quote-block">你不是不想说话，你只是在用自己的方式感受世界。</div>
<div class="spacer"></div>
<div class="text-light">安静不是缺席，是另一种在场。</div>
""", "2")

# ─── Card 3: Insight ────────────────────────────────────────────────────────
CARD3 = wrap_body("""\
<div class="series-tag">换个角度看自己</div>
<div class="accent-box"><span class="ab-text">内向者优势</span></div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">1</div>
    <div class="step-text">深度思考力 — 你在安静中抵达别人看不到的深处</div>
</div>
<div class="step-item">
    <div class="step-num">2</div>
    <div class="step-text">敏锐觉察力 — 你听得见别人没说出的话，看得见细微的情绪</div>
</div>
<div class="step-item">
    <div class="step-num">3</div>
    <div class="step-text">丰盈内在世界 — 独处不是孤独，是你与自己深度对话的方式</div>
</div>
<div class="spacer"></div>
<div class="text-light">这个世界需要外向者去照亮舞台，</div>
<div class="text-light">也需要内向者去守护深度。</div>
""", "3")

# ─── Card 4: Method ─────────────────────────────────────────────────────────
CARD4 = wrap_body("""\
<div class="series-tag">善待自己</div>
<div class="highlight-title">给内向者的3个温柔建议</div>
<div class="divider"></div>
<div class="step-item">
    <div class="step-num">❶</div>
    <div class="step-text"><b>保护你的休息时间</b><br><span style="font-weight:300;font-size:22px;color:#C4A882;">社交后给自己留一段独处充电的时间，这不是逃避，是必需</span></div>
</div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">❷</div>
    <div class="step-text"><b>不必为安静道歉</b><br><span style="font-weight:300;font-size:22px;color:#C4A882;">不想说话时，温柔地说「我在听就好」—— 倾听也是参与</span></div>
</div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">❸</div>
    <div class="step-text"><b>选择适合你的社交方式</b><br><span style="font-weight:300;font-size:22px;color:#C4A882;">一对一深聊 > 一群人热闹，小范围 > 大场面</span></div>
</div>
""", "4")

# ─── Card 5: Gentle ─────────────────────────────────────────────────────────
CARD5 = wrap_body("""\
<div class="series-tag">写给你</div>
<div class="quote-block">
「你不需要变得外向。你需要的是遇见那个喜欢安静的你，并告诉 ta：你这样就很好。」
</div>
<div class="spacer"></div>
<div class="text-body">你的敏感，是你的雷达。</div>
<div class="text-body">你的沉默，是你的语言。</div>
<div class="text-body">你的独处，是你的修复。</div>
<div class="spacer"></div>
<div class="text-light">不是所有的花都在阳光下盛开。</div>
<div class="text-light">有些花在月光下，反而开得更美。</div>
""", "5")

# ─── Card 6: CTA ────────────────────────────────────────────────────────────
CARD6 = wrap_body("""\
<div class="title-xl">做自己</div>
<div class="title-lg">世界会适应你</div>
<div class="divider"></div>
<div class="text-body">内向不是缺陷，是你的出厂设置。</div>
<div class="text-body">在这个吵闹的世界里，你的安静是一种稀有资源。</div>
<div class="spacer"></div>
<div class="cta-tag">评论区说说你的故事 💬</div>
<div class="hashtags">#社交焦虑自救 #内向力量 #情绪树洞 #内向者优势 #安静的力
#自我接纳 #社恐自救 #治愈系</div>
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
                time.sleep(1.5)  # let fonts settle
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
        "day_num": 17,
        "date": TODAY,
        "series": "社交焦虑自救",
        "title": "内向的人，不需要变外向",
        "v2_angle": "你的安静，是你的天赋 — 从「伪装外向」到「内向者优势」",
        "emotion_tag": "内向力量",
        "color_scheme": "暖杏→焦糖棕",
        "v2_of": f"day_{TODAY}_day17",
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
        "day_num": 17,
        "date": TODAY,
        "series": "社交焦虑自救",
        "title": "内向的人，不需要变外向",
        "emotion_tag": "内向力量",
        "v2_angle": "你的安静，是你的天赋",
        "content_text": "你的安静，是你的天赋\n\n你是否有过这样的时刻：\n「你怎么不说话？」\n「放松点嘛」\n「多出去走走就好了」\n\n但你知道吗？\n你的安静不是缺陷，是上天给你的超能力。\n\n内向者优势：\n· 深度思考力 — 你在安静中抵达别人看不到的深处\n· 敏锐觉察力 — 你听得见别人没说出的话\n· 丰盈内在世界 — 独处是你与自己深度对话的方式\n\n三个温柔建议：\n❶ 保护你的休息时间 — 社交后给自己留充电时间\n❷ 不必为安静道歉 — 「我在听就好」\n❸ 选择适合你的社交方式 — 一对一深聊 > 一群人热闹\n\n你不需要变得外向。\n你需要的是遇见那个喜欢安静的你，\n并告诉 ta：你这样就很好。\n\n不是所有的花都在阳光下盛开。\n有些花在月光下，反而开得更美。\n\n做自己，世界会适应你。",
        "hashtags": [
            "#社交焦虑自救", "#内向力量", "#情绪树洞",
            "#内向者优势", "#安静的力", "#自我接纳",
            "#社恐自救", "#治愈系"
        ],
        "images": [f"card_v2_{i}.jpg" for i in range(1, 7)],
        "image_count": 6,
        "renderer": "html-fallback",
        "v2_of": f"day_{TODAY}_day17",
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
