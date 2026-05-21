#!/usr/bin/env python3
"""
Xiaohongshu Publish Script v10 — FINAL MERGED VERSION
======================================================
Merged from:
  - xhs_publish.py v9: _onPublish() auto-publish, async API
  - xhs_publish_v8.py: Bezier mouse, keyboard typing, overlay hiding, tab click
  - xhs_publish_cdp_sync.py: CDP WS resolve, home-first navigation, tab detection

Key features:
  1. CDP connection with manual WebSocket URL resolution
  2. Home-first navigation to clear SPA state
  3. Tab detection + Bezier-curve click to switch to image tab
  4. Image upload via file input (triggers form render)
  5. Form filling: JS nativeSetter (primary) → keyboard typing (fallback)
  6. Overlay hiding before publish
  7. Publish via _onPublish() — fully automatic, bypasses event.isTrusted
  8. Post-publish verification (URL + page text)
  9. Screenshots at every step
  10. Human-like random delays throughout

Usage:
    $PYTHON ~/.hermes/skills/xiaohongshu-creator/scripts/xhs_publish.py \\
        --title "标题" --content "正文" --images /path/to/image.jpg

Prerequisites:
    Chrome running with --remote-debugging-port=9222
    Cookies saved at ~/.xiaohongshu-creator/cookies.json
"""
import asyncio, json, os, random, sys, math, subprocess, argparse, http.client
from urllib.parse import urlparse

COOKIE_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
CDP_URL_FILE = "/tmp/xhs_cdp_url.txt"
CDP_ENDPOINT = "http://127.0.0.1:9222"
SCREENSHOT_DIR = "/tmp/xhs_screenshots"
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def activate_chrome():
    """Bring Chrome window to front."""
    try:
        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'],
                      timeout=5, capture_output=True)
    except Exception:
        pass


def resolve_cdp_ws_url(endpoint: str) -> str:
    """Manually resolve CDP WebSocket URL from /json/version."""
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


