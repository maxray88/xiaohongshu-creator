#!/usr/bin/env python3
"""
Xiaohongshu Hashtag Research Script

Scrapes trending hashtags and topics from the creator platform's
"笔记灵感" (Inspiration) page. Provides hashtag metrics including
participant count and view count for each trending topic.

Usage:
    python3 xhs_hashtags.py [--category NAME] [--limit N] [--output json|table] [--cookies-file PATH]
    
Categories:
    全部, 美食, 美妆, 时尚, 出行, 知识, 兴趣爱好

Output:
    List of trending hashtags with participant count, view count, and example posts.
"""

import argparse
import json
import os
import sys
import time
import re

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

DEFAULT_COOKIES_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
INSPIRATION_URL = "https://creator.xiaohongshu.com/new/inspiration"

CATEGORY_URLS = {
    "全部": INSPIRATION_URL,
    "美食": f"{INSPIRATION_URL}?category=food",
    "美妆": f"{INSPIRATION_URL}?category=beauty",
    "时尚": f"{INSPIRATION_URL}?category=fashion",
    "出行": f"{INSPIRATION_URL}?category=travel",
    "知识": f"{INSPIRATION_URL}?category=knowledge",
    "兴趣爱好": f"{INSPIRATION_URL}?category=hobby",
}


def load_cookies(cookies_file):
    if not os.path.exists(cookies_file):
        print(f"ERROR: Cookies file not found: {cookies_file}")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_count(text):
    """Parse Chinese count format: '30.7万人参与' -> 307000, '14.6亿次浏览' -> 1460000000."""
    if not text:
        return 0
    text = text.strip()
    match = re.search(r'([\d.]+)\s*万', text)
    if match:
        return int(float(match.group(1)) * 10000)
    match = re.search(r'([\d.]+)\s*亿', text)
    if match:
        return int(float(match.group(1)) * 100000000)
    match = re.search(r'(\d+)', text)
    if match:
        return int(match.group(1))
    return 0


