#!/usr/bin/env python3
"""
Render Xiaohongshu card-style images (card-xiaohongshu spec) using Playwright.
6 cards: Cover, Point 1, Point 2, Point 3, Point 4, CTA
Each 1080x1440, vertical, soft healing aesthetic.
"""

import asyncio
import os
import argparse
from playwright.async_api import async_playwright

# Card dimensions
WIDTH = 1080
HEIGHT = 1440

# Color palette - soft morandi/pink healing tones
PALETTES = {
    "pink_cream": {
        "bg": "linear-gradient(135deg, #fdf2f8 0%, #fce7f3 50%, #fdf2f8 100%)",
        "accent": "#ec4899",
        "accent_light": "#f9a8d4",
        "text_dark": "#4c1d95",
        "text_mid": "#86198f",
        "text_light": "#be185d",
        "card_bg": "rgba(255, 255, 255, 0.9)",
        "card_border": "rgba(236, 72, 153, 0.2)",
    },
    "blue_twilight": {
        "bg": "linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 50%, #c7d2fe 100%)",
        "accent": "#6366f1",
        "accent_light": "#a5b4fc",
        "text_dark": "#1e1b4b",
        "text_mid": "#312e81",
        "text_light": "#4338ca",
        "card_bg": "rgba(255, 255, 255, 0.95)",
        "card_border": "rgba(99, 102, 241, 0.2)",
    },
    "green_warm": {
        "bg": "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 50%, #bbf7d0 100%)",
        "accent": "#22c55e",
        "accent_light": "#86efac",
        "text_dark": "#14532d",
        "text_mid": "#166534",
        "text_light": "#15803d",
        "card_bg": "rgba(255, 255, 255, 0.95)",
        "card_border": "rgba(34, 197, 94, 0.2)",
    },
    "orange_cream": {
        "bg": "linear-gradient(135deg, #fff7ed 0%, #ffedd5 50%, #fed7aa 100%)",
        "accent": "#f97316",
        "accent_light": "#fdba74",
        "text_dark": "#7c2d12",
        "text_mid": "#9a3412",
        "text_light": "#c2410c",
        "card_bg": "rgba(255, 255, 255, 0.95)",
        "card_border": "rgba(249, 115, 22, 0.2)",
    },
}


def get_palette(day_num: int) -> dict:
    """Rotate through palettes for variety."""
    palettes = list(PALETTES.values())
    return palettes[day_num % len(palettes)]


def build_cover_html(data: dict, palette: dict) -> str:
    """Card 1: Cover - Giant title + subtitle + tag."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
.cover {{ width:100%; height:100%; position:relative;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:{palette['bg']}; }}
.bg-pattern {{ position:absolute; inset:0; opacity:0.4; }}
/* Soft geometric pattern */
.bg-pattern::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0;
  background-image:
    radial-gradient(circle at 20% 20%, {palette['accent']}15 0px, transparent 80px),
    radial-gradient(circle at 80% 80%, {palette['accent_light']}20 0px, transparent 100px),
    radial-gradient(circle at 50% 50%, {palette['accent']}08 0px, transparent 150px); }}
.content {{ position:relative; z-index:1; padding:80px 60px; height:100%;
  display:flex; flex-direction:column; justify-content:center; }}
.tag {{ display:inline-block; padding:12px 32px; border-radius:60px;
  background:{palette['accent']}; color:#fff; font-size:32px; font-weight:700;
  width:fit-content; margin-bottom:40px; box-shadow:0 8px 24px {palette['accent']}40; }}
.main-title {{ font-size:96px; font-weight:900; color:{palette['text_dark']};
  line-height:1.15; letter-spacing:2px; margin-bottom:24px;
  text-shadow:0 2px 8px {palette['accent']}20; }}
.subtitle {{ font-size:48px; font-weight:500; color:{palette['text_mid']};
  line-height:1.4; letter-spacing:1px; opacity:0.9; }}
.watermark {{ position:absolute; bottom:40px; right:40px;
  font-size:28px; color:{palette['text_light']}80; font-weight:500; }}
</style></head><body>
<div class="cover">
  <div class="bg-pattern"></div>
  <div class="content">
    <div class="tag">{data['tag']}</div>
    <div class="main-title">{data['main_title']}</div>
    <div class="subtitle">{data['subtitle']}</div>
  </div>
  <div class="watermark">{data['watermark']}</div>
</div>
</body></html>"""


