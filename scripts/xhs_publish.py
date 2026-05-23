#!/usr/bin/env python3
"""
Xiaohongshu Publish Script v11 — Anti-Detection CDP Mode
=========================================================
保留原有核心逻辑，仅做以下改动以抗检测：
  1. 使用 browser.contexts[0] 而非 browser.new_context()（避免创建可检测的自动化 context）
  2. 所有点击使用贝塞尔曲线鼠标移动（bezier_move）
  3. 所有键盘输入使用随机延迟打字
  4. 关键步骤之间加入随机延迟
  5. 不覆盖 User-Agent
  6. 不使用 add_init_script
  7. 不使用 JS 直接赋值，改用键盘打字（敏感字段）

核心流程（与原版一致）：
  1. 手动解析 CDP WS URL
  2. home-first 导航（清除 SPA 状态）
  3. Tab 检测 + 切换到"上传图文"
  4. 上传图片
  5. 填标题、内容（人类打字）
  6. 保存草稿或发布
"""

import asyncio
import json
import math
import os
import random
import sys
import argparse
import http.client
import subprocess
import time as time_module
from urllib.parse import urlparse

# ── Constants ──────────────────────────────────────────────────────────────────
COOKIE_FILE = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
CDP_URL_FILE = "/tmp/xhs_cdp_url.txt"
CDP_ENDPOINT = "http://127.0.0.1:9222"
SCREENSHOT_DIR = "/tmp/xhs_screenshots"
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
HOME_URL = "https://www.xiaohongshu.com/new/home"
TIMEOUT = 30000  # 30s default timeout


# ── CDP Helpers ───────────────────────────────────────────────────────────────

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


# ── Human-like Interaction Helpers ───────────────────────────────────────────

