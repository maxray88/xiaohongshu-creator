# Session Learnings — 2026-05-18 (Part 2)

## Content Generator — Prompt Template Architecture (1:00 PM session)

### Problem
The `xhs_content_generator.py` script had the LLM prompt template hardcoded as a Python string literal. This caused two issues:
1. **Maintenance difficulty**: Changing the prompt required editing the script
2. **Python `.format()` conflicts**: JSON examples like `{"titles": [...]}` were interpreted as format placeholders, causing `KeyError`

### Solution
Moved prompt template to external file: `templates/xhs_content_prompt_template.md`

**Template file rules:**
- Use `{{}}` for all JSON example braces (escaped for Python `.format()`)
- Use `<=` instead of `≤` (Unicode char causes `SyntaxError` in Python string literals)
- Use `-` instead of `—` (em dash causes `SyntaxError` in Python string literals)
- Only `{topic}` should remain as a single brace (the actual format placeholder)

### LLM Processing Pattern
`xhs_content_generator.py` does NOT call the LLM itself. The workflow is:
1. Script outputs `__AGENT_PROCESS__` signal
2. Agent reads prompt from `/tmp/xhs_content_prompt.txt`
3. Agent generates JSON content via built-in LLM
4. Agent writes JSON to `{output_dir}/content/post_data.json`
5. Re-run with `--from-json` to continue pipeline

## Full Pipeline Execution — End-to-End Test (2:00 PM session)

Successfully ran the complete pipeline for "小新的幸福生活":
1. Content generation → 5 titles, 429-char body, 12 hashtags, 3 cover designs
2. Image search → 3 Bing searches, 5 images each
3. Cover rendering → 3 Playwright-rendered covers (1080x1440)
4. Publishing → CDP connect → form fill → _onPublish() → submitted

### Data Accuracy Note
When presenting analytics data, always double-check that column headers match the correct values. User caught a bug where 点赞 and 评论 values were swapped. **Always verify data mapping before sending reports.**

## Marketing Analysis Workflow (3:00 PM session)

```bash
$PYTHON xhs_analytics.py  # Fetches account + note metrics
```

Cross-reference with `references/xiaohongshu-marketing.md` for benchmarks:
- CTR >5% (cover effectiveness)
- Likes >2% of exposure (resonance)
- Comments >0.5% of exposure (engagement)
- Saves >1% of exposure (value)
- Shares >0.2% of exposure (virality)