def build_card1_html(data: dict, palette: dict) -> str:
    """Card 2: Scenario/opening with poignant description."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
.card {{ width:100%; height:100%; position:relative;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:{palette['bg']}; }}
.bg-pattern {{ position:absolute; inset:0; opacity:0.3; }}
.bg-pattern::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0;
  background-image:
    radial-gradient(circle at 10% 10%, {palette['accent']}10 0px, transparent 100px),
    radial-gradient(circle at 90% 90%, {palette['accent_light']}15 0px, transparent 120px); }}
.content {{ position:relative; z-index:1; padding:100px 80px; height:100%;
  display:flex; flex-direction:column; justify-content:center; }}
.number {{ display:inline-block; width:60px; height:60px; border-radius:50%;
  background:{palette['accent']}; color:#fff; font-size:28px; font-weight:800;
  text-align:center; line-height:60px; margin-bottom:32px; }}
.title {{ font-size:58px; font-weight:800; color:{palette['text_dark']};
  line-height:1.25; margin-bottom:32px; letter-spacing:1px; }}
.desc {{ font-size:42px; font-weight:400; color:{palette['text_mid']};
  line-height:1.7; letter-spacing:0.5px; opacity:0.95; }}
.highlight {{ color:{palette['accent']}; font-weight:700; }}
.watermark {{ position:absolute; bottom:40px; right:40px;
  font-size:28px; color:{palette['text_light']}80; font-weight:500; }}
</style></head><body>
<div class="card">
  <div class="bg-pattern"></div>
  <div class="content">
    <div class="number">01</div>
    <div class="title">{data['title']}</div>
    <div class="desc">{data['desc']}</div>
  </div>
  <div class="watermark">{data['watermark']}</div>
</div>
</body></html>"""


def build_card2_html(data: dict, palette: dict) -> str:
    """Card 3: Core insight/quote - large text emphasis."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
.card {{ width:100%; height:100%; position:relative;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:{palette['bg']}; }}
.bg-pattern {{ position:absolute; inset:0; opacity:0.3; }}
.bg-pattern::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0;
  background-image:
    radial-gradient(circle at 50% 30%, {palette['accent']}12 0px, transparent 200px),
    radial-gradient(circle at 50% 70%, {palette['accent_light']}15 0px, transparent 180px); }}
.content {{ position:relative; z-index:1; padding:100px 80px; height:100%;
  display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }}
.number {{ display:inline-block; width:60px; height:60px; border-radius:50%;
  background:{palette['accent']}; color:#fff; font-size:28px; font-weight:800;
  text-align:center; line-height:60px; margin-bottom:40px; }}
.quote {{ font-size:68px; font-weight:800; color:{palette['text_dark']};
  line-height:1.3; letter-spacing:1.5px; margin-bottom:24px; }}
.quote .emphasis {{ color:{palette['accent']}; font-weight:900; }}
.subtext {{ font-size:38px; font-weight:400; color:{palette['text_mid']};
  line-height:1.6; opacity:0.85; max-width:800px; }}
.watermark {{ position:absolute; bottom:40px; right:40px;
  font-size:28px; color:{palette['text_light']}80; font-weight:500; }}
</style></head><body>
<div class="card">
  <div class="bg-pattern"></div>
  <div class="content">
    <div class="number">02</div>
    <div class="quote">{data['quote']}</div>
    <div class="subtext">{data['subtext']}</div>
  </div>
  <div class="watermark">{data['watermark']}</div>
</div>
</body></html>"""


