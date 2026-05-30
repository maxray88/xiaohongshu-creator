#!/usr/bin/env python3
"""
Xiaohongshu Creator Login Script (refactored)

Opens a Chrome browser, navigates to the Xiaohongshu creator login page,
waits for the user to complete login (SMS verification), then saves the
session cookies to a file for persistent authentication.

Usage:
 python3 xhs_login.py [--cookies-file PATH]

Output:
 Saves cookies as JSON to ~/.xiaohongshu-creator/cookies.json (default)
"""

import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip3 install playwright && python3 -m playwright install chromium")
    sys.exit(1)

import json  # noqa: E402

from xhs_config import LOGIN_URL, COOKIES_PATH  # noqa: E402
from xhs_browser import save_cookies, wait_for_login, is_logged_in  # noqa: E402


from typing import Optional

def find_chrome_binary() -> Optional[str]:
    """Find Chrome/Chromium binary on common paths."""
    import shutil
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    return shutil.which("google-chrome") or shutil.which("chromium")


def main() -> None:
    parser = argparse.ArgumentParser(description="Xiaohongshu Creator Login - Save session cookies")
    parser.add_argument(
        "--cookies-file",
        default=COOKIES_PATH,
        help=f"Path to save cookies (default: {COOKIES_PATH})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Login timeout in minutes (default: 5)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Wait for manual Enter key press to confirm login (more reliable)",
    )
    args = parser.parse_args()

    cookies_file = args.cookies_file

    print("=" * 60)
    print("🔐 Xiaohongshu Creator Login")
    print("=" * 60)

    with sync_playwright() as p:
        print("\n🚀 Opening Chrome browser...")
        chrome_bin = find_chrome_binary()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1280,900",
        ]

        browser = p.chromium.launch(
            headless=False,
            executable_path=chrome_bin,
            args=launch_args,
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = context.new_page()

        print(f"📱 Navigating to {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="commit", timeout=60000)

        if wait_for_login(page, timeout_minutes=args.timeout, manual_confirm=args.manual):
            save_cookies(context, cookies_file)

            storage_state_file = cookies_file.replace(".cookies.json", ".json")
            if storage_state_file == cookies_file:
                storage_state_file = cookies_file.replace(".json", "_state.json")

            state = context.storage_state()
            with open(storage_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved storage state to {storage_state_file}")

            print("\n🎉 Login successful! You can now close the browser.")
            print(f" Cookies saved to: {cookies_file}")
            browser.close()
        else:
            print("\n❌ Login failed or timed out.")
            print(" Please try again.")
            browser.close()
            sys.exit(1)


if __name__ == "__main__":
    main()
