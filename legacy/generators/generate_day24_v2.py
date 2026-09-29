"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day24_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 24 V2 素材生成
Completely different color scheme and copy angle from V1.
V1: 深蓝→暮光紫 (dark, cool, observational)
V2: 暖杏白→玫瑰红棕 (warm, inviting, acceptance-based)
"""
import json, os, glob
from datetime import datetime

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
STATE_FILE = os.path.join(BASE, "current_day.txt")

# ─── Day number dedup for V2 ───────────────────────────────────────────
# For V2, we need the SAME day_num as today's V1 manifest, not the next day.
# Scan manifests to find today's V1 day number.
TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_FS = datetime.now().strftime("%Y%m%d")

def find_today_v1_daynum():
    """Find the day_num from today's V1 manifest (not v2)."""
    today_v1 = None
    for mf in glob.glob(os.path.join(BASE, f"day_{TODAY_FS}_day*/manifest.json")):
        # Skip v2 manifests
        if "_v2" in mf:
            continue
        try:
            with open(mf) as f:
                data = json.load(f)
                dn = data.get("day_num", 0)
                if dn > 0:
                    today_v1 = dn
        except:
            pass
    return today_v1

v1_daynum = find_today_v1_daynum()
if v1_daynum is None:
    # Fallback: scan all manifests for max, use that (same as v1 logic)
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

# Also read current_day.txt for logging
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        last_day_raw = f.read().strip()
else:
    last_day_raw = "0"

scanned_max = DAY_NUM  # for display

day_dir = os.path.join(BASE, f"day_{TODAY_FS}_day{DAY_NUM}_v2")
img_dir = os.path.join(day_dir, "images")
os.makedirs(img_dir, exist_ok=True)

# ─── Color Palette: 暖杏白→玫瑰红棕 (completely different from V1) ──────
C = {
    "bg_start": "#FFFAF0",      # floral white / warm cream
    "bg_end": "#FDE8E0",        # light peach
    "card_bg": "#FFFFFFE0",     # white with slight transparency
    "text_main": "#1C1917",     # near black (warm)
    "text_sub": "#57534E",      # warm dark gray
    "text_soft": "#8B7E72",     # medium warm brown
    "accent": "#C0392B",        # crimson red — pops against warm bg
    "accent_dark": "#922B21",   # dark red
    "accent_light": "#FADBD8",  # light pink
    "accent_warm": "#E67E22",   # orange accent
    "divider": "#E8D5C4",       # tan/beige
    "watermark": "rgba(192,57,43,0.15)",
    "shadow": "rgba(192,57,43,0.08)",
}

# ─── Content ────────────────────────────────────────────────────────────
POST_TITLE = "情绪不需要被治好"
SERIES = "当代年轻人精神状态实录"
SERIES_TAG = "情绪自由"
V2_ANGLE = "情绪不是问题，感受本身就是答案 — 允许一切发生"