def build_card3_html(data: dict, palette: dict) -> str:
    """Card 4: Action principles (3 or fewer)."""
    items_html = ""
    for i, item in enumerate(data['items'], 1):
        items_html += f"""
    <div class="item">
      <div class="bullet">{i}</div>
      <div class="item-text">{item}</div>
    </div>"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
.card {{ width:100%; height:100%; position:relative;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:{palette['bg']}; }}
.bg-pattern {{ position:absolute; inset:0; opacity:0.3; }}
.bg-pattern::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0;
  background-image:
    radial-gradient(circle at 20% 50%, {palette['accent']}10 0px, transparent 150px),
    radial-gradient(circle at 80% 50%, {palette['accent_light']}15 0px, transparent 150px); }}
.content {{ position:relative; z-index:1; padding:100px 80px; height:100%;
  display:flex; flex-direction:column; justify-content:center; }}
.number {{ display:inline-block; width:60px; height:60px; border-radius:50%;
  background:{palette['accent']}; color:#fff; font-size:28px; font-weight:800;
  text-align:center; line-height:60px; margin-bottom:32px; }}
.title {{ font-size:58px; font-weight:800; color:{palette['text_dark']};
  line-height:1.25; margin-bottom:40px; letter-spacing:1px; }}
.items {{ display:flex; flex-direction:column; gap:28px; }}
.item {{ display:flex; gap:24px; align-items:flex-start; }}
.bullet {{ width:52px; height:52px; border-radius:50%;
  background:{palette['accent']}; color:#fff; font-size:24px; font-weight:800;
  text-align:center; line-height:52px; flex-shrink:0; margin-top:4px;
  box-shadow:0 4px 16px {palette['accent']}40; }}
.item-text {{ font-size:40px; font-weight:500; color:{palette['text_dark']};
  line-height:1.55; letter-spacing:0.5px; }}
.item-text .kw {{ color:{palette['accent']}; font-weight:700; }}
.watermark {{ position:absolute; bottom:40px; right:40px;
  font-size:28px; color:{palette['text_light']}80; font-weight:500; }}
</style></head><body>
<div class="card">
  <div class="bg-pattern"></div>
  <div class="content">
    <div class="number">03</div>
    <div class="title">{data['title']}</div>
    <div class="items">{items_html}</div>
  </div>
  <div class="watermark">{data['watermark']}</div>
</div>
</body></html>"""


def build_card4_html(data: dict, palette: dict) -> str:
    """Card 5: Gentle closure/self-acceptance."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
.card {{ width:100%; height:100%; position:relative;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:{palette['bg']}; }}
.bg-pattern {{ position:absolute; inset:0; opacity:0.35; }}
.bg-pattern::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0;
  background-image:
    radial-gradient(circle at 50% 50%, {palette['accent']}18 0px, transparent 300px); }}
.content {{ position:relative; z-index:1; padding:100px 80px; height:100%;
  display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }}
.number {{ display:inline-block; width:60px; height:60px; border-radius:50%;
  background:{palette['accent']}; color:#fff; font-size:28px; font-weight:800;
  text-align:center; line-height:60px; margin-bottom:40px; }}
.main-text {{ font-size:52px; font-weight:600; color:{palette['text_dark']};
  line-height:1.45; letter-spacing:0.5px; margin-bottom:24px; max-width:850px; }}
.main-text .soft {{ color:{palette['accent']}; font-weight:700; }}
.sub-text {{ font-size:38px; font-weight:400; color:{palette['text_mid']};
  line-height:1.7; opacity:0.85; max-width:800px; }}
.watermark {{ position:absolute; bottom:40px; right:40px;
  font-size:28px; color:{palette['text_light']}80; font-weight:500; }}
</style></head><body>
<div class="card">
  <div class="bg-pattern"></div>
  <div class="content">
    <div class="number">04</div>
    <div class="main-text">{data['main_text']}</div>
    <div class="sub-text">{data['sub_text']}</div>
  </div>
  <div class="watermark">{data['watermark']}</div>
</div>
</body></html>"""


