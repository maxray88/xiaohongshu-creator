"""
Xiaohongshu Image Search → Download → Cover Pipeline
=====================================================
All-in-one tool: search images, generate covers with real backgrounds.

Usage:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py \\
        --query "Crayon Shinchan Misae mom" \\
        --title "美伢的5个真相" \\
        --emoji "😭" \\
        --subtitle "看完妈妈们都哭了" \\
        --cta "你家娃也这样吗？" \\
        --output /tmp/xhs_covers

Steps:
    1. Search Bing for images (multiple queries for variety)
    2. Download and validate images
    3. Pick top 3 by resolution
    4. Render 3 covers using Playwright HTML (base64 bg + emoji + CJK text)
    5. Save as JPEG 1080×1440

Requirements: requests, playwright, Pillow
"""

import argparse, asyncio, os, re, sys, time, base64
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

COVER_W, COVER_H = 1080, 1440

DESIGN_TEMPLATES = [
    {
        "accent": "#dc3c3c", "accent_light": "#ffc8b8",
        "cta_btn": "评论区说说你的故事", "btn_emoji": "❤️",
    },
    {
        "accent": "#b432b4", "accent_light": "#f0c0ff",
        "cta_btn": "留言区见", "btn_emoji": "👇",
    },
    {
        "accent": "#e1941e", "accent_light": "#ffe48c",
        "cta_btn": "说出你的故事", "btn_emoji": "✨",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

EMOJI_CDN = {
    "😭": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/1f62d.png",
    "🌸": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/1f338.png",
    "🔥": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/1f525.png",
    "❤️": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/2764-fe0f.png",
    "👇": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/1f447.png",
    "✨": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/2728.png",
    "💪": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/1f4aa.png",
    "💔": "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/1f494.png",
}

# ─── Image Search ─────────────────────────────────────────────────────────────

def search_bing_images(query: str, count: int = 20) -> list[str]:
    """Search Bing Images and return list of direct image URLs."""
    import requests

    encoded = requests.utils.quote(query)
    url = f"https://www.bing.com/images/search?q={encoded}&first=1&count={count}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text
    except Exception as e:
        print(f"  ⚠️  Bing search failed for '{query}': {e}")
        return []

    # Two patterns for Bing's HTML (they change over time)
    urls1 = re.findall(r'&quot;murl&quot;:&quot;(https?://[^&]+)&quot;', html)
    urls2 = re.findall(r'"murl":"(https?://[^\"]+)"', html)

    # Deduplicate and filter out Bing tracking thumbnails
    seen = set()
    results = []
    for u in urls1 + urls2:
        u = u.replace('\\u002F', '/')
        if u not in seen and 'bing' not in u and 'microsoft' not in u:
            seen.add(u)
            results.append(u)

    return results[:count]


def download_image(url: str, dest: str, min_size: int = 5000) -> bool:
    """Download an image, validate it, return True on success."""
    import requests
    from PIL import Image
    from io import BytesIO

    try:
        resp = requests.get(url, headers={**HEADERS, "Referer": "https://www.bing.com/"}, timeout=12)
        if resp.status_code != 200 or len(resp.content) < min_size:
            return False
        img = Image.open(BytesIO(resp.content))
        img.verify()
        with open(dest, "wb") as f:
            f.write(resp.content)
        return True
    except Exception:
        return False


def search_and_download(query: str, output_dir: str, target: int = 10) -> list[str]:
    """Search multiple query variants and download images. Return list of valid file paths."""
    from PIL import Image

    os.makedirs(output_dir, exist_ok=True)

    # Generate query variants for better coverage
    base = query.strip()
    variants = [base]
    # Add Japanese/Chinese variants if English query
    if re.match(r'^[a-zA-Z\s]+$', base):
        variants.extend([
            f"{base} キャラクター",
            f"{base} イラスト",
        ])

    all_urls = []
    for v in variants:
        urls = search_bing_images(v, count=20)
        all_urls.extend(urls)
        time.sleep(1)

    # Deduplicate
    all_urls = list(dict.fromkeys(all_urls))
    print(f"  Found {len(all_urls)} unique URLs, downloading...")

    downloaded = []
    for i, url in enumerate(all_urls):
        if len(downloaded) >= target:
            break
        ext = "jpg" if any(e in url.lower() for e in (".jpg", ".jpeg")) else "png"
        dest = os.path.join(output_dir, f"img_{len(downloaded)+1:02d}.{ext}")
        if download_image(url, dest):
            try:
                img = Image.open(dest)
                w, h = img.size
                if w >= 300 and h >= 300:
                    downloaded.append(dest)
                    print(f"    ✅ img_{len(downloaded):02d}.{ext} ({w}x{h})")
                else:
                    os.remove(dest)
            except Exception:
                pass

    return downloaded


# ─── Emoji PNG Cache ──────────────────────────────────────────────────────────

def ensure_emoji_cache(cache_dir: str, emojis: list[str]) -> dict[str, str]:
    """Download emoji PNGs if not cached. Returns {emoji: local_path}."""
    import requests

    os.makedirs(cache_dir, exist_ok=True)
    paths = {}
    for emj in emojis:
        local = os.path.join(cache_dir, f"{emj}.png")
        if not os.path.exists(local):
            url = EMOJI_CDN.get(emj)
            if url:
                try:
                    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    with open(local, "wb") as f:
                        f.write(r.content)
                except Exception:
                    pass
        if os.path.exists(local):
            paths[emj] = local
    return paths


# ─── Cover Rendering (Playwright HTML) ────────────────────────────────────────

def img_to_base64(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def build_cover_html(d: dict) -> str:
    """Build HTML for a single cover design. Includes key points from body text."""
    sub_emj_html = f'<span class="sub-emoji">{d.get("sub_emoji","")}</span>' if d.get("sub_emoji") else ""
    cta_emj_html = f'<span class="cta-emoji">{d.get("cta_emoji","")}</span>' if d.get("cta_emoji") else ""
    btn_emj_html = f'<span class="btn-emoji">{d.get("btn_emoji","")}</span>' if d.get("btn_emoji") else ""

    # Build key points HTML (numbered list from body)
    key_points_html = ""
    key_points = d.get("key_points", [])
    if key_points:
        items_html = ""
        for i, point in enumerate(key_points[:5]):  # Max 5 points
            items_html += f'<li><span class="kp-num">{i+1}</span><span class="kp-text">{point}</span></li>\n'
        key_points_html = f'<ul class="key-points">{items_html}</ul>'

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
    {d["accent"]}ee 0%, {d["accent"]}88 18%, transparent 38%,
    transparent 55%, {d["accent"]}55 78%, {d["accent"]}ee 100%); }}