CARDS = [
    # ── Card 1: Cover ──
    {
        "type": "cover",
        "lines": [
            ("tag", "情绪树洞"),
            ("big", "情绪不需要"),
            ("big", "被「治好」"),
            ("medium", "它只是需要被好好看见"),
            ("spacer", ""),
            ("body", "致每一个在情绪中浮沉的你"),
        ]
    },
    # ── Card 2: Scene ──
    {
        "type": "scene",
        "lines": [
            ("tag", "日常碎片"),
            ("quote", "开心的时候觉得世界都是我的"),
            ("quote", "难过的时候觉得自己一无所有"),
            ("spacer", ""),
            ("quote", "有时候电量满格"),
            ("quote", "有时候只想静音"),
            ("spacer", ""),
            ("body", "状态起起伏伏，才是活着的感觉啊"),
        ]
    },
    # ── Card 3: Insight ──
    {
        "type": "insight",
        "lines": [
            ("tag", "一个温柔的提醒"),
            ("highlight", "情绪没有好坏之分"),
            ("spacer", ""),
            ("body", "焦虑——是身体在保护你"),
            ("body", "悲伤——是心在处理失去"),
            ("body", "愤怒——是边界被触碰的信号"),
            ("body", "每一种情绪都在为你工作"),
        ]
    },
    # ── Card 4: Method ──
    {
        "type": "method",
        "lines": [
            ("tag", "试试这样做"),
            ("step", "🫂  停下来"),
            ("body", "放下手机，深呼吸三次"),
            ("spacer", ""),
            ("step", "🌊  感受它"),
            ("body", "问自己「我现在是什么感觉？」给情绪取个名字"),
            ("spacer", ""),
            ("step", "💛  送走它"),
            ("body", "想象情绪像云一样飘过，你只需要看着它"),
        ]
    },
    # ── Card 5: Gentle ──
    {
        "type": "gentle",
        "lines": [
            ("tag", "想对你说"),
            ("highlight", "你不必总是「正常」"),
            ("spacer", ""),
            ("quote", "你可以快乐，也可以难过"),
            ("quote", "可以高效，也可以摆烂"),
            ("quote", "可以做对，也可以搞砸"),
            ("spacer", ""),
            ("body", "你是活生生的人，不是精密的机器"),
        ]
    },
    # ── Card 6: CTA ──
    {
        "type": "cta",
        "lines": [
            ("big", "今天"),
            ("medium", "你的情绪是什么颜色？"),
            ("spacer", ""),
            ("body", "在评论区画出来 🎨"),
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

    html = f"""<!DOCTYPE html>
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
    background: linear-gradient(150deg, {C['bg_start']} 0%, {C['bg_end']} 50%, #FDF2E9 100%);
    font-family: 'PingFang SC', 'Heiti SC', 'Noto Sans SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Warm organic decorative blobs */
body::before {{
    content: '';
    position: absolute;
    top: -120px;
    right: -80px;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_light']}88 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -100px;
    left: -100px;
    width: 350px;
    height: 350px;
    border-radius: 50%;
    background: radial-gradient(circle, {C['accent_warm']}22 0%, transparent 70%);
    pointer-events: none;
}}

/* Floating organic shape — right side */
.floating-blob {{
    position: absolute;
    top: 200px;
    right: -50px;
    width: 200px;
    height: 200px;
    border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
    background: {C['accent']}0D;
    pointer-events: none;
    z-index: 0;
}}

.floating-blob-2 {{
    position: absolute;
    bottom: 250px;
    left: -70px;
    width: 180px;
    height: 180px;
    border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
    background: {C['accent_light']}44;
    pointer-events: none;
    z-index: 0;
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
    background: linear-gradient(180deg, {C['accent']}, {C['accent_warm']}, {C['accent_light']});
    border-radius: 2px;
}}

.watermark {{
    position: absolute;
    bottom: 34px;
    right: 44px;
    font-family: 'PingFang SC', sans-serif;
    font-size: 12px;
    font-weight: 300;
    color: {C['watermark']};
    letter-spacing: 2px;
    z-index: 3;
}}

.page-num {{
    position: absolute;
    bottom: 34px;
    left: 44px;
    font-size: 12px;
    font-weight: 300;
    color: {C['watermark']};
    letter-spacing: 1px;
    z-index: 3;
}}

/* ─── Typography ─── */
.tag {{
    font-size: 18px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 3px;
    margin-bottom: 30px;
    padding: 6px 20px;
    border: 1px solid {C['accent']}44;
    border-radius: 24px;
    background: {C['accent_light']}33;
}}

.big-title {{
    font-size: 72px;
    font-weight: 700;
    color: {C['text_main']};
    letter-spacing: 6px;
    line-height: 1.25;
    text-align: center;
    margin-bottom: 8px;
}}

.medium-title {{
    font-size: 36px;
    font-weight: 500;
    color: {C['text_sub']};
    letter-spacing: 4px;
    line-height: 1.5;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 6px;
}}

.highlight {{
    font-size: 40px;
    font-weight: 700;
    color: {C['accent']};
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 14px;
    width: 100%;
}}

.highlight-sub {{
    font-size: 30px;
    font-weight: 500;
    color: {C['accent_dark']};
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
}}

.quote {{
    font-size: 30px;
    font-weight: 400;
    color: {C['text_sub']};
    letter-spacing: 2px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}}

.body-text {{
    font-size: 26px;
    font-weight: 400;
    color: {C['text_soft']};
    letter-spacing: 1.5px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 4px;
}}

.step {{
    font-size: 34px;
    font-weight: 600;
    color: {C['accent']};
    letter-spacing: 3px;
    line-height: 1.5;
    text-align: center;
    margin-bottom: 14px;
}}

.small-text {{
    font-size: 20px;
    font-weight: 300;
    color: {C['text_soft']};
    letter-spacing: 2px;
    text-align: center;
}}

.cta-border {{
    margin-top: 8px;
    padding: 8px 24px;
    border: 1.5px solid {C['accent']}55;
    border-radius: 28px;
    color: {C['accent']};
    font-weight: 500;
}}

.spacer {{
    height: 16px;
}}
.spacer-lg {{
    height: 28px;
}}

/* ─── Per-type adjustments ─── */
.cover .big-title {{
    font-size: 80px;
    letter-spacing: 8px;
    margin-bottom: 8px;
    background: linear-gradient(135deg, {C['accent']}, {C['accent_dark']});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.cover .medium-title {{
    font-size: 34px;
    color: {C['text_sub']};
    margin-top: 12px;
}}
.cover .body-text {{
    font-size: 24px;
    color: {C['text_soft']};
    margin-top: 8px;
}}

.scene .quote {{
    font-size: 28px;
    font-weight: 400;
    color: {C['text_sub']};
}}

.insight .highlight {{
    font-size: 36px;
    padding: 16px 26px;
    background: {C['accent_light']}66;
    border-radius: 12px;
    text-align: center;
    width: 100%;
    border-left: 3px solid {C['accent']};
}}

.method .step {{
    color: {C['accent']};
    font-size: 32px;
}}
.method .body-text {{
    margin-bottom: 6px;
    padding-left: 20px;
    color: {C['text_soft']};
}}

.gentle .highlight {{
    font-size: 40px;
    color: {C['accent_dark']};
    margin-bottom: 24px;
}}
.gentle .quote {{
    font-size: 28px;
    font-weight: 400;
    color: {C['text_sub']};
}}
.gentle .body-text {{
    font-size: 26px;
    color: {C['accent']};
    font-weight: 500;
}}

.cta .big-title {{
    font-size: 90px;
    letter-spacing: 12px;
    margin-bottom: 8px;
    background: linear-gradient(135deg, {C['accent']}, {C['accent_warm']});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.cta .medium-title {{
    font-size: 38px;
    color: {C['accent_dark']};
    margin-bottom: 24px;
}}
.cta .body-text {{
    font-size: 26px;
    font-weight: 400;
    color: {C['text_soft']};
}}
</style>
</head>
<body>
<div class="floating-blob"></div>
<div class="floating-blob-2"></div>
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
    from playwright.sync_api import sync_playwright
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
            page.wait_for_timeout(1000)
            page.screenshot(path=jpg_path, full_page=False, type="jpeg", quality=95)
            page.close()

            img_size_kb = os.path.getsize(jpg_path) / 1024
            print(f"  [{idx+1}/6] card_v2_{idx+1}.jpg  ({img_size_kb:.0f} KB)")

        browser.close()
    print(f"\n[Render] All 6 V2 cards saved to: {img_dir}")


# ─── Metadata ───────────────────────────────────────────────────────────
def write_metadata():
    manifest_cards = []
    for i, c in enumerate(CARDS):
        fpath = os.path.join(img_dir, f"card_v2_{i+1}.jpg")
        manifest_cards.append({
            "index": i+1,
            "file": f"card_v2_{i+1}.jpg",
        })

    now = datetime.now().isoformat()

    manifest = {
        "day_num": DAY_NUM,
        "date": TODAY_FS,
        "series": SERIES,
        "title": POST_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": SERIES_TAG,
        "color_scheme": "暖杏白→玫瑰红棕",
        "v2_of": f"day_{TODAY_FS}_day{DAY_NUM}",
        "renderer": "html-fallback",
        "cards": manifest_cards,
        "images_rendered": True,
        "generated_at": now,
    }

    post_data = {
        "platform": "xiaohongshu",
        "day_num": DAY_NUM,
        "date": TODAY_FS,
        "series": SERIES,
        "title": POST_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": SERIES_TAG,
        "color_scheme": "暖杏白→玫瑰红棕",
        "v2_of": f"day_{TODAY_FS}_day{DAY_NUM}",
        "post_content": {
            "title": POST_TITLE,
            "body": (
                "你有没有这样的时刻：\n\n"
                "开心的时候觉得世界都是你的，\n"
                "难过的时候觉得自己一无所有。\n\n"
                "情绪像个来访者，想来就来，想走就走。\n"
                "我们总是想赶走坏情绪、留住好情绪。\n\n"
                "可你有没有想过——\n"
                "情绪根本不需要被「治好」，\n"
                "它只是需要被好好看见。\n\n"
                "焦虑是身体在保护你，\n"
                "悲伤是心在处理失去，\n"
                "愤怒是你的边界被触碰的信号。\n\n"
                "每一种情绪都在为你工作。\n\n"
                "试试这样做：\n"
                "🫂 停下来——放下手机，深呼吸三次\n"
                "🌊 感受它——问自己「我现在是什么感觉？」\n"
                "💛 送走它——想象情绪像云一样飘过\n\n"
                "你不必总是「正常」。\n"
                "你可以快乐，也可以难过。\n"
                "可以做对，也可以搞砸。\n\n"
                "你是活生生的人，不是精密的机器。\n"
                "状态起起伏伏，才是活着的感觉。\n\n"
                "你的情绪不需要被修理。\n"
                "它需要被拥抱。"
            ),
            "tags": [
                "情绪树洞",
                "情绪自由",
                "自我接纳",
                "当代年轻人",
                "精神状态",
                "治愈系",
                "正念",
                "情绪管理",
                "心理学",
                "自我成长"
            ]
        },
        "cards": manifest_cards,
        "generated_at": now,
    }

    with open(os.path.join(day_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(day_dir, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)

    # Update state file: write day_num|scanned_max
    with open(STATE_FILE, "w") as f:
        f.write(f"{DAY_NUM}|{scanned_max}")
    print(f"[Meta] manifest.json + post_data.json saved.")
    print(f"[State] current_day.txt updated to {DAY_NUM}|{scanned_max}")
# ─── Main ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"{'='*60}")
    print(f"  情绪树洞 · Day {DAY_NUM} · V2 素材生成")
    print(f"  日期: {TODAY}  |  系列: {SERIES}")
    print(f"  V2 角度: {V2_ANGLE}")
    print(f"  V1 配色: 深蓝→暮光紫  |  V2 配色: 暖杏白→玫瑰红棕")
    print(f"  双重校验: state_file={last_day_raw}, today_v1_manifest={v1_daynum}, day_num={DAY_NUM}")
    print(f"{'='*60}\n")

    render_all_cards()
    write_metadata()

    print(f"\n{'='*60}")
    print(f"  ✓ Day {DAY_NUM} V2 全部完成!")
    print(f"  素材目录: {img_dir}")
    print(f"  共 {len(CARDS)} 张配图")
    print(f"  渲染引擎: html-fallback")
    print(f"{'='*60}")
