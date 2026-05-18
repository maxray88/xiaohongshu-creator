"""
Render Xiaohongshu cover images using Playwright HTML rendering.
Supports: CJK text, color emoji, real photo backgrounds (base64 embedded).

Usage:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/render_covers.py \
        --bg /path/to/background.jpg \
        --title "标题" \
        --emoji "😭" \
        --subtitle "副标题" \
        --cta "互动引导语" \
        --output /tmp/cover.jpg

Requirements: playwright, Pillow
    pip install playwright && playwright install chromium
"""
import asyncio, os, base64, argparse
from playwright.async_api import async_playwright
from PIL import Image

def img_to_base64(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

def build_html(d):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:1080px; height:1440px; overflow:hidden; background:#111; }}
.cover {{ width:1080px; height:1440px; position:relative;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "STHeiti", sans-serif; }}
.bg {{ position:absolute; inset:0; background-image:url('{d["bg"]}');
  background-size:cover; background-position:center 20%; }}
.overlay {{ position:absolute; inset:0;
  background:linear-gradient(to bottom,
    {d["accent"]}ee 0%, {d["accent"]}66 20%, transparent 40%,
    transparent 60%, {d["accent"]}55 80%, {d["accent"]}ee 100%); }}
.accent-top {{ position:absolute; top:0; left:0; right:0; height:18px; background:{d["accent"]}; z-index:10; }}
.accent-bot {{ position:absolute; bottom:0; left:0; right:0; height:18px; background:{d["accent"]}; z-index:10; }}
.title-area {{ position:absolute; top:0; left:0; right:0; padding:100px 50px 20px; text-align:center; z-index:5; }}
.title-row {{ display:flex; align-items:center; justify-content:center; gap:16px; margin-bottom:10px; }}
.title-text {{ font-size:112px; font-weight:900; color:#fff;
  text-shadow:4px 6px 14px rgba(0,0,0,0.65); letter-spacing:2px; line-height:1.15; }}
.title-emoji {{ font-size:108px; filter:drop-shadow(3px 4px 8px rgba(0,0,0,0.5)); }}
.subtitle-row {{ display:flex; align-items:center; justify-content:center; gap:8px; }}
.subtitle-text {{ font-size:60px; font-weight:700; color:{d["accent_light"]};
  text-shadow:2px 3px 8px rgba(0,0,0,0.55); }}
.sub-emoji {{ font-size:55px; }}
.cta-area {{ position:absolute; bottom:0; left:0; right:0; padding:20px 50px 55px; text-align:center; z-index:5; }}
.cta-row {{ display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom:28px; }}
.cta-text {{ font-size:54px; font-weight:800; color:#fff; text-shadow:3px 4px 10px rgba(0,0,0,0.65); }}
.cta-emoji {{ font-size:52px; }}
.cta-btn {{ display:inline-flex; align-items:center; gap:12px; padding:24px 68px;
  border-radius:60px; background:{d["accent"]}; font-size:42px; font-weight:800; color:#fff;
  box-shadow:0 8px 24px rgba(0,0,0,0.45); }}
.btn-emoji {{ font-size:40px; }}
</style></head><body>
<div class="cover">
  <div class="bg"></div><div class="overlay"></div>
  <div class="accent-top"></div><div class="accent-bot"></div>
  <div class="title-area">
    <div class="title-row">
      <span class="title-text">{d["title"]}</span>
      <span class="title-emoji">{d["emoji"]}</span>
    </div>
    <div class="subtitle-row">
      <span class="subtitle-text">{d["subtitle"]}</span>
      {f'<span class="sub-emoji">{d["sub_emoji"]}</span>' if d.get("sub_emoji") else ""}
    </div>
  </div>
  <div class="cta-area">
    <div class="cta-row">
      <span class="cta-text">{d["cta"]}</span>
      {f'<span class="cta-emoji">{d["cta_emoji"]}</span>' if d.get("cta_emoji") else ""}
    </div>
    <div class="cta-btn">
      <span>{d["cta_btn"]}</span>
      {f'<span class="btn-emoji">{d["btn_emoji"]}</span>' if d.get("btn_emoji") else ""}
    </div>
  </div>
</div></body></html>"""

async def render_cover(d, output_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1440})
        await page.set_content(build_html(d), timeout=15000)
        await page.wait_for_timeout(1500)
        png_path = output_path.replace(".jpg", ".png")
        await page.screenshot(path=png_path, full_page=False)
        await browser.close()
    img = Image.open(png_path).convert("RGB")
    img.save(output_path, quality=95)
    os.remove(png_path)
    print(f"Saved: {output_path} ({img.size[0]}x{img.size[1]})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Xiaohongshu cover with Playwright")
    parser.add_argument("--bg", required=True, help="Background image path")
    parser.add_argument("--title", required=True, help="Title text")
    parser.add_argument("--emoji", default="", help="Title emoji")
    parser.add_argument("--subtitle", default="", help="Subtitle text")
    parser.add_argument("--cta", default="", help="CTA question text")
    parser.add_argument("--cta-btn", default="评论区见", help="CTA button text")
    parser.add_argument("--accent", default="#dc3c3c", help="Accent color hex")
    parser.add_argument("--accent-light", default="#ffc8b8", help="Accent light color hex")
    parser.add_argument("--output", default="/tmp/cover.jpg", help="Output JPG path")
    args = parser.parse_args()

    design = {
        "bg": img_to_base64(args.bg),
        "accent": args.accent,
        "accent_light": args.accent_light,
        "title": args.title,
        "emoji": args.emoji,
        "subtitle": args.subtitle,
        "cta": args.cta,
        "cta_btn": args.cta_btn,
    }
    asyncio.run(render_cover(design, args.output))
