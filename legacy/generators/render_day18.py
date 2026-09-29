"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ render_day18.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""Render Day 18 HTML cards to JPEG using Playwright."""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
DAY_DIR = os.path.join(BASE, "day_20260722_day18")
IMG_DIR = os.path.join(DAY_DIR, "images")

async def render_card(html_path, jpg_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,  # Retina quality
        )
        await page.goto(f"file://{html_path}", wait_until="networkidle")
        await page.wait_for_timeout(2000)  # Let fonts load
        await page.screenshot(path=jpg_path, full_page=False, type="jpeg", quality=95)
        await browser.close()

async def main():
    print("Rendering 6 cards with Playwright...")
    for i in range(1, 7):
        html_path = os.path.join(IMG_DIR, f"card_{i}.html")
        jpg_path = os.path.join(IMG_DIR, f"card_{i}.jpg")
        if not os.path.exists(html_path):
            print(f"  ✗ card_{i}.html not found, skipping")
            continue
        print(f"  Rendering card_{i}...")
        try:
            await render_card(html_path, jpg_path)
            size = os.path.getsize(jpg_path)
            print(f"    ✓ card_{i}.jpg ({size/1024:.0f} KB)")
        except Exception as e:
            print(f"    ✗ Error: {e}")

    # Update manifest
    manifest_path = os.path.join(DAY_DIR, "manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    manifest["images_rendered"] = True
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n✓ All done! Manifest updated at {manifest_path}")

if __name__ == "__main__":
    asyncio.run(main())
