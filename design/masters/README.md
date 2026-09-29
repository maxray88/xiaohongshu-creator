# Masters — 6 Card Templates (Open Design.app → generators/render_card.py + ComfyUI)

All cards share `design_tokens.json` canvas/spacing/typography. Export as `masters/*.html` references.

| Card | Purpose | Layout key |
|---|---|---|
| cover | Title + series, first-screen emotion keyword | centered title 56px + tag 18px + series caption |
| scene | Relatable everyday situation | left-aligned scene 2–3 lines, soft illustration slot |
| insight | Psychological perspective shift | quote block + accent bar |
| method | 3-step actionable exercise | numbered steps 1·2·3 with icons |
| gentle | Warm message | centered gentle copy + soft gradient |
| cta | Comment call-to-action | question + “评论区聊聊” button |

**Cover spec:** title ≤18 chars, emotion keyword in first line, safe margin 48px, high contrast (deep text on light bg or white on deep bg).

**Export:** Open Design → Export HTML masters to `design/masters/` (kept in sync with generators).
