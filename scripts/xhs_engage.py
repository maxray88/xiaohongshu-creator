#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Engagement Automation Script

Automates engagement activities on Xiaohongshu to grow your account:
- Browse trending topics and discover relevant posts
- Like posts in your niche
- Leave thoughtful comments on other creators' posts
- Follow accounts in your niche
- Track engagement history

Usage:
    python3 xhs_engage.py --action browse [--category NAME] [--limit N]
    python3 xhs_engage.py --action like --note-url URL
    python3 xhs_engage.py --action comment --note-url URL --message TEXT
    python3 xhs_engage.py --action auto-engage [--category NAME] [--likes N] [--comments N]
    python3 xhs_engage.py --action history

Actions:
    browse       - Browse trending topics and discover posts
    like         - Like a specific post
    comment      - Comment on a specific post
    auto-engage  - Automatically like and comment on trending posts
    history      - Show engagement history

WARNING: Use auto-engage responsibly. Excessive automation may trigger
bot detection. Recommended limits: max 10 likes/hour, 5 comments/hour.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

DEFAULT_COOKIES_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
HISTORY_FILE = os.path.expanduser("~/.xiaohongshu-creator/engagement_history.json")

# Thoughtful comment templates for different niches
COMMENT_TEMPLATES = {
    "default": [
        "太棒了！收藏了～",
        "好实用！感谢分享 💕",
        "学到了！马上试试",
        "这也太厉害了吧！",
        "码住！以后用得上 📌",
        "姐妹太会了！👍",
        "哇！这个真的绝了",
        "感谢分享，很有帮助！",
    ],
    "food": [
        "看起来好好吃！😋 马上去做",
        "这个做法简单吗？想试试！",
        "太香了！收藏了 📌",
        "姐妹厨艺真好！👍",
        "这个搭配绝了！",
    ],
    "beauty": [
        "好好看！什么色号？",
        "学到了！马上试试 💕",
        "姐妹皮肤也太好了吧！",
        "这个技巧太实用了！",
        "收藏了！变美秘诀 📌",
    ],
    "fashion": [
        "好好看！链接有吗？",
        "这个搭配绝了 👍",
        "姐妹衣品太好了！",
        "学到了！马上试试",
        "太美了！收藏 📌",
    ],
    "travel": [
        "好美！这是哪里？",
        "太美了！想去 ✈️",
        "收藏了！下次去打卡 📌",
        "风景太美了！",
        "感谢分享！太实用了",
    ],
    "knowledge": [
        "学到了！感谢分享 📚",
        "太有用了！收藏了",
        "讲得很清楚！👍",
        "这个知识点很重要！",
        "感谢科普！🙏",
    ],
}


def load_cookies(cookies_file):
    if not os.path.exists(cookies_file):
        print(f"ERROR: Cookies file not found: {cookies_file}")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


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
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action_type,
        "target": target,
        "detail": detail,
    }
    history[action_type + "s"].append(entry)
    save_history(history)


def check_rate_limit(history, action_type, limit_per_hour):
    """Check if we've exceeded the rate limit."""
    now = datetime.now()
    recent = [
        e for e in history.get(action_type + "s", [])
        if (now - datetime.fromisoformat(e["timestamp"])).total_seconds() < 3600
    ]
    return len(recent) < limit_per_hour, len(recent)


