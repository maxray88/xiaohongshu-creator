#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu publish using Patchright + CDP mode (sync API).
Connects to a real Chrome instance for maximum anti-detection.

Based on: https://yousali.com/posts/20260213-browser-automation-anti-detection/

Prerequisites:
    1. Chrome must be fully quit (Cmd+Q)
    2. Start Chrome with CDP port:
       /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
         --remote-debugging-port=9222 \\
         --user-data-dir=$HOME/.config/xhs-chrome-profile \\
         --no-first-run --no-default-browser-check
    3. Login to Xiaohongshu in that Chrome (or cookies will be injected)
    4. Run this script

Usage:
    python3 xhs_publish_cdp_sync.py --title "标题" --content "正文" --images /path/to/image.png
"""

import json
import os
import sys
import time
import random
import argparse
import subprocess
import http.client
from urllib.parse import urlparse

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    print("ERROR: patchright not installed. Run: pip install patchright")
    sys.exit(1)

COOKIES_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
CDP_ENDPOINT = "http://127.0.0.1:9222"


def resolve_cdp_ws_url(endpoint):
    """Manually resolve CDP WebSocket URL, bypassing Patchright's HTTP discovery bug."""
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint
    try:
        parsed = urlparse(endpoint)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9222
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/json/version")  # No trailing slash!
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


def human_delay(min_s=0.5, max_s=2.0):
    time.sleep(random.uniform(min_s, max_s))


def activate_chrome():
    try:
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'],
                      timeout=5, capture_output=True)
    except:
        pass


