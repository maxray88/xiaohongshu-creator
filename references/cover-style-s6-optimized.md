# S6 Optimized Cover Style - Approved 2026-05-21

## Overview
Warm paper texture style with keyword highlighting. This is the current approved cover style for the "情绪树洞" (Emotional Treehole) account after user rejected heavier AI-feeling styles.

## Design Specifications

### Layout
- **Canvas**: 1080×1440px (3:4 portrait)
- **Background**: Warm paper texture (`#faf6f1`) with subtle gradient overlays
- **Decorative Elements**: Watercolor blobs, corner doodles (✏️📝💭✨), scribble lines

### Typography
- **Title**: 
  - Size: 92px (base) + keyword highlighting up to 105px
  - Weight: 900 (Bold)
  - Color: `#2a2520` (dark warm brown)
  - Transform: `rotate(-0.8deg)` (slight counter-clockwise tilt)
  - Shadow: `3px 3px 0px rgba(0,0,0,0.04)`
  - **Keyword Highlighting**: 
    - Wrap important terms in `**text**` or `<text>` 
    - Color: `#e07850` ( warm terracotta)
    - Size: 105px
    - Shadow: `2px 3px 0px rgba(224,120,80,0.15)`
    - After-element: 8px height accent bar at bottom

- **Subtitle**:
  - Size: 40px
  - Color: `#9a8060` (muted warm gray-brown)
  - Weight: 600 (Semi-bold)
  - Transform: `rotate(0.5deg)` (slight clockwise tilt)

- **Key Points**:
  - Size: 38px
  - Color: `#3a3530` (dark warm gray)
  - Weight: 700 (Bold)
  - Line-height: 1.35
  - **Keyword Highlighting**: Same as title but scaled
    - Color: `#e07850` (same terracotta)
    - Size: 44px
    - Weight: 900
    - Shadow: `1px 1px 0px rgba(224,120,80,0.1)`
    - After-element: 6px height accent bar

- **CTA Text**:
  - Size: 36px
  - Color: `#fff` (white)
  - Weight: 700 (Bold)
  - Letter-spacing: 1px

### Key Point Cards
- **Container**: Flex column with 18px gap
- **Card Design**:
  - Display: flex, align-items:center
  - Gap: 20px (between icon and text)
  - Padding: 18px 28px
  - Background: `#fffef9` (near-white)
  - Border-radius: 6px
  - Shadow: 
    - `2px 3px 10px rgba(0,0,0,0.05)`
    - `0 0 0 1px rgba(0,0,0,0.02)`
  - Transform: `rotate(var(--r, 0deg))` (random slight rotation per card)
  - Border-left: `6px solid var(--c, #e8a87c)` (accent color border)

- **Badge** (left icon):
  - Size: 58×58px
  - Border-radius: 50% (circle)
  - Background: `var(--cb, #fef3e8)` (very light accent)
  - Color: `var(--c, #e8a87c)` (accent color)
  - Font-size: 28px
  - Weight: 900
  - Border: `2.5px dashed var(--c, #e8a87c)`
  - Flex-shrink: 0 (fixed size)

### CTA Button
- **Container**: Absolute positioned at bottom (60px from edge)
- **Design**:
  - Display: inline-block
  - Padding: 20px 56px
  - Background: `#2a2520` (dark warm brown, matches title)
  - Border-radius: 10px
  - Transform: `rotate(-1.2deg)` (slight counter-clockwise tilt)
  - Shadow: `5px 5px 0px rgba(0,0,0,0.08)`

### Decorative Elements
- **Corner Decos** (32px, 18% opacity):
  - Top-left: ✏️ (pencil)
  - Top-right: 📝 (memo)
  - Bottom-left: 💭 (thought bubble)
  - Bottom-right: ✨ (sparkles)
- **Scribble Lines** (3px height, 30% opacity):
  - Top-left area: 180px wide, rotated -3deg
  - Top-right area: 140px wide, rotated 2deg
  - Background: repeating-linear-gradient(90deg, #d4956b 0px, #d4956b 8px, transparent 8px, transparent 14px)
- **Brand Mark**: 
  - Position: bottom-right (22px from bottom, 35px from right)
  - Text: "情绪树洞 🌙"
  - Size: 22px
  - Color: `rgba(0,0,0,0.12)`
  - Weight: 600
  - Transform: `rotate(-2deg)`

### Accent Color Variables
- Primary Accent: `#e8a87c` (warm terracotta/sand)
- Accent Background: `#fef3e8` (very light terracotta)
- Keyword Color: `#e07850` (slightly richer terracotta for emphasis)

## Usage Instructions

### With xhs_image_pipeline.py
```bash
PYTHON=/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
$PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_image_pipeline.py \\
    --query "your background search query" \\
    --title "Your Title Here" \\
    --emoji "🎯" \\
    --subtitle "Your subtitle here" \\
    --cta "Your call-to-action" \\
    --key-points "Key point 1" "Key point 2" "Key point 3" \\
    --output /tmp/xhs_covers
```

### Key Point Formatting
- Use `**important term**` or `<important term>` in key point text to trigger highlighting
- Example: `深度工作**专注力**提升技巧` will make "专注力" highlighted
- Example: `学会说<不>，保护自己的能量` will make "不" highlighted

## Why This Style Works
1. **Warm & Approachable**: Paper texture and warm colors feel inviting, not clinical
2. **Hand-drawn Feel**: Slight rotations, watercolor blobs, and doodles create organic feel
3. **Readability**: Strong contrast between text and background
4. **Emphasis System**: Keyword highlighting draws eye to important concepts
5. **Brand Consistency**: Recognizable visual language builds account identity
6. **Platform Native**: Uses web technologies (HTML/CSS) that render reliably in Xiaohongshu's web view

## Approval History
- **2026-05-21**: User selected S6 style from 6 options
- **2026-05-21**: User requested optimization for keyword highlighting in key points
- **2026-05-21**: Final approved style implemented in xhs_image_pipeline.py