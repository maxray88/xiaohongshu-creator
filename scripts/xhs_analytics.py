#!/usr/bin/env python3
"""
Xiaohongshu Creator Analytics Script (refactored)

Fetches post performance data from the creator platform home page,
including account overview stats and individual note metrics.

Usage:
 python3 xhs_analytics.py [--output json|table] [--cookies-file PATH]
 
Output:
 Account overview: followers, following, likes, exposure, etc.
 Note list: title, date, views, likes, comments, saves, shares
"""

import argparse
import os
import sys
import re
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import json

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

from xhs_config import (  # noqa: E402
    COOKIES_PATH,
    CREATOR_HOME,
    LOGIN_URL_FRAGMENTS,
    NOTE_MANAGER_URL,
    PAGE_TIMEOUT_MS,
    SUCCESS_URL_FRAGMENTS,
)
from xhs_browser import load_cookies, make_browser_page, goto_and_wait  # noqa: E402


def parse_number(text: str) -> int:
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


def re_match(pattern: str, string: str):
    return re.match(pattern, string)


def fetch_account_overview(page) -> dict:
    """Scrape account overview from home page."""
    goto_and_wait(page, CREATOR_HOME)

    # Use shared is_logged_in check via URL fragments
    current_url = page.url
    for fragment in LOGIN_URL_FRAGMENTS:
        if fragment in current_url:
            print("ERROR: Session expired. Run xhs_login.py first.")
            sys.exit(1)

    data = page.evaluate('''() => {
    const text = document.body.innerText;
    const result = {};

    // Profile info
    const nameEl = document.querySelector('.user-name, .nickname, [class*="user-name"]');
    if (nameEl) result.nickname = nameEl.innerText.trim();

    // Stats from sidebar/profile area
    const statEls = document.querySelectorAll('[class*="stat"], [class*="count"], [class*="number"]');
    const stats = [];
    statEls.forEach(el => {
    const parent = el.parentElement;
    const label = parent ? parent.innerText.replace(el.innerText, '').trim() : '';
    stats.push({label: label, value: el.innerText.trim()});
    });
    result.stat_elements = stats;

    // Dashboard metrics
    const allText = document.body.innerText;
    result.raw_metrics_section = allText;

    return result;
    }''')

    return data


def fetch_note_list(page) -> list:
    """Scrape note list from note manager."""
    goto_and_wait(page, NOTE_MANAGER_URL)

    current_url = page.url
    for fragment in LOGIN_URL_FRAGMENTS:
        if fragment in current_url:
            print("ERROR: Session expired. Run xhs_login.py first.")
            sys.exit(1)

    notes = page.evaluate('''() => {
    const results = [];
    const noteEls = document.querySelectorAll('div.note');
    const processed = new Set();

    noteEls.forEach(el => {
    const text = el.innerText.trim();
    if (processed.has(text)) return;
    if (el.className !== 'note') return;

    const lines = text.split('\\n').filter(l => l.trim());
    const hasDate = lines.some(l => /\\d{4}年/.test(l));
    const hasStats = lines.filter(l => /^\\d+$/.test(l.trim())).length >= 3;

    if (hasDate && hasStats && lines.length >= 3) {
    processed.add(text);
    results.push({full_text: text, lines: lines});
    }
    });
    return results;
    }''')

    return notes