def build_cta_html(data: dict, palette: dict) -> str:
    """Card 6: CTA - Summary + open question."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
.card {{ width:100%; height:100%; position:relative;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:{palette['bg']}; }}
.bg-pattern {{ position:absolute; inset:0; opacity:0.3; }}
.bg-pattern::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0;
  background-image:
    radial-gradient(circle at 30% 30%, {palette['accent']}15 0px, transparent 180px),
    radial-gradient(circle at 70% 70%, {palette['accent_light']}20 0px, transparent 180px); }}
.content {{ position:relative; z-index:1; padding:100px 80px; height:100%;
  display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }}
.number {{ display:inline-block; width:60px; height:60px; border-radius:50%;
  background:{palette['accent']}; color:#fff; font-size:28px; font-weight:800;
  text-align:center; line-height:60px; margin-bottom:32px; }}
.summary-title {{ font-size:52px; font-weight:800; color:{palette['text_dark']};
  line-height:1.3; margin-bottom:24px; letter-spacing:1px; }}
.summary-text {{ font-size:38px; font-weight:400; color:{palette['text_mid']};
  line-height:1.6; opacity:0.85; margin-bottom:50px; max-width:850px; }}
.question-box {{ background:{palette['card_bg']}; border:2px solid {palette['card_border']};
  border-radius:28px; padding:40px 50px; max-width:850px;
  backdrop-filter:blur(10px); box-shadow:0 12px 40px {palette['accent']}15; }}
.question-label {{ font-size:30px; font-weight:700; color:{palette['accent']};
  margin-bottom:16px; letter-spacing:1px; }}
.question {{ font-size:44px; font-weight:600; color:{palette['text_dark']};
  line-height:1.4; letter-spacing:0.5px; }}
.watermark {{ position:absolute; bottom:40px; right:40px;
  font-size:28px; color:{palette['text_light']}80; font-weight:500; }}
</style></head><body>
<div class="card">
  <div class="bg-pattern"></div>
  <div class="content">
    <div class="number">05</div>
    <div class="summary-title">{data['summary_title']}</div>
    <div class="summary-text">{data['summary_text']}</div>
    <div class="question-box">
      <div class="question-label">{data['question_label']}</div>
      <div class="question">{data['question']}</div>
    </div>
  </div>
  <div class="watermark">{data['watermark']}</div>
</div>
</body></html>"""


