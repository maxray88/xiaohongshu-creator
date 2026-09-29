"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day22_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 22 V2 第二版配图生成
Topic: 我的精神状态：稳定地发疯 (当代年轻人精神状态实录)
V2 Angle: 情绪不是失控，是内心的一场暴风雨 — 学会在雨中跳舞
V2 Color: 深靛蓝→午夜紫 (vs V1 暖橙→淡娜)
Renderer: html-fallback
"""
import json, os, time
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
TODAY = "20260724"
V2_DIR = os.path.join(BASE, f"day_{TODAY}_day22_v2")
IMG_DIR = os.path.join(V2_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

# ─── V2 Color Palette: 深靛蓝→午夜紫 (deep indigo → midnight purple) ───
# Completely opposite of V1's warm orange/cream — cool, deep, introspective night-sky vibe
C = {
    "bg_start":       "#0F172A",  # slate-900 deep night
    "bg_end":         "#1E1B4B",  # indigo-950 deep purple
    "accent":         "#F0ABFC",  # fuchsia-300 soft pink glow
    "accent_dark":    "#D946EF",  # fuchsia-500 bright pink
    "accent_dim":     "#A21CAF",  # fuchsia-700
    "accent_light":   "rgba(240,171,252,0.10)",
    "text_main":      "#F8FAFC",  # slate-50 ice white
    "text_sub":       "#CBD5E1",  # slate-300 light grey
    "text_soft":      "#94A3B8",  # slate-400 muted
    "text_muted":     "#64748B",  # slate-500
    "divider":        "rgba(148,163,184,0.15)",
    "glow_pink":      "rgba(240,171,252,0.07)",
    "glow_blue":      "rgba(56,189,248,0.06)",
    "card_bg":        "rgba(255,255,255,0.03)",
    "pill_bg":        "rgba(240,171,252,0.12)",
    "step_circle":    "#F0ABFC",
    "step_text":      "#0F172A",
    "star":           "rgba(255,255,255,0.08)",
}

# ─── HTML Templates ──────────────────────────────────────────────────────────

CSS_COMMON = f"""@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@200;300;400;500;700;900&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: 1080px; height: 1440px; margin: 0; padding: 0;
    background: linear-gradient(160deg, {C['bg_start']} 0%, {C['bg_end']} 55%, #111827 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex; flex-direction: column; justify-content: center;
    align-items: flex-start;
    position: relative; overflow: hidden;
}}
/* Diffuse pink glow from top-right */
body::before {{
    content: ''; position: absolute;
    top: -200px; right: -180px;
    width: 600px; height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['glow_pink']}, transparent 70%);
    pointer-events: none; z-index: 0;
}}
/* Subtle blue glow bottom-left */
body::after {{
    content: ''; position: absolute;
    bottom: -150px; left: -120px;
    width: 450px; height: 450px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['glow_blue']}, transparent 70%);
    pointer-events: none; z-index: 0;
}}
/* Star field texture */
.texture {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(1px 1px at 10% 15%, {C['star']}, transparent),
        radial-gradient(1.5px 1.5px at 25% 45%, {C['star']}, transparent),
        radial-gradient(1px 1px at 50% 12%, {C['star']}, transparent),
        radial-gradient(1px 1px at 70% 30%, {C['star']}, transparent),
        radial-gradient(1px 1px at 85% 60%, {C['star']}, transparent),
        radial-gradient(1.5px 1.5px at 40% 75%, {C['star']}, transparent),
        radial-gradient(1px 1px at 20% 80%, {C['star']}, transparent),
        radial-gradient(1px 1px at 65% 88%, {C['star']}, transparent),
        radial-gradient(1.5px 1.5px at 90% 20%, {C['star']}, transparent),
        radial-gradient(1px 1px at 5% 55%, {C['star']}, transparent),
        radial-gradient(1px 1px at 45% 55%, {C['star']}, transparent),
        radial-gradient(1px 1px at 75% 10%, {C['star']}, transparent),
        radial-gradient(1.5px 1.5px at 55% 35%, {C['star']}, transparent),
        radial-gradient(1px 1px at 30% 65%, {C['star']}, transparent);
    pointer-events: none; z-index: 1;
}}
.card {{
    position: relative; z-index: 2;
    padding: 80px 85px;
    width: 100%; height: 100%;
    display: flex; flex-direction: column;
}}
/* Vertical accent line */
.vertical-bar {{
    position: absolute; left: 35px; top: 12%;
    width: 2px; height: 76%;
    background: linear-gradient(to bottom, {C['accent']}44, {C['accent']}15, transparent);
    border-radius: 2px; pointer-events: none; z-index: 1;
}}
/* Small diamond deco */
.diamond {{
    position: absolute; top: 45px; right: 55px;
    width: 20px; height: 20px;
    border: 1.5px solid {C['divider']};
    transform: rotate(45deg);
    pointer-events: none; z-index: 1;
}}
.diamond-2 {{
    position: absolute; bottom: 55px; left: 50px;
    width: 14px; height: 14px;
    border: 1px solid {C['divider']};
    transform: rotate(45deg);
    pointer-events: none; z-index: 1;
}}
.circle-deco {{
    position: absolute; bottom: 120px; right: 60px;
    width: 60px; height: 60px;
    border: 1.5px solid {C['divider']};
    border-radius: 50%;
    pointer-events: none; z-index: 1;
}}
.watermark {{
    position: absolute;
    bottom: 38px; left: 85px;
    font-size: 12px; font-weight: 300;
    color: {C['text_muted']}; letter-spacing: 2px; z-index: 3;
    opacity: 0.4;
}}
.page-num {{
    position: absolute;
    bottom: 38px; right: 85px;
    font-size: 12px; font-weight: 300;
    color: {C['text_muted']}; letter-spacing: 1px; z-index: 3;
    opacity: 0.35;
}}
/* Series tag */
.series-tag {{
    font-size: 15px; font-weight: 400;
    color: {C['accent']}; letter-spacing: 5px;
    margin-bottom: 22px;
    padding: 5px 16px;
    border: 1px solid {C['divider']};
    display: inline-block; align-self: flex-start;
    opacity: 0.8;
    background: {C['pill_bg']};
    border-radius: 20px;
}}
/* Typography */
.title-xl {{
    font-size: 80px; font-weight: 900;
    color: {C['text_main']};
    letter-spacing: 5px; line-height: 1.2;
    margin-bottom: 4px;
}}
.title-lg {{
    font-size: 52px; font-weight: 700;
    color: {C['accent']};
    letter-spacing: 4px; line-height: 1.25;
    margin-bottom: 4px;
}}
.title-md {{
    font-size: 32px; font-weight: 500;
    color: {C['text_sub']};
    letter-spacing: 3px; line-height: 1.5;
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
    letter-spacing: 2px; line-height: 1.9;
}}
.text-muted {{
    font-size: 18px; font-weight: 300;
    color: {C['text_muted']};
    letter-spacing: 2px; line-height: 1.8;
}}
.highlight-title {{
    font-size: 40px; font-weight: 700;
    color: {C['accent']};
    letter-spacing: 4px; line-height: 1.5;
    margin-bottom: 14px;
}}
.quote-block {{
    font-size: 28px; font-weight: 350;
    color: {C['text_sub']};
    letter-spacing: 2px; line-height: 2;
    padding: 16px 22px;
    margin: 10px 0;
    border-left: 3px solid {C['accent']}55;
    background: {C['card_bg']};
    font-style: italic;
}}
.cta-tag {{
    display: inline-block;
    font-size: 17px; font-weight: 400;
    color: {C['accent']};
    letter-spacing: 3px;
    padding: 8px 22px;
    border: 1px solid {C['divider']};
    margin-top: 18px;
    background: {C['pill_bg']};
    border-radius: 24px;
}}
.spacer {{ height: 14px; }}
.spacer-sm {{ height: 8px; }}
.spacer-lg {{ height: 28px; }}
/* Steps */
.step-item {{
    display: flex; align-items: flex-start;
    gap: 14px; margin-bottom: 14px;
}}
.step-num {{
    display: flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; border-radius: 50%;
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
    padding: 6px 18px;
    background: {C['pill_bg']};
    color: {C['accent']};
    font-size: 15px; font-weight: 400; letter-spacing: 2px;
    border-radius: 18px;
    margin-bottom: 14px;
}}
/* Divider */
.divider {{
    width: 50px; height: 1.5px;
    background: {C['accent']}77;
    margin: 8px 0 16px 0;
}}
/* Accent box */
.accent-box {{
    display: inline-block;
    padding: 10px 22px;
    border: 1px solid {C['divider']};
    background: {C['card_bg']};
    margin-bottom: 12px;
}}
.accent-box .ab-text {{
    font-size: 26px; font-weight: 500;
    color: {C['accent']}; letter-spacing: 3px;
}}
/* Hashtags row */
.hashtags {{
    position: absolute;
    bottom: 76px; left: 85px;
    font-size: 13px; font-weight: 300;
    color: {C['text_muted']};
    letter-spacing: 2px; line-height: 2;
    z-index: 3; opacity: 0.4;
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
/* Wave divider SVG animation effect */
.wave-line {{
    width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent 0%, {C['accent']}44 25%, {C['accent']}88 50%, {C['accent']}44 75%, transparent 100%);
    margin: 12px 0 16px 0;
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
<div class="circle-deco"></div>
<div class="card">
{inner_html}
</div>
<div class="watermark">@情绪树洞 · v2 · 2026.07.24</div>
<div class="page-num">{page_num} / 6</div>
</body>
</html>"""

# ─── Card 1: Cover ──────────────────────────────────────────────────────────
CARD1 = wrap_body("""\
<div class="series-tag">当 代 年 轻 人 精 神 状 态</div>
<div class="num-display">22</div>
<div class="title-xl">情绪不是失控</div>
<div class="title-lg">是內心的一场暴风雨</div>
<div class="divider"></div>
<div class="title-md">学会在雨中跳舞</div>
<div class="spacer-lg"></div>
<div class="text-light">—— 那些波动起伏的情绪里，藏着你最真实的生命力 ——</div>
""", "1")

# ─── Card 2: Scene ──────────────────────────────────────────────────────────
CARD2 = wrap_body("""\
<div class="series-tag">情绪晴雨表</div>
<div class="highlight-title">「今天也是情绪过山车的一天」</div>
<div class="text-body">早上一杯咖啡：感觉能征服世界</div>
<div class="text-body">中午被老板说了一句：天塌了</div>
<div class="text-body">下午同事分零食：又活过来了</div>
<div class="text-body">晚上回到家：不知道为什么就哭了</div>
<div class="spacer"></div>
<div class="quote-block">你不是不稳定。你的情绪在告诉你：你的每一天都活得如此真实而鲜活。</div>
<div class="spacer"></div>
<div class="text-light">情绪不是你的敌人。它是你的内心在呼吸。</div>
""", "2")

# ─── Card 3: Insight ────────────────────────────────────────────────────────
CARD3 = wrap_body("""\
<div class="series-tag">一个视角转换</div>
<div class="accent-box"><span class="ab-text">「发疯」背后的三个礼物</span></div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">1</div>
    <div class="step-text"><b>情绪深度</b> — 你能在一天内体验喜怒哀乐的完整光谱，这是灵魂的丰富性</div>
</div>
<div class="step-item">
    <div class="step-num">2</div>
    <div class="step-text"><b>自我觉察力</b> — 那些崩溃的瞬间，恰恰是你最了解自己的时刻</div>
</div>
<div class="step-item">
    <div class="step-num">3</div>
    <div class="step-text"><b>恢复力</b> — 每次觉得自己撑不住了，但第二天依然起来了，这本身就是奇迹</div>
</div>
<div class="spacer"></div>
<div class="text-light">你的情绪波动，不是故障。是你生命系统的正常心跳。</div>
""", "3")

# ─── Card 4: Method ─────────────────────────────────────────────────────────
CARD4 = wrap_body("""\
<div class="series-tag">与情绪共舞</div>
<div class="highlight-title">3 个温柔的「雨中舞步」</div>
<div class="wave-line"></div>
<div class="step-item">
    <div class="step-num">❶</div>
    <div class="step-text"><b>情绪日记 — 命名即驯服</b><br><span style="font-weight:300;font-size:20px;color:#94A3B8;">写下：「我现在感到____，因为它____，我需要____」—— 书写即解离</span></div>
</div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">❷</div>
    <div class="step-text"><b>10 秒「暂停按钮」</b><br><span style="font-weight:300;font-size:20px;color:#94A3B8;">感觉要失控时，深呼吸 10 秒，问自己：此刻的我，需要什么？一杯水？一个拥抱？还是只是被听到？</span></div>
</div>
<div class="spacer-sm"></div>
<div class="step-item">
    <div class="step-num">❸</div>
    <div class="step-text"><b>设置「安心角落」</b><br><span style="font-weight:300;font-size:20px;color:#94A3B8;">在家里找一个角落，放上让你舒服的东西。每天给自己 10 分钟，在那里不做任何事，只是待着。</span></div>
</div>
""", "4")

# ─── Card 5: Gentle ─────────────────────────────────────────────────────────
CARD5 = wrap_body("""\
<div class="series-tag">一封深夜来信</div>
<div class="quote-block">
「如果你今天情绪起伏很大，我想对你说：那不是你不够好，那是你活得太用力了。你在乎工作、在乎关系、在乎自己的成长，每一份在乎都伴随着情绪的波澜。那些看似「发疯」的时刻，是你内心那个真实的小孩在替你说出那些你白天不敢说的话。」
</div>
<div class="spacer"></div>
<div class="text-body">允许自己崩溃，</div>
<div class="text-body">也允许自己重新好起来。</div>
<div class="spacer"></div>
<div class="text-light">你的每一次情绪波动，</div>
<div class="text-light">都在证明你是一个有血有肉的人。</div>
<div class="spacer"></div>
<div class="text-body" style="color:#F0ABFC;">—— 而这，本身就是一件值得骄傲的事。</div>
""", "5")

# ─── Card 6: CTA ────────────────────────────────────────────────────────────
CARD6 = wrap_body("""\
<div class="title-xl">你的情绪</div>
<div class="title-lg">是你活着的证据</div>
<div class="divider"></div>
<div class="text-body">不必追求「情绪稳定」的假象。</div>
<div class="text-body">去追求「情绪自由」——</div>
<div class="text-body">允许自己开心时大笑，难过时哭泣，</div>
<div class="text-body">愤怒时表达，迷茫时安静。</div>
<div class="spacer"></div>
<div class="text-body" style="color:#F0ABFC;">稳定的不是情绪，是你面对情绪的方式。</div>
<div class="spacer"></div>
<div class="cta-tag">今晚，你的情绪是什么颜色？🌙</div>
<div class="hashtags">#情绪树洞 #精神状态 #当代年轻人 #稳定地发疯 #情绪自由 #情绪价值 #自我和解 #治愈系 #夜间随想</div>
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
        "day_num": 22,
        "date": TODAY,
        "series": "当代年轻人精神状态实录",
        "title": "我的精神状态：稳定地发疯",
        "v2_angle": "情绪不是失控，是内心的一场暴风雨 — 学会在雨中跳舞",
        "emotion_tag": "情绪自由",
        "color_scheme": "深靛蓝→午夜紫",
        "v2_of": f"day_{TODAY}_day22",
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
        "day_num": 22,
        "date": TODAY,
        "series": "当代年轻人精神状态实录",
        "title": "我的精神状态：稳定地发疯",
        "emotion_tag": "情绪自由",
        "v2_angle": "情绪不是失控，是内心的一场暴风雨",
        "content_text": (
            "情绪不是失控，是内心的一场暴风雨\n\n"
            "早上一杯咖啡：感觉能征服世界\n"
            "中午被老板说了一句：天塌了\n"
            "下午同事分零食：又活过来了\n"
            "晚上回到家：不知道为什么就哭了\n\n"
            "你不是不稳定。你的情绪在告诉你：你的每一天都活得如此真实而鲜活。\n\n"
            "「发疯」背后的三个礼物：\n"
            "❶ 情绪深度 — 你能在一天内体验喜怒哀乐的完整光谱\n"
            "❷ 自我觉察力 — 崩溃的瞬间，恰恰是你最了解自己的时刻\n"
            "❸ 恢复力 — 每次觉得自己撑不住了但第二天依然起来\n\n"
            "3 个温柔的「雨中舞步」：\n"
            "❶ 情绪日记 — 命名即驯服\n"
            "❷ 10 秒「暂停按钮」— 深呼吸，问自己需要什么\n"
            "❸ 设置「安心角落」— 每天给自己 10 分钟\n\n"
            "不必追求「情绪稳定」的假象。\n"
            "去追求「情绪自由」——\n"
            "允许自己开心时大笑，难过时哭泣。\n\n"
            "稳定的不是情绪，是你面对情绪的方式。"
        ),
        "hashtags": [
            "#情绪树洞", "#精神状态", "#当代年轻人",
            "#稳定地发疯", "#情绪自由", "#情绪价值",
            "#自我和解", "#治愈系", "#夜间随想"
        ],
        "images": [f"card_v2_{i}.jpg" for i in range(1, 7)],
        "image_count": 6,
        "renderer": "html-fallback",
        "v2_of": f"day_{TODAY}_day22",
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
    print(f"\n✅ Day 22 V2 generated in {V2_DIR}")
