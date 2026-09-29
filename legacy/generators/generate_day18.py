"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ generate_day18.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Generate Day 18 cards for Xiaohongshu 情绪树洞."""
import json, os, sys
from datetime import datetime

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
DAY_DIR = os.path.join(BASE, "day_20260722_day18")
IMG_DIR = os.path.join(DAY_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

# ── Day 18 content ──────────────────────────────────────
DAY_NUM = 18
SERIES = "社交焦虑自救"
TITLE = "社交焦虑自救指南"
EMOTION_TAG = "实用建议"
COLOR_SCHEME = "柔粉→米白"   # rotating palette

# Color scheme: Soft Pink → Cream White
colors = {
    "bg_start": "#fce4ec",   # soft pink
    "bg_end": "#fef9f0",     # cream white
    "accent": "#e91e63",     # pink accent
    "text_main": "#4a2c2a",  # dark warm brown
    "text_soft": "#8d6e6b",  # soft brown
    "watermark": "#c9a9a6",  # watermark color
}

# ── Card content ─────────────────────────────────────────
cards_data = [
    {
        "type": "cover",
        "lines": [
            {"text": "社交焦虑", "size": 56, "weight": "bold", "color": colors["accent"]},
            {"text": "自救指南", "size": 52, "weight": "bold", "color": colors["text_main"]},
            {"text": "", "size": 20},
            {"text": "你不是一个人", "size": 28, "weight": "normal", "color": colors["text_soft"]},
        ]
    },
    {
        "type": "scene",
        "lines": [
            {"text": "走进人多的地方", "size": 32, "weight": "bold", "color": colors["text_main"]},
            {"text": "心跳就开始加速", "size": 32, "weight": "bold", "color": colors["text_main"]},
            {"text": "", "size": 20},
            {"text": "明明想说话，却张不开口", "size": 26, "weight": "normal", "color": colors["text_soft"]},
            {"text": "生怕自己说错什么", "size": 26, "weight": "normal", "color": colors["text_soft"]},
            {"text": "被所有人注意到", "size": 26, "weight": "normal", "color": colors["text_soft"]},
        ]
    },
    {
        "type": "insight",
        "lines": [
            {"text": "社交焦虑不是你的错", "size": 34, "weight": "bold", "color": colors["accent"]},
            {"text": "", "size": 16},
            {"text": "它是你内心那个", "size": 28, "weight": "normal", "color": colors["text_main"]},
            {"text": "想要保护你的小孩", "size": 28, "weight": "normal", "color": colors["text_main"]},
            {"text": "", "size": 16},
            {"text": "在说：这里不安全", "size": 26, "weight": "normal", "color": colors["text_soft"]},
            {"text": "我们可以慢慢来", "size": 26, "weight": "normal", "color": colors["text_soft"]},
        ]
    },
    {
        "type": "method",
        "lines": [
            {"text": "四步自救法", "size": 36, "weight": "bold", "color": colors["accent"]},
            {"text": "", "size": 20},
            {"text": "① 觉察：意识到焦虑来了", "size": 24, "weight": "normal", "color": colors["text_main"]},
            {"text": "② 呼吸：深呼气，数到四", "size": 24, "weight": "normal", "color": colors["text_main"]},
            {"text": "③ 接纳：允许自己紧张", "size": 24, "weight": "normal", "color": colors["text_main"]},
            {"text": "④ 小行动：只说一句话就好", "size": 24, "weight": "normal", "color": colors["text_main"]},
            {"text": "", "size": 16},
            {"text": "每一步都算数", "size": 26, "weight": "normal", "color": colors["text_soft"]},
        ]
    },
    {
        "type": "gentle",
        "lines": [
            {"text": "你不必变得外向", "size": 32, "weight": "bold", "color": colors["text_main"]},
            {"text": "不必讨好所有人", "size": 32, "weight": "bold", "color": colors["text_main"]},
            {"text": "", "size": 20},
            {"text": "做自己就已经足够", "size": 28, "weight": "normal", "color": colors["accent"]},
            {"text": "", "size": 16},
            {"text": "安静的人,也可以", "size": 24, "weight": "normal", "color": colors["text_soft"]},
            {"text": "拥有很深的力量", "size": 24, "weight": "normal", "color": colors["text_soft"]},
        ]
    },
    {
        "type": "cta",
        "lines": [
            {"text": "你也有社交焦虑吗？", "size": 34, "weight": "bold", "color": colors["text_main"]},
            {"text": "", "size": 24},
            {"text": "评论区说说你的故事", "size": 28, "weight": "normal", "color": colors["accent"]},
            {"text": "", "size": 20},
            {"text": "你不是一个人", "size": 24, "weight": "normal", "color": colors["text_soft"]},
            {"text": "我们都在慢慢变好", "size": 24, "weight": "normal", "color": colors["text_soft"]},
        ]
    },
]

# ── Post body content ───────────────────────────────────
post_body = """社交焦虑不是弱点，是你在保护自己

每次走进人群，心跳就加快
每次要说话，脑子就一片空白
每次聚会后，都要独自充电好久

如果你也是这样，请记住：

你不是不够好
你只是太在意自己的感受
这没有错

试试这个小练习：
下次感到焦虑时
先深呼吸三次
然后告诉自己
"我安全，我只是在成长"

慢慢来
你不需要一夜之间变外向
每天进步一点点就够了""";

# ── HTML Template ───────────────────────────────────────
def make_html(card):
    lines_html = ""
    for line in card["lines"]:
        if not line["text"]:
            lines_html += f'<div style="height:{line["size"]}px;"></div>\n'
        else:
            style = f'font-size:{line["size"]}px; color:{line["color"]};'
            if line["weight"] == "bold":
                style += " font-weight:700;"
            lines_html += f'<div class="line" style="{style}">{line["text"]}</div>\n'

    type_label = {
        "cover": "情绪树洞 · 社交焦虑自救",
        "scene": "你也是这样吗",
        "insight": "看见即疗愈",
        "method": "实用建议",
        "gentle": "温柔提醒",
        "cta": "一起聊聊",
    }.get(card["type"], "")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    width: 1080px; height: 1440px;
    background: linear-gradient(160deg, {colors["bg_start"]}, {colors["bg_end"]});
    font-family: 'Noto Sans SC', sans-serif;
    display: flex; flex-direction: column;
    padding: 70px 80px;
    position: relative;
    overflow: hidden;
  }}
  .tag {{
    font-size: 18px; color: {colors["accent"]}; opacity: 0.7;
    letter-spacing: 2px; margin-bottom: 40px;
  }}
  .content {{
    flex: 1;
    display: flex; flex-direction: column;
    justify-content: center;
  }}
  .line {{
    line-height: 1.6;
    margin-bottom: 6px;
  }}
  .watermark {{
    position: absolute; bottom: 40px; right: 60px;
    font-size: 16px; color: {colors["watermark"]};
    font-weight: 300; letter-spacing: 1px;
  }}
  /* decorative elements */
  .deco {{
    position: absolute;
    border-radius: 50%;
    opacity: 0.06;
  }}
  .deco-1 {{ width:300px; height:300px; background:{colors["accent"]}; top:-80px; right:-80px; }}
  .deco-2 {{ width:200px; height:200px; background:{colors["accent"]}; bottom:100px; left:-60px; }}
