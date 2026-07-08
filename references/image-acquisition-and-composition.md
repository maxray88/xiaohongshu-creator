# Image Acquisition & Composition for Xiaohongshu Posts

## Image Specifications

- **Ideal ratio**: 3:4 (portrait) — 1080×1440 pixels
- **Accepted ratios**: 1:1 (square), 4:3 (landscape)
- **Formats**: JPG, PNG, WebP, GIF
- **Max size**: 32MB per image
- **Max count**: 18 images per post

## Image Acquisition Strategy

### Method 1: Bing Image Search (Most Reliable for Anime/Character Images)

Use `requests` + regex to extract `murl` from Bing's HTML. This is more reliable than browser console:

```python
import requests, urllib.parse, re

def search_bing_images(query, count=5):
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/images/search?q={encoded}&first=1"
    resp = requests.get(url, timeout=15, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    })
    html = resp.text
    
    # Extract image URLs — two patterns work:
    urls = re.findall(r'"murl":"(https?://[^"]+)"', html)
    if not urls:
        urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', html)
    
    # Filter
    filtered = []
    seen = set()
    for u in urls:
        u = u.replace('\\u002F', '/')
        if u not in seen and 'bing' not in u and 'microsoft' not in u:
            seen.add(u)
            filtered.append(u)
    
    return filtered[:count]

# Download
def download_image(url, filename):
    resp = requests.get(url, timeout=15, headers={
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.bing.com/',
    })
    if resp.status_code == 200 and len(resp.content) > 5000:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(resp.content))
        img.verify()  # Validate it's a real image
        with open(filename, 'wb') as f:
            f.write(resp.content)
        return True
    return False
```

Works well for anime/character searches (e.g., `"crayon shinchan misae mom"`, `"クレヨンしんちゃん 美伢 キャラクター"`). Returns ~15-20 results per query. Can also use Japanese/Chinese keywords for better results.

### Method 2: Openverse API (CC-Licensed, No Key Needed)

```python
import urllib.request, json, urllib.parse

def search_openverse(query, count=5):
    encoded = urllib.parse.quote(query)
    url = f"https://api.openverse.engineering/v1/images/?q={encoded}&page_size={count}&license=by,by-sa,cc0&extension=jpg,png"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data.get('results', [])

# Usage:
results = search_openverse("anime illustration japanese", count=3)
for i, item in enumerate(results):
    img_url = item.get('url', '')
    title = item.get('title', 'unknown')[:40]
    if img_url:
        download_image(img_url, f"openverse_{i+1}.jpg")
```

**Tips:**
- Search queries in English work best for Openverse
- Results are CC-licensed (by, by-sa, cc0) — safe for commercial use
- Image quality varies; check file size (>5KB is usually real)
- Rate limit: be polite, add `time.sleep(0.5)` between downloads
- Character-specific queries (e.g., "crayon shinchan") return few results on Openverse — use Bing for character images
- Use Japanese/Chinese keywords on Bing for better anime results

**What does NOT work:**
- Pexels web scraping — blocked by anti-bot
- Unsplash Source (`source.unsplash.com`) — 503
- Pixabay — requires API key
- DuckDuckGo image search — connection timeout

### Method 3: Generate with PIL/Pillow

When no suitable image can be found, create a custom design. See "Cover Composition" below.

**Do NOT attempt pixel-by-pixel anime character drawing** — use real photos or simple geometric/stylized designs instead.

## Font Choices for Covers

**Reliable in sandbox:**
- `/System/Library/Fonts/STHeiti Medium.ttc` — best fallback for Chinese text
- `/System/Library/Fonts/Hiragino Sans GB.ttc` — good for body text

**Emoji — ⚠️ CRITICAL: Pillow CANNOT render Apple Color Emoji `.ttc` directly.** Calling `ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", size)` throws `OSError: invalid pixel size`. Pillow's FreeType driver cannot handle bitmap-based color emoji fonts.

**Workaround A — Playwright HTML rendering (BEST, preferred):** Use `scripts/render_covers.py`. It creates an HTML page with native emoji in `<span>` elements and uses `page.screenshot()` to capture at 1080×1440. This produces perfect emoji + Chinese text. See "Cover Rendering" section below.