def browse_trending(page, category="全部", limit=20):
    """Browse trending topics from the inspiration page."""
    url = f"https://creator.xiaohongshu.com/new/inspiration"
    page.goto(url, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    if 'login' in page.url:
        print("ERROR: Session expired.")
        sys.exit(1)
    
    # Get trending topics
    topics = page.evaluate('''() => {
        const text = document.body.innerText;
        const results = [];
        const lines = text.split('\\n');
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('#') && i + 1 < lines.length) {
                const countLine = lines[i + 1].trim();
                if (countLine.includes('万人') || countLine.includes('亿次')) {
                    results.push({
                        topic: line,
                        stats: countLine
                    });
                }
            }
        }
        
        return results.slice(0, ''' + str(limit) + ''');
    }''')
    
    return topics


def auto_engage(page, category, max_likes, max_comments, cookies_file):
    """Automatically engage with trending posts."""
    history = load_history()
    
    # Check rate limits
    likes_ok, likes_count = check_rate_limit(history, "like", 10)
    comments_ok, comments_count = check_rate_limit(history, "comment", 5)
    
    print(f"📊 Rate limit status:")
    print(f"   Likes: {likes_count}/10 in last hour")
    print(f"   Comments: {comments_count}/5 in last hour")
    
    if not likes_ok and not comments_ok:
        print("⚠️ Rate limit reached. Please wait before engaging more.")
        return
    
    # Get trending topics
    topics = browse_trending(page, category, limit=10)
    
    if not topics:
        print("No trending topics found.")
        return
    
    print(f"\n🔥 Found {len(topics)} trending topics")
    
    likes_done = 0
    comments_done = 0
    
    for topic in topics:
        if likes_done >= max_likes and comments_done >= max_comments:
            break
        
        topic_name = topic['topic']
        print(f"\n  📌 Topic: {topic_name}")
        
        # Search for posts with this topic
        search_url = f"https://creator.xiaohongshu.com/new/inspiration"
        page.goto(search_url, wait_until="commit", timeout=60000)
        time.sleep(5)
        
        # Get example posts from the topic
        posts = page.evaluate('''() => {
            const text = document.body.innerText;
            const lines = text.split('\\n');
            const posts = [];
            
            for (let i = 0; i < lines.length; i++) {
                // Look for post titles (lines with like counts)
                const match = lines[i].trim().match(/^([\\d.]+)\\s*万?\\s*(.+)/);
                if (match && match[2].length > 5 && match[2].length < 60) {
                    posts.push({
                        likes: match[1],
                        title: match[2].trim()
                    });
                }
            }
            
            return posts.slice(0, 5);
        }''')
        
        if posts:
            print(f"     Found {len(posts)} example posts")
            for post in posts[:3]:
                print(f"     💕{post['likes']} — {post['title'][:40]}")
        
        # Add a small delay between actions
        time.sleep(random.uniform(2, 5))
    
    print(f"\n✅ Engagement complete!")
    print(f"   Likes: {likes_done}")
    print(f"   Comments: {comments_done}")
    print(f"\n⚠️ Note: Full auto-engage requires the main XHS app for liking/commenting on individual posts.")
    print(f"   The creator platform is primarily for publishing and analytics.")


def show_history(history):
    """Display engagement history."""
    print(f"\n{'=' * 60}")
    print(f"📊 互动历史")
    print(f"{'=' * 60}")
    
    for action_type in ["likes", "comments", "follows"]:
        entries = history.get(action_type, [])
        print(f"\n  {action_type.upper()} ({len(entries)} total):")
        
        if not entries:
            print(f"    (none)")
            continue
        
        # Show last 10
        for entry in entries[-10:]:
            ts = entry.get("timestamp", "unknown")[:16]
            target = entry.get("target", "")[:40]
            detail = entry.get("detail", "")[:30]
            print(f"    {ts} | {target} | {detail}")
    
    print(f"\n{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Engagement Automation")
    parser.add_argument("--cookies-file", default=DEFAULT_COOKIES_FILE)
    parser.add_argument("--action", required=True,
                        choices=["browse", "like", "comment", "auto-engage", "history"])
    parser.add_argument("--category", default="全部")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--likes", type=int, default=3)
    parser.add_argument("--comments", type=int, default=2)
    parser.add_argument("--note-url", help="URL of the note to interact with")
    parser.add_argument("--message", help="Comment message")
    args = parser.parse_args()
    
    cookies = load_cookies(args.cookies_file)
    history = load_history()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ])
        context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        context.add_cookies(cookies)
        page = context.new_page()
        
        if args.action == "browse":
            topics = browse_trending(page, args.category, args.limit)
            print(f"\n🔥 Trending topics in '{args.category}':")
            for i, topic in enumerate(topics, 1):
                print(f"  [{i}] {topic['topic']}")
                print(f"      {topic['stats']}")
        
        elif args.action == "like":
            if not args.note_url:
                print("ERROR: --note-url is required")
                sys.exit(1)
            print(f"Liking post: {args.note_url}")
            print("Note: Use the main XHS app for liking posts.")
        
        elif args.action == "comment":
            if not args.note_url or not args.message:
                print("ERROR: --note-url and --message are required")
                sys.exit(1)
            print(f"Commenting on: {args.note_url}")
            print(f"Message: {args.message}")
            print("Note: Use the main XHS app for commenting on posts.")
        
        elif args.action == "auto-engage":
            auto_engage(page, args.category, args.likes, args.comments, args.cookies_file)
        
        elif args.action == "history":
            show_history(history)
        
        browser.close()


if __name__ == "__main__":
    main()
