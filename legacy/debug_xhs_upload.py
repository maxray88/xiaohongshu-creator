"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ debug_xhs_upload.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 — Playwright 上传视频到小红书（调试版）
先用非无头模式看看到底什么情况。
"""
import json, os, subprocess, sys, re, time
from pathlib import Path

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")
SCREENSHOT_DIR = os.path.expanduser("~/.hermes/data/xhs_treehole/video_upload_logs")

# --- Same get_today_info() ---
def get_today_info(day_spec=None):
    if day_spec:
        candidates = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)) and d.startswith(f"day_{day_spec}") and d.endswith("_v2")], reverse=True)
        if not candidates: print("[FATAL] Day not found"); sys.exit(1)
        v2_name = candidates[0]
    else:
        dirs = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)) and d.startswith("day_") and d.endswith("_v2")], reverse=True)
        if not dirs: print("[FATAL] No v2 dirs"); sys.exit(1)
        v2_name = dirs[0]
    v2_dir = os.path.join(BASE, v2_name)
    v1_name = re.sub(r"_v2$", "", v2_name)
    v1_dir = os.path.join(BASE, v1_name)
    video_path = os.path.join(v2_dir, "video", "video_note.mp4")
    if not os.path.isfile(video_path):
        for root, _, files in os.walk(v2_dir):
            for f in files:
                if f.endswith(".mp4"): video_path = os.path.join(root, f); break
    if not os.path.isfile(video_path): print("[FATAL] No video"); sys.exit(1)
    title = "情绪树洞"; body = ""; tags = []
    p1 = os.path.join(v1_dir, "post_data.json")
    if os.path.isfile(p1):
        with open(p1, "r", encoding="utf-8") as f:
            data = json.load(f)
        pc = data.get("post_content", data)
        title = pc.get("title", data.get("title", title))
        body = pc.get("body", data.get("content_text", ""))
        tags = pc.get("tags", data.get("hashtags", []))
    m2 = os.path.join(v2_dir, "manifest.json")
    if os.path.isfile(m2):
        with open(m2) as f:
            m2d = json.load(f)
        if title == "情绪树洞": title = m2d.get("title", title)
    tags_str = " ".join(tags)
    text_body = (body.strip() + "\n\n" + tags_str).strip()
    return v2_dir, video_path, title, text_body

def main():
    print("=" * 60)
    print("📹 Playwright 上传调试")
    print("=" * 60)
    day_spec = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--day" else None
    v2_dir, video_path, title, body_text = get_today_info(day_spec)
    day_label = os.path.basename(v2_dir).replace("day_", "").replace("_v2", "")
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    print(f"  Video: {video_path}")
    print(f"  Title: {title}")
    print()

    from playwright.sync_api import sync_playwright

    CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    CHROME_PROFILE = os.path.expanduser("~/Library/Application Support/Google/Chrome")

    with sync_playwright() as p:
        # Launch persistent context with the user's Chrome profile
        # Not headless so we can see what happens
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE,
            headless=False,
            executable_path=CHROME_PATH,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            args=["--no-sandbox"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("[1] Navigating to creator.xiaohongshu.com...")
        page.goto("https://creator.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        print(f"  URL: {page.url}")

        if "login" in page.url.lower():
            print("  ❌ Redirected to login page")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_login.png"))
            print("  Screenshot saved: debug_login.png")
            context.close()
            sys.exit(1)

        print("  ✅ Logged in! URL:", page.url[:80])

        # Save screenshot
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"debug_{day_label}.png"), full_page=True)
        print(f"  Screenshot: debug_{day_label}.png")

        # Navigate to publish
        print("\n[2] Opening publish page...")
        page.goto("https://creator.xiaohongshu.com/publish/publish",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        print(f"  URL: {page.url[:80]}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_publish.png"))
        print("  Screenshot: debug_publish.png")

        # Keep browser open for 30s for visual inspection
        print("\n[3] Keeping browser open for 30s for you to see...")
        page.wait_for_timeout(30000)

        context.close()
        print("Done.")

if __name__ == "__main__":
    main()
