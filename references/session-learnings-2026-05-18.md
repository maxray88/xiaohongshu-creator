# Session Learnings — 2026-05-18

## Cover Image Generation — Emoji Rendering Breakthrough

### Problem
User requested cover images for a Xiaohongshu post about Shinchan's mom (野原美伢). The initial covers had two issues:
1. **Fonts too small** — Title at 72px, subtitle at 42px were not readable on mobile
2. **Emoji not rendering** — Pillow displayed blank/boxes instead of colorful emoji

### Root Cause
**Pillow CANNOT render Apple Color Emoji `.ttc` font.** Calling:
```python
ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 100)
```
throws `OSError: invalid pixel size`. Pillow's FreeType driver cannot handle bitmap-based color emoji fonts (Apple's emoji font uses SBIX/bitmap tables, not standard glyph outlines).

### Solution: Playwright HTML Rendering (BEST)
The most reliable approach is to **skip Pillow entirely** for covers that need emoji:

1. Create an HTML page with CSS-styled layout and native emoji in `<span>` elements
2. Use Playwright headless Chromium to render and screenshot at 1080×1440
3. Convert PNG to JPEG with Pillow

This produces **perfect emoji + Chinese text** because the browser engine handles all rendering.

### Solution: Emoji PNG CDN (Pillow-only fallback)
If Pillow must be used (e.g., compositing with downloaded images):
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
```
Download as 64×64 RGBA PNGs, resize with LANCZOS, and `paste()` onto canvas with alpha channel.

### Approved Font Sizes
User explicitly requested larger fonts. Approved sizes:
- **Title**: 112px (Comic Sans MS Bold)
- **Subtitle**: 60px (Arial Rounded Bold)
- **CTA text**: 54px (STHeiti Medium)
- **Button text**: 42px (STHeiti Medium)
- **Emoji**: 108px (rendered natively via browser or CDN PNG)

### Cover Design v2 Elements
- Diagonal gradient backgrounds (warm colors)
- Accent color lines (16-18px) at top and bottom edges
- Top title area: ~380px with gradient overlay
- Bottom CTA area: ~280px with pill-shaped button
- CTA asks personal question (not yes/no) to encourage comments
- 1080×1440 (3:4 portrait)

### Files Generated
- `/tmp/xhs_covers_v2/cover_1_final.jpg` — 美伢的5个真相 😭 (red gradient)
- `/tmp/xhs_covers_v2/cover_2_final.jpg` — 野原美伢 🌸 (purple gradient)
- `/tmp/xhs_covers_v2/cover_3_final.jpg` — 小新妈妈美伢 🔥 (gold gradient)
- `/tmp/render_covers.py` — Playwright HTML cover rendering script

### Integrating Real Background Images (10:00 AM session)

User requested: "把下载的图片整合进去" — use real downloaded Shinchan/Misae photos as cover backgrounds instead of solid gradients.

**Approach: Base64 embedding in HTML**
```python
def img_to_base64(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"
```

Then use `background-image: url('{b64_data_uri}')` in CSS. This avoids `file://` protocol security restrictions in Playwright.

**Cover layout with real photo:**
```css
.bg {
  position: absolute; inset: 0;
  background-image: url('{b64}');
  background-size: cover;
  background-position: center 20%; /* focus on upper portion for character faces */
}
.overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to bottom,
    {accent}ee 0%, {accent}66 20%, transparent 40%,
    transparent 60%, {accent}55 80%, {accent}ee 100%);
}
```

**Image selection criteria:**
- Minimum 400×500px for 1080×1440 cover (center-cropped)
- Sort by file size (larger = higher quality) when picking from search results
- Use `background-position: center 20%` to focus on character faces (usually in upper portion)

**Files:**
- `/tmp/render_covers_final.py` — final Playwright cover renderer with base64 bg images
- `/tmp/shinchan_imgs/` — downloaded Bing search results (10 usable images)
- `/tmp/xhs_covers_v2/cover_*_final.jpg` — final covers with real backgrounds

### Image Acquisition — Bing Search Pattern
Bing image search HTML structure (as of 2026-05):
```python
# Pattern 1: murl in JSON-like structure
urls = re.findall(r'&quot;murl&quot;:&quot;(https?://[^&]+)&quot;', html)
# Pattern 2: direct JSON
urls2 = re.findall(r'"murl":"(https?://[^"]+)"', html)
combined = list(dict.fromkeys(urls + urls2))
```

**Note**: Bing returns 0 results with `urllib` (no cookies), but works with `requests` library. Always use `requests` with proper headers.

### Key Takeaway
**Never use Pillow's `ImageFont.truetype()` with Apple Color Emoji.** Always use Playwright HTML rendering or CDN PNG approach for emoji in cover images.

**For covers with real photos:** Base64-embed images in HTML `background-image` URLs. Use CSS gradient overlays for text readability.