async def render_html_to_jpg(html: str, output_path: str):
    """Render HTML to JPG via Playwright."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        await page.set_content(html, timeout=15000)
        # Wait for fonts and rendering
        await page.wait_for_timeout(2000)
        png_path = output_path.replace(".jpg", ".png")
        await page.screenshot(path=png_path, full_page=False)
        await browser.close()
    # Convert PNG to JPG
    from PIL import Image
    img = Image.open(png_path).convert("RGB")
    img.save(output_path, quality=95)
    os.remove(png_path)
    print(f"  ✓ Saved: {output_path} ({img.size[0]}x{img.size[1]})")


async def main():
    parser = argparse.ArgumentParser(description="Render 6 card-xiaohongshu images")
    parser.add_argument("--day", type=int, required=True, help="Day number (1-30)")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--title", required=True, help="Main topic title")
    parser.add_argument("--output-dir", required=True, help="Output directory for images")
    parser.add_argument("--author", default="情绪树洞", help="Author name for watermark")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    palette = get_palette(args.day)
    watermark = f"{args.author} · {args.date.replace('-', '.')}"

    # ===== CONTENT FOR DAY 7: "同事不是朋友，保持距离就好" =====
    # Adjust content based on day
    if args.day == 7:
        # Cover
        cover_data = {
            "tag": "职场清醒",
            "main_title": "同事不是朋友\n保持距离\n就好",
            "subtitle": "把边界感留给重要的人，\n把体面留给自己",
            "watermark": watermark,
        }
        # Card 1: Scenario
        card1_data = {
            "title": "午休时的那个瞬间",
            "desc": "你把委屈告诉了坐在对面的同事，\n以为那是信任，\n隔天全组都知道了你的“小情绪”。\n\n<span class=\"highlight\">真正的朋友不需要职场当背景板，\n真正的同事也不需要你的真心换体面。</span>",
            "watermark": watermark,
        }
        # Card 2: Core quote
        card2_data = {
            "quote": "职场关系的本质，\n是<span class=\"emphasis\">利益交换</span>，\n不是情感寄托",
            "subtext": "把“同事”还原成“合作者”，\n把“朋友”留给值得托付的人。\n界限分明，才是成年人最大的体面。",
            "watermark": watermark,
        }
        # Card 3: Action principles
        card3_data = {
            "title": "三条职场护身符",
            "items": [
                "<span class=\"kw\">不透露核心隐私</span>：薪资、家庭矛盾、跳槽计划——只告诉家人和挚友",
                "<span class=\"kw\">不参与办公室八卦</span>：听了当没听，传不到你嘴里，烂不到你手里",
                "<span class=\"kw\">拒绝情绪勒索</span>：帮忙是情分，不帮是本分，“不”是说给自己的安全感",
            ],
            "watermark": watermark,
        }
        # Card 4: Gentle closure
        card4_data = {
            "main_text": "保持距离，\n不是冷漠，<span class=\"soft\">是清醒</span>。",
            "sub_text": "你可以和善、专业、靠谱，\n但不必把心掏给每一个共事的人。\n\n保护好自己的能量场，\n下班后的生活，才真正属于你。",
            "watermark": watermark,
        }
        # Card 5: CTA
        cta_data = {
            "summary_title": "同事≠朋友，\n距离感是最高级的职场修养",
            "summary_text": "把边界立稳了，\n麻烦自然绕道走；\n把心留给懂你的人，\n余生才不辜负。",
            "question_label": "💬 树洞时间",
            "question": "你有过“把同事当朋友然后翻车”的经历吗？\n评论区说说，我们一起长记性。",
            "watermark": watermark,
        }
    else:
        # Generic fallback for other days
        cover_data = {"tag": "情绪树洞", "main_title": args.title, "subtitle": "治愈从这里开始", "watermark": watermark}
        card1_data = {"title": "开始", "desc": "内容待定", "watermark": watermark}
        card2_data = {"quote": "核心洞察", "subtext": "详细说明", "watermark": watermark}
        card3_data = {"title": "行动建议", "items": ["建议一", "建议二", "建议三"], "watermark": watermark}
        card4_data = {"main_text": "温柔收束", "sub_text": "自我和解", "watermark": watermark}
        cta_data = {"summary_title": "总结", "summary_text": "核心观点", "question_label": "聊聊", "question": "你怎么看？", "watermark": watermark}

    # Render all 6 cards
    cards = [
        ("cover_01_main.jpg", build_cover_html(cover_data, palette)),
        ("cover_02_scene.jpg", build_card1_html(card1_data, palette)),
        ("cover_03_insight.jpg", build_card2_html(card2_data, palette)),
        ("cover_04_action.jpg", build_card3_html(card3_data, palette)),
        ("cover_05_healing.jpg", build_card4_html(card4_data, palette)),
        ("cover_06_cta.jpg", build_cta_html(cta_data, palette)),
    ]

    print(f"\n🎨 Rendering 6 cards for Day {args.day} ({args.date})...")
    print(f"   Palette: {list(PALETTES.keys())[args.day % len(PALETTES)]}")
    print(f"   Output: {args.output_dir}\n")

    for filename, html in cards:
        output_path = os.path.join(args.output_dir, filename)
        await render_html_to_jpg(html, output_path)

    print(f"\n✅ All 6 cards rendered successfully!")
    print(f"   Files in {args.output_dir}:")
    for f in os.listdir(args.output_dir):
        if f.endswith(".jpg"):
            size = os.path.getsize(os.path.join(args.output_dir, f)) // 1024
            print(f"     {f} ({size}KB)")


if __name__ == "__main__":
    asyncio.run(main())