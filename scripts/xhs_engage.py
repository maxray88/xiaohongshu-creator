#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Engagement Script — Like + Comment on hot posts via CDP.
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
import argparse, json, os, random, sys, time
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_COOKIES_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
HISTORY_FILE = os.path.expanduser("~/.xiaohongshu-creator/engagement_history.json")

COMMENT_TEMPLATES = {
    "default": ["太棒了！收藏了～", "好实用！感谢分享 💕", "学到了！马上试试", "这也太厉害了吧！", "码住！以后用得上 📌", "姐妹太会了！👍"],
    "anime": ["哇！这个角度好新颖 😂", "身为二次元表示狠狠认同！", "这个分析太到位了！", "经典就是经典，百看不厌 ✨", "说到心坎了！收藏 📌", "同好握手！🤝"],
    "food": ["看起来好好吃！😋", "马上去做！", "太香了！收藏了 📌"],
    "beauty": ["好好看！什么色号？", "学到了！马上试试 💕", "姐妹皮肤也太好了吧！"],
    "fashion": ["好好看！链接有吗？", "这个搭配绝了 👍", "姐妹衣品太好了！"],
    "travel": ["好美！这是哪里？", "太美了！想去 ✈️", "收藏了！下次去打卡 📌"],
}


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"likes": [], "comments": [], "follows": []}


def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_history(history, action_type, target, detail=""):
    entry = {"timestamp": datetime.now().isoformat(), "action": action_type, "target": target, "detail": detail}
    history[action_type + "s"].append(entry)
    save_history(history)


def check_rate_limit(history, action_type, limit_per_hour):
    now = datetime.now()
    recent = [e for e in history.get(action_type + "s", []) if (now - datetime.fromisoformat(e["timestamp"])).total_seconds() < 3600]
    return len(recent) < limit_per_hour, len(recent)


# ─── CDP: Search for posts ────────────────────────────────────────────────────