def parse_note_data(raw_notes: list) -> list:
    """Parse raw note data into structured format."""
    parsed = []
    for raw in raw_notes:
        lines = raw['lines']
        note = {
            'title': '',
            'date': '',
            'exposure': 0,
            'likes': 0,
            'comments': 0,
            'saves': 0,
            'shares': 0,
        }
        title_found = False
        date_found = False
        numbers = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if '发布于' in line:
                note['date'] = line.replace('发布于 ', '')
                date_found = True
                continue
            if re_match(r'^[\d,]+$', line):
                numbers.append(int(line.replace(',', '')))
                continue
            if date_found and not title_found and not re_match(r'^[\d,]+$', line):
                if line not in ('权限设置', '置顶', '编辑', '删除'):
                    note['title'] = line
                    title_found = True
                    continue
            if not title_found and not date_found and not re_match(r'^[\d,]+$', line):
                if line not in ('权限设置', '置顶', '编辑', '删除'):
                    note['title'] = line

        if len(numbers) >= 5:
            note['exposure'] = numbers[0]
            note['comments'] = numbers[1]
            note['likes'] = numbers[2]
            note['saves'] = numbers[3]
            note['shares'] = numbers[4]
        elif len(numbers) >= 3:
            note['exposure'] = numbers[0]
            note['comments'] = numbers[1]
            note['likes'] = numbers[2]

        if note['title']:
            parsed.append(note)

    return parsed


def fetch_dashboard_metrics(page) -> dict:
    """Fetch detailed dashboard metrics from the home page."""
    goto_and_wait(page, CREATOR_HOME)

    metrics = page.evaluate('''() => {
    const text = document.body.innerText;
    const result = {};
    const metricNames = ['曝光数', '观看数', '封面点击率', '视频完播率', '点赞数', '评论数', '收藏数', '分享数', '净涨粉', '新增关注', '取消关注', '主页访客'];

    for (const name of metricNames) {
    const idx = text.indexOf(name);
    if (idx >= 0) {
    const after = text.substring(idx + name.length, idx + name.length + 30);
    const numMatch = after.match(/([\\d.]+%?)/);
    if (numMatch) result[name] = numMatch[1];
    }
    }

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

    const idMatch = text.match(/小红书账号:\\s*(\\d+)/);
    if (idMatch) result['账号ID'] = idMatch[1];

    const dateMatch = text.match(/统计周期\\s*([\\d-]+\\s*至\\s*[\\d-]+)/);
    if (dateMatch) result['统计周期'] = dateMatch[1];

    return result;
    }''')

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Xiaohongshu Creator Analytics")
    parser.add_argument("--cookies-file", default=COOKIES_PATH)
    parser.add_argument("--output", choices=["json", "table"], default="table")
    parser.add_argument("--section", choices=["overview", "notes", "dashboard", "all"], default="all")
    args = parser.parse_args()

    browser, context, page = make_browser_page(cookies_file=args.cookies_file)

    result = {}

    try:
        if args.section in ("dashboard", "all"):
            print("📊 Fetching dashboard metrics...")
            result['dashboard'] = fetch_dashboard_metrics(page)

        if args.section in ("notes", "all"):
            print("📝 Fetching note list...")
            raw_notes = fetch_note_list(page)
            result['notes'] = parse_note_data(raw_notes)
    finally:
        browser.close()

    # Output
    if args.output == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        dash = result.get('dashboard', {})
        print("\n" + "=" * 50)
        print("📊 账号数据概览")
        print("=" * 50)

        account_fields = ['账号ID', '关注数', '粉丝数', '获赞与收藏', '统计周期']
        for field in account_fields:
            if field in dash:
                print(f" {field}: {dash[field]}")

        metric_fields = ['曝光数', '观看数', '封面点击率', '视频完播率', '点赞数', '评论数', '收藏数', '分享数', '净涨粉', '新增关注', '取消关注', '主页访客']
        print("\n📈 笔记数据 (近7日)")
        print("-" * 50)
        for field in metric_fields:
            if field in dash:
                print(f" {field}: {dash[field]}")

        notes = result.get('notes', [])
        if notes:
            print(f"\n📝 笔记列表 ({len(notes)} 篇)")
            print("-" * 50)
            for i, note in enumerate(notes, 1):
                print(f"\n [{i}] {note['title']}")
                print(f" 发布: {note['date']}")
                print(f" 曝光: {note['exposure']} | 点赞: {note['likes']} | 评论: {note['comments']} | 收藏: {note['saves']} | 分享: {note['shares']}")

        print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