def main():
    parser = argparse.ArgumentParser(description='Xiaohongshu publish via CDP')
    parser.add_argument('--title', required=True, help='Post title (max 20 chars)')
    parser.add_argument('--content', required=True, help='Post content')
    parser.add_argument('--images', nargs='+', required=True, help='Image paths')
    parser.add_argument('--cdp', default=CDP_ENDPOINT, help='CDP endpoint URL')
    args = parser.parse_args()

    title = args.title
    content = args.content
    image_paths = args.images
    cdp_endpoint = args.cdp

    # Validate title length
    if len(title) > 20:
        print(f"WARNING: Title {len(title)} chars > 20, truncating: {title[:20]}")
        title = title[:20]

    # Load cookies
    cookies = []
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE) as f:
            cookies = json.load(f)
        print(f"Loaded {len(cookies)} cookies")

    image_path = os.path.abspath(image_paths[0])
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        sys.exit(1)
    print(f"Image: {image_path}")

    # Resolve CDP WebSocket URL
    ws_url = resolve_cdp_ws_url(cdp_endpoint)
    print(f"CDP WebSocket: {ws_url}")

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(ws_url)
        print("Connected to Chrome via CDP!")

        # Use existing context — do NOT call new_context()
        ctx = browser.contexts[0]
        print(f"Using existing context")

        # Inject cookies
        if cookies:
            ctx.add_cookies(cookies)
            print(f"Injected {len(cookies)} cookies")

        page = ctx.new_page()

        # Step 1: Navigate via home to clear SPA state
        print("\n[Step 1] Navigating via home page...")
        page.goto("https://creator.xiaohongshu.com/new/home", wait_until="commit", timeout=60000)
        human_delay(3, 5)
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        human_delay(1, 2)
        page.goto(PUBLISH_URL, wait_until="commit", timeout=60000)
        print("  Waiting 10s for SPA render...")
        human_delay(8, 12)

        # Check active tab
        active = page.evaluate("""() => {
            for (var t of document.querySelectorAll('.creator-tab')) {
                var r = t.getBoundingClientRect();
                if (t.classList.contains('active') && r.x > 0) return t.innerText.trim();
            }
            return 'unknown';
        }""")
        print(f"  Active tab: {active}")

        # If not on image tab, try clicking it
        if active != '上传图文':
            print("  Not on image tab, clicking 上传图文...")
            result = page.evaluate("""() => {
                var tabs = document.querySelectorAll('.creator-tab');
                for (var i = 0; i < tabs.length; i++) {
                    var box = tabs[i].getBoundingClientRect();
                    if (tabs[i].textContent.trim() === '上传图文' && box.x > 0 && box.y > 0) {
                        tabs[i].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        return 'clicked at (' + Math.round(box.x + box.width/2) + ',' + Math.round(box.y + box.height/2) + ')';
                    }
                }
                return 'not found';
            }""")
            print(f"  Tab click: {result}")
            human_delay(3, 5)
            active = page.evaluate("""() => {
                var a = document.querySelector('.creator-tab.active');
                return a ? a.textContent.trim() : 'unknown';
            }""")
            print(f"  Active tab: {active}")

        # Step 2: Click "上传图片" button
        print("\n[Step 2] Clicking '上传图片' button...")
        upload_btn = page.query_selector('button:has-text("上传图片")')
        if not upload_btn:
            upload_btn = page.query_selector('.image-upload-buttons button')

        if upload_btn:
            upload_btn.scroll_into_view_if_needed()
            human_delay(0.3, 0.8)
            box = upload_btn.bounding_box()
            if box:
                cx = box['x'] + box['width'] / 2
                cy = box['y'] + box['height'] / 2
                page.mouse.move(cx, cy)
                human_delay(0.2, 0.5)
            upload_btn.click()
            print("  Clicked!")
            human_delay(1.5, 2.5)
        else:
            print("  ERROR: Upload button not found!")
            btns = page.evaluate("() => Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim())")
            print(f"  Buttons: {btns}")

        # Step 3: Upload image
        print("\n[Step 3] Uploading image...")
        file_input = page.query_selector('input[type="file"]')
        if not file_input:
            file_inputs = page.query_selector_all('input[type="file"]')
            if file_inputs:
                file_input = file_inputs[0]

        if file_input:
            file_input.set_input_files(image_path)
            print(f"  File set: {image_path}")
            human_delay(1.5, 2.5)
            print("  Waiting 15s for upload...")
            human_delay(13, 17)
        else:
            print("  ERROR: No file input found!")

        # Step 4: Wait for form
        print("\n[Step 4] Waiting for form to render...")
        human_delay(8, 12)

        # Check form state
        form_state = page.evaluate("""() => {
            return JSON.stringify({
                titleInput: !!document.querySelector('input[placeholder*="title"], input[placeholder*="Title"], input[placeholder*="标题"], input.d-text, input[maxlength]'),
                editor: !!document.querySelector('.tiptap, .ProseMirror, [contenteditable="true"]'),
                publishBtn: !!document.querySelector('xhs-publish-btn'),
                activeTab: document.querySelector('.creator-tab.active') ? document.querySelector('.creator-tab.active').textContent.trim() : 'unknown'
            });
        }""")
        print(f"  Form state: {form_state}")

        # Step 5: Fill title
        print(f"\n[Step 5] Filling title: '{title}'")
        title_escaped = title.replace("'", "\\'")
        title_js = (
            "(function() {"
            "var selectors = ['input[placeholder*=\"title\"]', 'input[placeholder*=\"Title\"]', 'input[placeholder*=\"标题\"]', 'input.d-text', 'input[maxlength]'];"
            "for (var i = 0; i < selectors.length; i++) {"
            "  var el = document.querySelector(selectors[i]);"
            "  if (el) {"
            "    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;"
            "    nativeSetter.call(el, '" + title_escaped + "');"
            "    el.dispatchEvent(new Event('input', { bubbles: true }));"
            "    el.dispatchEvent(new Event('change', { bubbles: true }));"
            "    return 'filled: ' + el.value;"
            "  }"
            "}"
            "return 'not found';"
            "})()"
        )
        title_r = page.evaluate(title_js)
        print(f"  Title: {title_r}")
        human_delay(0.5, 1.5)

        # Step 6: Fill content
        print(f"\n[Step 6] Filling content ({len(content)} chars)...")
        content_escaped = content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        content_js = (
            "(function() {"
            "var editor = document.querySelector('.tiptap, .ProseMirror, [contenteditable=\"true\"]');"
            "if (!editor) return 'no editor';"
            "editor.focus();"
            "document.execCommand('insertText', false, '" + content_escaped + "');"
            "return 'inserted, len=' + editor.textContent.length;"
            "})()"
        )
        content_r = page.evaluate(content_js)
        print(f"  Content: {content_r}")
        human_delay(1, 2)

        # Screenshot before publish
        page.screenshot(path='/tmp/xhs_cdp_sync_pre.png')
        print("\n  Screenshot saved: /tmp/xhs_cdp_sync_pre.png")

        # Remove overlays
        page.evaluate("""
            document.querySelectorAll('.get-cover-suggest, [class*="suggest"], [class*="popup"], [class*="tooltip"]')
                .forEach(el => { el.style.display = 'none'; });
        """)

        # Find publish button
        print("\n[Step 7] Finding publish button...")
        publish_btn_info = page.evaluate("""() => {
            var btn = document.querySelector('xhs-publish-btn');
            if (btn) {
                var box = btn.getBoundingClientRect();
                if (box.x > 0 && box.y > 0) {
                    return JSON.stringify({type: 'xhs-publish-btn', x: Math.round(box.x + box.width/2), y: Math.round(box.y + box.height/2), w: Math.round(box.width), h: Math.round(box.height)});
                }
            }
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var text = btns[i].textContent.trim().toLowerCase();
                if (text.includes('publish') || text.includes('发布')) {
                    var box = btns[i].getBoundingClientRect();
                    if (box.x > 0 && box.y > 0) {
                        return JSON.stringify({type: 'button', text: btns[i].textContent.trim(), x: Math.round(box.x + box.width/2), y: Math.round(box.y + box.height/2), w: Math.round(box.width), h: Math.round(box.height)});
                    }
                }
            }
            return null;
        }""")

        if publish_btn_info:
            btn = json.loads(publish_btn_info)
            print(f"  Found: {btn}")
        else:
            print("  No publish button found!")
            all_btns = page.evaluate("() => Array.from(document.querySelectorAll('button, xhs-publish-btn')).map(b => b.tagName + ':' + b.textContent.trim().substring(0,30))")
            print(f"  All: {all_btns}")

        # Keep browser open for manual publish click
        print("\n" + "=" * 60)
        print("  BROWSER OPEN - Form filled!")
        print(f"  Title: {title}")
        print(f"  Content: {len(content)} chars")
        print(f"  Image: {image_path}")
        if publish_btn_info:
            btn = json.loads(publish_btn_info)
            print(f"  Publish button: {btn.get('text', 'xhs-publish-btn')} at ({btn['x']}, {btn['y']})")
        print("  Please click the publish button in the browser.")
        print("  Waiting 600s...")
        print("=" * 60)

        activate_chrome()
        time.sleep(1)
        activate_chrome()

        for i in range(40):
            human_delay(12, 18)
            activate_chrome()

        page.screenshot(path='/tmp/xhs_cdp_sync_post.png')
        print("Final screenshot saved: /tmp/xhs_cdp_sync_post.png")
        print(f"Final URL: {page.url}")


if __name__ == '__main__':
    main()
