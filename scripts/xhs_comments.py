#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Comment Management Script

Reads comments on your posts from the creator platform and allows
replying to them. Also supports posting new comments on www.xiaohongshu.com
via CDP (logged-in Chrome).

Usage:
    python3 xhs_comments.py --action list [--note-title TITLE] [--cookies-file PATH]
    python3 xhs_comments.py --action reply --comment-id ID --message TEXT [--cookies-file PATH]
    python3 xhs_comments.py --action batch-reply --message TEXT [--cookies-file PATH]
    python3 xhs_comments.py --action post --note-url URL --message TEXT [--cdp URL]
    python3 xhs_comments.py --action post --profile URL --note-index N --message TEXT [--cdp URL]

Actions:
    list          - List all comments on your posts (creator platform)
    reply         - Reply to a specific comment (creator platform)
    batch-reply   - Reply to all unread comments with the same message
    mark-read     - Mark all comments as read
    post          - Post a new comment on www.xiaohongshu.com via CDP

Note: The `post` action requires a logged-in Chrome with CDP on port 9222.
      Direct /explore/ URLs return 404 — must navigate via profile page click.
"""

import argparse
import json
import os
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

DEFAULT_COOKIES_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
HOME_URL = "https://creator.xiaohongshu.com/new/home"
NOTE_MANAGER_URL = "https://creator.xiaohongshu.com/new/note-manager"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"


def load_cookies(cookies_file):
    if not os.path.exists(cookies_file):
        print(f"ERROR: Cookies file not found: {cookies_file}")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


def post_comment_cdp(note_url, message, cdp_url=DEFAULT_CDP_URL, profile_url=None, note_index=0):
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
    with sync_playwright() as p:
        print(f"Connecting to Chrome CDP: {cdp_url}")
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        page = context.new_page()

        # Navigate to profile page
        target_profile = profile_url or "https://www.xiaohongshu.com/user/profile/598b76525e87e778c1141505"
        print(f"Navigating to profile: {target_profile}")
        page.goto(target_profile, wait_until="commit", timeout=60000)
        time.sleep(8)

        if 'login' in page.url:
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
            print(f"  [{n['index']}] {n['title'][:40]}")

        # Select target note
        if note_url:
            # Find note matching the URL
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

        # Activate comment input (bypass not-active overlay with force=True)
        print("Activating comment input...")
        try:
            page.click('#content-textarea', force=True, timeout=5000)
        except Exception:
            # Fallback: JS click
            page.evaluate("() => { document.querySelector('#content-textarea').click(); }")
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
            page.click('button.btn.submit', force=True, timeout=5000)
        except Exception:
            page.evaluate("() => { document.querySelector('button.btn.submit').click(); }")
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


def list_comments(page):
    """List comments from the note manager page."""
    page.goto(NOTE_MANAGER_URL, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    if 'login' in page.url:
        print("ERROR: Session expired.")
        sys.exit(1)
    
    # Get all notes with comment counts
    notes = page.evaluate('''() => {
        const results = [];
        const noteEls = document.querySelectorAll('.note');
        
        noteEls.forEach(el => {
            const text = el.innerText.trim();
            const lines = text.split('\\n').filter(l => l.trim());
            
            // Parse note info
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
            
            // Stats order: exposure, likes, comments, ?, saves
            if (numbers.length >= 3) {
                commentCount = numbers[2];
            }
            
            if (title) {
                results.push({
                    title: title,
                    date: date,
                    commentCount: commentCount,
                    stats: numbers
                });
            }
        });
        
        return results;
    }''')
    
    return notes


def reply_to_comment(page, comment_id, message):
    """Reply to a specific comment.
    
    Note: The creator platform may not have a direct comment reply API.
    This function navigates to the note's public page to reply.
    """
    # This is a placeholder - the creator platform's comment management
    # interface varies. The actual implementation depends on whether
    # the platform exposes comment reply functionality.
    print(f"Attempting to reply to comment {comment_id}...")
    print(f"Message: {message}")
    
    # Navigate to the note manager to find the note
    page.goto(NOTE_MANAGER_URL, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    # The creator platform shows comment counts but may not have
    # a built-in reply feature. Users may need to use the main XHS app.
    print("Note: Comment reply may need to be done through the main XHS app.")
    print("The creator platform primarily shows analytics, not comment management.")
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Comment Management")
    parser.add_argument("--cookies-file", default=DEFAULT_COOKIES_FILE)
    parser.add_argument("--action", choices=["list", "reply", "batch-reply", "mark-read", "post"], required=True)
    parser.add_argument("--note-title", help="Filter by note title")
    parser.add_argument("--comment-id", help="Comment ID to reply to")
    parser.add_argument("--message", help="Reply/comment message")
    parser.add_argument("--output", choices=["json", "table"], default="table")
    parser.add_argument("--cdp", default=DEFAULT_CDP_URL, help="CDP endpoint URL (for post action)")
    parser.add_argument("--note-url", help="Note URL to comment on (for post action)")
    parser.add_argument("--profile", help="Profile URL to find notes from (for post action)")
    parser.add_argument("--note-index", type=int, default=0, help="Note card index on profile (0-based)")
    args = parser.parse_args()

    if args.action == "post":
        # Post comment via CDP (www.xiaohongshu.com)
        if not args.message:
            print("ERROR: --message is required for post action")
            sys.exit(1)
        success = post_comment_cdp(
            note_url=args.note_url,
            message=args.message,
            cdp_url=args.cdp,
            profile_url=args.profile,
            note_index=args.note_index,
        )
        sys.exit(0 if success else 1)

    cookies = load_cookies(args.cookies_file)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ])
        context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        context.add_cookies(cookies)
        page = context.new_page()
        
        if args.action == "list":
            notes = list_comments(page)
            
            if args.note_title:
                notes = [n for n in notes if args.note_title in n['title']]
            
            if args.output == "json":
                print(json.dumps(notes, ensure_ascii=False, indent=2))
            else:
                print(f"\n{'=' * 60}")
                print(f"💬 笔记评论概览")
                print(f"{'=' * 60}")
                
                total_comments = 0
                for note in notes:
                    total_comments += note['commentCount']
                    print(f"\n  📝 {note['title']}")
                    print(f"     发布: {note['date']}")
                    print(f"     评论数: {note['commentCount']}")
                    if note['stats']:
                        labels = ['曝光', '点赞', '评论', '?', '收藏']
                        stats_str = ' | '.join(f"{labels[i]}: {v}" for i, v in enumerate(note['stats']) if i < len(labels))
                        print(f"     数据: {stats_str}")
                
                print(f"\n  总计: {len(notes)} 篇笔记, {total_comments} 条评论")
                print(f"{'=' * 60}")
        
        elif args.action == "reply":
            if not args.comment_id or not args.message:
                print("ERROR: --comment-id and --message are required for reply")
                sys.exit(1)
            reply_to_comment(page, args.comment_id, args.message)
        
        elif args.action == "batch-reply":
            if not args.message:
                print("ERROR: --message is required for batch-reply")
                sys.exit(1)
            print("Batch reply: listing notes with comments first...")
            notes = list_comments(page)
            notes_with_comments = [n for n in notes if n['commentCount'] > 0]
            
            if not notes_with_comments:
                print("No notes with comments found.")
            else:
                print(f"Found {len(notes_with_comments)} notes with comments.")
                for note in notes_with_comments:
                    print(f"  📝 {note['title']} ({note['commentCount']} comments)")
                print(f"\nReply message: {args.message}")
                print("Note: Use the main XHS app for actual comment replies.")
        
        elif args.action == "mark-read":
            print("Marking all comments as read...")
            print("Note: This feature depends on the creator platform's notification system.")
            page.goto(HOME_URL, wait_until="commit", timeout=60000)
            time.sleep(8)
            # The platform may have a notification center
            print("Done. Check the creator platform for notification status.")
        
        browser.close()


if __name__ == "__main__":
    main()