.accent-top {{ position:absolute; top:0; left:0; right:0; height:22px; background:{d["accent"]}; z-index:10; }}
.accent-bot {{ position:absolute; bottom:0; left:0; right:0; height:22px; background:{d["accent"]}; z-index:10; }}

/* ── Title area ── */
.title-area {{ position:absolute; top:0; left:0; right:0; padding:70px 40px 10px; text-align:center; z-index:5; }}
.title-row {{ display:flex; align-items:center; justify-content:center; gap:14px; margin-bottom:10px; flex-wrap:wrap; }}
.title-text {{
  font-size:130px; font-weight:900; color:#fff;
  letter-spacing:3px; line-height:1.1;
  -webkit-text-stroke: 4px {d["accent"]};
  paint-order: stroke fill;
  text-shadow:
    0 0 30px {d["accent"]}cc,
    0 0 60px {d["accent"]}66,
    5px 8px 18px rgba(0,0,0,0.7);
}}
.title-emoji {{ font-size:110px; filter:drop-shadow(4px 6px 12px rgba(0,0,0,0.55)); }}
.subtitle-row {{ display:flex; align-items:center; justify-content:center; gap:10px; }}
.subtitle-text {{
  font-size:68px; font-weight:800; color:{d["accent_light"]};
  text-shadow:
    0 0 20px {d["accent"]}88,
    3px 4px 10px rgba(0,0,0,0.6);
  letter-spacing:1px;
}}
.sub-emoji {{ font-size:60px; }}