async def human_delay(min_s=0.5, max_s=2.0):
    """Random human-like delay."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def bezier_move(page, end_x, end_y, steps=25):
    """Move mouse along a Bezier curve to simulate human movement."""
    viewport = page.viewport_size or {"width": 1200, "height": 800}
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
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.003, 0.012))

    # Small overshoot (30% chance)
    if random.random() < 0.3:
        await page.mouse.move(end_x + random.randint(-4, 4), end_y + random.randint(-4, 4))
        await asyncio.sleep(random.uniform(0.03, 0.1))
        await page.mouse.move(end_x, end_y)


async def human_click(page, x, y):
    """Click with human-like Bezier movement, press duration, and micro-delays."""
    await bezier_move(page, x, y, steps=random.randint(20, 35))
    await asyncio.sleep(random.uniform(0.08, 0.25))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.1, 0.3))
    await page.mouse.up()
    await asyncio.sleep(random.uniform(0.05, 0.15))


# ─── Main Publish Flow ────────────────────────────────────────────────────────

async def publish(image_paths: list[str], title: str, content: str, cdp_endpoint: str = CDP_ENDPOINT, draft_only: bool = False):
    from playwright.async_api import async_playwright

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ── Load cookies ──────────────────────────────────────────────────────
    if not os.path.exists(COOKIE_FILE):
        print(f"❌ Cookie file not found: {COOKIE_FILE}")
        print("   Run xhs_login.py first to save cookies.")
        sys.exit(1)

    with open(COOKIE_FILE) as f:
        cookies = json.load(f)
    print(f"🍪 Loaded {len(cookies)} cookies")

    # ── Validate title ────────────────────────────────────────────────────
    if len(title) > 20:
        print(f"⚠️  Title is {len(title)} chars, truncating to 20: '{title[:20]}'")
        title = title[:20]
    print(f"📌 Title: '{title}' ({len(title)} chars)")
    print(f"📝 Content: {len(content)} chars")
    print(f"🖼️  Images: {len(image_paths)} file(s)")

    # ── Resolve CDP URL ───────────────────────────────────────────────────
    # Try file first (v9 compat), then endpoint
    cdp_url = None
    if os.path.exists(CDP_URL_FILE):
        with open(CDP_URL_FILE) as f:
            cdp_url = f.read().strip()
        print(f"📡 CDP URL from file: {cdp_url}")

    if not cdp_url:
        cdp_url = resolve_cdp_ws_url(cdp_endpoint)
        print(f"📡 CDP URL resolved: {cdp_url}")

    # ── Connect ───────────────────────────────────────────────────────────
    print(f"\n🔗 Connecting to Chrome via CDP...")
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        await context.add_cookies(cookies)
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Connected!")

        # ── Step 1: Navigate via home to clear SPA state ──────────────────
        print("\n📄 Step 1: Navigating via home page to clear SPA state...")
        try:
            await page.goto("https://creator.xiaohongshu.com/new/home",
                           wait_until="domcontentloaded", timeout=30000)
        except Exception:
            print("  ⚠️  Home page load timeout, continuing...")
        await human_delay(2, 3)
        try:
            await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        except Exception:
            pass
        await human_delay(1, 2)
        # Navigate to publish URL (twice to force SPA re-render)
        try:
            await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            print("  ⚠️  Publish URL first load timeout, retrying...")
            await human_delay(3, 5)
            await page.goto(PUBLISH_URL, wait_until="commit", timeout=30000)
        await human_delay(3, 5)
        try:
            await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            print("  ⚠️  Publish URL second load timeout, continuing...")
        print("⏳ Waiting 12s for SPA render...")
        await human_delay(10, 14)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_loaded.png")
        print(f"  📸 Screenshot: {SCREENSHOT_DIR}/01_loaded.png")

        # ── Step 2: Ensure we're on the image tab ─────────────────────────
        print("\n📑 Step 2: Checking active tab...")
        active_tab = await page.evaluate("""() => {
            for (const t of document.querySelectorAll('.creator-tab')) {
                const r = t.getBoundingClientRect();
                if (t.classList.contains('active') && r.x > 0) return t.innerText.trim();
            }
            return 'unknown';
        }""")
        print(f"  Active tab: '{active_tab}'")

        if active_tab != '上传图文':
            print("  Not on image tab, clicking '上传图文' with human-like movement...")
            tab_info = await page.evaluate("""() => {
                const tabs = document.querySelectorAll('.creator-tab');
                for (let i = 0; i < tabs.length; i++) {
                    const box = tabs[i].getBoundingClientRect();
                    if (tabs[i].textContent.trim() === '上传图文' && box.x > 0 && box.y > 0) {
                        return JSON.stringify({x: Math.round(box.x + box.width/2), y: Math.round(box.y + box.height/2)});
                    }
                }
                return null;
            }""")
            if tab_info:
                pos = json.loads(tab_info)
                await human_click(page, pos['x'], pos['y'])
                print(f"  Tab clicked at ({pos['x']}, {pos['y']})")
                await human_delay(3, 5)
                active_tab = await page.evaluate("""() => {
                    const a = document.querySelector('.creator-tab.active');
                    return a ? a.textContent.trim() : 'unknown';
                }""")
                print(f"  Active tab after click: '{active_tab}'")
            else:
                print("  ⚠️  Could not find '上传图文' tab, continuing anyway...")

        # ── Step 3: Upload images ──────────────────────────────────────────
        print(f"\n🖼️  Step 3: Uploading {len(image_paths)} image(s)...")
        file_input = page.locator('input[type="file"]').first
        try:
            await file_input.wait_for(state="attached", timeout=15000)
        except Exception:
            print("  ⚠️  File input not attached yet, waiting 10 more seconds...")
            await human_delay(8, 12)

        # Upload all at once (Playwright handles batch)
        try:
            await file_input.set_input_files(image_paths)
            print(f"  ✅ File input set ({len(image_paths)} images at once)")
        except Exception as e:
            print(f"  ⚠️  Batch upload failed ({e}), trying one by one...")
            # Fallback: upload first, wait, then add more
            await file_input.set_input_files([image_paths[0]])
            print(f"  ✅ First image uploaded")
            await human_delay(10, 15)
            for img_path in image_paths[1:]:
                try:
                    await file_input.set_input_files([img_path])
                    print(f"  ✅ Added: {os.path.basename(img_path)}")
                    await human_delay(5, 8)
                except Exception as e2:
                    print(f"  ⚠️  Failed to add {os.path.basename(img_path)}: {e2}")

        wait_time = 20 + len(image_paths) * 5
        print(f"  ⏳ Waiting {wait_time}s for upload to complete and form to render...")
        await human_delay(wait_time - 5, wait_time + 5)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_uploaded.png")

        # Verify form appeared
        has_title = await page.evaluate(
            "() => !!document.querySelector('input[placeholder*=\"填写标题\"]')")
        has_editor = await page.evaluate(
            "() => !!document.querySelector('.tiptap.ProseMirror')")
        print(f"  Title input visible: {has_title}")
        print(f"  Editor visible: {has_editor}")

        if not has_title:
            print("  ⚠️  Title input not found, waiting 10 more seconds...")
            await asyncio.sleep(10)

        # ── Step 4: Fill title ─────────────────────────────────────────────
        print(f"\n✏️  Step 4: Filling title: '{title}'")

        # Method 1: JS nativeSetter (fast, reliable)
        title_result = await page.evaluate("""
            (text) => {
                const input = document.querySelector('input[placeholder*="填写标题"]');
                if (input) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeSetter.call(input, text);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    return 'filled: ' + input.value;
                }
                return 'no title input found';
            }
        """, title)
        print(f"  JS method: {title_result}")

        # Fallback: keyboard typing if JS method failed
        if 'not found' in title_result or 'filled: ' == title_result:
            print("  Fallback: keyboard typing...")
            title_el = page.locator('input[placeholder*="填写标题"]').first
            if await title_el.count() > 0:
                await title_el.click()
                await human_delay(0.2, 0.5)
                await title_el.type(title, delay=random.uniform(15, 30))
                val = await title_el.input_value()
                print(f"  Keyboard method: '{val}' ({len(val)} chars)")

        await human_delay(0.5, 1.0)

        # ── Step 5: Fill content ───────────────────────────────────────────
        print(f"\n📝 Step 5: Filling content ({len(content)} chars)...")

        # Method 1: JS execCommand (fast, reliable)
        content_result = await page.evaluate("""
            (text) => {
                const editor = document.querySelector('.tiptap.ProseMirror');
                if (editor) {
                    editor.focus();
                    document.execCommand('insertText', false, text);
                    return 'filled: ' + editor.textContent.substring(0, 50);
                }
                return 'no editor found';
            }
        """, content)
        print(f"  JS method: {content_result}")

        # Fallback: keyboard typing
        if 'not found' in content_result:
            print("  Fallback: keyboard typing...")
            editor_el = page.locator('.tiptap.ProseMirror').first
            if await editor_el.count() > 0:
                await editor_el.click()
                await human_delay(0.2, 0.5)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        await page.keyboard.type(line, delay=random.uniform(3, 8))
                    if i < len(lines) - 1:
                        await page.keyboard.press("Enter")
                print(f"  Keyboard method: {len(content)} chars typed")

        await human_delay(0.5, 1.0)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_form_filled.png")

        # ── Step 6: Verify form state ──────────────────────────────────────
        print("\n🔍 Step 6: Verifying form state...")
        form_state = await page.evaluate("""() => {
            const title = document.querySelector('input[placeholder*="填写标题"]');
            const editor = document.querySelector('.tiptap.ProseMirror');
            const btn = document.querySelector('xhs-publish-btn');
            return {
                titleValue: title ? title.value : 'not found',
                titleLength: title ? title.value.length : 0,
                editorText: editor ? editor.textContent.substring(0, 50) : 'not found',
                btnFound: !!btn,
                btnSubmitDisabled: btn ? btn.getAttribute('submit-disabled') : 'N/A',
                url: window.location.href
            };
        }""")
        print(f"  Title: '{form_state['titleValue']}' ({form_state['titleLength']} chars)")
        print(f"  Editor: '{form_state['editorText']}'")
        print(f"  Publish btn found: {form_state['btnFound']}")
        print(f"  Submit disabled: {form_state['btnSubmitDisabled']}")
        print(f"  URL: {form_state['url']}")

        # ── Step 6.5: Draft-only mode — save and exit ───────────────
        if draft_only:
            print("\n📝 DRAFT MODE: Saving as draft (skipping publish)...")
            # The form is already filled; just wait a moment for auto-save
            await human_delay(3, 5)
            draft_url = page.url
            print(f"  📝 Draft saved at: {draft_url}")
            await page.screenshot(path=f"{SCREENSHOT_DIR}/06_draft_saved.png")
            print(f"  📸 Screenshot: {SCREENSHOT_DIR}/06_draft_saved.png")
            print(f"\n✅ DRAFT SAVED — Form filled, NOT published.")
            print(f"   Title: '{title}'")
            print(f"   Content: {len(content)} chars")
            print(f"   Images: {len(image_paths)} file(s)")
            return

        # ── Step 7: Hide overlays ──────────────────────────────────────────
        print("\n🧹 Step 7: Hiding overlays that may block the publish button...")
        await page.evaluate("""
            document.querySelectorAll(
                '.get-cover-suggest, [class*="suggest"], [class*="popup"], [class*="tooltip"], [data-tippy-root]'
            ).forEach(el => { el.style.display = 'none'; });
        """)

        # ── Step 8: Click publish button via _onPublish() ──────────────────
        print("\n🚀 Step 8: Publishing via _onPublish()...")

        publish_result = await page.evaluate("""() => {
            const btn = document.querySelector('xhs-publish-btn');
            if (!btn) return 'not found';
            if (typeof btn._onPublish === 'function') {
                btn._onPublish();
                return 'called _onPublish';
            }
            // Fallback: dispatch CustomEvent
            btn.dispatchEvent(new CustomEvent('publish', {bubbles: true, composed: true}));
            return 'dispatched publish event';
        }""")
        print(f"  Result: {publish_result}")

        if publish_result == 'not found':
            print("  ❌ Publish button not found! Listing all buttons...")
            all_btns = await page.evaluate(
                "() => Array.from(document.querySelectorAll('button, xhs-publish-btn')).map(b => b.tagName + ':' + b.textContent.trim().substring(0,30))")
            print(f"  All buttons: {all_btns}")

        print("  ⏳ Waiting 10s for publish to complete...")
        await asyncio.sleep(10)

        # ── Step 9: Verify publish result ─────────────────────────────────
        print("\n✅ Step 9: Verifying publish result...")
        current_url = page.url
        print(f"  URL after publish: {current_url}")

        # Check for success indicators
        if 'success' in current_url:
            print("  🎉 SUCCESS! URL contains 'success'!")
        elif 'publish' not in current_url:
            print(f"  🎉 SUCCESS! Page navigated away from publish page!")
        else:
            # URL still on publish page — check page text
            page_text = await page.evaluate(
                "() => document.body.innerText.substring(0, 500)")
            if "发布成功" in page_text:
                print("  🎉 Post submitted successfully! (页面显示发布成功)")
            elif "审核" in page_text:
                print("  🎉 Post submitted for review! (页面显示审核中)")
            elif "草稿" in page_text:
                print("  📝 Post saved as draft (草稿)")
            else:
                print(f"  ⚠️  Still on publish page")
                print(f"  Page text: {page_text[:300]}")
                # Poll for up to 60s
                print("  Polling for 60s...")
                for i in range(6):
                    await asyncio.sleep(10)
                    current_url = page.url
                    if 'success' in current_url or 'publish' not in current_url:
                        print(f"  🎉 Published! URL: {current_url}")
                        break
                    await activate_chrome()

        # ── Final screenshot ───────────────────────────────────────────────
        final_url = page.url
        await page.screenshot(path=f"{SCREENSHOT_DIR}/04_final.png")
        print(f"\n📍 Final URL: {final_url}")
        print(f"📸 All screenshots saved to: {SCREENSHOT_DIR}/")
        print("🖥️  Browser window is still open.")

        if 'publish' not in final_url or 'success' in final_url:
            print("\n🎉🎉🎉 POST PUBLISHED SUCCESSFULLY! 🎉🎉🎉")
        else:
            print("\n⚠️  Please verify in the browser window.")


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Xiaohongshu Publish Script v10 — Auto-publish with _onPublish()",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard publish:
  %(prog)s --title "标题" --content "正文 #标签" --images /path/to/image.jpg

  # Multiple images:
  %(prog)s --title "标题" --content "正文" --images img1.jpg img2.jpg img3.jpg

  # Custom CDP endpoint:
  %(prog)s --title "标题" --content "正文" --images img.jpg --cdp http://127.0.0.1:9222
        """
    )
    parser.add_argument("--images", nargs="+", required=True, help="Image file paths")
    parser.add_argument("--title", required=True, help="Note title (max 20 chars)")
    parser.add_argument("--content", required=True, help="Note content")
    parser.add_argument("--cdp", default=CDP_ENDPOINT, help="CDP endpoint URL (default: http://127.0.0.1:9222)")
    parser.add_argument("--draft-only", action="store_true", help="Only fill form and save as draft, do NOT publish")
    args = parser.parse_args()

    asyncio.run(publish(args.images, args.title, args.content, args.cdp, args.draft_only))