def fetch_trending_topics(page, category="全部", limit=20):
    """Scrape trending topics from the inspiration page."""
    url = CATEGORY_URLS.get(category, INSPIRATION_URL)
    page.goto(url, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    if 'login' in page.url:
        print("ERROR: Session expired. Run xhs_login.py first.")
        sys.exit(1)
    
    # Get the full page text and parse topics
    topics = page.evaluate('''() => {
        const results = [];
        const text = document.body.innerText;
        
        // Try to find topic containers
        const topicEls = document.querySelectorAll('[class*="topic"], [class*="card"], [class*="item"], [class*="theme"]');
        
        if (topicEls.length > 0) {
            topicEls.forEach(el => {
                const t = (el.innerText || '').trim();
                if (t.length > 10 && t.length < 500 && (t.includes('万人') || t.includes('亿次') || t.includes('#'))) {
                    results.push(t);
                }
            });
        }
        
        // Also return the full text for parsing
        return {
            structured: results,
            full_text: text
        };
    }''')
    
    return topics


def parse_topics_from_text(full_text, limit=20):
    """Parse trending topics from the full page text."""
    topics = []
    
    lines = full_text.split('\n')
    i = 0
    
    # Known category labels to skip
    category_labels = {'美食', '美妆', '时尚', '出行', '知识', '兴趣爱好', '经典话题'}
    # Known UI text to skip
    ui_text = {'遇到问题', '创作服务平台', '发布笔记', '首页', '笔记管理', '数据看板',
               '活动中心', '笔记灵感', '创作学院', '创作百科', '收起侧边栏', '静坐着呢'}
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for the stats line: "X万人参与 · X亿次浏览"
        if '万人参与' in line and '亿次浏览' in line:
            # The topic name is the previous non-empty line
            topic_name = ''
            for j in range(i - 1, max(i - 5, -1), -1):
                if j >= 0:
                    candidate = lines[j].strip()
                    if candidate and candidate not in category_labels and candidate not in ui_text:
                        # Make sure it's not a number
                        if not re.match(r'^[\d.]+$', candidate):
                            topic_name = candidate
                            break
            
            # Parse participant and view counts
            participants = 0
            views = 0
            part_match = re.search(r'([\d.]+)\s*万', line)
            if part_match:
                participants = int(float(part_match.group(1)) * 10000)
            view_match = re.search(r'([\d.]+)\s*亿', line)
            if view_match:
                views = int(float(view_match.group(1)) * 100000000)
            
            # Collect example post titles (lines after stats until next topic)
            examples = []
            j = i + 1
            while j < len(lines) and len(examples) < 4:
                ex_line = lines[j].strip()
                # Check if this is a like count (pure number or X万)
                if re.match(r'^[\d.]+万?$', ex_line):
                    # Next line should be a post title
                    if j + 1 < len(lines):
                        title_line = lines[j + 1].strip()
                        if title_line and len(title_line) > 3 and len(title_line) < 80:
                            # Verify it's not another topic
                            if not any(c in title_line for c in ['万人参与', '亿次浏览']):
                                like_str = ex_line.replace('万', '')
                                try:
                                    likes_val = int(float(like_str) * 10000) if '万' in ex_line else int(like_str)
                                    examples.append({
                                        'likes': likes_val,
                                        'title': title_line[:60]
                                    })
                                except ValueError:
                                    pass
                            j += 1  # Skip the title line we just processed
                j += 1
            
            if topic_name:
                # Add # prefix if not present
                display_name = topic_name if topic_name.startswith('#') else f'#{topic_name}'
                topics.append({
                    'topic': display_name,
                    'topic_raw': topic_name,
                    'participants': participants,
                    'views': views,
                    'examples': examples
                })
            
            if len(topics) >= limit:
                break
        
        i += 1
    
    return topics


def analyze_hashtag_competition(topic):
    """Provide competition analysis for a hashtag."""
    participants = topic['participants']
    views = topic['views']
    
    if participants > 1000000:
        competition = "🔴 极高"
        advice = "超大流量池，但竞争激烈。需要高质量内容+精准标题才能突围。"
    elif participants > 100000:
        competition = "🟠 高"
        advice = "热门话题，有一定竞争。建议结合细分角度切入。"
    elif participants > 10000:
        competition = "🟡 中等"
        advice = "中等竞争，有机会获得曝光。适合新账号参与。"
    else:
        competition = "🟢 低"
        advice = "小众话题，竞争较少。容易获得精准流量。"
    
    # Calculate views-per-participant ratio (engagement indicator)
    if participants > 0:
        ratio = views / participants
        if ratio > 1000:
            engagement = "🔥 极高互动"
        elif ratio > 100:
            engagement = "📈 高互动"
        elif ratio > 10:
            engagement = "👍 中等互动"
        else:
            engagement = "📊 一般互动"
    else:
        engagement = "N/A"
        ratio = 0
    
    return {
        'competition_level': competition,
        'engagement': engagement,
        'views_per_participant': round(ratio, 1),
        'advice': advice
    }


def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Hashtag Research")
    parser.add_argument("--cookies-file", default=DEFAULT_COOKIES_FILE)
    parser.add_argument("--category", default="全部", choices=list(CATEGORY_URLS.keys()))
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--output", choices=["json", "table"], default="table")
    parser.add_argument("--analyze", action="store_true", help="Include competition analysis")
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
        
        print(f"🔍 Fetching trending topics for category: {args.category}...")
        raw = fetch_trending_topics(page, args.category, args.limit)
        
        browser.close()
    
    # Parse topics
    full_text = raw.get('full_text', '')
    topics = parse_topics_from_text(full_text, args.limit)
    
    if not topics:
        # Try structured results
        for structured in raw.get('structured', []):
            print(f"  Raw: {structured[:100]}")
    
    # Add analysis if requested
    if args.analyze:
        for topic in topics:
            topic['analysis'] = analyze_hashtag_competition(topic)
    
    # Output
    if args.output == "json":
        print(json.dumps(topics, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"🔥 小红书热门话题 — {args.category}")
        print(f"{'=' * 60}")
        
        for i, topic in enumerate(topics, 1):
            participants_w = topic['participants'] / 10000
            views_yi = topic['views'] / 100000000
            
            print(f"\n  [{i}] {topic['topic']}")
            print(f"      参与人数: {participants_w:.1f}万 | 浏览量: {views_yi:.1f}亿")
            
            if topic['examples']:
                print(f"      热门笔记:")
                for ex in topic['examples'][:2]:
                    likes_display = f"{ex['likes']//10000}万" if ex['likes'] >= 10000 else str(ex['likes'])
                    print(f"        💕{likes_display} {ex['title'][:40]}")
            
            if args.analyze and 'analysis' in topic:
                a = topic['analysis']
                print(f"      竞争程度: {a['competition_level']} | 互动指数: {a['engagement']}")
                print(f"      💡 {a['advice']}")
        
        print(f"\n{'=' * 60}")
        print(f"共 {len(topics)} 个话题")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