/* ── Key points area ── */
.key-points-area {{ position:absolute; top:40%; left:0; right:0; padding:0 55px; z-index:5; }}
.key-points {{ list-style:none; display:flex; flex-direction:column; gap:16px; }}
.key-points li {{ display:flex; align-items:flex-start; gap:16px; }}
.kp-num {{
  display:inline-flex; align-items:center; justify-content:center;
  min-width:52px; height:52px; border-radius:50%;
  background:linear-gradient(135deg, {d["accent"]}, {d["accent_light"]});
  color:#fff; font-size:28px; font-weight:900; flex-shrink:0; margin-top:4px;
  box-shadow:0 4px 12px rgba(0,0,0,0.4);
  border:2px solid rgba(255,255,255,0.3);
}}
.kp-text {{
  font-size:44px; font-weight:700; color:#fff;
  text-shadow:
    0 0 14px {d["accent"]}66,
    2px 3px 8px rgba(0,0,0,0.65);
  line-height:1.45; letter-spacing:0.5px;
}}

/* ── CTA area ── */
.cta-area {{ position:absolute; bottom:0; left:0; right:0; padding:12px 50px 42px; text-align:center; z-index:5; }}
.cta-row {{ display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:22px; }}
.cta-text {{
  font-size:54px; font-weight:900; color:#fff;
  text-shadow:
    0 0 18px {d["accent"]}88,
    3px 5px 12px rgba(0,0,0,0.7);
}}
.cta-emoji {{ font-size:50px; }}
.cta-btn {{
  display:inline-flex; align-items:center; gap:14px;
  padding:22px 68px; border-radius:60px;
  background:linear-gradient(135deg, {d["accent"]}, {d["accent_light"]});
  font-size:42px; font-weight:900; color:#fff;
  box-shadow:0 10px 30px rgba(0,0,0,0.5), 0 0 20px {d["accent"]}44;
  border:2px solid rgba(255,255,255,0.25);
}}
.btn-emoji {{ font-size:40px; }}
</style></head><body>
<div class="cover">
  <div class="bg"></div>
  <div class="overlay"></div>
  <div class="accent-top"></div>
  <div class="accent-bot"></div>
  <div class="title-area">
    <div class="title-row">
      <span class="title-text">{d["title"]}</span>
      <span class="title-emoji">{d["emoji"]}</span>
    </div>
    <div class="subtitle-row">
      <span class="subtitle-text">{d["subtitle"]}</span>
      {sub_emj_html}
    </div>
  </div>
  <div class="key-points-area">
    {key_points_html}
  </div>
  <div class="cta-area">
    <div class="cta-row">
      <span class="cta-text">{d["cta"]}</span>
      {cta_emj_html}
    </div>
    <div class="cta-btn">
      <span>{d["cta_btn"]}</span>
      {btn_emj_html}
    </div>
  </div>
