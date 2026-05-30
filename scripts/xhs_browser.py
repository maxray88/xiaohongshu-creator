"""
Shared browser/bootstrap helpers for all xiaohongshu-creator scripts.

Provides:
 - load_cookies / save_cookies
 - resolve_cdp_ws_url
 - make_browser_page (sync Playwright)
 - make_browser_page_async (async Playwright + CDP)
 - is_logged_in (sync)
"""
from __future__ import annotations

import http.client
import json
import os
import sys
import time
import urllib.parse
from typing import Optional

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

from xhs_config import (  # noqa: E402
    COOKIES_PATH,
    DEFAULT_CDP_ENDPOINT,
    LOGIN_URL_FRAGMENTS,
    LOGIN_URL,
    PAGE_NAV_WAIT_AFTER_S,
    PAGE_TIMEOUT_MS,
    SUCCESS_URL_FRAGMENTS,
    VIEWPORT,
)


# ── Cookie helpers ─────────────────────────────────────────────────────────────


def load_cookies(cookies_file: str) -> list[dict]:
    """Load a cookies JSON file; exit with a clear message if missing."""
    if not os.path.exists(cookies_file):
        print(f"ERROR: Cookies file not found: {cookies_file}")
        print("Run xhs_login.py first.")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cookies(context, cookies_file: str) -> None:
    """Persist cookies from a Playwright context."""
    os.makedirs(os.path.dirname(cookies_file) or ".", exist_ok=True)
    with open(cookies_file, "w", encoding="utf-8") as f:
        json.dump(context.cookies(), f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(context.cookies())} cookies to {cookies_file}")


# ── CDP resolution ─────────────────────────────────────────────────────────────


def resolve_cdp_ws_url(endpoint: str) -> str:
    """Resolve a CDP endpoint to a ws:// WebSocket URL.

    If the caller already passed a ws:// URL, return it unchanged.
    """
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint
    try:
        parsed = urllib.parse.urlparse(endpoint)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9222
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/json/version")
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read())
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                conn.close()
                return ws_url
        conn.close()
    except Exception:
        pass
    return endpoint


# ── Login-state checker ────────────────────────────────────────────────────────


def is_logged_in(page) -> bool:
    """Heuristic: does the current URL + DOM suggest a logged-in state?"""
    current_url = page.url

    for fragment in LOGIN_URL_FRAGMENTS:
        if fragment in current_url:
            return False

    for fragment in SUCCESS_URL_FRAGMENTS:
        if fragment in current_url:
            return True

    if "creator.xiaohongshu.com" in current_url:
        has_login_form = page.query_selector('input[placeholder*="手机号"]') is not None
        has_sms_button = page.query_selector('button:has-text("获取验证码")') is not None
        if not has_login_form and not has_sms_button:
            return True

    return False


def wait_for_login(page, timeout_minutes: int = 5, manual_confirm: bool = False) -> bool:
    """Poll until logged in (or timeout)."""
    import threading

    print(f"\n⏳ Waiting up to {timeout_minutes} minutes for login...")

    enter_pressed = [False]
    if manual_confirm:
        print("(Press Enter in this terminal after logging in)")
        t = threading.Thread(
            target=lambda: (input(), setattr(enter_pressed, "__setitem__", (0, True)) or None),
            daemon=True,
        )
        # The above lambda trick is brittle; use a closure instead:
        def _wait_enter() -> None:
            input()
            enter_pressed[0] = True

        t = threading.Thread(target=_wait_enter, daemon=True)
        t.start()

    start_time = time.time()
    check_interval = 2

    while time.time() - start_time < timeout_minutes * 60:
        try:
            if is_logged_in(page):
                print("✅ Login detected!")
                time.sleep(3)
                return True
            if enter_pressed[0]:
                print("✅ Manual confirmation received!")
                time.sleep(2)
                return True
            page.wait_for_timeout(check_interval * 1000)
            remaining = int(timeout_minutes * 60 - (time.time() - start_time))
            print(f"\r⏳ Waiting... {remaining}s", end="", flush=True)
        except Exception as exc:
            print(f"\n⚠️  Wait error: {exc}")
            time.sleep(check_interval)

    print("\n⏰ Login timeout reached.")
    return False


# ── Sync browser factory ───────────────────────────────────────────────────────


def make_browser_page(
    cookies_file: str = COOKIES_PATH,
    headless: bool = True,
    cdp_url: Optional[str] = None,
    chrome_bin: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    user_agent: Optional[str] = None,
):
    """Return (browser, context, page) using sync Playwright.

    * If ``cdp_url`` is given, connect over CDP and reuse ``contexts[0]``.
    * Otherwise launch a new Chromium session.
    """
    from xhs_config import CHROME_LAUNCH_ARGS, CHROME_USER_AGENT

    cookies = load_cookies(cookies_file)
    launch_args = list(extra_args or CHROME_LAUNCH_ARGS)
    if user_agent:
        launch_args = launch_args + [f"--user-agent={user_agent}"]

    pw = sync_playwright().start()

    if cdp_url:
        ws_url = resolve_cdp_ws_url(cdp_url)
        browser = pw.chromium.connect_over_cdp(ws_url)
        if not browser.contexts:
            context = browser.new_context(viewport=VIEWPORT, locale="zh-CN")
        else:
            context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
    else:
        browser = pw.chromium.launch(
            headless=headless,
            executable_path=chrome_bin,
            args=launch_args,
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            locale="zh-CN",
            user_agent=user_agent or CHROME_USER_AGENT,
        )
        context.add_cookies(cookies)
        page = context.new_page()

    return browser, context, page


# ── Async browser factory (CDP) ───────────────────────────────────────────────


async def make_browser_page_async(
    cookies_file: str = COOKIES_PATH,
    cdp_endpoint: str = DEFAULT_CDP_ENDPOINT,
):
    """Return (browser, context, page) using async Playwright + CDP.

    This is the path used by ``xhs_publish.py`` which needs async + CDP.
    """
    from xhs_config import CHROME_LAUNCH_ARGS

    cookies = load_cookies(cookies_file)
    ws_url = resolve_cdp_ws_url(cdp_endpoint)

    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(ws_url)
        if not browser.contexts:
            context = await browser.new_context(viewport=VIEWPORT, locale="zh-CN")
        else:
            context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await context.add_cookies(cookies)
        # Hand back the live objects; caller is responsible for closing.
        return browser, context, page


# ── Navigation helper ──────────────────────────────────────────────────────────


def goto_and_wait(page, url: str, wait: str = "commit") -> None:
    """Navigate and pad with a fixed wait so callers don't repeat this idiom."""
    page.goto(url, wait_until=wait, timeout=PAGE_TIMEOUT_MS)
    time.sleep(PAGE_NAV_WAIT_AFTER_S)
    if "login" in page.url:
        print("ERROR: Session expired. Run xhs_login.py first.")
        sys.exit(1)
