#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Creator Login Script

Opens a Chrome browser, navigates to the Xiaohongshu creator login page,
waits for the user to complete login (SMS verification), then saves the
session cookies to a file for persistent authentication.

Usage:
    python3 xhs_login.py [--cookies-file PATH]

Output:
    Saves cookies as JSON to ~/.xiaohongshu-creator/cookies.json (default)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip3 install playwright && python3 -m playwright install chromium")
    sys.exit(1)

DEFAULT_COOKIES_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
LOGIN_URL = "https://creator.xiaohongshu.com/login"
HOME_URL = "https://creator.xiaohongshu.com/"
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"

# URLs that indicate successful login
SUCCESS_URLS = [
    "creator.xiaohongshu.com/publish",
    "creator.xiaohongshu.com/home",
    "creator.xiaohongshu.com/creator",
    "creator.xiaohongshu.com/new",
]

# URLs that indicate still on login page
LOGIN_URLS = [
    "creator.xiaohongshu.com/login",
    "creator.xiaohongshu.com/passport",
]


def is_logged_in(page) -> bool:
    """Check if the current page indicates a logged-in state."""
    current_url = page.url

    # If still on login page, not logged in
    for login_url in LOGIN_URLS:
        if login_url in current_url:
            return False

    # If on a known success URL, logged in
    for success_url in SUCCESS_URLS:
        if success_url in current_url:
            return True

    # If URL is the root domain (not login), likely logged in
    if "creator.xiaohongshu.com" in current_url:
        # Check if login form is still present
        has_login_form = page.query_selector('input[placeholder*="手机号"]') is not None
        has_sms_button = page.query_selector('button:has-text("获取验证码")') is not None
        if not has_login_form and not has_sms_button:
            return True

    return False


def wait_for_login(page, timeout_minutes: int = 5, manual_confirm: bool = False) -> bool:
    """
    Wait for the user to complete login.
    Polls the URL and page state to detect successful authentication.
    If manual_confirm is True, also waits for user to press Enter in the terminal.
    """
    print(f"\n🌐 Browser opened. Please complete login in the Chrome window.")
    print(f"   Waiting up to {timeout_minutes} minutes...")

    if manual_confirm:
        print(f"   (You can also press Enter here after logging in)\n")
    else:
        print()

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    check_interval = 2  # seconds

    # Start a thread to listen for Enter key if manual confirm
    enter_pressed = [False]
    if manual_confirm:
        def wait_enter():
            input()  # Wait for Enter
            enter_pressed[0] = True
        import threading
        t = threading.Thread(target=wait_enter, daemon=True)
        t.start()

    while time.time() - start_time < timeout_seconds:
        try:
            # Check if URL changed to a post-login page
            if is_logged_in(page):
                print("✅ Login detected! URL:", page.url)
                # Wait a bit for all cookies to be set
                time.sleep(3)
                return True

            # Check if user pressed Enter (manual confirm)
            if enter_pressed[0]:
                print("✅ Manual login confirmation received!")
                time.sleep(2)
                return True

            page.wait_for_timeout(check_interval * 1000)

            remaining = int(timeout_seconds - (time.time() - start_time))
            print(f"\r   ⏳ Waiting for login... ({remaining}s remaining)", end="", flush=True)

        except Exception as e:
            print(f"\n   Warning during wait: {e}")
            time.sleep(check_interval)

    print("\n⏰ Login timeout reached.")
    return False


def save_cookies(context, cookies_file: str) -> None:
    """Save browser context cookies to a JSON file."""
    cookies = context.cookies()

    # Ensure directory exists
    os.makedirs(os.path.dirname(cookies_file), exist_ok=True)

    with open(cookies_file, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved {len(cookies)} cookies to {cookies_file}")


def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Creator Login - Save session cookies")
    parser.add_argument(
        "--cookies-file",
        default=DEFAULT_COOKIES_FILE,
        help=f"Path to save cookies (default: {DEFAULT_COOKIES_FILE})",
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
        # Launch visible Chrome (not headless) so user can interact
        print("\n🚀 Opening Chrome browser...")
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1280,900",
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
        )

        # Create a fresh context (no stored state)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        page = context.new_page()

        # Navigate to login page
        print(f"📱 Navigating to {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="commit", timeout=60000)

        # Wait for user to complete login
        if wait_for_login(page, timeout_minutes=args.timeout, manual_confirm=args.manual):
            # Save cookies
            save_cookies(context, cookies_file)

            # Also save storage state (localStorage, sessionStorage)
            storage_state_file = cookies_file.replace(".cookies.json", ".json")
            if storage_state_file == cookies_file:
                storage_state_file = cookies_file.replace(".json", "_state.json")

            state = context.storage_state()
            with open(storage_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved storage state to {storage_state_file}")

            print("\n🎉 Login successful! You can now close the browser.")
            print(f"   Cookies saved to: {cookies_file}")
        else:
            print("\n❌ Login failed or timed out.")
            print("   Please try again.")
            browser.close()
            sys.exit(1)

        browser.close()


if __name__ == "__main__":
    main()