</div></body></html>"""


async def render_covers(designs: list[dict], output_dir: str):
    """Render cover images using Playwright."""
    from playwright.async_api import async_playwright
    from PIL import Image

    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for i, d in enumerate(designs):
            html = build_cover_html(d)
            page = await browser.new_page(viewport={"width": COVER_W, "height": COVER_H})
            await page.set_content(html, timeout=15000)
            await page.wait_for_timeout(1500)

            png_path = os.path.join(output_dir, f"cover_{i+1}.png")
            jpg_path = os.path.join(output_dir, f"cover_{i+1}.jpg")

            await page.screenshot(path=png_path, full_page=False)
            img = Image.open(png_path).convert("RGB")
            img.save(jpg_path, quality=95)

            print(f"  ✅ cover_{i+1}.jpg ({img.size[0]}x{img.size[1]}) — {d['title']} {d['emoji']}")
            await page.close()

        await browser.close()


# ─── Main Pipeline ────────────────────────────────────────────────────────────

async def run_pipeline(args):
    PYTHON = sys.executable
    work_dir = args.output or "/tmp/xhs_covers"
    img_dir = os.path.join(work_dir, "_images")
    os.makedirs(work_dir, exist_ok=True)

    print(f"{'='*60}")
    print(f"Xiaohongshu Image → Cover Pipeline")
    print(f"{'='*60}")

    # ── Step 1: Search & Download ─────────────────────────────────────────
    print(f"\n📸 Step 1: Searching images for '{args.query}'...")
    images = search_and_download(args.query, img_dir, target=args.count)

    if not images:
        print("  ❌ No images found. Trying fallback queries...")
        # Fallback: try simpler queries
        fallback_queries = args.query.split()[:2]
        for fq in fallback_queries:
            images = search_and_download(fq, img_dir, target=args.count)
            if images:
                break

    if not images:
        print("  ❌ All searches failed. Using gradient backgrounds.")
        images = []

    print(f"  ✅ {len(images)} images downloaded to {img_dir}")

    # Sort by file size (larger = higher quality)
    images.sort(key=lambda f: os.path.getsize(f), reverse=True)

    # ── Step 2: Ensure emoji cache ────────────────────────────────────────
    print(f"\n🎨 Step 2: Preparing emoji assets...")
    all_emojis = [args.emoji]
    if args.sub_emoji:
        all_emojis.append(args.sub_emoji)
    if args.cta_emoji:
        all_emojis.append(args.cta_emoji)
    for t in DESIGN_TEMPLATES:
        all_emojis.append(t["btn_emoji"])

    emoji_paths = ensure_emoji_cache(os.path.join(work_dir, "_emoji"), all_emojis)
    print(f"  ✅ {len(emoji_paths)} emoji PNGs ready")

    # ── Step 3: Build designs ─────────────────────────────────────────────
    print(f"\n🖼️  Step 3: Building cover designs...")

    # Pick top 3 images (or cycle if fewer)
    selected = []
    for i in range(3):
        if images:
            selected.append(images[i % len(images)])
        else:
            selected.append(None)

    designs = []
    for i in range(3):
        tmpl = DESIGN_TEMPLATES[i]
        bg = selected[i]

        d = {
            "bg": img_to_base64(bg) if bg else "",
            "accent": tmpl["accent"],
            "accent_light": tmpl["accent_light"],
            "title": args.title,
            "emoji": args.emoji,
            "subtitle": args.subtitle,
            "sub_emoji": args.sub_emoji or "",
            "cta": args.cta,
            "cta_emoji": args.cta_emoji or "",
            "cta_btn": tmpl["cta_btn"],
            "btn_emoji": tmpl["btn_emoji"],
            "key_points": args.key_points if args.key_points else [],
        }

        # If no bg image, use gradient fallback
        if not bg:
            d["bg"] = ""  # Will show dark background

        designs.append(d)
        bg_name = os.path.basename(bg) if bg else "gradient"
        kp_count = len(d["key_points"])
        print(f"  Cover {i+1}: bg={bg_name}, accent={tmpl['accent']}, key_points={kp_count}")

    # ── Step 4: Render ────────────────────────────────────────────────────
    print(f"\n🎬 Step 4: Rendering covers with Playwright...")
    await render_covers(designs, work_dir)

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"✅ DONE — Covers saved to: {work_dir}")
    print(f"{'='*60}")
    for i in range(3):
        jpg = os.path.join(work_dir, f"cover_{i+1}.jpg")
        png = os.path.join(work_dir, f"cover_{i+1}.png")
        if os.path.exists(jpg):
            size = os.path.getsize(jpg) // 1024
            print(f"  📄 cover_{i+1}.jpg ({size}KB)")
        if os.path.exists(png):
            os.remove(png)  # Clean up PNG, keep JPEG

    print(f"\nNext step: Publish with:")
    print(f"  $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \\")
    print(f"    --title \"{args.title}\" \\")
    print(f"    --content \"{args.content or args.subtitle}\" \\")
    print(f"    --images {work_dir}/cover_1.jpg")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Xiaohongshu Image Search → Cover Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search, download, and generate 3 covers:
  %(prog)s --query "Crayon Shinchan Misae mom" \\
           --title "美伢的5个真相" --emoji "😭" \\
           --subtitle "看完妈妈们都哭了" \\
           --cta "你家娃也这样吗？" \\
           --output /tmp/xhs_covers

  # Use pre-downloaded images:
  %(prog)s --query "skip" --images /tmp/my_images \\
           --title "标题" --emoji "🔥" \\
           --subtitle "副标题" --cta "互动引导"
        """
    )

    parser.add_argument("--query", required=True, help="Image search query (or 'skip' to use --images)")
    parser.add_argument("--title", required=True, help="Cover title (Chinese)")
    parser.add_argument("--emoji", required=True, help="Title emoji (e.g., 😭)")
    parser.add_argument("--subtitle", required=True, help="Subtitle text")
    parser.add_argument("--sub-emoji", default="", help="Subtitle emoji (optional)")
    parser.add_argument("--cta", required=True, help="CTA question text")
    parser.add_argument("--cta-emoji", default="", help="CTA emoji (optional)")
    parser.add_argument("--key-points", nargs="+", default=[], help="Key points to display on cover (e.g., '乐高积木' '泡泡玛特盲盒' '指尖陀螺')")
    parser.add_argument("--content", default="", help="Post body content (for publish hint)")
    parser.add_argument("--output", default="/tmp/xhs_covers", help="Output directory")
    parser.add_argument("--count", type=int, default=10, help="Number of images to download")
    parser.add_argument("--images", default="", help="Use pre-downloaded images from this dir")

    args = parser.parse_args()

    if args.query.lower() == "skip" and args.images:
        # Skip search, use provided images
        img_dir = args.images
        images = [
            os.path.join(img_dir, f)
            for f in os.listdir(img_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        images = [f for f in images if os.path.getsize(f) > 5000]
        images.sort(key=lambda f: os.path.getsize(f), reverse=True)
        print(f"Using {len(images)} pre-downloaded images from {img_dir}")
        # Override the search step
        async def run_with_existing():
            work_dir = args.output or "/tmp/xhs_covers"
            os.makedirs(work_dir, exist_ok=True)
            all_emojis = [args.emoji, args.sub_emoji, args.cta_emoji] + [t["btn_emoji"] for t in DESIGN_TEMPLATES]
            all_emojis = [e for e in all_emojis if e]
            emoji_paths = ensure_emoji_cache(os.path.join(work_dir, "_emoji"), all_emojis)
            designs = []
            for i in range(3):
                tmpl = DESIGN_TEMPLATES[i]
                bg = images[i % len(images)] if images else None
                d = {
                    "bg": img_to_base64(bg) if bg else "",
                    "accent": tmpl["accent"],
                    "accent_light": tmpl["accent_light"],
                    "title": args.title,
                    "emoji": args.emoji,
                    "subtitle": args.subtitle,
                    "sub_emoji": args.sub_emoji or "",
                    "cta": args.cta,
                    "cta_emoji": args.cta_emoji or "",
                    "cta_btn": tmpl["cta_btn"],
                    "btn_emoji": tmpl["btn_emoji"],
                }
                designs.append(d)
            await render_covers(designs, work_dir)
            print(f"\n✅ Covers saved to {work_dir}")
        asyncio.run(run_with_existing())
    else:
        asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