def search_posts_cdp(page, keyword, limit=10):
    """Search for posts on www.xiaohongshu.com and return note links with positions."""
    search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
    print(f"Searching: {search_url}")
    page.goto(search_url, wait_until="commit", timeout=60000)
    time.sleep(8)

    # Scroll to load more results
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)

    # Extract note links - use .note-item (section) rect, not <a> (zero-size)
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
            if (rect.width > 0 && rect.height > 50) {
                results.push({
                    href: link.href,
                    title: title ? title.innerText.trim().substring(0, 60) : '',
                    rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)},
                });
            }
        });
        return results;
    }""")

    print(f"Found {len(notes)} posts for '{keyword}'")
    return notes[:limit]


# ─── CDP: Like a post ─────────────────────────────────────────────────────────

def like_post_cdp(page):
    """Click the like button on the current note page."""
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


# ─── CDP: Comment on a post ───────────────────────────────────────────────────

def comment_post_cdp(page, message):
    """Type and send a comment on the current note page."""
    try:
        page.click('#content-textarea', force=True, timeout=5000)
    except Exception:
        page.evaluate("() => { document.querySelector('#content-textarea').click(); }")
    time.sleep(1)

    page.keyboard.type(message, delay=80)
    time.sleep(1)

    typed = page.evaluate("() => { const el = document.querySelector('#content-textarea'); return el ? (el.innerText || el.value || '') : ''; }")
    if not typed:
        return False, "Failed to type"

    try:
        page.click('button.btn.submit', force=True, timeout=5000)
    except Exception:
        page.evaluate("() => { document.querySelector('button.btn.submit').click(); }")
    time.sleep(3)

    text = page.evaluate("() => document.body.innerText")
    success = message[:8] in text
    return success, "OK" if success else "May not have posted"


# ─── CDP: Engage with a post ──────────────────────────────────────────────────

def engage_with_post(page, message, do_like=True, do_comment=True):
    """Like and/or comment on the current note page."""
    results = {}
    if do_like:
        like_result = like_post_cdp(page)
        results["like"] = like_result
        print(f"  Like: {like_result}")
        time.sleep(random.uniform(1, 3))
    if do_comment:
        comment_success, comment_detail = comment_post_cdp(page, message)
        results["comment"] = {"success": comment_success, "detail": comment_detail}
        print(f"  Comment: {comment_detail}")
        time.sleep(random.uniform(1, 2))
    return results


# ─── Main auto-engage flow ────────────────────────────────────────────────────

def auto_engage_cdp(keyword, max_likes, max_comments, cdp_url, niche="default"):
    """Search for posts and auto-like/comment on them."""
    history = load_history()

    likes_ok, likes_count = check_rate_limit(history, "like", 10)
    comments_ok, comments_count = check_rate_limit(history, "comment", 5)
    print(f"Rate limits - Likes: {likes_count}/10, Comments: {comments_count}/5 (last hour)")
    if not likes_ok and not comments_ok:
        print("Rate limit reached. Wait before engaging more.")
        return

    templates = COMMENT_TEMPLATES.get(niche, COMMENT_TEMPLATES["default"])

    with sync_playwright() as p:
        print(f"Connecting to Chrome CDP: {cdp_url}")
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        page = context.new_page()

        notes = search_posts_cdp(page, keyword, limit=max_likes + max_comments + 5)
        if not notes:
            print("No posts found.")
            page.close()
            browser.close()
            return

        likes_done = 0
        comments_done = 0

        for note in notes:
            if likes_done >= max_likes and comments_done >= max_comments:
                break

            title = note.get("title", "")[:40]
            print(f"\nPost: {title}")

            # Click note card to open it
            cx = note["rect"]["x"] + note["rect"]["w"] // 2
            cy = note["rect"]["y"] + note["rect"]["h"] // 2
            page.mouse.click(cx, cy)
            time.sleep(6)

            if "explore/" not in page.url:
                print(f"  WARNING: Not on note page: {page.url}")
                page.mouse.click(cx, cy)
                time.sleep(5)

            if "explore/" not in page.url:
                print("  SKIPPING: Could not open note")
                page.go_back()
                time.sleep(3)
                continue

            print(f"  URL: {page.url[:80]}")

            do_like = likes_done < max_likes and likes_ok
            do_comment = comments_done < max_comments and comments_ok
            comment_msg = random.choice(templates)

            results = engage_with_post(page, comment_msg, do_like=do_like, do_comment=do_comment)

            if do_like and "like" in results:
                likes_done += 1
                add_history(history, "like", page.url, title)
            if do_comment and results.get("comment", {}).get("success"):
                comments_done += 1
                add_history(history, "comment", page.url, comment_msg)

            delay = random.uniform(3, 8)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

            page.go_back()
            time.sleep(3)

        page.close()
        browser.close()

    print(f"\nEngagement complete! Likes: {likes_done}, Comments: {comments_done}")


# ─── Browse trending (creator platform) ───────────────────────────────────────

def browse_trending(page, category="全部", limit=20):
    url = "https://creator.xiaohongshu.com/new/inspiration"
    page.goto(url, wait_until="commit", timeout=60000)
    time.sleep(8)
    if "login" in page.url:
        print("ERROR: Session expired.")
        sys.exit(1)
    topics = page.evaluate("""() => {
        const text = document.body.innerText;
        const results = [];
        const lines = text.split('\\n');
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('#') && i + 1 < lines.length) {
                const countLine = lines[i + 1].trim();
                if (countLine.includes('万人') || countLine.includes('亿次')) {
                    results.push({topic: line, stats: countLine});
                }
            }
        }
        return results.slice(0, """ + str(limit) + """);
    }""")
    return topics


def show_history(history):
    print(f"\n{'=' * 60}")
    print(f"Engagement History")
    print(f"{'=' * 60}")
    for action_type in ["likes", "comments", "follows"]:
        entries = history.get(action_type, [])
        print(f"\n  {action_type.upper()} ({len(entries)} total):")
        if not entries:
            print("    (none)")
            continue
        for entry in entries[-10:]:
            ts = entry.get("timestamp", "unknown")[:16]
            target = entry.get("target", "")[:50]
            detail = entry.get("detail", "")[:30]
            print(f"    {ts} | {target} | {detail}")
    print(f"\n{'=' * 60}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Engagement Automation")
    parser.add_argument("--action", required=True, choices=["browse", "like", "comment", "auto-engage", "history"])
    parser.add_argument("--keyword", help="Search keyword for auto-engage")
    parser.add_argument("--category", default="全部")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--likes", type=int, default=3)
    parser.add_argument("--comments", type=int, default=2)
    parser.add_argument("--cdp", default=DEFAULT_CDP_URL, help="CDP endpoint URL")
    parser.add_argument("--note-url", help="Note URL to interact with")
    parser.add_argument("--message", help="Comment message")
    parser.add_argument("--niche", default="default", choices=list(COMMENT_TEMPLATES.keys()))
    parser.add_argument("--cookies-file", default=DEFAULT_COOKIES_FILE)
    args = parser.parse_args()

    if args.action == "history":
        show_history(load_history())
        return

    if args.action == "browse":
        cookies = load_cookies(args.cookies_file)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
            context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
            context.add_cookies(cookies)
            page = context.new_page()
            topics = browse_trending(page, args.category, args.limit)
            print(f"\nTrending topics in '{args.category}':")
            for i, topic in enumerate(topics, 1):
                print(f"  [{i}] {topic['topic']}  {topic['stats']}")
            browser.close()
        return

    if args.action == "auto-engage":
        if not args.keyword:
            print("ERROR: --keyword is required")
            sys.exit(1)
        auto_engage_cdp(args.keyword, args.likes, args.comments, args.cdp, args.niche)
        return

    if args.action in ("like", "comment"):
        if not args.note_url:
            print("ERROR: --note-url is required")
            sys.exit(1)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(args.cdp)
            context = browser.contexts[0]
            page = context.new_page()
            page.goto(args.note_url, wait_until="commit", timeout=60000)
            time.sleep(6)
            if args.action == "like":
                result = like_post_cdp(page)
                print(f"Like result: {result}")
            elif args.action == "comment":
                if not args.message:
                    print("ERROR: --message is required")
                    sys.exit(1)
                success, detail = comment_post_cdp(page, args.message)
                print(f"Comment result: {detail}")
            page.close()
            browser.close()
        return


def load_cookies(cookies_file):
    if not os.path.exists(cookies_file):
        print(f"ERROR: Cookies file not found: {cookies_file}")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    main()
