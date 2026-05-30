#!/usr/bin/env python3
"""
Xiaohongshu Engagement Script (refactored) — Like + Comment on hot posts via CDP.
Uses logged-in Chrome (port 9222) to bypass bot detection.

Usage:
 python3 xhs_engage.py --action auto-engage --keyword KEYWORD [--likes N] [--comments N] [--cdp URL] [--niche NICHE]
 python3 xhs_engage.py --action like --note-url URL [--cdp URL]
 python3 xhs_engage.py --action comment --note-url URL --message TEXT [--cdp URL]
 python3 xhs_engage.py --action browse [--category NAME] [--limit N] [--cookies-file PATH]
 python3 xhs_engage.py --action history

Key pitfalls:
 - Direct /explore/ URLs return 404. Must navigate via search page click.
 - .note-item <a> tags have zero-size rect (display:contents). Use <section> rect for clicking.
 - Like button: .like-wrapper (verified)
 - Comment input: #content-textarea (force=True to bypass not-active overlay)
 - Send button: button.btn.submit
"""

import argparse
import json
import os
import sys
import time
import random
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

from xhs_config import (  # noqa: E402
    CATEGORY_URLS,
    COOKIES_PATH,
    DEFAULT_CDP_URL,
    ENGAGEMENT_HISTORY_FILE,
    INSPIRATION_URL,
    LOGIN_URL_FRAGMENTS,
    PAGE_TIMEOUT_MS,
    PUBLIC_HOME,
    PUBLIC_SEARCH,
    SELECTOR_COMMENT_INPUT,
    SELECTOR_SEND_BTN,
    SELECTOR_LIKE_BTN,
    SELECTOR_NOTE_ITEM,
    SUCCESS_URL_FRAGMENTS,
)
from xhs_browser import load_cookies, make_browser_page  # noqa: E402
from xhs_utils import force_click  # noqa: E402


COMMENT_TEMPLATES = {
    "default": ["太棒了！收藏了～", "好实用！感谢分享 💕", "学到了！马上试试", "这也太厉害了吧！", "码住！以后用得上 📌", "姐妹太会了！👍"],
    "anime": ["哇！这个角度好新颖 😂", "身为二次元表示狠狠认同！", "这个分析太到位了！", "经典就是经典，百看不厌 ✨", "说到心坎了！收藏 📌", "同好握手！🤝"],
    "food": ["看起来好好吃！😋", "马上去做！", "太香了！收藏了 📌"],
    "beauty": ["好好看！什么色号？", "学到了！马上试试 💕", "姐妹皮肤也太好了吧！"],
    "fashion": ["好好看！链接有吗？", "这个搭配绝了 👍", "姐妹衣品太好了！"],
    "travel": ["好美！这是哪里？", "太美了！想去 ✈️", "收藏了！下次去打卡 📌"],
}


# ── History / rate limit ───────────────────────────────────────────────────────


