"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day25_v2.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 - Day 25 V2 素材生成
Completely different color scheme and copy angle from V1.
V1: 浅绿→暖白 (fresh green, gentle warm — "lying flat isn't shameful")
V2: 深蓝→星夜紫 (deep navy, mystical purple — "rest is your birthright")
"""
import json, os, glob, subprocess, sys
from datetime import datetime

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
STATE_FILE = os.path.join(BASE, "current_day.txt")
TODAY_FS = datetime.now().strftime("%Y%m%d")

# ─── Day number dedup for V2 ───────────────────────────────────────────
# For V2, we need the SAME day_num as today's V1 manifest, not the next day.
def find_today_v1_daynum():
    """Find the day_num from today's V1 manifest (not v2)."""
    today_v1 = None
    for mf in glob.glob(os.path.join(BASE, f"day_{TODAY_FS}_day*/manifest.json")):
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

# Also read current_day.txt for reference
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        last_day_raw = f.read().strip()
else:
    last_day_raw = "0"

day_dir = os.path.join(BASE, f"day_{TODAY_FS}_day{DAY_NUM}_v2")
img_dir = os.path.join(day_dir, "images")
os.makedirs(img_dir, exist_ok=True)

# ─── Color Palette: 深蓝→星夜紫 (completely different from V1's light green) ──
C = {
    "bg_start": "#0F172A",        # deep navy
    "bg_end": "#1E1B4B",          # dark indigo
    "card_bg": "rgba(30,27,75,0.85)",  # semi-transparent indigo
    "text_main": "#F1F5F9",       # near white (slate-100)
    "text_sub": "#CBD5E1",        # light slate
    "text_soft": "#94A3B8",       # medium slate
    "text_warm": "#FDE68A",       # warm amber
    "accent": "#A78BFA",          # violet-400
    "accent_dark": "#7C3AED",     # violet-600
    "accent_soft": "#8B5CF6",     # violet-500
    "accent_light": "#DDD6FE",    # violet-200
    "accent_warm": "#F59E0B",     # amber-500
    "divider": "rgba(167,139,250,0.2)",  # violet with low opacity
    "watermark": "rgba(167,139,250,0.25)",
    "shadow": "rgba(124,58,237,0.15)",
    "star": "rgba(255,255,255,0.06)",
}

# ─── Content ────────────────────────────────────────────────────────────
POST_TITLE = "躺平不可耻，内耗才可悲"
SERIES = "当代年轻人精神状态实录"
SERIES_TAG = "自我和解"
V2_ANGLE = "休息是天赋人权，不是你赢得的奖励 — 心安理得地什么都不做"

CARDS = [
    # ── Card 1: Cover ──
    {
        "type": "cover",
        "lines": [
            ("tag", "当代年轻人精神状态实录"),
            ("big", "休息是"),
            ("big", "天赋人权"),
            ("medium", "不是你赢得的奖励"),
            ("spacer", ""),
            ("body", "致每一个不敢停下来的人"),
        ]
    },
    # ── Card 2: Scene ──
    {
        "type": "scene",
        "lines": [
            ("tag", "你是否也在经历"),
            ("quote", "周末躺到中午就充满罪恶感"),
            ("quote", "刷手机时觉得自己在浪费时间"),
            ("quote", "休假还在回老板消息"),
            ("quote", "连生病都觉得是自己不够强"),
            ("spacer", ""),
            ("body", "你不是懒，你只是忘了——"),
            ("body_small", "休息是一种能力，不是一种缺陷"),
        ]
    },
    # ── Card 3: Insight ──
    {
        "type": "insight",
        "lines": [
            ("tag", "一个真相"),
            ("highlight", "努力不是美德"),
            ("spacer", ""),
            ("body", "盲目努力是一种惯性"),
            ("body", "停下来才是真正的勇气"),
            ("spacer", ""),
            ("body", "就像田地需要休耕"),
            ("body", "你的大脑也需要彻底放空"),
        ]
    },
    # ── Card 4: Method ──
    {
        "type": "method",
        "lines": [
            ("tag", "今天试试"),
            ("step", "🌙  设一个「合法的休息时段」"),
            ("body", "比如 19:00-21:00，像开会一样写进日程"),
            ("spacer", ""),
            ("step", "📵  来一次「数字排毒」"),
            ("body", "把手机放到另一个房间，什么都不做地坐着"),
            ("spacer", ""),
            ("step", "☕  做一件「无用之事」"),
            ("body", "看云、煮茶、发呆、晒背——不需要产出什么"),
        ]
    },
    # ── Card 5: Gentle ──
    {
        "type": "gentle",
        "lines": [
            ("tag", "请记住"),
            ("highlight", "你的存在本身"),
            ("big", "就是价值。"),
            ("spacer", ""),
            ("quote", "你不需要用忙碌来证明自己值得被爱"),
            ("spacer", ""),
            ("body", "你活着，你在这里，就已经够了"),
        ]
    },
    # ── Card 6: CTA ──
    {
        "type": "cta",
        "lines": [
            ("big", "今天"),
            ("medium", "你给自己放假了吗？"),
            ("spacer", ""),
            ("body", "评论区告诉我 🍃"),
            ("spacer", ""),
            ("small", "💬 你的休息计划是什么？"),
        ]
    },
]

