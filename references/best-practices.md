# Xiaohongshu Publishing Best Practices

## Content Creation Guidelines

### Title Requirements
- Maximum 20 characters
- Should include emotional hooks, numbers, or questions
- Examples of effective titles:
  - "3个让皮肤变好的秘密"
  - "99%的人不知道的护肤技巧"
  - "为什么你化妆没用？"

## Content Structure
1. Hook - Grab attention immediately
2. Story - Personal experience or narrative
3. Value - What the reader gains
4. Close - Call to action
5. Hashtags - 5-10 relevant tags

## Image Requirements
- Dimensions: 1080x1440 pixels (portrait)
- File size: Max 100MB
- Format: JPG or PNG
- Cover images should have:
  - Warm gradient background
  - High contrast text
  - Clear subject
  - Visible CTA

## Hashtag Strategy
- Mix of broad (#好物分享) + niche (#护肤心得) + trending tags
- Use 5-10 hashtags per post
- Research trending topics daily in the "笔记灵感" section

## Platform Quirks

### event.isTrusted Security
Xiaohongshu implements strict security measures:
- Publish button requires real human click
- Form automation works for title/content
- Image upload must be done via file input
- Bypassing security will result in account restrictions

### File Input Upload Restriction (CRITICAL — 2026-06-20)
Chrome blocks programmatic file attachment to hidden file inputs (`visible: false`). The `opencli browser upload` command returns `{"code":-32000,"message":"Not allowed"}`.

**Workaround**: Use `eval` with DataTransfer API. Full procedure in `references/opencli-xhs-workflow.md` Section 5 and `references/session-learnings-2026-06-20.md`.

### Workaround for Manual Publish
1. Script fills all fields automatically
2. User manually clicks "发布" button
3. Chrome window is auto-activated when needed

## Automation Best Practices

### Timing
- Post 3-5 times per week
- Optimal times: 8-10 AM, 12-2 PM, 8-10 PM

### Engagement
- Reply to every comment within 1 hour
- Engage with 10+ posts daily
- Use the platform's "互动" features

### Account Optimization
- Complete profile
- Consistent niche
- Professional bio with clear value proposition