</style>
</head>
<body>
  <div class="deco deco-1"></div>
  <div class="deco deco-2"></div>
  {f'<div class="tag">{type_label}</div>' if type_label else ''}
  <div class="content">
    {lines_html}
  </div>
  <div class="watermark">@情绪树洞 · 2026.07.22</div>
</body>
</html>"""
    return html


# ── Generate HTML files ────────────────────────────────
print("Generating HTML files...")
html_files = []
for i, card in enumerate(cards_data, 1):
    html_content = make_html(card)
    fname = f"card_{i}.html"
    fpath = os.path.join(IMG_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html_content)
    html_files.append((i, fpath, f"card_{i}.jpg"))
    print(f"  → {fname}")

# ── Generate manifest ──────────────────────────────────
manifest = {
    "day_num": DAY_NUM,
    "date": "20260722",
    "series": SERIES,
    "title": TITLE,
    "emotion_tag": EMOTION_TAG,
    "color_scheme": COLOR_SCHEME,
    "renderer": "html-playwright",
    "cards": [
        {"index": i, "type": cards_data[i-1]["type"], "file": f"card_{i}.jpg"}
        for i in range(1, 7)
    ],
    "images_rendered": False,
    "generated_at": datetime.now().isoformat(),
}
with open(os.path.join(DAY_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print("  → manifest.json")

# ── Generate post_data ─────────────────────────────────
post_data = {
    "day_num": DAY_NUM,
    "date": "20260722",
    "series": SERIES,
    "title": TITLE,
    "post_body": post_body,
    "hashtags": [
        "#情绪树洞", "#社交焦虑自救", "#社恐", "#内向",
        "#当代年轻人", "#治愈系", "#心灵治愈", "#自我成长"
    ],
    "publish_time": "21:30",
    "generated_at": datetime.now().isoformat(),
}
with open(os.path.join(DAY_DIR, "post_data.json"), "w", encoding="utf-8") as f:
    json.dump(post_data, f, ensure_ascii=False, indent=2)
print("  → post_data.json")

print(f"\nDone! Files in: {IMG_DIR}")
print("Now run Playwright rendering...")
