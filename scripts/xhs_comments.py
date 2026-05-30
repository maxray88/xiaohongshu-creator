#!/usr/bin/env python3
"""
Xiaohongshu Comment Management Script (refactored)

Reads comments on your posts from the creator platform and allows
replying to them. Also supports posting new comments on www.xiaohongshu.com
via CDP (logged-in Chrome).

Usage:
 python3 xhs_comments.py --action list [--note-title TITLE] [--cookies-file PATH]
 python3 xhs_comments.py --action reply --comment-id ID --message TEXT [--cookies-file PATH]
 python3 xhs_comments.py --action batch-reply --message TEXT [--cookies-file PATH]
 python3 xhs_comments.py --action mark-read
 python3 xhs_comments.py --action post --note-url URL --message TEXT [--cdp URL]
 python3 xhs_comments.py --action post --profile URL --note-index N --message TEXT [--cdp URL]

Actions:
 list - List all comments on your posts (creator platform)
 reply - Reply to a specific comment (creator platform)
 batch-reply - Reply to all unread comments with the same message
 mark-read - Mark all comments as read
 post - Post a new comment on www.xiaohongshu.com via CDP

Note: The `post` action requires a logged-in Chrome with CDP on port 9222.
 Direct /explore/ URLs return 404 — must navigate via profile page click.
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
    print("ERROR: playwright not installed.")
    sys.exit(1)

from xhs_config import (  # noqa: E402
    COOKIES_PATH,
    CREATOR_HOME,
    DEFAULT_CDP_URL,
    LOGIN_URL_FRAGMENTS,
    NOTE_MANAGER_URL,
    PAGE_TIMEOUT_MS,
    PUBLIC_HOME,
    SELECTOR_COMMENT_INPUT,
    SELECTOR_SEND_BTN,
    SUCCESS_URL_FRAGMENTS,
)
from xhs_browser import load_cookies, make_browser_page  # noqa: E402
from xhs_utils import force_click  # noqa: E402


# ── Core CDP comment-posting (canonical, shared with engage.py style) ─────────


def post_comment_cdp(note_url, message, cdp_url=DEFAULT_CDP_URL, profile_url=None, note_index=0) -> bool:
    """
    Post a comment on www.xiaohongshu.com via CDP (logged-in Chrome).

    Two modes:
    1. --note-url mode: Navigate to profile, find matching note by title, click it, post comment
    2. --profile + --note-index mode: Navigate to profile, click Nth note card, post comment

    Key pitfalls:
    - Direct /explore/ URLs return 404 (error_code=300031). Must navigate via profile page click.
    - Comment input has `not-active` overlay — use force=True to bypass.
    - Send button: button.btn.submit or button:has-text("发送")
    """
    browser, context, page = make_browser_page(
        cookies_file=COOKIES_PATH,
        cdp_url=cdp_url,
    )

    try:
        # Navigate to profile page
        target_profile = profile_url or "https://www.xiaohongshu.com/user/profile/598b76525e87e778c1141505"
        print(f"Navigating to profile: {target_profile}")
        page.goto(target_profile, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
        time.sleep(8)

        current_url = page.url
        for fragment in LOGIN_URL_FRAGMENTS:
            if fragment in current_url:
                print("ERROR: Not logged in on www.xiaohongshu.com")
                page.close()
                browser.close()
                return False

        # Scroll to notes section
        page.evaluate("window.scrollBy(0, 600)")
        time.sleep(3)

        # Find note cards
        notes = page.evaluate("""() => {
        const results = [];
        const items = document.querySelectorAll('.note-item');
        items.forEach((item, i) => {
        const rect = item.getBoundingClientRect();
        const link = item.querySelector('a[href*="/explore/"]');
        const title = item.querySelector('[class*="title"]');
        results.push({
        index: i,
        rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)},
        href: link ? link.href : '',
        title: title ? title.innerText.trim().substring(0, 60) : '',
        });
        });
        return results;
        }""")

        if not notes:
            print("ERROR: No note cards found on profile page")
            page.close()
            browser.close()
            return False

        print(f"Found {len(notes)} note cards")
        for n in notes:
            print(f" [{n['index']}] {n['title'][:40]}")

        # Select target note
        if note_url:
            target = None
            for n in notes:
                if note_url in n['href'] or n['href'] in note_url:
                    target = n
                    break
            if not target:
                print(f"WARNING: Note URL not found in profile cards, using index 0")
                target = notes[0]
        else:
            if note_index >= len(notes):
                print(f"ERROR: note-index {note_index} out of range (max {len(notes)-1})")
                page.close()
                browser.close()
                return False
            target = notes[note_index]

        print(f"Target note: {target['title']}")

        # Click note card to open it (SPA routing)
        cx = target['rect']['x'] + target['rect']['w'] // 2
        cy = target['rect']['y'] + target['rect']['h'] // 2
        print(f"Clicking note card at ({cx}, {cy})")
        page.mouse.click(cx, cy)
        time.sleep(6)

        # Check if we're on the note page
        if 'explore/' not in page.url:
            print(f"WARNING: Page URL didn't change to note page: {page.url}")
            # Try clicking again
            page.mouse.click(cx, cy)
            time.sleep(5)

        print(f"Note page URL: {page.url}")

        # Activate comment input
        print("Activating comment input...")
        try:
            page.click(SELECTOR_COMMENT_INPUT, force=True, timeout=5000)
        except Exception:
            force_click(page, SELECTOR_COMMENT_INPUT)
        time.sleep(1)

        # Type comment
        print(f"Typing: {message}")
        page.keyboard.type(message, delay=80)
        time.sleep(1)

        # Verify typed content
        typed = page.evaluate("() => { const el = document.querySelector('#content-textarea'); return el ? (el.innerText || el.value || '') : ''; }")
        print(f"Typed content: '{typed}'")

        if not typed:
            print("ERROR: Failed to type comment")
            page.close()
            browser.close()
            return False

        # Click send button
        print("Clicking send...")
        try:
            page.click(SELECTOR_SEND_BTN, force=True, timeout=5000)
        except Exception:
            force_click(page, SELECTOR_SEND_BTN)
        time.sleep(4)

        # Verify comment was posted
        text = page.evaluate("() => document.body.innerText")
        success = message[:8] in text
        if success:
            print(f"SUCCESS! Comment posted: '{message}'")
        else:
            print(f"WARNING: Comment may not have posted. Check page manually.")

        page.screenshot(path='/tmp/xhs_comment_result.png')
        print("Screenshot: /tmp/xhs_comment_result.png")

        page.close()
        browser.close()
        return success

    except Exception as exc:
        print(f"ERROR during comment posting: {exc}")
        try:
            browser.close()
        except Exception:
            pass
        return False


# ── Comment listing / reply (creator-platform) ────────────────────────────────


def list_comments(page) -> list:
    """List comments from the note manager page."""
    page.goto(NOTE_MANAGER_URL, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
    time.sleep(8)

    current_url = page.url
    for fragment in LOGIN_URL_FRAGMENTS:
        if fragment in current_url:
            print("ERROR: Session expired.")
            sys.exit(1)

    notes = page.evaluate('''() => {
    const results = [];
    const noteEls = document.querySelectorAll('.note');

    noteEls.forEach(el => {
    const text = el.innerText.trim();
    const lines = text.split('\\n').filter(l => l.trim());
    let title = '', date = '', commentCount = 0;
    const numbers = [];

    for (const line of lines) {
    if (line.includes('发布于')) {
    date = line.replace('发布于 ', '');
    } else if (/^\\d+$/.test(line.trim())) {
    numbers.push(parseInt(line.trim()));
    } else if (!title && line.trim().length > 2) {
    title = line.trim();
    }
    }

    if (numbers.length >= 3) {
    commentCount = numbers[2];
    }

    if (title) {
    results.push({title: title, date: date, commentCount: commentCount, stats: numbers});
    }
    });

    return results;
    }''')

    return notes


def reply_to_comment(page, comment_id, message) -> bool:
    """Reply to a specific comment."""
    print(f"Attempting to reply to comment {comment_id}...")
    print(f"Message: {message}")

    page.goto(NOTE_MANAGER_URL, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
    time.sleep(8)

    print("Note: Comment reply may need to be done through the main XHS app.")
    print("The creator platform primarily shows analytics, not comment management.")

    return False


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Xiaohongshu Comment Management")
    parser.add_argument("--cookies-file", default=COOKIES_PATH)
    parser.add_argument("--cdp", default=DEFAULT_CDP_URL)
    args = parser.parse_args()

    action = args.action

    if action in ("list", "reply", "batch-reply", "mark-read"):
        browser, context, page = make_browser_page(cookies_file=args.cookies_file)
        try:
            if action == "list":
                comments = list_comments(page)
                for c in comments:
                    print(f"[{c['date']}] {c['title']} — comments: {c['commentCount']}")
            elif action == "reply":
                reply_to_comment(page, args.comment_id, args.message)
            elif action == "batch-reply":
                print("batch-reply not yet implemented in refactored version")
            elif action == "mark-read":
                print("mark-read not yet implemented")
        finally:
            browser.close()
    elif action == "post":
        success = post_comment_cdp(
            note_url=getattr(args, 'note_url', None),
            message=args.message,
            cdp_url=args.cdp,
            profile_url=getattr(args, 'profile', None),
            note_index=getattr(args, 'note_index', 0),
        )
        print("Posted:", success)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