def load_history() -> dict:
    if os.path.exists(ENGAGEMENT_HISTORY_FILE):
        with open(ENGAGEMENT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[name-defined]
    return {"likes": [], "comments": [], "follows": []}


def save_history(history: dict) -> None:
    os.makedirs(os.path.dirname(ENGAGEMENT_HISTORY_FILE), exist_ok=True)
    with open(ENGAGEMENT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)  # type: ignore[arg-type]


def add_history(history: dict, action_type: str, target: str, detail: str = "") -> None:
    entry = {"timestamp": datetime.now().isoformat(), "action": action_type, "target": target, "detail": detail}
    history[action_type + "s"].append(entry)
    save_history(history)


def check_rate_limit(history: dict, action_type: str, limit_per_hour: int):
    now = datetime.now()
    recent = [e for e in history.get(action_type + "s", []) if (now - datetime.fromisoformat(e["timestamp"])).total_seconds() < 3600]
    return len(recent) < limit_per_hour, len(recent)


# ── Search ────────────────────────────────────────────────────────────────────


def search_posts_cdp(page, keyword: str, limit: int = 10) -> list:
    """Search for posts on www.xiaohongshu.com and return note links with positions."""
    search_url = PUBLIC_SEARCH.format(keyword=keyword)
    print(f"Searching: {search_url}")
    page.goto(search_url, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
    time.sleep(8)

    # Scroll to load more results
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)

    # Extract note links
    notes = page.evaluate("""() => {
    const results = [];
    const items = document.querySelectorAll('.note-item');
    const seen = new Set();
    items.forEach(item => {
    const link = item.querySelector('a[href*="/explore/"]');
    if (!link || !link.href || seen.has(link.href)) return;
    seen.add(link.href);
    const title = item.querySelector('[class*="title"], [class*="desc"]');
    const rect = item.getBoundingClientRect();
    const w = item.offsetWidth || 203;
    const h = item.offsetHeight || 300;
    if (w > 0 && h > 50) {
    results.push({
    href: link.href,
    title: title ? title.innerText.trim().substring(0, 60) : '',
    rect: {x: Math.round(rect.x + w/2), y: Math.round(rect.y + h/2), w, h},
    });
    }
    });
    return results;
    }""")

    print(f"Found {len(notes)} posts for '{keyword}'")
    return notes[:limit]


# ── Navigation ────────────────────────────────────────────────────────────────


def navigate_to_note(page, note: dict) -> bool:
    """Navigate to a note page by clicking the note card."""
    href = note["href"]

    # Strategy 1: page.mouse.click() at the center of the note card
    cx = note["rect"]["x"]
    cy = note["rect"]["y"]
    try:
        page.mouse.click(cx, cy)
        time.sleep(6)
        if "explore/" in page.url and "404" not in page.url:
            print(f" Navigated via mouse.click: {page.url[:80]}")
            return True
    except Exception as e:
        print(f" mouse.click failed: {e}")

    # Strategy 2: page.click on nth note-item
    try:
        page.click(f".note-item >> nth=0", timeout=5000)
        time.sleep(5)
        if "explore/" in page.url and "404" not in page.url:
            print(f" Navigated via page.click: {page.url[:80]}")
            return True
    except Exception as e:
        print(f" page.click failed: {e}")

    return False


# ── Like / comment actions ─────────────────────────────────────────────────────


def like_post_cdp(page) -> str:
    """Click the like button on the current note page."""
    try:
        page.wait_for_selector(SELECTOR_LIKE_BTN, timeout=10000)
    except Exception:
        print(" WARNING: .like-wrapper not found after 10s, trying anyway")

    result = page.evaluate("""() => {
    const el = document.querySelector('.like-wrapper');
    if (el) { el.click(); return 'clicked .like-wrapper'; }
    const all = document.querySelectorAll('[class*="like"]');
    for (const e of all) {
    const rect = e.getBoundingClientRect();
    if (rect.width > 10 && rect.height > 10) { e.click(); return 'clicked: ' + (e.className||'').substring(0,50); }
    }
    return 'not found';
    }""")
    return result


def comment_post_cdp(page, message: str):
    """Type and send a comment on the current note page."""
    try:
        page.wait_for_selector(SELECTOR_COMMENT_INPUT, timeout=10000)
    except Exception:
        print(" WARNING: #content-textarea not found after 10s, trying anyway")

    force_click(page, SELECTOR_COMMENT_INPUT)
    time.sleep(1)

    page.keyboard.type(message, delay=80)
    time.sleep(1)

    typed = page.evaluate("() => { const el = document.querySelector('#content-textarea'); return el ? (el.innerText || el.value || '') : ''; }")
    if not typed:
        return False, "Failed to type"

    force_click(page, SELECTOR_SEND_BTN)
    time.sleep(3)

    text = page.evaluate("() => document.body.innerText")
    success = message[:8] in text
    return success, "OK" if success else "May not have posted"


def engage_with_post(page, message: str, do_like: bool = True, do_comment: bool = True) -> dict:
    """Like and/or comment on the current note page."""
    results = {}
    if do_like:
        like_result = like_post_cdp(page)
        results["like"] = like_result
        print(f" Like: {like_result}")
        time.sleep(random.uniform(1, 3))
    if do_comment:
        comment_success, comment_detail = comment_post_cdp(page, message)
        results["comment"] = {"success": comment_success, "detail": comment_detail}
        print(f" Comment: {comment_detail}")
        time.sleep(random.uniform(1, 2))
    return results


def browse_trending(category: str = "全部", limit: int = 10) -> None:
    """Scrape trending topics using shared CATEGORY_URLS config."""
    browser, context, page = make_browser_page(cookies_file=COOKIES_PATH)

    try:
        url = CATEGORY_URLS.get(category, INSPIRATION_URL)
        page.goto(url, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
        time.sleep(8)

        current_url = page.url
        for fragment in LOGIN_URL_FRAGMENTS:
            if fragment in current_url:
                print("ERROR: Session expired. Run xhs_login.py first.")
                return

        print(f"Browsing trending: {category} (URL: {url})")
        # Defer actual parsing to caller or a follow-up step; this is a stub.
        # TODO: implement parse_topics_from_text() in xhs_hashtags and reuse it here.
    finally:
        browser.close()


# ── Main auto-engage flow ─────────────────────────────────────────────────────


def auto_engage_cdp(keyword: str, max_likes: int, max_comments: int, cdp_url: str, niche: str = "default") -> None:
    """Search for posts and auto-like/comment on them."""
    history = load_history()

    likes_ok, likes_count = check_rate_limit(history, "like", 10)
    comments_ok, comments_count = check_rate_limit(history, "comment", 5)
    print(f"Rate limits - Likes: {likes_count}/10, Comments: {comments_count}/5 (last hour)")
    if not likes_ok and not comments_ok:
        print("Rate limit reached. Wait before engaging more.")
        return

    templates = COMMENT_TEMPLATES.get(niche, COMMENT_TEMPLATES["default"])

    browser, context, page = make_browser_page(cookies_file=COOKIES_PATH, cdp_url=cdp_url)

    try:
        notes = search_posts_cdp(page, keyword, limit=max_likes + max_comments + 5)
        if not notes:
            print("No posts found.")
            return

        likes_done = 0
        comments_done = 0

        for note in notes:
            if likes_done >= max_likes and comments_done >= max_comments:
                break

            title = note.get("title", "")[:40]
            print(f"\nPost: {title}")

            success = navigate_to_note(page, note)
            if not success:
                print(" SKIPPING: Could not navigate to note")
                try:
                    page.goto(PUBLIC_SEARCH.format(keyword=keyword), wait_until="commit", timeout=30000)
                    time.sleep(5)
                except Exception:
                    pass
                continue

            print(f" URL: {page.url[:80]}")

            do_like = likes_done < max_likes and likes_ok
            do_comment = comments_done < max_comments and comments_ok
            comment_msg = random.choice(templates)

            results = engage_with_post(page, comment_msg, do_like=do_like, do_comment=do_comment)

            if do_like and "like" in results:
                likes_done += 1
            if do_comment and results.get("comment", {}).get("success"):
                comments_done += 1
    finally:
        browser.close()


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Xiaohongshu Engagement Script")
    parser.add_argument("--action", required=True, choices=["auto-engage", "like", "comment", "browse", "history"])
    parser.add_argument("--keyword")
    parser.add_argument("--likes", type=int, default=3)
    parser.add_argument("--comments", type=int, default=2)
    parser.add_argument("--cdp", default=DEFAULT_CDP_URL)
    parser.add_argument("--niche", default="default")
    parser.add_argument("--note-url")
    parser.add_argument("--message", default="好棒！👍")
    parser.add_argument("--profile")
    parser.add_argument("--note-index", type=int, default=0)
    parser.add_argument("--category", default="全部")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--cookies-file", default=COOKIES_PATH)

    # allow legacy parsing from scripts/ as "python xhs_engage.py <positional>"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        sys.argv.insert(1, "--action")

    args = parser.parse_args()

    if args.action == "history":
        history = load_history()
        for action_type in ("likes", "comments", "follows"):
            entries = history.get(action_type, [])[-10:]
            print(f"\n{action_type.upper()} (last {len(entries)}):")
            for e in entries:
                print(f"  [{e['timestamp']}] {e.get('target', '')}")
        return

    if args.action == "browse":
        browse_trending(category=args.category, limit=args.limit)
        return

    if args.action == "auto-engage":
        auto_engage_cdp(
            keyword=args.keyword,
            max_likes=args.likes,
            max_comments=args.comments,
            cdp_url=args.cdp,
            niche=args.niche,
        )
        return

    # Single-action helpers (like / comment / post)
    browser, context, page = make_browser_page(cookies_file=args.cookies_file, cdp_url=args.cdp)
    try:
        if args.action == "like":
            # navigate first via URL or use helper
            page.goto(args.note_url, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
            time.sleep(3)
            print(like_post_cdp(page))
        elif args.action == "comment":
            page.goto(args.note_url, wait_until="commit", timeout=PAGE_TIMEOUT_MS)
            time.sleep(3)
            print(comment_post_cdp(page, args.message))
    finally:
        browser.close()


if __name__ == "__main__":
    main()
