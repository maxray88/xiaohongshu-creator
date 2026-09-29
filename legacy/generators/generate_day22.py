"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day22.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
Generate Day 22: 我的精神状态：稳定地发疯
Series: 当代年轻人精神状态实录
Color scheme: 暖橙→淡娜
"""
import os, json, subprocess, shutil, sys
from datetime import datetime, timezone

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
DAY_NUM = 22
DATE_STR = "20260724"
OUT_DIR = f"{BASE}/day_{DATE_STR}_day{DAY_NUM}"
IMG_DIR = f"{OUT_DIR}/images"
TODAY = "2026-07-24"

# Color scheme: Warm Orange → Light Nude
BG_COLOR_1 = "#FDF6EC"  # warm cream
BG_COLOR_2 = "#FFF4E6"  # light peach
ACCENT = "#C67B4B"      # warm amber/orange
ACCENT_LIGHT = "#E8C9A6" # light caramel
ACCENT_DIM = "#A8653A"  # darker orange
TEXT_DARK = "#2D1B0C"   # deep brown
TEXT_MED = "#8B6F4E"    # medium brown
TEXT_LIGHT = "#C4A88A"  # light brown
WHITE = "#FFFFFF"
CARD_BG = "linear-gradient(155deg, #FDF6EC 0%, #FFF4E6 50%, #FEF0DC 100%)"

os.makedirs(IMG_DIR, exist_ok=True)

# Content for Day 22
TITLE = "我的精神状态：稳定地发疯"
SERIES = "当代年轻人精神状态实录"
EMOTION_TAG = "精神状态"
SERIES_LABEL = "精神状态实录"

# 6-card content
cards_data = [
    {
        "type": "cover",
        "elements": [
            {"tag": "label", "text": SERIES_LABEL},
            {"tag": "spacer", "h": 100},
            {"tag": "big_title", "text": "我的精神状态"},
            {"tag": "big_title_accent", "text": "稳定地发疯"},
            {"tag": "spacer", "h": 40},
            {"tag": "subtitle", "text": "当代年轻人精神状态实录 · 第22天"},
        ]
    },
    {
        "type": "scene",
        "elements": [
            {"tag": "label", "text": "日常场景"},
            {"tag": "spacer", "h": 50},
            {"tag": "body", "text": "白天在工位上岁月静好"},
            {"tag": "body", "text": "深夜在卧室里发疯文学"},
            {"tag": "spacer", "h": 30},
            {"tag": "divider"},
            {"tag": "spacer", "h": 30},
            {"tag": "body_small", "text": "开会时思路清晰仿佛一切尽在掌握"},
            {"tag": "body_small", "text": "下班后因为找不到耳机崩溃五分钟"},
            {"tag": "spacer", "h": 20},
            {"tag": "body_small", "text": "然后在路边买了根烤肠"},
            {"tag": "body_small", "text": "又觉得人间值得"},
        ]
    },
    {
        "type": "insight",
        "elements": [
            {"tag": "label", "text": "一个洞察"},
            {"tag": "spacer", "h": 50},
            {"tag": "quote", "text": "所谓稳定地发疯"},
            {"tag": "quote_accent", "text": "就是学会了与自己的"},
            {"tag": "quote_accent", "text": "混乱和平共处"},
            {"tag": "spacer", "h": 30},
            {"tag": "divider"},
            {"tag": "spacer", "h": 30},
            {"tag": "body_small", "text": "不再试图把自己修好"},
            {"tag": "body_small", "text": "不再假装一切都很好"},
            {"tag": "body_small", "text": "允许自己偶尔失控"},
            {"tag": "body_small", "text": "也是一种清醒的活法"},
        ]
    },
    {
        "type": "method",
        "elements": [
            {"tag": "label", "text": "实操指南"},
            {"tag": "spacer", "h": 50},
            {"tag": "list_item", "num": "1", "text": "允许自己在安全的环境里发疯"},
            {"tag": "list_item", "num": "2", "text": "给情绪一个出口，写下来、喊出来、跑起来"},
            {"tag": "list_item", "num": "3", "text": "分清「真的重要」和「不值得疯」"},
            {"tag": "list_item", "num": "4", "text": "给自己一个「正常营业」的开关"},
            {"tag": "list_item", "num": "5", "text": "疯完了，记得对自己说声辛苦了"},
            {"tag": "spacer", "h": 30},
            {"tag": "body_small", "text": "稳定是一种能力，发疯是一种释放"},
            {"tag": "body_small", "text": "两者不冲突"},
        ]
    },
    {
        "type": "gentle",
        "elements": [
            {"tag": "label", "text": "温柔提醒"},
            {"tag": "spacer", "h": 60},
            {"tag": "quote_gentle", "text": "你不用一直稳定"},
            {"tag": "spacer", "h": 20},
            {"tag": "quote_gentle", "text": "偶尔发疯"},
            {"tag": "quote_gentle", "text": "是身体在保护你"},
            {"tag": "spacer", "h": 30},
            {"tag": "divider"},
            {"tag": "spacer", "h": 30},
            {"tag": "body_small", "text": "那些看似不稳定的日子里"},
            {"tag": "body_small", "text": "你在用自己的方式"},
            {"tag": "body_small", "text": "用力地活着"},
        ]
    },
    {
        "type": "cta",
        "elements": [
            {"tag": "label", "text": "聊一聊"},
            {"tag": "spacer", "h": 80},
            {"tag": "big_title_accent", "text": "你的精神状态"},
            {"tag": "big_title_accent", "text": "今天是什么颜色？"},
            {"tag": "spacer", "h": 40},
            {"tag": "divider"},
            {"tag": "spacer", "h": 30},
            {"tag": "body", "text": "评论区报个到"},
            {"tag": "body_small", "text": "看看有多少人和你一样"},
            {"tag": "spacer", "h": 50},
            {"tag": "footer_text", "text": "情绪树洞 · 陪你一起发疯"},
        ]
    }
]

def build_html(card):
    """Build HTML string from card elements."""
    lines = []
    lines.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1080px; height: 1440px;
    background: ''' + CARD_BG + ''';
    font-family: 'Noto Sans SC', -apple-system, sans-serif;
    display: flex; flex-direction: column;
    padding: 80px 80px 60px 80px;
    position: relative; overflow: hidden;
  }
  .deco-circle {
    position: absolute; border-radius: 50%; pointer-events: none; z-index: 0;
  }
  .deco-1 {
    width: 400px; height: 400px;
    background: radial-gradient(circle, ''' + ACCENT_LIGHT + '''55 0%, transparent 70%);
    top: -100px; right: -80px;
  }
  .deco-2 {
    width: 300px; height: 300px;
    background: radial-gradient(circle, ''' + ACCENT + '''30 0%, transparent 70%);
    bottom: -50px; left: -60px;
  }
  .deco-3 {
    width: 180px; height: 180px;
    border: 2px solid ''' + ACCENT_LIGHT + '''80;
    top: 40%; right: -30px;
  }
  .label {
    font-size: 16px; font-weight: 400;
    color: ''' + ACCENT + ''';
    letter-spacing: 6px;
    padding: 8px 20px;
    border: 1px solid ''' + ACCENT_LIGHT + ''';
    border-radius: 30px;
    display: inline-block; align-self: flex-start;
    background: rgba(255,255,255,0.5);
    backdrop-filter: blur(4px);
    position: relative; z-index: 1;
  }
  .big-title {
    font-size: 72px; font-weight: 900;
    color: ''' + TEXT_DARK + ''';
    line-height: 1.2; letter-spacing: 4px;
    position: relative; z-index: 1;
  }
  .big-title-accent {
    font-size: 72px; font-weight: 900;
    color: ''' + ACCENT + ''';
    line-height: 1.2; letter-spacing: 4px;
    position: relative; z-index: 1;
  }
  .subtitle {
    font-size: 22px; font-weight: 300;
    color: ''' + TEXT_MED + ''';
    letter-spacing: 3px;
    position: relative; z-index: 1;
  }
  .body-text {
    font-size: 32px; font-weight: 400;
    color: ''' + TEXT_DARK + ''';
    line-height: 1.6; letter-spacing: 2px;
    position: relative; z-index: 1;
  }
  .body-small {
    font-size: 26px; font-weight: 300;
    color: ''' + TEXT_MED + ''';
    line-height: 1.6; letter-spacing: 1px;
    position: relative; z-index: 1;
  }
  .quote-text {
    font-size: 38px; font-weight: 500;
    color: ''' + TEXT_DARK + ''';
    line-height: 1.6; letter-spacing: 2px;
    position: relative; z-index: 1;
  }
  .quote-accent {
    font-size: 42px; font-weight: 700;
    color: ''' + ACCENT + ''';
    line-height: 1.5; letter-spacing: 2px;
    position: relative; z-index: 1;
  }
  .quote-gentle {
    font-size: 36px; font-weight: 500;
    color: ''' + TEXT_DARK + ''';
    line-height: 1.6; letter-spacing: 3px;
    position: relative; z-index: 1;
    font-style: italic;
  }
  .quote-gentle::before {
    content: '\\201C';
    font-size: 60px; color: ''' + ACCENT_LIGHT + ''';
    font-weight: 900;
    position: absolute; top: -20px; left: -15px; opacity: 0.4;
  }
  .divider {
    width: 60px; height: 3px;
    background: ''' + ACCENT_LIGHT + ''';
    border-radius: 2px;
    position: relative; z-index: 1;
  }
  .list-item {
    display: flex; align-items: flex-start; gap: 16px;
    position: relative; z-index: 1;
    margin-bottom: 14px;
  }
  .list-num {
    width: 32px; height: 32px;
    background: ''' + ACCENT + ''';
    color: ''' + WHITE + ''';
    font-size: 16px; font-weight: 700;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 4px;
  }
  .list-text {
    font-size: 28px; font-weight: 400;
    color: ''' + TEXT_DARK + ''';
    line-height: 1.5; letter-spacing: 1px;
    padding-top: 3px;
  }
  .footer-text {
    font-size: 20px; font-weight: 300;
    color: ''' + TEXT_LIGHT + ''';
    letter-spacing: 3px;
    position: relative; z-index: 1;
  }
  .watermark {
    position: absolute; bottom: 30px; right: 40px;
    font-size: 14px; font-weight: 300;
    color: ''' + TEXT_LIGHT + ''';
    letter-spacing: 2px; z-index: 2;
  }
  .spacer { position: relative; z-index: 1; }
  .content-wrapper {
    flex: 1;
    display: flex; flex-direction: column;
  }
</style>
</head>
<body>
''')
    lines.append('<div class="deco-circle deco-1"></div>')
    lines.append('<div class="deco-circle deco-2"></div>')
    lines.append('<div class="deco-circle deco-3"></div>')
    lines.append('<div class="content-wrapper">')

    for el in card["elements"]:
        t = el["tag"]
        if t == "label":
            lines.append(f'<div class="label">{el["text"]}</div>')
        elif t == "spacer":
            lines.append(f'<div class="spacer" style="height:{el["h"]}px;"></div>')
        elif t == "big_title":
            lines.append(f'<div class="big-title">{el["text"]}</div>')
        elif t == "big_title_accent":
            lines.append(f'<div class="big-title-accent">{el["text"]}</div>')
        elif t == "subtitle":
            lines.append(f'<div class="subtitle">{el["text"]}</div>')
        elif t == "body":
            lines.append(f'<div class="body-text">{el["text"]}</div>')
        elif t == "body_small":
            lines.append(f'<div class="body-small">{el["text"]}</div>')
        elif t == "quote":
            lines.append(f'<div class="quote-text">{el["text"]}</div>')
        elif t == "quote_accent":
            lines.append(f'<div class="quote-accent">{el["text"]}</div>')
        elif t == "quote_gentle":
            lines.append(f'<div class="quote-gentle">{el["text"]}</div>')
        elif t == "divider":
            lines.append('<div class="divider"></div>')
        elif t == "list_item":
            lines.append(f'''
    <div class="list-item">
      <div class="list-num">{el["num"]}</div>
      <div class="list-text">{el["text"]}</div>
    </div>''')
        elif t == "footer_text":
            lines.append(f'<div class="footer-text">{el["text"]}</div>')

    lines.append('</div>')  # content-wrapper
    lines.append(f'<div class="watermark">情绪树洞 · {TODAY}</div>')
    lines.append('</body></html>')
    return "\n".join(lines)

def render_card(html_content, output_path):
    """Render HTML to JPEG using Playwright."""
    import asyncio
    from playwright.async_api import async_playwright
    
    async def _render():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={"width": 1080, "height": 1440},
                device_scale_factor=2
            )
            await page.set_content(html_content, wait_until="networkidle")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=output_path, full_page=False)
            await browser.close()
    
    asyncio.run(_render())

# Main
print(f"Generating Day {DAY_NUM} — {TITLE}")
print(f"Series: {SERIES}")
print(f"Output: {OUT_DIR}")

for i, card in enumerate(cards_data, 1):
    card_type = card["type"]
    html_content = build_html(card)
    
    html_path = os.path.join(IMG_DIR, f"card_{i}.html")
    img_path = os.path.join(IMG_DIR, f"card_{i}.jpg")
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"  Card {i}/{len(cards_data)} ({card_type}) → rendering...")
    render_card(html_content, img_path)
    
    size = os.path.getsize(img_path)
    print(f"    ✓ {img_path} ({size:,} bytes)")

# Generate manifest
manifest = {
    "day_num": DAY_NUM,
    "date": DATE_STR,
    "series": SERIES,
    "title": TITLE,
    "emotion_tag": EMOTION_TAG,
    "color_scheme": "暖橙→淡娜",
    "renderer": "html-playwright",
    "cards": [
        {"index": i+1, "type": c["type"], "file": f"card_{i+1}.jpg",
         "size": os.path.getsize(os.path.join(IMG_DIR, f"card_{i+1}.jpg"))}
        for i, c in enumerate(cards_data)
    ],
    "images_rendered": True,
    "generated_at": datetime.now(timezone.utc).isoformat()
}

with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

# Generate post data
post_data = {
    "day_num": DAY_NUM,
    "date": DATE_STR,
    "series": SERIES,
    "title": TITLE,
    "emotion_tag": EMOTION_TAG,
    "color_scheme": "暖橙→淡娜",
    "post_content": {
        "title": TITLE,
        "body": (
            "白天在工位上岁月静好，深夜在卧室里发疯文学。\n\n"
            "开会时思路清晰仿佛一切尽在掌握，\n"
            "下班后因为找不到耳机崩溃五分钟，\n"
            "然后在路边买了根烤肠，又觉得人间值得。\n\n"
            "所谓稳定地发疯，\n"
            "就是学会了与自己的混乱和平共处。\n\n"
            "不再试图把自己修好，\n"
            "不再假装一切都很好，\n"
            "允许自己偶尔失控，\n"
            "也是一种清醒的活法。\n\n"
            "你不用一直稳定，\n"
            "偶尔发疯，是身体在保护你。"
        ),
        "tags": [
            "情绪树洞",
            "精神状态",
            "当代年轻人",
            "稳定地发疯",
            "自我和解",
            "治愈系"
        ]
    },
    "cards": manifest["cards"],
    "generated_at": manifest["generated_at"]
}

with open(os.path.join(OUT_DIR, "post_data.json"), "w", encoding="utf-8") as f:
    json.dump(post_data, f, ensure_ascii=False, indent=2)

# Update state file
with open(f"{BASE}/current_day.txt", "w") as f:
    f.write(str(DAY_NUM + 1))

print(f"\n✓ Day {DAY_NUM} complete!")
print(f"  Manifest: {OUT_DIR}/manifest.json")
print(f"  Post data: {OUT_DIR}/post_data.json")
print(f"  State file updated to day {DAY_NUM + 1}")
