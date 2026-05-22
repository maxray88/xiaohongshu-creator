#!/usr/bin/env python3
import os
import json
import urllib.request
import sys

def get_tenant_token():
    """Get tenant access token from Feishu using app credentials."""
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    if not app_id or not app_secret:
        print("ERROR: FEISHU_APP_ID and FEISHU_APP_SECRET must be set in ~/.hermes/.env")
        sys.exit(1)
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        token = json.loads(resp.read())["tenant_access_token"]
        return token
    except Exception as e:
        print(f"ERROR: Failed to get tenant token: {e}")
        sys.exit(1)

def send_message(text):
    """Send a text message to the configured home channel."""
    token = get_tenant_token()
    chat_id = os.getenv('FEISHU_HOME_CHANNEL')
    if not chat_id:
        print("ERROR: FEISHU_HOME_CHANNEL must be set in ~/.hermes/.env")
        sys.exit(1)
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        if result.get("code") != 0:
            print(f"ERROR: Failed to send message: {result.get('msg')}")
            sys.exit(1)
        print(f"✅ Message sent, ID: {result['data']['message_id']}")
    except Exception as e:
        print(f"ERROR: HTTP request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cron_notify.py \"message text\"")
        print("Example: cron_notify.py \"✅ Day 2 published: 领导画饼？清醒一点\"")
        sys.exit(1)
    send_message(sys.argv[1])