# ─── HTML Template ──────────────────────────────────────────────────────
# Night sky aesthetic with stars, constellations, and warm amber accents

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

@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@400;600;700&display=swap');

body {{
    width: 1080px;
    height: 1440px;
    margin: 0;
    padding: 0;
    background: linear-gradient(155deg, {C['bg_start']} 0%, {C['bg_end']} 40%, #312E81 70%, #1E1B4B 100%);
    font-family: 'Noto Sans SC', 'PingFang SC', 'Heiti SC', sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
}}

/* Star field */
.stars {{
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(1.5px 1.5px at 10% 20%, {C['star']} 100%, transparent),
        radial-gradient(1px 1px at 25% 55%, {C['star']} 100%, transparent),
        radial-gradient(2px 2px at 40% 10%, {C['star']} 100%, transparent),
        radial-gradient(1.5px 1.5px at 55% 40%, {C['star']} 100%, transparent),
        radial-gradient(1px 1px at 70% 15%, {C['star']} 100%, transparent),
        radial-gradient(2px 2px at 85% 50%, {C['star']} 100%, transparent),
        radial-gradient(1.5px 1.5px at 15% 80%, {C['star']} 100%, transparent),
        radial-gradient(1px 1px at 45% 75%, {C['star']} 100%, transparent),
        radial-gradient(2px 2px at 75% 85%, {C['star']} 100%, transparent),
        radial-gradient(1.5px 1.5px at 90% 25%, {C['star']} 100%, transparent),
        radial-gradient(1px 1px at 5% 45%, {C['star']} 100%, transparent),
        radial-gradient(2px 2px at 60% 65%, {C['star']} 100%, transparent),
        radial-gradient(1.5px 1.5px at 35% 90%, {C['star']} 100%, transparent),
        radial-gradient(1px 1px at 80% 5%, {C['star']} 100%, transparent),
        radial-gradient(2px 2px at 50% 50%, {C['star']} 100%, transparent);
    pointer-events: none;
    z-index: 0;
}}

/* Glowing nebula effect */
body::before {{
    content: '';
    position: absolute;
    top: -200px;
    right: -150px;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(167,139,250,0.10) 0%, transparent 70%);
    pointer-events: none;
}}

body::after {{
    content: '';
    position: absolute;
    bottom: -180px;
    left: -120px;
    width: 450px;
    height: 450px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(245,158,11,0.06) 0%, transparent 70%);
    pointer-events: none;
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
    box-shadow: 0 8px 40px {C['shadow']}, 0 0 80px rgba(167,139,250,0.05);
    border: 1px solid {C['divider']};
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}}

/* Top accent line — like a shooting star trail */
.card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 2px;
    background: linear-gradient(90deg, transparent, {C['accent']}, transparent);
    border-radius: 1px;
}}

/* Left decorative line */
.card::after {{
    content: '';
    position: absolute;
    left: 0;
    top: 40px;
    bottom: 40px;
    width: 3px;
    background: linear-gradient(180deg, {C['accent']}, {C['accent_warm']}, transparent);
    border-radius: 2px;
}}

.watermark {{
    position: absolute;
    bottom: 34px;
    right: 44px;
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
    color: {C['accent_light']};
    letter-spacing: 3px;
    margin-bottom: 28px;
    padding: 6px 20px;
    border: 1px solid {C['divider']};
    border-radius: 24px;
    background: rgba(167,139,250,0.06);
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
    font-size: 34px;
    font-weight: 500;
    color: {C['text_warm']};
    letter-spacing: 4px;
    line-height: 1.5;
    text-align: center;
    margin-top: 8px;
    margin-bottom: 6px;
}}

