"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ publish_xhs_video.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 — Playwright 无头浏览器上传视频到小红书

使用 Playwright 独立 Chromium，首次需要扫码登录一次，
登录状态保存在 profile 目录，后续 cron 复用。

用法:
  python3 publish_xhs_video.py              # 自动找最新 day
  python3 publish_xhs_video.py --login      # 首次扫码登录
"""
import json, os, subprocess, sys, re, time
from pathlib import Path

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")
SCREENSHOT_DIR = os.path.expanduser("~/.hermes/data/xhs_treehole/video_upload_logs")
PLAYWRIGHT_PROFILE = os.path.expanduser("~/Library/Application Support/Google/Chrome")


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


def do_login():
    """First-time login: open browser, let user scan QR code."""
    from playwright.sync_api import sync_playwright
    print("=" * 60)
    print("🔑 首次登录小红书创作者中心")
    print("=" * 60)
    print("  Playwright 将打开一个浏览器窗口")
    print("  请扫码登录小红书创作者中心")
    print("  登录成功后按 Ctrl+C 关闭窗口")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_PROFILE,
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://creator.xiaohongshu.com", wait_until="domcontentloaded")
        print("  ✅ 浏览器已打开，请扫码登录...")
        page.wait_for_timeout(120000)  # Wait up to 2 min for login
        context.close()
    print("  ✅ 登录状态已保存，后续 cron 将自动复用")


def do_upload():
    """Upload video using saved Playwright profile."""
    from playwright.sync_api import sync_playwright

    day_spec = None
    if len(sys.argv) > 2 and sys.argv[1] == "--day":
        day_spec = sys.argv[2]

    v2_dir, video_path, title, body_text = get_today_info(day_spec)
    day_label = os.path.basename(v2_dir).replace("day_", "").replace("_v2", "")
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    print(f"  日期:    {day_label}")
    print(f"  标题:    {title}")
    print(f"  视频:    {os.path.basename(video_path)} ({os.path.getsize(video_path)/1024/1024:.1f} MB)")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_PROFILE,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,  # XHS blocks headless; window auto-closes
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        # Hide webdriver
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 1. Check login - wait for page to stabilize
        print("\n[1/5] Loading creator.xiaohongshu.com...")
        page.goto("https://creator.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        # Check: if URL still has "login" or page has login button, we're not logged in
        is_login_page = "login" in page.url.lower()
        has_login_btn = page.get_by_text("手机号登录").count() > 0 or page.get_by_text("扫码登录").count() > 0
        if is_login_page or has_login_btn:
            print(f"  ❌ Not logged in (url={page.url[:60]})")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"fail_login_{day_label}.png"))
            context.close()
            sys.exit(1)
        print("  ✅ Logged in")

        # 2. Navigate to publish
        print("[2/5] Opening publish page...")
        page.goto("https://creator.xiaohongshu.com/publish/publish",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # 3. Click video tab
        print("[3/5] Selecting video upload...")
        video_tab = page.get_by_text("上传视频")
        if video_tab.count() > 0:
            video_tab.first.click()
            print("  ✅ Clicked '上传视频'")
        else:
            print("  ⚠ Tab not found, trying file input directly")
        page.wait_for_timeout(1000)

        # 4. Upload file
        print("[4/5] Uploading video...")
        file_input = page.locator("input[type='file']")
        if file_input.count() > 0:
            file_input.first.set_input_files(video_path)
            print(f"  ✅ File selected ({os.path.getsize(video_path)/1024/1024:.1f} MB)")
        else:
            print("  ⚠ No file input, trying drag zone")
        page.wait_for_timeout(5000)

        # Fill title
        title_input = page.get_by_placeholder(lambda p: "标题" in (p or ""))
        if title_input.count() > 0:
            title_input.first.fill(title[:20])
            print(f"  ✅ Title: {title[:20]}")
        page.wait_for_timeout(5000)

        # Screenshot
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"upload_{day_label}.png")
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"  📸 Screenshot: {screenshot_path}")

        context.close()
        print("\n✅ 上传流程完成")
        print(f"  请登录 小红书创作者中心 → 草稿箱 查看")


def main():
    print("=" * 60)
    print("📹 情绪树洞 · 视频自动上传到小红书")
    print("=" * 60)

    if "--login" in sys.argv:
        do_login()
    else:
        do_upload()


if __name__ == "__main__":
    main()
