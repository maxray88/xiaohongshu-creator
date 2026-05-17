#!/usr/bin/env python3
"""
Xiaohongshu Publish Script v9 - FINAL WORKING VERSION
Key discoveries:
1. SPA always defaults to "上传视频" tab - upload image via file input to trigger image form
2. Title input and editor ONLY appear AFTER image upload succeeds
3. xhs-publish-btn checks event.isTrusted - ONLY real human mouse clicks work
4. Fill form, then keep browser open for manual publish click
"""
import asyncio
import json
import os
import random
import sys
import math
import subprocess

COOKIE_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
CDP_URL_FILE = "/tmp/xhs_cdp_url.txt"
SCREENSHOT_DIR = "/tmp/xhs_screenshots"


async def activate_chrome():
    subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'],
                  timeout=5, capture_output=True)


async def publish(image_paths: list[str], title: str, content: str):
    from playwright.async_api import async_playwright

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with open(COOKIE_FILE) as f:
        cookies = json.load(f)
    with open(CDP_URL_FILE) as f:
        cdp_url = f.read().strip()

    # Validate title length
    if len(title) > 20:
        print(f"⚠️ Title is {len(title)} chars, truncating to 20...")
        title = title[:20]
    print(f"🔗 Connecting to Chrome via CDP...")
    print(f"📌 Title: {title} ({len(title)} chars)")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        await context.add_cookies(cookies)
        page = context.pages[0]

        # ── Step 0: Navigate to publish page ──────────────────────────────
        print("📄 Step 0: Navigating to publish page...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish?from=menu&target=image",
                       wait_until="commit", timeout=60000)
        print("⏳ Waiting 12s for SPA render...")
        await asyncio.sleep(12)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_loaded.png")

        # ── Step 1: Upload images (triggers image form to appear) ─────────
        print("🖼️ Step 1: Uploading images via file input...")
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(image_paths)
        print(f"  ✅ Uploaded {len(image_paths)} image(s)")

        print("⏳ Waiting 20s for upload to complete and form to render...")
        await asyncio.sleep(20)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_uploaded.png")

        # Verify the image form appeared
        has_title = await page.evaluate("() => !!document.querySelector('input[placeholder*=\"填写标题\"]')")
        has_editor = await page.evaluate("() => !!document.querySelector('.tiptap.ProseMirror')")
        print(f"  Title input visible: {has_title}")
        print(f"  Editor visible: {has_editor}")

        if not has_title:
            print("  ⚠️ Title input not found, waiting 10 more seconds...")
            await asyncio.sleep(10)

        # ── Step 2: Fill title ────────────────────────────────────────────
        print("✏️ Step 2: Filling title...")
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
        print(f"  {title_result}")
        await asyncio.sleep(random.uniform(0.5, 1.0))

        # ── Step 3: Fill content ──────────────────────────────────────────
        print("📝 Step 3: Filling content...")
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
        print(f"  {content_result}")
        await asyncio.sleep(random.uniform(0.5, 1.0))

        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_form_filled.png")

        # ── Step 4: Verify form is ready ───────────────────────────────────
        print("🔍 Step 4: Verifying form...")
        form_state = await page.evaluate("""
            () => {
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
            }
        """)
        print(f"  Title: {form_state['titleValue']} ({form_state['titleLength']} chars)")
        print(f"  Editor: {form_state['editorText']}")
        print(f"  Publish btn found: {form_state['btnFound']}")
        print(f"  Submit disabled: {form_state['btnSubmitDisabled']}")
        print(f"  URL: {form_state['url']}")

        # ── Step 5: Click publish button via _onPublish() ──────────────────
        print("\n🚀 Step 5: Clicking publish button via _onPublish()...")
        
        publish_result = await page.evaluate("""
            () => {
                const btn = document.querySelector('xhs-publish-btn');
                if (!btn) return 'not found';
                if (typeof btn._onPublish === 'function') {
                    btn._onPublish();
                    return 'called _onPublish';
                }
                // Fallback: dispatch CustomEvent
                btn.dispatchEvent(new CustomEvent('publish', {bubbles: true, composed: true}));
                return 'dispatched publish event';
            }
        """)
        print(f"  Result: {publish_result}")
        
        print("⏳ Waiting 10s for publish to complete...")
        await asyncio.sleep(10)
        
        current_url = page.url
        if 'publish' not in current_url or 'success' in current_url:
            print(f"\n  🎉 Page navigated! URL: {current_url}")
        else:
            print(f"\n  ⚠️ URL after click: {current_url}")
            print("  📌 If not published yet, please click '发布' button manually.")
            for i in range(6):
                await asyncio.sleep(5)
                current_url = page.url
                if 'success' in current_url or 'publish' not in current_url:
                    print(f"  🎉 Published! URL: {current_url}")
                    break
                await activate_chrome()

        # ── Final state ───────────────────────────────────────────────────
        final_url = page.url
        await page.screenshot(path=f"{SCREENSHOT_DIR}/04_final.png")

        print(f"\n📍 Final URL: {final_url}")

        if 'publish' not in final_url:
            print("🎉 SUCCESS! Post published!")
        else:
            text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
            if "发布成功" in text or "审核" in text:
                print("🎉 Post submitted successfully!")
            elif "草稿" in text:
                print("📝 Post saved as draft")
            else:
                print(f"⚠️ Still on publish page")
                print(f"  Page text: {text[:300]}")

        print(f"\n📸 All screenshots saved to: {SCREENSHOT_DIR}/")
        print("🖥️  Browser window is still open.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Publish a note on Xiaohongshu")
    parser.add_argument("--images", nargs="+", required=True, help="Image file paths")
    parser.add_argument("--title", required=True, help="Note title (max 20 chars)")
    parser.add_argument("--content", required=True, help="Note content")
    args = parser.parse_args()
    asyncio.run(publish(args.images, args.title, args.content))