.highlight {{
    font-size: 42px;
    font-weight: 700;
    color: {C['accent_warm']};
    letter-spacing: 4px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 12px;
    width: 100%;
}}

.quote {{
    font-size: 28px;
    font-weight: 400;
    color: {C['text_sub']};
    letter-spacing: 2px;
    line-height: 1.9;
    text-align: center;
    margin-bottom: 6px;
}}

.body-text {{
    font-size: 26px;
    font-weight: 400;
    color: {C['text_soft']};
    letter-spacing: 1.5px;
    line-height: 1.8;
    text-align: center;
    margin-bottom: 6px;
}}

.small-text {{
    font-size: 20px;
    font-weight: 300;
    color: {C['text_soft']};
    letter-spacing: 1.5px;
    text-align: center;
}}

.cta-border {{
    margin-top: 8px;
    padding: 8px 24px;
    border: 1px solid {C['divider']};
    border-radius: 24px;
    color: {C['accent_light']};
    font-size: 20px;
    font-weight: 400;
    letter-spacing: 2px;
    background: rgba(167,139,250,0.06);
}}

.step {{
    font-size: 30px;
    font-weight: 500;
    color: {C['accent']};
    letter-spacing: 2px;
    line-height: 1.6;
    text-align: center;
    margin-bottom: 8px;
    margin-top: 4px;
}}

.spacer {{ height: 14px; }}

/* ─── Per-type adjustments ─── */
.cover .big-title {{
    font-size: 80px;
    letter-spacing: 10px;
    margin-bottom: 10px;
}}
.cover .medium-title {{
    font-size: 34px;
    color: {C['accent_warm']};
    margin-top: 6px;
}}

.scene .quote {{
    font-size: 28px;
    color: {C['text_sub']};
}}
.scene .body-text {{
    margin-top: 8px;
    color: {C['accent_light']};
    font-weight: 500;
}}
.scene .small-text {{
    color: {C['text_warm']};
    font-weight: 400;
}}

.insight .highlight {{
    font-size: 42px;
    padding: 12px 28px;
    background: rgba(245,158,11,0.06);
    border-radius: 12px;
    text-align: center;
    width: 100%;
    border: 1px solid rgba(245,158,11,0.15);
}}
.insight .body-text {{
    font-size: 26px;
}}

.method .step {{
    color: {C['accent']};
}}
.method .body-text {{
    color: {C['text_sub']};
    font-size: 24px;
}}

.gentle .highlight {{
    font-size: 42px;
    color: {C['accent_warm']};
    margin-bottom: 6px;
}}
.gentle .big-title {{
    font-size: 56px;
    color: {C['text_warm']};
    margin-bottom: 18px;
}}
.gentle .quote {{
    font-size: 28px;
    color: {C['text_sub']};
}}
.gentle .body-text {{
    color: {C['accent_light']};
    font-weight: 500;
    font-size: 26px;
}}

.cta .big-title {{
    font-size: 80px;
    letter-spacing: 14px;
    margin-bottom: 10px;
}}
.cta .medium-title {{
    font-size: 34px;
    color: {C['accent_warm']};
    margin-bottom: 20px;
}}
.cta .body-text {{
    font-size: 26px;
    color: {C['text_sub']};
}}
</style>
</head>
<body>
<div class="stars"></div>
<div class="card {type_class}">
    {"".join(lines_html)}
</div>
<div class="watermark">@情绪树洞 · {TODAY_FS}</div>
<div class="page-num">{card_idx} / 6</div>
</body>
</html>"""
    return html


# ─── Main ───────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f"  情绪树洞 Day {DAY_NUM} V2 素材生成")
    print(f"  「{POST_TITLE}」")
    print(f"  V2 角度: {V2_ANGLE}")
    print(f"  配色方案: 深蓝→星夜紫 (vs V1 浅绿→暖白)")
    print(f"{'='*60}\n")

    # 1. Write HTML files
    html_files = []
    for i, card in enumerate(CARDS, 1):
        html_content = make_html(i, card)
        html_path = os.path.join(img_dir, f"card_v2_{i}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        html_files.append(html_path)
        print(f"  ✓ Wrote {html_path}")

    # 2. Render with Playwright
    print(f"\n  Rendering {len(html_files)} cards with Playwright...")
    render_script = """
