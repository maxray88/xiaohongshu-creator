# Feishu Channel Notification Pattern

## Use Case
After automated publishing (cron job or manual), send a structured notification report to a Feishu group/channel.

## Prerequisites
Feishu app credentials in `~/.hermes/.env`:
```
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxx
FEISHU_DOMAIN=feishu
FEISHU_HOME_CHANNEL=oc_xxxxxxxxxxxx  # target channel ID
```

## API Pattern (Python urllib)

### Step 1: Get Tenant Access Token
```python
import json, urllib.request

url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
data = json.dumps({
    "app_id": FEISHU_APP_ID,
    "app_secret": FEISHU_APP_SECRET
}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=15)
token = json.loads(resp.read())["tenant_access_token"]
```

### Step 2: Send Text Message to Channel
```python
send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
payload = {
    "receive_id": FEISHU_HOME_CHANNEL,  # chat_id format: oc_xxxxx
    "msg_type": "text",
    "content": json.dumps({"text": "your message here"})
}
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(send_url, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
resp = urllib.request.urlopen(req, timeout=15)
result = json.loads(resp.read())
# result["code"] == 0 means success
# result["data"]["message_id"] is the sent message ID
```

### Key Parameters
- `receive_id_type=chat_id` — required for group/channel messages
- `receive_id` — the chat ID (starts with `oc_`)
- `msg_type=text` — plain text message (use `json.dumps({"text": ...})` for content)

## Pitfalls
- **HTTP 400 with interactive/card msg_type**: The interactive message format requires specific `content` structure. Use `msg_type=text` with `json.dumps({"content": {"text": ...}})` for simple messages, or ensure card JSON matches Feishu's schema exactly.
- **`receive_id_type=open_id` vs `chat_id`**: For channels/groups, MUST use `chat_id`. `open_id` is for direct user messages.
- **Token caching**: Tokens last ~2 hours. Cache within a session but re-fetch if getting 401.

## Cron Job Notification Template
For daily auto-publish reports, use this message structure:
```
📱 [Project Name] · Daily Publish Report

✅ Today's publish: SUCCESS/FAILED
📌 Title: {title}
📅 Day: {current_day} / {total_days}
🕘 Time: {timestamp}

━━━━━━━━━━━━━━

📋 Next preview (Day {next_day}):
Title: {next_title}
Subtitle: {next_subtitle}
CTA: {next_cta}

━━━━━━━━━━━━━━

📊 Weekly schedule:
Day 1 ✅ {title_1}
Day 2 ⏳ {title_2}
...
```

## Session Evidence
- 2026-05-21: Successfully sent publish notification for 小红书情绪树洞 Day 1 to `oc_8a19d24a7aefc9519d114b2159282cc0`. Message ID: `om_x100b6fc47aa8fc7cb4a91d2a9efeea3`.