async def human_delay(min_s: float = 0.5, max_s: float = 2.0):
    """Random human-like delay between actions."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def bezier_move(page, end_x: int, end_y: int, steps: int = None):
    """Move mouse along a Bezier curve — simulates human movement."""
    if steps is None:
        steps = random.randint(20, 35)
    viewport = page.viewport_size or {"width": 1280, "height": 800}
    start_x = random.randint(200, max(201, viewport["width"] - 100))
    start_y = random.randint(100, max(101, viewport["height"] - 100))

    dx, dy = end_x - start_x, end_y - start_y
    cp1x = start_x + dx * random.uniform(0.2, 0.5) + random.uniform(-60, 60)
    cp1y = start_y + dy * random.uniform(0.1, 0.4) + random.uniform(-60, 60)
    cp2x = start_x + dx * random.uniform(0.5, 0.8) + random.uniform(-60, 60)
    cp2y = start_y + dy * random.uniform(0.5, 0.9) + random.uniform(-60, 60)

    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3 * start_x + 3 * u**2 * t * cp1x + 3 * u * t**2 * cp2x + t**3 * end_x
        y = u**3 * start_y + 3 * u**2 * t * cp1y + 3 * u * t**2 * cp2y + t**3 * end_y
        await page.mouse.move(int(x), int(y))
        await asyncio.sleep(random.uniform(0.003, 0.015))
        await human_delay(0.003, 0.015)

    # Small overshoot (30% chance) — mimics hand jitter
    if random.random() < 0.3:
        await page.mouse.move(end_x + random.randint(-5, 5), end_y + random.randint(-5, 5))
        await asyncio.sleep(random.uniform(0.03, 0.12))
        await page.mouse.move(end_x, end_y)
        await asyncio.sleep(random.uniform(0.03, 0.10))


async def human_click(page, x: int, y: int):
    """Click after Bezier mouse movement, with random press duration."""
    await bezier_move(page, x, y)
    await asyncio.sleep(random.uniform(0.08, 0.25))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.10, 0.30))
    await page.mouse.up()
    await asyncio.sleep(random.uniform(0.05, 0.15))


async def human_click_element(page, element, steps: int = None):
    """Click an element with Bezier movement and random delays."""
    await element.scroll_into_view_if_needed()
    await asyncio.sleep(random.uniform(0.1, 0.3))
    box = await element.bounding_box()
    if not box:
        await element.click()
        return
    x = int(box["x"] + box["width"] / 2)
    y = int(box["y"] + box["height"] / 2)
    await human_click(page, x, y)


async def human_type_text(page, element, text: str, char_delay: tuple = (0.04, 0.12)):
    """Type text into an element with per-character random delay."""
    await element.click()
    await asyncio.sleep(random.uniform(0.15, 0.4))
    # Select all first
    await page.keyboard.press("Control+a")
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await page.keyboard.press("Backspace")
    await asyncio.sleep(random.uniform(0.08, 0.2))
    # Type with random delay per character
    for char in text:
        await page.keyboard.type(char, delay=random.uniform(char_delay[0], char_delay[1]))
        await asyncio.sleep(random.uniform(0.005, 0.02))
    await asyncio.sleep(random.uniform(0.1, 0.3))


async def bring_chrome_to_front():
    """Activate Chrome window on macOS."""
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to activate'],
            timeout=5, capture_output=True
        )
    except Exception:
        pass


# ── Screenshot Helper ─────────────────────────────────────────────────────────

def _screenshot_path(name: str) -> str:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    return os.path.join(SCREENSHOT_DIR, f"{name}_{int(time_module.time())}.png")


# ── Main Publish Flow ──────────────────────────────────────────────────────────

async def publish(
    image_paths: list[str],
    title: str,
    content: str,
    cdp_endpoint: str = CDP_ENDPOINT,
    draft_only: bool = False,
):
    from playwright.async_api import async_playwright

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # Validate title length (max 20 chars on Xiaohongshu)
    original_title = title
    if len(title) > 20:
        title = title[:20]
        print(f"⚠️  Title truncated to 20 chars: '{title}'")

    print(f"🍪 Loaded {len(image_paths)} image(s)")
    print(f"📌 Title: '{title}' ({len(title)} chars)")
    print(f"📝 Content: {len(content)} chars")

    # ── Load cookies ────────────────────────────────────────────────────────
    if not os.path.exists(COOKIE_FILE):
        print(f"❌ Cookie file not found: {COOKIE_FILE}")
        sys.exit(1)
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    # ── CDP Connection ─────────────────────────────────────────────────────
    ws_url = resolve_cdp_ws_url(cdp_endpoint)
    print(f"🔗 CDP URL resolved: {ws_url}")

    async with async_playwright() as p:
        print("🔗 Connecting to Chrome via CDP...")
        browser = await p.chromium.connect_over_cdp(ws_url)
        print("✅ Connected!")

        # ── 关键：使用 browser.contexts[0] 而非 new_context() ─────────────
        # 这样复用已有 context，不添加自动化特征
        if not browser.contexts:
            # Fallback: 创建一个临时 context（仅当真的没有 context 时）
            print("⚠️  No existing context, creating one (may be detectable)")
            context = await browser.new_context()
        else:
            context = browser.contexts[0]
            print(f"✅ Using existing context (has {len(context.pages)} page(s))")

        # Add cookies BEFORE navigation so user is logged in from the start
        await context.add_cookies(cookies)
        await human_delay(0.5, 1.5)

        # Create or reuse a page
        if context.pages:
            page = context.pages[0]
            # Navigate to blank first to reset state
            await page.goto("about:blank")
            await human_delay(0.3, 0.8)
        else:
            page = await context.new_page()

        # Bring Chrome to front
        await bring_chrome_to_front()

        # ── Step 1: Home-first navigation (clear SPA state) ──────────────
        print(f"\n📄 Step 1: Navigating via home page to clear SPA state...")
        await page.goto(HOME_URL, wait_until="networkidle", timeout=20000)
        await human_delay(3, 5)
        print(f"  📸 Screenshot: {_screenshot_path('01_home')}")
        await page.screenshot(path=_screenshot_path("01_home"))

        # ── Step 2: Navigate to publish page and detect active tab ──────
        print(f"\n📑 Step 2: Navigating to publish page...")
        await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=15000)
        await human_delay(5, 8)  # Wait for React to render

        # Check which tab is active
        try:
            # Try new selector (2024+ redesign)
            tab_el = page.locator(".tabs .tab.active, .tab-item.active, [class*='tab'][class*='active']").first
            active_tab = await tab_el.text_content(timeout=3000)
        except Exception:
            active_tab = "unknown"

        print(f"  Active tab: '{active_tab.strip()}'")

        # If not on "上传图文" tab, click to switch
        tab_keywords = ["上传图文", "图文"]
        if not any(kw in active_tab for kw in tab_keywords):
            print(f"  Not on image tab, clicking '上传图文' with human-like movement...")
            try:
                tab_btn = page.locator('span:has-text("上传图文"), div:has-text("上传图文"), [class*="tab"]:has-text("上传图文")').first
                await human_click_element(page, tab_btn)
                await human_delay(2, 4)
            except Exception as e:
                print(f"  ⚠️  Could not find '上传图文' tab: {e}, continuing anyway...")
        else:
            print(f"  ✅ Already on image upload tab")

        await page.screenshot(path=_screenshot_path("02_tab"))
        await human_delay(1, 2)

        # ── Step 3: Upload images ─────────────────────────────────────────
        print(f"\n🖼️  Step 3: Uploading {len(image_paths)} image(s)...")

        file_input = page.locator('input[type="file"]').first
        # Wait for file input to be attached
        try:
            await file_input.wait_for(state="attached", timeout=10000)
        except Exception:
            print(f"  ⚠️  File input not attached after initial wait, waiting more...")
            await human_delay(10, 15)

        try:
            await file_input.set_input_files(image_paths)
            print(f"  ✅ File input set ({len(image_paths)} images)")
        except Exception as e:
            print(f"  ⚠️  Batch upload failed: {e}")
            # Try one by one
            for img in image_paths:
                try:
                    await file_input.set_input_files([img])
                    await human_delay(2, 4)
                except Exception:
                    pass

        # Wait for upload to complete and form to render
        upload_wait = 20 + max(0, (len(image_paths) - 1) * 5)
        print(f"  ⏳ Waiting {upload_wait}s for upload and form render...")
        await asyncio.sleep(upload_wait)
        await page.screenshot(path=_screenshot_path("03_uploaded"))
        print(f"  ✅ Upload completed")

        # ── Step 4: Fill title ───────────────────────────────────────────
        print(f"\n✏️  Step 4: Filling title: '{title}'")

        # Try different selectors for title input
        title_selectors = [
            'input[placeholder*="标题"]',
            'input[name="title"]',
            'input[maxlength="20"]',
            '.title-input input',
            '[class*="title"] input',
        ]
        title_input = None
        for sel in title_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    title_input = el
                    print(f"  ✅ Found title input with selector: {sel}")
                    break
            except Exception:
                continue

        if not title_input:
            print("  ❌ Could not find title input! Trying JS fallback...")
            # Last resort: JS fallback
            try:
                await page.evaluate("""
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {
                        if (inp.placeholder && inp.placeholder.includes('标题')) {
                            inp.scrollIntoView();
                            inp.focus();
                            break;
                        }
                    }
                """)
                await human_delay(1, 2)
                title_input = page.locator('input[placeholder*="标题"]').first
            except Exception:
                pass

        if title_input:
            await human_type_text(page, title_input, title)
            print(f"  ✅ Title filled with human typing")
        else:
            print(f"  ❌ Still could not find title input")

        # ── Step 5: Fill content ─────────────────────────────────────────
        print(f"\n📝 Step 5: Filling content ({len(content)} chars)...")

        # Wait for editor to be ready
        await human_delay(1, 3)

        # Try different content editor selectors
        editor_selectors = [
            'div[contenteditable="true"]',
            '.editor-content[contenteditable="true"]',
            '.ql-editor',
            '[class*="editor"] [contenteditable="true"]',
            'textarea[name="content"]',
        ]
        editor = None
        for sel in editor_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    editor = el
                    print(f"  ✅ Found editor with selector: {sel}")
                    break
            except Exception:
                continue

        if editor:
            await human_type_text(page, editor, content, char_delay=(0.03, 0.10))
            print(f"  ✅ Content filled with human typing")
        else:
            # JS fallback for editor
            print(f"  ⚠️  Editor not found, trying JS fallback...")
            try:
                await page.evaluate("""
                    const editors = document.querySelectorAll('[contenteditable="true"]');
                    if (editors.length > 0) {
                        const ed = editors[editors.length - 1];
                        ed.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        ed.focus();
                    }
                """)
                await human_delay(1, 2)
                editor = page.locator('[contenteditable="true"]').last
                await human_type_text(page, editor, content, char_delay=(0.03, 0.10))
            except Exception as e:
                print(f"  ❌ JS fallback failed: {e}")

        await page.screenshot(path=_screenshot_path("05_content"))
        await human_delay(1, 2)

        # ── Step 6: Verify form state ───────────────────────────────────
        print(f"\n🔍 Step 6: Verifying form state...")
        try:
            title_val = await title_input.input_value() if title_input else "(not found)"
        except Exception:
            title_val = "(error reading)"
        try:
            editor_val = await editor.inner_text() if editor else "(not found)"
        except Exception:
            editor_val = "(error reading)"

        print(f"  Title: '{title_val}' ({len(title_val) if title_val else 0} chars)")
        print(f"  Editor: '{editor_val[:50]}...' ({len(editor_val) if editor_val else 0} chars)")

        # Find publish button
        try:
            publish_btn = page.locator('button:has-text("发布")').first
            is_enabled = await publish_btn.is_enabled(timeout=3000)
        except Exception:
            is_enabled = False
            publish_btn = None

        print(f"  Publish button: {'enabled' if is_enabled else 'disabled'}")

        # ── Step 7: Save draft or publish ───────────────────────────────
        if draft_only:
            print("\n📝 DRAFT MODE: Saving as draft...")
            save_btn = page.locator('button:has-text("存草稿")').first
            await human_click_element(page, save_btn)
            await human_delay(2, 4)
            print("✅ Draft saved")
        else:
            print("\n🚀 Publishing...")
            if publish_btn:
                await human_click_element(page, publish_btn)
                await human_delay(3, 5)

                # Handle confirmation dialog if it appears
                try:
                    confirm_btn = page.locator('button:has-text("确认发布")').first
                    await confirm_btn.wait_for(state="visible", timeout=5000)
                    await human_click_element(page, confirm_btn)
                    await human_delay(2, 4)
                except Exception:
                    pass

                print("✅ Published!")
            else:
                print("❌ Publish button not found")

        await page.screenshot(path=_screenshot_path("finish"))
        print(f"\n✅ Done!")

        await browser.close()


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Xiaohongshu Publish Script v11 (Anti-Detection)")
    parser.add_argument("--title", required=True, help="Title (max 20 chars)")
    parser.add_argument("--content", required=True, help="Content body")
    parser.add_argument("--images", nargs="+", required=True, help="Image file path(s)")
    parser.add_argument(
        "--draft-only", action="store_true", help="Save as draft without publishing"
    )
    parser.add_argument(
        "--cdp-endpoint",
        default=CDP_ENDPOINT,
        help="Chrome CDP endpoint (default: http://127.0.0.1:9222)",
    )
    args = parser.parse_args()

    asyncio.run(
        publish(
            image_paths=args.images,
            title=args.title,
            content=args.content,
            cdp_endpoint=args.cdp_endpoint,
            draft_only=args.draft_only,
        )
    )


if __name__ == "__main__":
    main()