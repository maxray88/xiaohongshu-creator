# Batch Generation + Cron Publishing Workflow

## Overview
This documents the workflow for batch-generating multiple posts and setting up automated daily publishing.

## Use Case
User wants to generate N posts (e.g., 7 for a week), save them as drafts, and auto-publish one per day.

## Workflow

### Step 1: Batch Generate Content + Covers

Create a Python script that generates all N posts' data, then run the image pipeline for each:

```python
# 1. Generate post data JSON for each day
POSTS = [
    {
        "day": 1,
        "title": "工作而已，何必内耗自己",
        "emoji": "🔥",
        "subtitle": "职场反内耗指南",
        "cta": "你遇到过吗？",
        "content": "...",
        "key_points": ["下班就关机", "别过度解读", ...],
        "kp_image_queries": ["office worker tired", ...],
        "bg_query": "office workspace minimal aesthetic"
    },
    # ... more posts
]

# Save each to /tmp/xhs_batch/day{N}/post_data.json

# 2. Run image pipeline for each post
for day in range(1, 8):
    args = argparse.Namespace(
        query=post['bg_query'],
        title=post['title'],
        emoji=post['emoji'],
        subtitle=post['subtitle'],
        sub_emoji='', cta=post['cta'], cta_emoji='',
        key_points=post['key_points'],
        kp_emojis=[],
        kp_image_queries=post['kp_image_queries'],
        content='',
        output=f'/tmp/xhs_batch/day{day}/covers',
        count=5, images=''
    )
    asyncio.run(run_pipeline(args))
```

### Step 2: Batch Save Drafts

Run `xhs_publish.py` with `--draft-only` for each post. Use **short content** (~100 chars) to avoid CLI security scan timeout:

```python
for day in range(1, 8):
    short_content = post['content'][:100]  # Avoid CLI timeout
    asyncio.run(publish(
        image_paths=[cover],
        title=post['title'],
        content=short_content,
        cdp_endpoint='http://127.0.0.1:9222',
        draft_only=True
    ))
```

> ⚠️ Content >~200 chars or with many emojis in CLI args triggers security scan timeout. Always use Python API (`asyncio.run(publish(...))`) for long content.

### Step 3: Create Daily Publish Script

```bash
#!/bin/bash
# /tmp/xhs_batch/daily_publish.sh
DAY_FILE="/tmp/xhs_batch/current_day.txt"
DAY=$(cat "$DAY_FILE" 2>/dev/null || echo "1")
[ "$DAY" -lt 1 ] || [ "$DAY" -gt 7 ] && DAY=1

PYTHON="/Users/maochundong/.hermes/hermes-agent/venv/bin/python3"
$PYTHON /tmp/xhs_batch/publish_day.py --day $DAY 2>&1

NEXT_DAY=$((DAY + 1))
[ "$NEXT_DAY" -gt 7 ] && NEXT_DAY=1
echo "$NEXT_DAY" > "$DAY_FILE"
```

### Step 4: Set Up Cron Job

```bash
# Initialize day counter
echo "1" > /tmp/xhs_batch/current_day.txt

# Cron: 21:00 daily
# Use cronjob tool with schedule "0 21 * * *"
```

The cron job should:
1. Read current day from file
2. Execute daily_publish.sh
3. Increment day (wrap to 1 after 7)
4. Send Feishu notification with result

### Step 5: Manual Publish Test

Before relying on cron, manually publish Day 1 to verify the full pipeline works:

```python
asyncio.run(publish(
    image_paths=[cover_1],
    title=post['title'],
    content=post['content'],  # Full content for actual publish
    cdp_endpoint='http://127.0.0.1:9222',
    draft_only=False
))
```

## Key Pitfalls

| Pitfall | Solution |
|---------|----------|
| CLI content too long | Use Python API, not subprocess/cli |
| Cron task can't find Chrome CDP | Ensure Chrome is running with `--remote-debugging-port=9222` |
| Image upload times out | Wait time scales: 20s + 5s/image |
| Draft saved but content truncated | Draft auto-saves full content from form; use short content just to trigger save |
| Feishu MEDIA:/path doesn't show image | Use Feishu image API upload → image_key → image message flow |
| Strategy pivot mid-task | Save all generated files; new strategy may reuse image pipeline scripts with different content |

## Strategy Pivots

When the user pivots content strategy (e.g., from 冷知识科普 to 泛心理):

1. **Don't redo infrastructure** — image pipeline, publish scripts, and cron are strategy-agnostic
2. **Only content changes** — titles, body text, cover queries, and key points
3. **Save strategy docs** to `references/` for future reference
4. **Reusable assets** — bg images from old strategy may not fit new theme; always search new images


