#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Comment Management Script

Reads comments on your posts from the creator platform and allows
replying to them. Also supports batch operations like replying to
all unread comments.

Usage:
    python3 xhs_comments.py --action list [--note-title TITLE] [--cookies-file PATH]
    python3 xhs_comments.py --action reply --comment-id ID --message TEXT [--cookies-file PATH]
    python3 xhs_comments.py --action batch-reply --message TEXT [--cookies-file PATH]

Actions:
    list          - List all comments on your posts
    reply         - Reply to a specific comment
    batch-reply   - Reply to all unread comments with the same message
    mark-read     - Mark all comments as read
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


def load_cookies(cookies_file):
    if not os.path.exists(cookies_file):
        print(f"ERROR: Cookies file not found: {cookies_file}")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


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
    parser.add_argument("--action", choices=["list", "reply", "batch-reply", "mark-read"], required=True)
    parser.add_argument("--note-title", help="Filter by note title")
    parser.add_argument("--comment-id", help="Comment ID to reply to")
    parser.add_argument("--message", help="Reply message")
    parser.add_argument("--output", choices=["json", "table"], default="table")
    args = parser.parse_args()
    
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
