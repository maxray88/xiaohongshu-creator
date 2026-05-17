#!/Users/maochundong/.hermes/hermes-agent/venv/bin/python3
"""
Xiaohongshu Publish Script v8 - FINAL
Uses Patchright + CDP mode with human-like mouse simulation.
All 7 CDP pitfalls fixed. Keyboard typing for form filling.
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
        conn.request("GET", "/json/version")
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
    """Bring Chrome window to front."""
    try:
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'],
                      timeout=5, capture_output=True)
    except:
        pass


def bezier_move(page, end_x, end_y, steps=25):
    """Move mouse along a Bezier curve to simulate human movement."""
    viewport = page.viewport_size
    if not viewport:
        viewport = {"width": 1200, "height": 800}
    start_x = random.randint(300, max(301, viewport["width"] - 50))
    start_y = random.randint(200, max(201, viewport["height"] - 50))

    dx, dy = end_x - start_x, end_y - start_y
    cp1x = start_x + dx * random.uniform(0.2, 0.5) + random.uniform(-50, 50)
    cp1y = start_y + dy * random.uniform(0.1, 0.4) + random.uniform(-50, 50)
    cp2x = start_x + dx * random.uniform(0.5, 0.8) + random.uniform(-50, 50)
    cp2y = start_y + dy * random.uniform(0.5, 0.9) + random.uniform(-50, 50)

    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3*start_x + 3*u**2*t*cp1x + 3*u*t**2*cp2x + t**3*end_x
        y = u**3*start_y + 3*u**2*t*cp1y + 3*u*t**2*cp2y + t**3*end_y
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.003, 0.012))

    # Small overshoot (30% chance)
    if random.random() < 0.3:
        page.mouse.move(end_x + random.randint(-4, 4), end_y + random.randint(-4, 4))
        time.sleep(random.uniform(0.03, 0.1))
        page.mouse.move(end_x, end_y)


def human_click(page, x, y):
    """Click with human-like movement, press duration, and micro-delays."""
    bezier_move(page, x, y, steps=random.randint(20, 35))
    time.sleep(random.uniform(0.08, 0.25))
    page.mouse.down()
    time.sleep(random.uniform(0.1, 0.3))
    page.mouse.up()
    time.sleep(random.uniform(0.05, 0.15))


def main():
    parser = argparse.ArgumentParser(description='Xiaohongshu publish via CDP + Patchright')
    parser.add_argument('--title', required=True, help='Post title (max 20 chars)')
    parser.add_argument('--content', required=True, help='Post content')
    parser.add_argument('--images', nargs='+', required=True, help='Image paths')
    parser.add_argument('--cdp', default=CDP_ENDPOINT, help='CDP endpoint URL')
    args = parser.parse_args()

    title = args.title
    content = args.content
    image_paths = args.images
    cdp_endpoint = args.cdp

    # Validate title length (hard limit 20 chars)
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

        # ── Step 1: Navigate via home to clear SPA state ──
        print("\n[Step 1] Navigating via home page to clear SPA state...")
        page.goto("https://creator.xiaohongshu.com/new/home", wait_until="commit", timeout=60000)
        human_delay(3, 5)
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        human_delay(1, 2)
        page.goto(PUBLISH_URL, wait_until="commit", timeout=60000)
        print("  Waiting 12s for SPA render...")
        human_delay(10, 14)

        # Check active tab
        active = page.evaluate("""() => {
            for (var t of document.querySelectorAll('.creator-tab')) {
                var r = t.getBoundingClientRect();
                if (t.classList.contains('active') && r.x > 0) return t.innerText.trim();
            }
            return 'unknown';
        }""")
        print(f"  Active tab: {active}")

        # If not on image tab, click it with human-like movement
        if active != '上传图文':
            print("  Not on image tab, clicking 上传图文 with human-like movement...")
            tab_info = page.evaluate("""() => {
                var tabs = document.querySelectorAll('.creator-tab');
                for (var i = 0; i < tabs.length; i++) {
                    var box = tabs[i].getBoundingClientRect();
                    if (tabs[i].textContent.trim() === '上传图文' && box.x > 0 && box.y > 0) {
                        return JSON.stringify({x: Math.round(box.x + box.width/2), y: Math.round(box.y + box.height/2)});
                    }
                }
                return null;
            }""")
            if tab_info:
                tab_pos = json.loads(tab_info)
                human_click(page, tab_pos['x'], tab_pos['y'])
                print(f"  Tab clicked at ({tab_pos['x']}, {tab_pos['y']})")
                human_delay(3, 5)
                active = page.evaluate("""() => {
                    var a = document.querySelector('.creator-tab.active');
                    return a ? a.textContent.trim() : 'unknown';
                }""")
                print(f"  Active tab after click: {active}")

        # ── Step 2: Upload image ──
        print("\n[Step 2] Uploading image...")
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

        # ── Step 3: Wait for form to render ──
        print("\n[Step 3] Waiting for form to render...")
        human_delay(8, 12)

        # Check form state
        form_state = page.evaluate("""() => {
            return JSON.stringify({
                titleInput: !!document.querySelector('input[placeholder*="填写标题"], input.d-text, input[maxlength]'),
                editor: !!document.querySelector('.tiptap.ProseMirror, [contenteditable="true"]'),
                publishBtn: !!document.querySelector('xhs-publish-btn'),
                activeTab: document.querySelector('.creator-tab.active') ? document.querySelector('.creator-tab.active').textContent.trim() : 'unknown'
            });
        }""")
        print(f"  Form state: {form_state}")

        # ── Step 4: Fill title using keyboard typing (most reliable) ──
        print(f"\n[Step 4] Filling title: '{title}'")
        title_input = page.query_selector('input[placeholder*="填写标题"]')
        if not title_input:
            title_input = page.query_selector('input.d-text')
        if title_input:
            title_input.click()
            human_delay(0.2, 0.5)
            title_input.type(title, delay=random.uniform(15, 30))
            human_delay(0.3, 0.7)
            val = title_input.input_value()
            print(f"  Title: '{val}' ({len(val)} chars)")
        else:
            print("  ERROR: Title input not found!")

        # ── Step 5: Fill content using keyboard typing ──
        print(f"\n[Step 5] Filling content ({len(content)} chars)...")
        editor = page.query_selector('.tiptap.ProseMirror')
        if not editor:
            editor = page.query_selector('[contenteditable="true"]')
        if editor:
            editor.click()
            human_delay(0.2, 0.5)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    page.keyboard.type(line, delay=random.uniform(3, 8))
                if i < len(lines) - 1:
                    page.keyboard.press("Enter")
            print(f"  Content filled: {len(content)} chars")
        else:
            print("  ERROR: Editor not found!")

        # ── Step 6: Hide overlays that may block the publish button ──
        print("\n[Step 6] Hiding overlays...")
        page.evaluate("""
            document.querySelectorAll('.get-cover-suggest, [class*="suggest"], [class*="popup"], [class*="tooltip"]')
                .forEach(el => { el.style.display = 'none'; });
        """)

        # ── Step 7: Find and click the publish button ──
        print("\n[Step 7] Finding and clicking publish button...")
        btn_info = page.evaluate("""() => {
            var btn = document.querySelector('xhs-publish-btn');
            if (btn) {
                var box = btn.getBoundingClientRect();
                if (box.x > 0 && box.y > 0) {
                    return JSON.stringify({
                        x: Math.round(box.x + box.width/2),
                        y: Math.round(box.y + box.height/2),
                        w: Math.round(box.width),
                        h: Math.round(box.height),
                        submitText: btn.getAttribute('submit-text'),
                        submitDisabled: btn.getAttribute('submit-disabled')
                    });
                }
            }
            return null;
        }""")

        if btn_info:
            btn = json.loads(btn_info)
            print(f"  Found: {btn}")
            print(f"  submit-text: {btn.get('submitText')}")
            print(f"  submit-disabled: {btn.get('submitDisabled')}")

            if btn.get('submitDisabled') == 'true':
                print("  WARNING: Publish button is disabled!")
            else:
                # Click the RIGHT side of the button (where "发布" is)
                # The button is 680px wide, "发布" is on the right side
                publish_x = btn['x'] + btn['w'] * 0.25  # Right side (75% from left)
                publish_y = btn['y']
                print(f"  Clicking '发布' at ({publish_x}, {publish_y})...")

                # Human-like Bezier movement and click
                human_click(page, publish_x, publish_y)
                print("  ✅ Clicked!")
        else:
            print("  ERROR: Publish button not found!")
            all_btns = page.evaluate("() => Array.from(document.querySelectorAll('button, xhs-publish-btn')).map(b => b.tagName + ':' + b.textContent.trim().substring(0,30))")
            print(f"  All buttons: {all_btns}")

        # ── Step 8: Wait and verify ──
        print("\n[Step 8] Waiting 30s to observe result...")
        human_delay(25, 35)

        final_url = page.url
        page.screenshot(path='/tmp/xhs_screenshots/publish_result.png')
        print(f"\n📍 Final URL: {final_url}")
        print("📸 Screenshot saved: /tmp/xhs_screenshots/publish_result.png")

        if 'publish' not in final_url:
            print("🎉 SUCCESS! Page navigated away from publish page!")
        else:
            text = page.evaluate("() => document.body.innerText.substring(0, 500)")
            if "发布成功" in text or "审核" in text:
                print("🎉 Post submitted successfully!")
            elif "草稿" in text:
                print("📝 Post saved as draft")
            else:
                print(f"⚠️ Still on publish page")
                print(f"  Page text: {text[:300]}")


if __name__ == '__main__':
    main()
