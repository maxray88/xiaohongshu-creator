# Xiaohongshu AI Detection Failure & Recovery (2026-06-03)

## The Failure
User reported: "草稿保存就触发风控/限号" — even draft-only mode triggers account restriction.
Past auto-publish attempts also resulted in restricted traffic.

## Root Cause: Multi-Layer Detection
Xiaohongshu's AI/bot detection operates at 5 layers:

| Layer | What it checks | Can browser swap fix it? |
|-------|---------------|-------------------------|
| 1. Browser fingerprint | CDP artifacts, navigator.webdriver, DevTools flags | Partial (1/3) |
| 2. Behavioral sequence | Fixed login→upload→fill→save pattern | No |
| 3. Content fingerprint | AI text semantic patterns | No |
| 4. Temporal patterns | Cron-triggered fixed intervals | No |
| 5. Session context | Fresh cookie + immediate script action | No |

Anti-detection mouse curves + random delays only address layer 1 partially. Layers 2-5 remain detectable.

## Solution: Material-Only Mode
Convert all cron jobs from "full automation" to "generate + notify only":

```
SAFE workflow:
1. Cron triggers → generate cover image → /tmp/xhs_covers/dayXX.png
2. Generate content → /tmp/xhs_content/dayXX.txt
3. Send Feishu notification with preview
4. User manually uploads to creator platform
```

## Recovery Path
1. Stop ALL cron jobs that call xhs_publish.py
2. Flagged account: rest 2-4 weeks with zero automation
3. New accounts: first 30 days must be 100% manual
4. After 30 days: resume "material-only" mode

## Firefox Anti-Detect Assessment
- undetected-playwright for Firefox CAN solve layer 1
- DOES NOT solve layers 2-5
- Rewrite cost: all DOM selectors need porting (XHS has Chrome-specific DOM)
- Verdict: not worth it given partial benefit