**Workaround B — Emoji PNG CDN (Pillow-only):** Download 64×64 emoji PNGs and paste as RGBA images:
```python
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
# Download, resize with LANCZOS, paste with alpha:
emoji_img = Image.open(BytesIO(requests.get(url).content)).convert("RGBA").resize((size, size), Image.LANCZOS)
canvas.paste(emoji_img, (x, y), emoji_img)
```

**Font size guidance (user-approved):** Title ≥110px, Subtitle ≥60px, CTA ≥54px, Button ≥42px. Smaller fonts are not readable on mobile.

**Playful/cartoon style (all in `/System/Library/Fonts/`):**
- `Comic Sans MS Bold.ttf` — cartoon, casual
- `Chalkduster.ttf` — chalk hand-drawn
- `MarkerFelt.ttc` — marker pen
- `Bradley Hand Bold.ttf` — handwriting
- `Arial Rounded Bold.ttf` — rounded, friendly
- `Impact.ttf` — bold, attention-grabbing
- `DIN Alternate Bold.ttf` — geometric, clean
- `Tahoma Bold.ttf` — readable, neutral

**Avoid:**
- `PingFang.ttc` — may fail with `OSError: cannot open resource` in sandbox

**Always wrap font loading:**
```python
font = None
for fp in font_paths:
    if os.path.exists(fp):
        try:
            font = ImageFont.truetype(fp, size)
            break
        except: continue
if not font:
    font = ImageFont.load_default()
```

## Complete Image → Cover Pipeline (Recommended Workflow)

Since 2026-05-18, the recommended end-to-end workflow is a single script:

```bash
PYTHON=python3  # Python 3.11 required
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py \
    --query "Crayon Shinchan Misae mom" \
    --title "美伢的5个真相" \
    --emoji "😭" \
    --subtitle "看完妈妈们都哭了" \
    --cta "你家娃也这样吗？" \
    --output /tmp/xhs_covers
```

This single command:
1. Searches Bing with multiple query variants (English + Japanese)
2. Downloads and validates ~10 images
3. Picks top 3 by file size (quality proxy)
4. Renders 3 covers with Playwright (base64 bg + emoji + CJK text)
5. Saves as JPEG 1080×1440

To use pre-downloaded images (skip search):
```bash
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py \
    --query "skip" --images /tmp/my_images \
    --title "标题" --emoji "🔥" --subtitle "副标题" --cta "互动引导"
```

## Cover Composition Workflow

### Method A: Playwright HTML Rendering (BEST — preferred since 2026-05-18)

Use `scripts/render_covers.py` for covers that need emoji + Chinese text:
```bash
PYTHON=python3  # Python 3.11 required
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/render_covers.py --output /tmp/xhs_covers
```

Edit the `designs` list in the script to customize covers. The script:
1. Builds an HTML page per design with gradient backgrounds, title + emoji, subtitle, CTA
2. Uses Playwright headless Chromium to render at 1080×1440
3. Saves as PNG + JPEG (quality=95)

This is the **only reliable way** to render emoji + Chinese text together on covers.

### Method B: Pillow-only (no emoji)

For covers with only Chinese text + image compositing:
1. Load and crop background image to 1080×1440
2. Draw gradient overlays for top (title) and bottom (CTA) areas
3. Draw Chinese text using STHeiti/Arial Rounded fonts
4. For emoji: use the CDN PNG approach above
5. Save as JPEG quality=95

### Xiaohongshu Style v2 Design Elements

- **Diagonal gradient backgrounds** (warm colors)
- **Accent color lines** (16-18px) at top and bottom edges
- **Top area** (~380px): title + subtitle with gradient overlay
- **Bottom area** (~280px): CTA text + pill-shaped button
- **Pill button**: `border-radius = height/2`, accent color fill, white text
- **CTA**: Ask a personal question (not yes/no) to encourage comments. E.g., "你家娃也这样吗？"

## Design Principles for Xiaohongshu

1. **Color**: Warm gradients (orange→pink, pink→purple) perform well
2. **Text readability**: Always use dark overlays or light backgrounds behind text
3. **Emoji**: Use `Apple Color Emoji.ttc` font for colorful emoji rendering
4. **Text density**: Don't overcrowd — leave breathing room
5. **CTA placement**: Bottom area, clear pill-shaped button
6. **Hashtags**: Include in the post content, not as image text
7. **Font pairing**: Use playful fonts (Comic Sans, Chalkduster) for titles + clean fonts (STHeiti) for body
8. **Accent colors**: Use a consistent accent color for lines, pills, and subtitle text