import sys, os, asyncio
from playwright.async_api import async_playwright

async def render():
    images_dir = sys.argv[1]
    html_files = sorted([f for f in os.listdir(images_dir) if f.endswith('.html')])
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,
        )
        for html_file in html_files:
            path = os.path.join(images_dir, html_file)
            jpg_file = html_file.replace(".html", ".jpg")
            jpg_path = os.path.join(images_dir, jpg_file)
            await page.goto(f"file://{path}", wait_until="networkidle")
            await asyncio.sleep(1.5)
            await page.screenshot(
                path=jpg_path,
                full_page=False,
                quality=95,
                type="jpeg",
            )
            size = os.path.getsize(jpg_path)
            print(f"  ✓ {jpg_file} ({size//1024} KB)")
        await browser.close()

asyncio.run(render())
"""
    result = subprocess.run(
        [sys.executable, "-c", render_script, img_dir],
        capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0:
        print(f"  ✗ Render error: {result.stderr}")
        sys.exit(1)
    print(result.stdout)

    # 3. Collect card info
    cards_info = []
    for i, card in enumerate(CARDS, 1):
        jpg_path = os.path.join(img_dir, f"card_v2_{i}.jpg")
        size = os.path.getsize(jpg_path) if os.path.exists(jpg_path) else 0
        cards_info.append({
            "index": i,
            "file": f"card_v2_{i}.jpg",
            "size": size,
        })

    # 4. Write manifest.json
    manifest = {
        "day_num": DAY_NUM,
        "date": TODAY_FS,
        "series": SERIES,
        "title": POST_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": SERIES_TAG,
        "color_scheme": "深蓝→星夜紫",
        "v2_of": f"day_{TODAY_FS}_day{DAY_NUM}",
        "renderer": "html-fallback",
        "cards": cards_info,
        "images_rendered": True,
        "generated_at": datetime.now().isoformat(),
    }
    manifest_path = os.path.join(day_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Wrote {manifest_path}")

    # 5. Write post_data.json
    post_body = (
        "你有没有发现，\n"
        "我们这一代人，患上了一种叫做「不敢休息」的病。\n"
        "\n"
        "周末躺了半天就开始自责，\n"
        "休假时还要偷偷回工作消息，\n"
        "看一部电影要加速播放，\n"
        "连生病都觉得是自己不够强。\n"
        "\n"
        "有没有一种可能——\n"
        "你之所以这么累，\n"
        "不是因为你做得不够，\n"
        "而是因为你从没真正停下来过。\n"
        "\n"
        "内耗最可怕的地方在于：\n"
        "它让你以为自己很努力，\n"
        "实际上只是在原地反复消耗自己。\n"
        "\n"
        "真正的休息，不是偷懒，是蓄力。\n"
        "你是一台需要保养的机器，不是永动机。\n"
        "\n"
        "所以今天，给你一个任务：\n"
        "放下手机，找个舒服的姿势，\n"
        "什么也不想，什么也不做。\n"
        "\n"
        "就只是——好好待着。\n"
        "\n"
        "记住：你的存在本身，就是价值。\n"
        "你不需要用忙碌来证明自己值得被爱。"
    )

    post_content = {
        "title": POST_TITLE,
        "body": post_body,
        "tags": [
            "情绪树洞",
            "休息是天赋人权",
            "告别内耗",
            "自我和解",
            "当代年轻人",
            "精神状态",
            "治愈系",
            "反内卷",
            "心安理得躺平",
        ],
    }

    post_data = {
        "platform": "xiaohongshu",
        "day_num": DAY_NUM,
        "date": TODAY_FS,
        "series": SERIES,
        "title": POST_TITLE,
        "v2_angle": V2_ANGLE,
        "emotion_tag": SERIES_TAG,
        "color_scheme": "深蓝→星夜紫",
        "v2_of": f"day_{TODAY_FS}_day{DAY_NUM}",
        "post_content": post_content,
        "generated_at": datetime.now().isoformat(),
        "cards": cards_info,
    }
    post_path = os.path.join(day_dir, "post_data.json")
    with open(post_path, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Wrote {post_path}")

    print(f"\n  ✅ Day {DAY_NUM} V2 complete! All files in {day_dir}")
    print(f"  Cards: {len(cards_info)} rendered")
    print(f"  Images: {img_dir}/")


if __name__ == "__main__":
    main()
