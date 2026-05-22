# S6 Style Optimizations (2026-05-22) — 职场搞钱与搞副业（现实主义）

## Summary
Updated the default S6 hand-drawn cover template to meet realistic monetization niche requirements: larger fonts, stroke+glow effects, centered layout, and precise vertical positioning for readability.

## CSS Changes in `xhs_image_pipeline.py` (`build_cover_html`)

### Title
- **Before**: `font-size: 92px`, simple `text-shadow`
- **After**: `font-size: 130px` (spec ≥130px), `-webkit-text-stroke: 2px solid #C9A66B`, enhanced `text-shadow` for glow
- **Keyword (`.kw`)**: `150px` (20% larger)

### Key Points
- **Before**: `font-size: 38px`, left-aligned, no stroke, `top: 390px`
- **After**: `font-size: 110px` (spec ≥88px, choose larger for emphasis), `-webkit-text-stroke: 1px solid #C9A66B`, soft glow
- **Keyword (`.kw`)**: `130px`
- **Layout**: `justify-content: center` on `.kp-card`, `top: 480px` (adjusted to fit 4 cards without clipping)
- **Spacing**: `gap: 15px`, card `padding: 16px 24px`, badge `64px`
- **Result**: 4 cards fit comfortably within 1440px height with title and CTA.

### General
- All sizes are minimums; can be adjusted per campaign.

## Rationale
- User feedback: initial covers had fonts too small and text concentrated in top-left.
- Larger fonts + stroke + glow improve readability on mobile and create stronger visual hierarchy.
- Centered key points align with S6 natural aesthetic and "realism" tone.

## Usage Notes
- These changes are now the default for all covers generated via `xhs_image_pipeline.py`.
- If a different look is desired (e.g., minimal style), consider custom HTML overrides or reintroduce legacy sizes via script parameters.

## Related Niche: 职场搞钱与搞副业（现实主义）
- Content pillars: 副业实操, AI工具, 省钱攒钱, 逆袭故事
- Tone: 真实、可复刻、拒绝画饼
- Cover elements: warm paper texture, watercolor blobs, keyword highlighting, CTA emphasis
- See `make-money-xiaohongshu` skill for full strategy.
