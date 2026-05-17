# Image Acquisition & Composition for Xiaohongshu Posts

## Image Specifications

- **Ideal ratio**: 3:4 (portrait) — 1080×1440 pixels
- **Accepted ratios**: 1:1 (square), 4:3 (landscape)
- **Formats**: JPG, PNG, WebP, GIF
- **Max size**: 32MB per image
- **Max count**: 18 images per post

## Image Acquisition Strategy

### Method 1: Bing Image Search (Most Reliable)

Use the browser to search Bing Images, then extract direct URLs via JS console:

```python
# Step 1: Navigate to Bing Image Search
browser_navigate(url="https://www.bing.com/images/search?q=关键词&first=1")

# Step 2: Extract media URLs via JS console
browser_console(expression="""
const urls = [];
document.querySelectorAll('a').forEach(a => {
  const href = a.href || '';
  if (href.includes('mm.bing.net') || href.includes('.jpg') || href.includes('.png')) {
    urls.push(href);
  }
});
// Also extract from data-m attributes
document.querySelectorAll('[data-m]').forEach(el => {
  try {
    const m = JSON.parse(el.getAttribute('data-m') || '{}');
    if (m.murl) urls.push(m.murl);
  } catch(e) {}
});
JSON.stringify(urls.slice(0, 20));
""")
```

The `mediaurl` parameter in Bing result URLs contains the direct image URL. Decode it with `urllib.parse.unquote()`.

### Method 2: Direct Download (After Getting URL)

```python
import urllib.request

req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.bing.com/'
})
data = urllib.request.urlopen(req, timeout=15).read()
```

**Working image sources** (as of 2026-05):
- `i2.kknews.cc` — works with Referer header
- `castle.womany.net` — works with Referer header
- `k.sinaimg.cn` — works with Referer header
- `c-ssl.dtstatic.com` — works with Referer header

**Broken sources** (403/404):
- `img.moegirl.org.cn` — 404
- `upload.wikimedia.org` — 404 for specific files
- `static.wikia.nocookie.net` — 404
- `i0.hdslb.com` — 403 (needs special headers)
- `i.pinimg.com` — 403
- Most PNG-specific sites (pngall, pngkey) — 404

### Method 3: Generate with PIL/Pillow

When no suitable image can be found, create a custom design:

```python
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# Create 1080x1440 canvas
W, H = 1080, 1440
canvas = Image.new('RGB', (W, H), (255, 240, 245))

# Draw gradient background
draw = ImageDraw.Draw(canvas)
for y in range(H):
    t = y / H
    r = int(255 * (1 - t * 0.3))
    g = int(200 * (1 - t * 0.3) + 100 * t)
    b = int(220 * (1 - t * 0.2) + 150 * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))
```

**Do NOT attempt pixel-by-pixel anime character drawing** — it produces poor results and is extremely slow. Use real photos or simple geometric/stylized designs instead.

## Image Composition Workflow

### Enhancing a Downloaded Photo

```python
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# Load and resize to fit 1080 width
img = Image.open("/tmp/source.jpg")
ratio = 1080 / img.size[0]
new_h = int(img.size[1] * ratio)
img_resized = img.resize((1080, new_h), Image.LANCZOS)

# Enhance
img_resized = ImageEnhance.Color(img_resized).enhance(1.2)
img_resized = ImageEnhance.Contrast(img_resized).enhance(1.1)
img_resized = ImageEnhance.Brightness(img_resized).enhance(1.05)

# Create 1080x1440 canvas and paste
canvas = Image.new('RGB', (1080, 1440), (255, 240, 245))
canvas.paste(img_resized, (0, 0))

# Add gradient overlay at bottom for text readability
draw = ImageDraw.Draw(canvas)
img_bottom = new_h
for y in range(img_bottom - 150, 1440):
    if y < img_bottom:
        t = (y - (img_bottom - 150)) / 150
        alpha = t * 0.7
    else:
        alpha = 0.7
    for x in range(1080):
        r, g, b = canvas.getpixel((x, y))
        # Blend with warm pink
        nr = int(r * (1 - alpha) + 255 * alpha)
        ng = int(g * (1 - alpha) + 182 * alpha)
        nb = int(b * (1 - alpha) + 193 * alpha)
        canvas.putpixel((x, y), (nr, ng, nb))
```

### Adding Text Overlay

Use system Chinese fonts (macOS):
- `/System/Library/Fonts/PingFang.ttc` — modern, clean
- `/System/Library/Fonts/STHeiti Medium.ttc` — reliable fallback
- `/System/Library/Fonts/Hiragino Sans GB.ttc` — good for body text

```python
font_title = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 68)
font_body = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 38)
font_cta = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 44)

# Title with background pill for readability
draw.rounded_rectangle([(100, 30), (980, 130)], radius=20, fill=(255, 255, 255))
draw.text((540, 80), "标题文字", fill=(180, 50, 80), font=font_title, anchor='mm')

# Body text
draw.text((80, y_pos), "正文内容", fill=(60, 30, 50), font=font_body)

# CTA
draw.text((540, cta_y), "评论区告诉我～ 💕", fill=(180, 40, 70), font=font_cta, anchor='mt')
```

## Design Principles for Xiaohongshu

1. **Warm color palettes** (pink, coral, warm white) perform well
2. **White text on dark gradient** or **dark text on white pill** for readability
3. **Emoji usage**: moderate, natural — 1-3 per section max
4. **Text density**: Don't overcrowd — leave breathing room
5. **CTA placement**: Bottom 1/3 of the image, clear and inviting
6. **Hashtags**: Include in the post content, not as image text
