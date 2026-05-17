#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Creator Analytics Script

Fetches post performance data from the creator platform home page,
including account overview stats and individual note metrics.

Usage:
    python3 xhs_analytics.py [--output json|table] [--cookies-file PATH]
    
Output:
    Account overview: followers, following, likes, exposure, etc.
    Note list: title, date, views, likes, comments, saves, shares
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

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
        print("Run xhs_login.py first.")
        sys.exit(1)
    with open(cookies_file, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_number(text):
    """Parse Chinese number format like '1.2万' -> 12000."""
    if not text or text.strip() == '-':
        return 0
    text = text.strip().replace(',', '')
    if '万' in text:
        return int(float(text.replace('万', '')) * 10000)
    if '亿' in text:
        return int(float(text.replace('亿', '')) * 100000000)
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return 0


def fetch_account_overview(page):
    """Scrape account overview from home page."""
    page.goto(HOME_URL, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    if 'login' in page.url:
        print("ERROR: Session expired. Run xhs_login.py first.")
        sys.exit(1)
    
    data = page.evaluate('''() => {
        const text = document.body.innerText;
        const result = {};
        
        // Profile info
        const nameEl = document.querySelector('.user-name, .nickname, [class*="user-name"]');
        if (nameEl) result.nickname = nameEl.innerText.trim();
        
        // Stats from sidebar/profile area
        // The platform shows: 关注数, 粉丝数, 获赞与收藏
        const statEls = document.querySelectorAll('[class*="stat"], [class*="count"], [class*="number"]');
        const stats = [];
        statEls.forEach(el => {
            const parent = el.parentElement;
            const label = parent ? parent.innerText.replace(el.innerText, '').trim() : '';
            stats.push({label: label, value: el.innerText.trim()});
        });
        result.stat_elements = stats;
        
        // Dashboard metrics from 数据看板 section
        // Look for metric containers
        const metricLabels = ['曝光数', '观看数', '封面点击率', '点赞数', '评论数', '收藏数', '分享数', '净涨粉', '新增关注', '取消关注', '主页访客'];
        const metrics = {};
        
        // Try to find metrics in the page
        const allText = document.body.innerText;
        
        result.raw_metrics_section = allText;
        
        return result;
    }''')
    
    return data


def fetch_note_list(page):
    """Scrape note list from note manager."""
    page.goto(NOTE_MANAGER_URL, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    if 'login' in page.url:
        print("ERROR: Session expired. Run xhs_login.py first.")
        sys.exit(1)
    
    notes = page.evaluate('''() => {
        const results = [];
        
        // Each note is in a container with class "note" (exact match to avoid containers)
        const noteEls = document.querySelectorAll('div.note');
        const processed = new Set();
        
        noteEls.forEach(el => {
            const text = el.innerText.trim();
            if (processed.has(text)) return;
            // Skip the outer container that has "notes-container" class
            if (el.className !== 'note') return;

            // Check if this element has a title — it's a note card
            // Note cards contain: title, date, and stats (numbers)
            const lines = text.split('\\n').filter(l => l.trim());
            
            // A note card has at least: title, date line, and stat numbers
            // Heuristic: look for date pattern (YYYY年)
            const hasDate = lines.some(l => /\\d{4}年/.test(l));
            const hasStats = lines.filter(l => /^\\d+$/.test(l.trim())).length >= 3;
            
            if (hasDate && hasStats && lines.length >= 3) {
                processed.add(text);
                results.push({
                    full_text: text,
                    lines: lines
                });
            }
        });
        
        return results;
    }''')
    
    return notes


def parse_note_data(raw_notes):
    """Parse raw note data into structured format."""
    parsed = []
    for raw in raw_notes:
        lines = raw['lines']
        note = {
            'title': '',
            'date': '',
            'exposure': 0,   # 曝光
            'likes': 0,      # 点赞
            'comments': 0,   # 评论
            'saves': 0,      # 收藏
            'shares': 0,     # 分享
        }
        
        title_found = False
        date_found = False
        numbers = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Date line: "发布于 2026年05月13日 20:15"
            if '发布于' in line:
                note['date'] = line.replace('发布于 ', '')
                date_found = True
                continue
            
            # Numbers (stats)
            if re_match(r'^[\d,]+$', line):
                numbers.append(int(line.replace(',', '')))
                continue
            
            # Title (first non-date, non-number line after date)
            if date_found and not title_found and not re_match(r'^[\d,]+$', line):
                if line not in ('权限设置', '置顶', '编辑', '删除'):
                    note['title'] = line
                    title_found = True
                continue
            
            if not title_found and not date_found and not re_match(r'^[\d,]+$', line):
                if line not in ('权限设置', '置顶', '编辑', '删除'):
                    note['title'] = line
        
        # Assign numbers to stats (platform order: 曝光, 点赞, 评论, 收藏, 分享)
        if len(numbers) >= 5:
            note['exposure'] = numbers[0]
            note['likes'] = numbers[1]
            note['comments'] = numbers[2]
            note['saves'] = numbers[3]
            note['shares'] = numbers[4]
        elif len(numbers) >= 3:
            note['exposure'] = numbers[0]
            note['likes'] = numbers[1]
            note['comments'] = numbers[2]
        
        if note['title']:
            parsed.append(note)
    
    return parsed


def re_match(pattern, string):
    import re
    return re.match(pattern, string)


def fetch_dashboard_metrics(page, cookies_file):
    """Fetch detailed dashboard metrics from the home page."""
    page.goto(HOME_URL, wait_until="commit", timeout=60000)
    time.sleep(8)
    
    metrics = page.evaluate('''() => {
        const text = document.body.innerText;
        const result = {};
        
        // Parse metrics from the "笔记数据总览" section
        const metricNames = ['曝光数', '观看数', '封面点击率', '视频完播率', '点赞数', '评论数', '收藏数', '分享数', '净涨粉', '新增关注', '取消关注', '主页访客'];
        
        for (const name of metricNames) {
            const idx = text.indexOf(name);
            if (idx >= 0) {
                // Get the text after the metric name (next ~20 chars)
                const after = text.substring(idx + name.length, idx + name.length + 30);
                // Extract the first number
                const numMatch = after.match(/([\d.]+%?)/);
                if (numMatch) {
                    result[name] = numMatch[1];
                }
            }
        }
        
        // Parse account stats
        const followIdx = text.indexOf('关注数');
        if (followIdx >= 0) {
            const after = text.substring(followIdx + 3, followIdx + 20);
            const match = after.match(/(\\d+)/);
            if (match) result['关注数'] = match[1];
        }
        
        const fanIdx = text.indexOf('粉丝数');
        if (fanIdx >= 0) {
            const after = text.substring(fanIdx + 3, fanIdx + 20);
            const match = after.match(/(\\d+)/);
            if (match) result['粉丝数'] = match[1];
        }
        
        const likeCollectIdx = text.indexOf('获赞与收藏');
        if (likeCollectIdx >= 0) {
            const after = text.substring(likeCollectIdx + 5, likeCollectIdx + 20);
            const match = after.match(/(\\d+)/);
            if (match) result['获赞与收藏'] = match[1];
        }
        
        // Parse account ID
        const idMatch = text.match(/小红书账号:\\s*(\\d+)/);
        if (idMatch) result['账号ID'] = idMatch[1];
        
        // Parse date range
        const dateMatch = text.match(/统计周期\\s*([\\d-]+\\s*至\\s*[\\d-]+)/);
        if (dateMatch) result['统计周期'] = dateMatch[1];
        
        return result;
    }''')
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Creator Analytics")
    parser.add_argument("--cookies-file", default=DEFAULT_COOKIES_FILE)
    parser.add_argument("--output", choices=["json", "table"], default="table")
    parser.add_argument("--section", choices=["overview", "notes", "dashboard", "all"], default="all")
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
        
        result = {}
        
        if args.section in ("dashboard", "all"):
            print("📊 Fetching dashboard metrics...")
            result['dashboard'] = fetch_dashboard_metrics(page, args.cookies_file)
        
        if args.section in ("notes", "all"):
            print("📝 Fetching note list...")
            raw_notes = fetch_note_list(page)
            result['notes'] = parse_note_data(raw_notes)
        
        browser.close()
    
    # Output
    if args.output == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Table format
        dash = result.get('dashboard', {})
        print("\n" + "=" * 50)
        print("📊 账号数据概览")
        print("=" * 50)
        
        account_fields = ['账号ID', '关注数', '粉丝数', '获赞与收藏', '统计周期']
        for field in account_fields:
            if field in dash:
                print(f"  {field}: {dash[field]}")
        
        metric_fields = ['曝光数', '观看数', '封面点击率', '视频完播率', '点赞数', '评论数', '收藏数', '分享数', '净涨粉', '新增关注', '取消关注', '主页访客']
        print("\n📈 笔记数据 (近7日)")
        print("-" * 50)
        for field in metric_fields:
            if field in dash:
                print(f"  {field}: {dash[field]}")
        
        notes = result.get('notes', [])
        if notes:
            print(f"\n📝 笔记列表 ({len(notes)} 篇)")
            print("-" * 50)
            for i, note in enumerate(notes, 1):
                print(f"\n  [{i}] {note['title']}")
                print(f"      发布: {note['date']}")
                print(f"      曝光: {note['exposure']} | 点赞: {note['likes']} | 评论: {note['comments']} | 收藏: {note['saves']} | 分享: {note['shares']}")
        
        print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
